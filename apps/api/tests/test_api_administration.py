"""Test administrasi pengguna dan peran (TASK 143).

Yang dijaga di sini bukan "layar administrasi dapat menyimpan", melainkan empat
penolakan yang menjadi alasan layar itu boleh ada sama sekali:

1. Password tidak dapat melewati jalur pengelolaan data — dan bila dikirim, **ditolak**,
   bukan diabaikan diam-diam. Diabaikan diam-diam berarti seorang admin yakin telah
   mengganti kredensial padahal tidak.
2. Tidak ada yang dapat mengubah perannya sendiri. Tanpa ini, satu akun Administrator
   dapat mengangkat dirinya menjadi pejabat yang menyetujui rekomendasinya sendiri, dan
   `test_rbac_separation_of_duties.py` berhenti berarti apa pun pada tingkat data.
3. Pemegang `commander_decision:approve` terakhir tidak dapat dipindahkan. Tanpa
   pemegangnya, rekomendasi tidak pernah menjadi tindakan (CLAUDE.md §13).
4. Peran ber-cakupan wajib punya atributnya, sebab akun tanpa atribut itu ditolak
   403 oleh setiap endpoint ber-cakupan dan tampak seperti sistem yang rusak.

Seluruhnya dijalankan di dalam transaksi yang dibatalkan, sehingga basis data demo
tetap utuh — termasuk satu-satunya akun Pimpinan yang dipakai menguji aturan ketiga.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers.administration import (
    APPROVAL_ACTION,
    APPROVAL_RESOURCE,
    CREDENTIAL_FIELDS,
)
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Permission, Role, RolePermission, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _role(session: Session, role_name: str) -> Role:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, f"role {role_name} belum ada — jalankan seed"
    return role


def _make_user(
    session: Session,
    role_name: str,
    *,
    polsek: str | None = None,
    function: str | None = None,
    locked: bool = False,
) -> User:
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        # Akun terkunci memakai penanda '!' yang sama dengan seed, sehingga status
        # kredensial yang diuji adalah keadaan yang benar-benar dipakai sistem.
        password_hash="!" if locked else hash_password(PASSWORD),
        role_id=_role(session, role_name).role_id,
        polsek=polsek,
        function=function,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    return user


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _sole_approver(session: Session) -> User:
    """Akun aktif satu-satunya yang memegang `commander_decision:approve`.

    Dicari lewat permission yang benar-benar dipegangnya, bukan lewat nama peran —
    sama seperti yang dilakukan endpoint. Test ini menuntut memang hanya ada satu:
    bila kelak ditambah akun Pimpinan kedua, aturan yang diuji tidak lagi berlaku dan
    test harus disesuaikan, bukan lolos diam-diam.
    """
    approvers = list(
        session.scalars(
            select(User)
            .join(RolePermission, RolePermission.role_id == User.role_id)
            .join(Permission, Permission.permission_id == RolePermission.permission_id)
            .where(Permission.resource == APPROVAL_RESOURCE)
            .where(Permission.action == APPROVAL_ACTION)
            .where(User.status == "ACTIVE")
        ).all()
    )
    assert len(approvers) == 1, f"data demo diharapkan punya satu penyetuju, ada {len(approvers)}"
    return approvers[0]


def _audits(session: Session, code: str) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.action == "UPDATE_USER")
            .where(AuditLog.resource_id == code)
            .order_by(AuditLog.timestamp)
        ).all()
    )


# ---------------------------------------------------------------------------
# Pembacaan
# ---------------------------------------------------------------------------


def test_user_list_never_returns_password_material(client: TestClient, session: Session) -> None:
    """Yang dikembalikan hanya kesimpulannya, bukan hash-nya."""
    admin = _make_user(session, "Administrator")
    locked = _make_user(session, "Administrator", locked=True)

    response = client.get("/api/v1/users", headers=_auth(client, admin))

    assert response.status_code == 200, response.text
    body = response.json()
    rows = {row["code"]: row for row in body["data"]}

    assert locked.code in rows
    assert rows[locked.code]["credential_locked"] is True
    assert rows[admin.code]["credential_locked"] is False

    # Tidak satu pun bidang boleh membawa materi kredensial, pada baris mana pun.
    # `must_change_password` sengaja tidak ikut diperiksa di sini: ia penanda, bukan
    # rahasia — yang dilarang adalah materi passwordnya sendiri. Pada arah tulis ia
    # tetap ditolak (lihat CREDENTIAL_FIELDS), sebab mengabaikannya diam-diam membuat
    # admin mengira ia sudah memaksa penggantian password.
    assert "password_hash" not in response.text
    for row in body["data"]:
        assert not any(field in row for field in ("password", "new_password", "password_hash"))


def test_user_list_carries_the_reason_password_is_absent(
    client: TestClient, session: Session
) -> None:
    """Layar tidak boleh mengarang alasan sendiri; alasannya datang dari backend."""
    admin = _make_user(session, "Administrator")

    body = client.get("/api/v1/users", headers=_auth(client, admin)).json()

    assert "user:password" in body["credential_basis"]
    assert "prod:password" in body["credential_basis"]
    assert body["editable_fields"] == ["role_code", "polsek", "function", "status"]
    # Pilihan penugasan berasal dari data dan konfigurasi, bukan diketik ulang di layar.
    assert "Polsek Tebet" in body["polsek_options"]
    assert {"value": "RESKRIM", "label": "Reskrim"} in body["function_options"]


def test_role_list_reports_holders_and_is_not_editable(
    client: TestClient, session: Session
) -> None:
    admin = _make_user(session, "Administrator")

    body = client.get("/api/v1/roles", headers=_auth(client, admin)).json()
    roles = {row["role_name"]: row for row in body["data"]}

    assert body["editable"] is False
    assert "permissions.yaml" in body["source_basis"]

    assert roles["Pimpinan"]["can_approve"] is True
    assert roles["Administrator"]["can_approve"] is False
    assert roles["Administrator"]["user_count"] >= 4  # tiga akun demo + akun uji
    assert roles["Polsek"]["scopes"]["OWN_JURISDICTION"] > 0
    assert roles["Fungsi"]["scopes"]["OWN_FUNCTION"] > 0
    assert roles["Administrator"]["permission_count"] == len(roles["Administrator"]["permissions"])


def test_reading_users_requires_permission(client: TestClient, session: Session) -> None:
    """Peran Pimpinan tidak memegang `user:read` — dan penolakannya tercatat."""
    pimpinan = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/users", headers=_auth(client, pimpinan))

    assert response.status_code == 403
    denied = session.scalars(
        select(AuditLog)
        .where(AuditLog.action == "READ_USER")
        .where(AuditLog.user_id == pimpinan.user_id)
    ).all()
    assert len(denied) == 1
    assert denied[0].result == "DENIED"


def test_managing_users_requires_permission(client: TestClient, session: Session) -> None:
    pimpinan = _make_user(session, "Pimpinan")
    target = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"status": "INACTIVE"},
        headers=_auth(client, pimpinan),
    )

    assert response.status_code == 403
    session.expire(target)
    assert target.status == "ACTIVE"


# ---------------------------------------------------------------------------
# Empat penolakan
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", CREDENTIAL_FIELDS)
def test_credentials_are_refused_not_ignored(
    client: TestClient, session: Session, field: str
) -> None:
    """Ditolak 400 beserta jalur yang benar — bukan diterima lalu diabaikan."""
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")
    before = target.password_hash

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"status": "INACTIVE", field: "PasswordBaru#2026"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 400, response.text
    message = response.json()["error"]["message"]
    assert field in message
    assert "user:password" in message

    # Tidak satu pun bagian permintaan boleh berlaku: perubahan status pun batal.
    session.expire(target)
    assert target.status == "ACTIVE"
    assert target.password_hash == before

    # Percobaannya tercatat — tetapi hanya nama bidangnya, tidak pernah nilainya.
    entries = _audits(session, target.code)
    assert [entry.result for entry in entries] == ["FAILED"]
    assert entries[0].detail == {"reason": f"bidang kredensial ditolak: {field}"}
    assert "PasswordBaru#2026" not in str([entry.detail for entry in entries])


def test_user_cannot_change_own_role(client: TestClient, session: Session) -> None:
    """Kewenangan memberi kewenangan tidak boleh dipakai atas diri sendiri."""
    admin = _make_user(session, "Administrator")
    pimpinan_role = _role(session, "Pimpinan")

    response = client.patch(
        f"/api/v1/users/{admin.code}",
        json={"role_code": pimpinan_role.code},
        headers=_auth(client, admin),
    )

    assert response.status_code == 409, response.text
    assert "sendiri" in response.json()["error"]["message"]

    session.expire(admin)
    assert admin.role_id != pimpinan_role.role_id

    # Percobaannya meninggalkan jejak — justru inilah yang paling perlu terlihat.
    entries = _audits(session, admin.code)
    assert [entry.result for entry in entries] == ["FAILED"]
    assert entries[0].detail == {"reason": "pengguna mengubah perannya sendiri"}


def test_user_may_still_change_own_jurisdiction(client: TestClient, session: Session) -> None:
    """Yang dilarang hanya peran; penugasan wilayah bukan pelebaran kewenangan."""
    admin = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{admin.code}",
        json={"polsek": "Polsek Tebet"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["polsek"] == "Polsek Tebet"


def test_last_approver_cannot_be_reassigned(client: TestClient, session: Session) -> None:
    """Tanpa pemegang `commander_decision:approve`, rantai human-in-the-loop mati."""
    admin = _make_user(session, "Administrator")
    approver = _sole_approver(session)

    response = client.patch(
        f"/api/v1/users/{approver.code}",
        json={"role_code": _role(session, "Administrator").code},
        headers=_auth(client, admin),
    )

    assert response.status_code == 409, response.text
    assert "commander_decision:approve" in response.json()["error"]["message"]

    session.expire(approver)
    assert approver.role.role_name == "Pimpinan"


def test_last_approver_cannot_be_deactivated_either(client: TestClient, session: Session) -> None:
    """Menonaktifkan akunnya menghabiskan pemegangnya sama saja dengan memindahkannya.

    `api/deps.py` menolak akun non-`ACTIVE`, jadi Pimpinan yang dinonaktifkan tidak
    dapat menyetujui apa pun. Aturannya diperiksa terhadap keadaan hasil, bukan
    terhadap satu bidang saja.
    """
    admin = _make_user(session, "Administrator")
    approver = _sole_approver(session)

    response = client.patch(
        f"/api/v1/users/{approver.code}",
        json={"status": "INACTIVE"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 409, response.text
    session.expire(approver)
    assert approver.status == "ACTIVE"


def test_approver_may_be_reassigned_once_a_replacement_exists(
    client: TestClient, session: Session
) -> None:
    """Aturannya diperiksa terhadap basis data, bukan terhadap daftar nama tetap.

    Begitu ada penyetuju kedua yang aktif, pemindahan yang tadinya ditolak menjadi sah.
    Tanpa test ini, aturan di atas sama saja dengan mengunci satu baris tertentu
    selamanya.
    """
    admin = _make_user(session, "Administrator")
    approver = _sole_approver(session)
    _make_user(session, "Pimpinan")  # pengganti

    response = client.patch(
        f"/api/v1/users/{approver.code}",
        json={"role_code": _role(session, "Administrator").code},
        headers=_auth(client, admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["role"] == "Administrator"


def test_scoped_role_requires_its_attribute(client: TestClient, session: Session) -> None:
    """Peran Polsek tanpa `polsek` akan ditolak setiap endpoint ber-cakupan."""
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"role_code": _role(session, "Polsek").code},
        headers=_auth(client, admin),
    )

    assert response.status_code == 400, response.text
    assert "polsek" in response.json()["error"]["message"]

    session.expire(target)
    assert target.role.role_name == "Administrator"


def test_scoped_function_role_requires_its_attribute(client: TestClient, session: Session) -> None:
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"role_code": _role(session, "Fungsi").code},
        headers=_auth(client, admin),
    )

    assert response.status_code == 400, response.text
    assert "function" in response.json()["error"]["message"]


def test_clearing_the_attribute_of_a_scoped_role_is_refused(
    client: TestClient, session: Session
) -> None:
    """Peran tetap, atributnya yang dicabut — hasilnya akun rusak yang sama."""
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Polsek", polsek="Polsek Tebet")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"polsek": None},
        headers=_auth(client, admin),
    )

    assert response.status_code == 400, response.text
    session.expire(target)
    assert target.polsek == "Polsek Tebet"


# ---------------------------------------------------------------------------
# Perpindahan yang sah
# ---------------------------------------------------------------------------


def test_assignment_is_moved_and_audited_with_before_and_after(
    client: TestClient, session: Session
) -> None:
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"role_code": _role(session, "Polsek").code, "polsek": "Polsek Tebet"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "Polsek"
    assert body["polsek"] == "Polsek Tebet"
    assert "password_hash" not in body

    entries = _audits(session, target.code)
    assert [entry.result for entry in entries] == ["SUCCESS"]
    detail = entries[0].detail
    assert detail is not None
    assert detail["before"]["role_code"] == _role(session, "Administrator").code
    assert detail["before"]["polsek"] is None
    assert detail["after"]["role_code"] == _role(session, "Polsek").code
    assert detail["after"]["polsek"] == "Polsek Tebet"
    # Yang tercatat hanya empat bidang penugasan — tidak ada kredensial, tidak ada
    # bidang tak dikenal yang terlanjur dikirim klien.
    assert set(detail) == {"before", "after"}
    assert set(detail["before"]) == {"role_code", "polsek", "function", "status"}
    assert entries[0].user_id == admin.user_id


def test_unknown_fields_are_dropped_and_never_audited(client: TestClient, session: Session) -> None:
    """Pengaman privasi yang sama dengan `data_entry.py`: bidang asing tidak ikut.

    Bidang bernuansa kredensial adalah pengecualiannya — itu ditolak, bukan diabaikan.
    """
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")

    response = client.patch(
        f"/api/v1/users/{target.code}",
        json={"status": "INACTIVE", "nama_lengkap_pemilik": "Budi Santoso", "nik": "31740…"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 200, response.text
    assert "Budi Santoso" not in response.text

    detail = _audits(session, target.code)[0].detail
    assert "Budi Santoso" not in str(detail)
    assert "nik" not in str(detail)


def test_empty_and_unchanged_requests_are_refused(client: TestClient, session: Session) -> None:
    """Permintaan tanpa perubahan tidak boleh menghasilkan audit palsu."""
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")

    assert (
        client.patch(
            f"/api/v1/users/{target.code}", json={}, headers=_auth(client, admin)
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/users/{target.code}",
            json={"status": "ACTIVE"},
            headers=_auth(client, admin),
        ).status_code
        == 400
    )
    assert _audits(session, target.code) == []


def test_unknown_values_are_refused(client: TestClient, session: Session) -> None:
    admin = _make_user(session, "Administrator")
    target = _make_user(session, "Administrator")
    headers = _auth(client, admin)

    for payload in (
        {"role_code": "ROLE-99"},
        {"status": "DITANGGUHKAN"},
        {"polsek": "Polsek Antah Berantah"},
        {"function": "SIBER"},
    ):
        response = client.patch(f"/api/v1/users/{target.code}", json=payload, headers=headers)
        assert response.status_code == 400, response.text


def test_unknown_user_is_not_found(client: TestClient, session: Session) -> None:
    admin = _make_user(session, "Administrator")

    response = client.patch(
        "/api/v1/users/USER-TIDAK-ADA",
        json={"status": "INACTIVE"},
        headers=_auth(client, admin),
    )

    assert response.status_code == 404
