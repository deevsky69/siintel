"""Test pintu masuk data: kejadian, laporan intelijen, dan triase laporan masyarakat.

Yang dijaga di sini bukan sekadar "endpoint menjawab 201". Tiga hal yang paling mudah
salah dan paling mahal akibatnya:

- **Cakupan wilayah pada penulisan.** Endpoint daftar sudah lama tersaring; penulisan
  belum pernah diuji sama sekali. Akun Polsek Tebet yang bisa menaruh kejadian di
  Kebayoran Baru akan merusak setiap angka yang dihitung per wilayah.
- **Kebocoran lewat kode status.** Lokasi di luar wilayah harus dijawab `404`, sama
  seperti lokasi yang memang tidak ada. `403` akan memberi tahu bahwa lokasinya ada.
- **Identitas orang.** Bidang seperti nama korban harus hilang tanpa jejak — termasuk
  dari detail audit, tempat data pribadi paling mudah menumpuk tanpa disadari.

Peran demo per 1 September 2026: Pimpinan, Administrator, Fungsi, Polsek.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    CitizenReport,
    CrimeIncident,
    Location,
    Permission,
    Role,
    RolePermission,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
TEBET = "Polsek Tebet"

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


def _make_user(
    session: Session, role_name: str, polsek: str | None = None, function: str | None = None
) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, f"role {role_name} belum ada — jalankan seed"

    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        polsek=polsek,
        function=function,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    return user


def _grant(session: Session, user: User, permission: str, scope: str = "ALL") -> None:
    """Memberikan satu permission kepada peran pengguna, di dalam transaksi test.

    Bersifat idempoten: bila peran itu sudah memegang permission-nya, tidak ada baris
    baru yang disisipkan. Tanpa itu, test akan pecah dengan `UniqueViolation` begitu
    permission yang sama diberikan sungguhan di `config/rbac/permissions.yaml` — dan
    pecahnya terjadi karena kewenangan **bertambah**, bukan karena perilaku berubah.

    Pemberian ini hidup di dalam transaksi yang dibatalkan setelah test, sehingga
    kewenangan sungguhan pada basis data demo **tidak** berubah. Mengubahnya di sana
    adalah keputusan kebijakan, bukan pekerjaan test (CLAUDE.md §2D).
    """
    resource, _, action = permission.partition(":")
    row = session.scalar(
        select(Permission).where(Permission.resource == resource).where(Permission.action == action)
    )
    assert row is not None, f"permission {permission} tidak ada di katalog"

    already = session.scalar(
        select(RolePermission)
        .where(RolePermission.role_id == user.role_id)
        .where(RolePermission.permission_id == row.permission_id)
    )
    if already is None:
        session.add(
            RolePermission(role_id=user.role_id, permission_id=row.permission_id, scope=scope)
        )
        session.flush()


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _location(session: Session, polsek: str | None = None) -> Location:
    query = select(Location)
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    location = session.scalar(query.limit(1))
    assert location is not None
    return location


def _location_outside(session: Session, polsek: str) -> Location:
    location = session.scalar(select(Location).where(Location.polsek != polsek).limit(1))
    assert location is not None
    return location


def _past_date() -> date:
    """Sehari sebelum waktu acuan aplikasi — bukan sebelum jam dinding.

    Jam acuan demo beku pada 31 Desember 2025 (SDL-16). Memakai `date.today()` akan
    membuat test ini gagal atau lulus karena tanggal mesin, bukan karena perilaku kode.
    """
    return clock.to_jakarta(clock.reference_now()).date() - timedelta(days=1)


def _future_date() -> date:
    return clock.to_jakarta(clock.reference_now()).date() + timedelta(days=1)


def _crime_payload(location: Location, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "incident_type": "CURANMOR",
        "incident_date": _past_date().isoformat(),
        "incident_time": "21:30",
        "location_code": location.code,
        "location_type": "Parkiran",
        "modus": "kunci_t",
        "target_type": "motor",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Kejadian kriminal
# ---------------------------------------------------------------------------


def test_crime_can_be_recorded_through_the_api(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")
    location = _location(session)

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(location),
        headers=_auth(client, officer),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"].startswith("INC-")
    # Status penanganan tidak diminta pada payload; nilai awalnya bukan tebakan layar.
    assert body["status"] == "REPORTED"
    assert body["polsek"] == location.polsek

    stored = session.scalar(select(CrimeIncident).where(CrimeIncident.code == body["code"]))
    assert stored is not None
    assert stored.location_id == location.location_id

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "CREATE_CRIME_INCIDENT")
        .where(AuditLog.resource_id == body["code"])
    )
    assert entry is not None
    assert entry.result == "SUCCESS"


def test_unknown_incident_type_is_refused_with_the_valid_list(
    client: TestClient, session: Session
) -> None:
    """Penolakan harus menuntun. Menyebut "tidak valid" tanpa daftar hanya menghentikan."""
    officer = _make_user(session, "Administrator")

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(_location(session), incident_type="PENCURIAN_HEWAN"),
        headers=_auth(client, officer),
    )

    assert response.status_code == 400
    message = response.json()["error"]["message"]
    assert "CURANMOR" in message
    # Taksonomi kini memuat sepuluh jenis, termasuk lima yang belum punya kejadian.
    for added in ("BEGAL", "PREMANISME", "NARKOBA", "UNJUK_RASA", "KERAMAIAN"):
        assert added in message


def test_a_future_incident_is_refused_against_the_reference_clock(
    client: TestClient, session: Session
) -> None:
    """Diukur terhadap waktu acuan aplikasi, bukan jam dinding (SDL-16)."""
    officer = _make_user(session, "Administrator")

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(_location(session), incident_date=_future_date().isoformat()),
        headers=_auth(client, officer),
    )

    assert response.status_code == 400
    assert "waktu acuan" in response.json()["error"]["message"].lower()


def test_person_identity_fields_are_dropped_and_never_audited(
    client: TestClient, session: Session
) -> None:
    """Spesifikasi §6.1: identitas korban/pelaku/saksi tidak diperlukan dan tidak disimpan.

    Yang diperiksa bukan hanya kolom tabel — `crime_incidents` memang tidak memilikinya —
    melainkan juga detail audit, tempat data pribadi paling mudah menumpuk tanpa
    disadari siapa pun.
    """
    officer = _make_user(session, "Administrator")

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(
            _location(session),
            nama_korban="Budi Santoso",
            victim_name="Budi Santoso",
            nik_pelaku="3174010101900001",
            saksi="Siti",
        ),
        headers=_auth(client, officer),
    )

    assert response.status_code == 201, response.text
    code = response.json()["code"]
    assert "korban" not in response.text.lower()

    entry = session.scalar(select(AuditLog).where(AuditLog.resource_id == code))
    assert entry is not None
    assert "Budi" not in str(entry.detail)
    assert "3174010101900001" not in str(entry.detail)


def test_leader_cannot_record_crimes(client: TestClient, session: Session) -> None:
    """Pimpinan membaca dan memutuskan; ia tidak memasukkan data kejadian."""
    leader = _make_user(session, "Pimpinan")

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(_location(session)),
        headers=_auth(client, leader),
    )

    assert response.status_code == 403
    denial = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == leader.user_id)
        .where(AuditLog.result == "DENIED")
    )
    assert denial is not None


def test_polsek_can_record_inside_its_own_jurisdiction(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Polsek", polsek=TEBET)
    location = _location(session, polsek=TEBET)

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(location),
        headers=_auth(client, officer),
    )

    assert response.status_code == 201, response.text
    assert response.json()["polsek"] == TEBET


def test_polsek_writing_outside_its_jurisdiction_gets_404_not_403(
    client: TestClient, session: Session
) -> None:
    """`404`, bukan `403`: membedakan keduanya membocorkan keberadaan lokasi itu.

    Percobaannya tetap tercatat — penolakan tanpa jejak membuat audit tidak dapat
    dipakai menilai kepatuhan RBAC.
    """
    officer = _make_user(session, "Polsek", polsek=TEBET)
    outside = _location_outside(session, TEBET)

    response = client.post(
        "/api/v1/crimes",
        json=_crime_payload(outside),
        headers=_auth(client, officer),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

    attempt = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == officer.user_id)
        .where(AuditLog.action == "CREATE_CRIME_INCIDENT")
        .where(AuditLog.result == "FAILED")
    )
    assert attempt is not None

    # Jawaban untuk lokasi yang benar-benar tidak ada harus sama persis.
    ghost = client.post(
        "/api/v1/crimes",
        json=_crime_payload(outside, location_code="LOC-TIDAK-ADA"),
        headers=_auth(client, officer),
    )
    assert ghost.status_code == 404
    assert ghost.json()["error"]["message"] == response.json()["error"]["message"]


# ---------------------------------------------------------------------------
# Laporan intelijen
# ---------------------------------------------------------------------------


def test_intelligence_write_is_held_by_exactly_one_role(
    client: TestClient, session: Session
) -> None:
    """Siapa pemegang `intelligence:write` — dijaga supaya tidak berubah diam-diam.

    Test ini semula menegaskan permission tersebut **tidak dipegang siapa pun**, dan itu
    memang keadaannya: pencabutannya dari peran Fungsi meninggalkannya tanpa pemegang,
    sehingga `POST /intelligence-reports` mustahil dipakai akun mana pun. Endpoint yang
    ada tetapi tidak dapat dijangkau siapa pun adalah cacat, bukan pengamanan.

    Permission itu kini diberikan kepada Administrator — peran yang, sejak penggabungan
    1 September 2026, memasukkan data operasional dan sudah memegang `crime:write`.

    Yang dijaga tetap sama maksudnya: perubahan pemegang kewenangan menulis intelijen
    harus menjadi keputusan sadar, bukan efek samping seed.
    """
    holders = session.scalars(
        select(Role.role_name)
        .join(RolePermission, RolePermission.role_id == Role.role_id)
        .join(Permission, Permission.permission_id == RolePermission.permission_id)
        .where(Permission.resource == "intelligence")
        .where(Permission.action == "write")
    ).all()

    assert sorted(holders) == ["Administrator"], (
        f"pemegang `intelligence:write` berubah menjadi {sorted(holders)} — perbarui test "
        f"ini bersama keputusan yang mengubahnya"
    )

    # Peran lain tetap ditolak — pemegangnya satu, bukan "siapa saja yang menulis data".
    officer = _make_user(session, "Polsek", polsek=_location(session).polsek)
    response = client.post(
        "/api/v1/intelligence-reports",
        json={
            "report_date": _past_date().isoformat(),
            "category": "Kerawanan Lokasi",
            "location_code": _location(session).code,
        },
        headers=_auth(client, officer),
    )

    assert response.status_code == 403


def test_intelligence_report_can_be_recorded_by_an_authorised_role(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Administrator")
    _grant(session, officer, "intelligence:write")
    location = _location(session)

    response = client.post(
        "/api/v1/intelligence-reports",
        json={
            "report_date": _past_date().isoformat(),
            "category": "Kerawanan Lokasi",
            "location_code": location.code,
            "reliability": "B",
            "confidence": 70,
            "urgency": 55,
            "impact": "HIGH",
        },
        headers=_auth(client, officer),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"].startswith("INT-")
    assert body["status"] == "NEW"
    assert body["impact"] == "HIGH"

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "CREATE_INTELLIGENCE_REPORT")
        .where(AuditLog.resource_id == body["code"])
    )
    assert entry is not None


def test_intelligence_report_is_scoped_by_jurisdiction(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Polsek", polsek=TEBET)
    _grant(session, officer, "intelligence:write", scope="OWN_JURISDICTION")

    response = client.post(
        "/api/v1/intelligence-reports",
        json={
            "report_date": _past_date().isoformat(),
            "category": "Kerawanan Lokasi",
            "location_code": _location_outside(session, TEBET).code,
        },
        headers=_auth(client, officer),
    )

    assert response.status_code == 404


def test_future_intelligence_report_is_refused(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")
    _grant(session, officer, "intelligence:write")

    response = client.post(
        "/api/v1/intelligence-reports",
        json={
            "report_date": _future_date().isoformat(),
            "category": "Kerawanan Lokasi",
            "location_code": _location(session).code,
        },
        headers=_auth(client, officer),
    )

    assert response.status_code == 400
    assert "waktu acuan" in response.json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Triase laporan masyarakat
# ---------------------------------------------------------------------------


def _report(session: Session, polsek: str | None = None, status: str = "RECEIVED") -> CitizenReport:
    query = (
        select(CitizenReport)
        .join(Location, Location.location_id == CitizenReport.location_id)
        .where(CitizenReport.status == status)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    report = session.scalar(query.limit(1))
    assert report is not None, f"data awal tidak menyediakan laporan {status} di {polsek}"
    return report


def test_report_status_change_is_recorded_with_before_and_after(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Administrator")
    report = _report(session)

    response = client.post(
        f"/api/v1/citizen-reports/{report.code}/status",
        json={"status": "VERIFIED", "note": "Dicek petugas piket."},
        headers=_auth(client, officer),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status_before"] == "RECEIVED"
    assert body["status"] == "VERIFIED"
    # Verifikasi disebut sebagai tindakan bermakna, bukan label administratif.
    assert "community_factor" in body["verification_basis"]

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "UPDATE_CITIZEN_REPORT_STATUS")
        .where(AuditLog.resource_id == report.code)
        .where(AuditLog.result == "SUCCESS")
    )
    assert entry is not None
    assert entry.detail is not None
    assert entry.detail["status_before"] == "RECEIVED"
    assert entry.detail["status_after"] == "VERIFIED"


def test_backward_and_skipping_transitions_are_allowed_but_recorded(
    client: TestClient, session: Session
) -> None:
    """Keputusan sadar: belum ada SOP triase, jadi urutannya tidak dipaksakan.

    Melarang mundur atau melompat berarti mengarang aturan yang tidak pernah ditetapkan
    siapa pun. Yang dijamin sebagai gantinya adalah jejaknya lengkap.
    """
    officer = _make_user(session, "Administrator")
    report = _report(session, status="RECEIVED")
    headers = _auth(client, officer)

    # Melompat dua langkah.
    leap = client.post(
        f"/api/v1/citizen-reports/{report.code}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert leap.status_code == 200, leap.text

    # Lalu mundur ke awal.
    back = client.post(
        f"/api/v1/citizen-reports/{report.code}/status",
        json={"status": "RECEIVED", "note": "Verifikasi keliru, dikembalikan."},
        headers=headers,
    )
    assert back.status_code == 200, back.text
    assert back.json()["status_before"] == "IN_PROGRESS"

    trail = session.scalars(
        select(AuditLog)
        .where(AuditLog.action == "UPDATE_CITIZEN_REPORT_STATUS")
        .where(AuditLog.resource_id == report.code)
        .where(AuditLog.result == "SUCCESS")
    ).all()
    assert len(trail) == 2


def test_setting_the_same_status_is_refused(client: TestClient, session: Session) -> None:
    """Bukan aturan alur kerja, melainkan penjagaan audit: yang tidak berubah tidak dicatat."""
    officer = _make_user(session, "Administrator")
    report = _report(session, status="VERIFIED")

    response = client.post(
        f"/api/v1/citizen-reports/{report.code}/status",
        json={"status": "VERIFIED"},
        headers=_auth(client, officer),
    )

    assert response.status_code == 409
    assert "Diverifikasi" in response.json()["error"]["message"]


def test_unknown_report_status_is_refused_with_the_valid_list(
    client: TestClient, session: Session
) -> None:
    officer = _make_user(session, "Administrator")

    response = client.post(
        f"/api/v1/citizen-reports/{_report(session).code}/status",
        json={"status": "DITOLAK"},
        headers=_auth(client, officer),
    )

    assert response.status_code == 400
    assert "FORWARDED" in response.json()["error"]["message"]


def test_report_outside_jurisdiction_is_not_found(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Polsek", polsek=TEBET)
    outside = session.scalar(
        select(CitizenReport)
        .join(Location, Location.location_id == CitizenReport.location_id)
        .where(Location.polsek != TEBET)
        .limit(1)
    )
    assert outside is not None

    response = client.post(
        f"/api/v1/citizen-reports/{outside.code}/status",
        json={"status": "VERIFIED"},
        headers=_auth(client, officer),
    )

    assert response.status_code == 404


def test_officer_without_permission_cannot_triage(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.post(
        f"/api/v1/citizen-reports/{_report(session).code}/status",
        json={"status": "VERIFIED"},
        headers=_auth(client, leader),
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Pilihan isian
# ---------------------------------------------------------------------------


def test_options_expose_the_full_threat_taxonomy(client: TestClient, session: Session) -> None:
    officer = _make_user(session, "Administrator")

    response = client.get("/api/v1/data-entry/options", headers=_auth(client, officer))

    assert response.status_code == 200, response.text
    body = response.json()
    values = [row["value"] for row in body["incident_type"]]
    assert len(values) == 10, "taksonomi ancaman kini 10 jenis (docs/16 §2)"
    assert "BEGAL" in values and "KERAMAIAN" in values
    # Label berasal dari konfigurasi, bukan dikarang di layar.
    labels = {row["value"]: row["label"] for row in body["incident_type"]}
    assert labels["UNJUK_RASA"] == "Unjuk Rasa"
    assert labels["KEJAHATAN_JALANAN"] == "Kejahatan Jalanan"


def test_options_do_not_leak_vocabulary_a_role_cannot_read(
    client: TestClient, session: Session
) -> None:
    """Saran yang berasal dari basis data mengikuti kewenangan baca tabel asalnya.

    Peran Fungsi kini tidak memegang `intelligence:read` — pemberiannya ditahan menunggu
    keputusan. Daftar kategori intelijen karena itu tidak boleh muncul lewat pintu
    belakang bernama "pilihan formulir".
    """
    officer = _make_user(session, "Fungsi", function="RESKRIM")

    body = client.get("/api/v1/data-entry/options", headers=_auth(client, officer)).json()

    assert "intelligence_category" not in body["suggestions"]
    assert "modus" in body["suggestions"], "Fungsi memegang crime:read"
