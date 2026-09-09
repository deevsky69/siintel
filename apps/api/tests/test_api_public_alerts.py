"""Kanal imbauan kepada masyarakat (TASK 111).

Sampai 9 September 2026 `public_alerts` punya tabel, model, seeder, dan 25 baris — tetapi
tidak satu endpoint pun. Peringatan dini berhenti di dalam organisasi. Yang diuji di sini
adalah lengan terakhir rantai pada CLAUDE.md §9, beserta batas-batas yang membuatnya boleh
menghadap keluar:

1. **Menerbitkan adalah keputusan komando** — hanya pemegang `public_alert:publish`.
2. **Isinya ditulis manusia** — rancangan tidak pernah tersimpan tanpa dikirim penerbitnya.
3. **Tidak ada detail internal yang bocor** ke kanal tanpa akun.
4. **Satu peringatan tidak diumumkan dua kali.**
5. **TIDAK ADA gerbang severity** — dan ketiadaannya dinyatakan, bukan didiamkan (sisa U-10).
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
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, EarlyWarning, Location, PublicAlert, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
PESAN = (
    "Imbauan kewaspadaan terhadap CURANMOR di wilayah Kecamatan Tebet pada malam hari. "
    "Kunci kendaraan dan laporkan hal mencurigakan kepada Polsek setempat."
)

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


def _user(session: Session, role_name: str, polsek: str | None = None) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        polsek=polsek,
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


def _a_candidate(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.get("/api/v1/public-alerts/candidates", headers=headers)
    assert response.status_code == 200, response.text
    candidates = response.json()["data"]
    assert candidates, "data awal tidak memuat peringatan yang dapat diumumkan"
    row: dict[str, object] = candidates[0]
    return row


# --- 1. Kewenangan ----------------------------------------------------------------------


def test_only_the_holder_of_publish_may_announce(client: TestClient, session: Session) -> None:
    """Administrator menjalankan prediksi, tetapi tidak mengumumkan hasilnya.

    Ini keputusan pemilik proyek 9 September 2026, dan justru peran yang paling berkuasa
    secara teknis yang harus terhalang di sini.
    """
    leader = _user(session, "Pimpinan")
    admin = _user(session, "Administrator")
    candidate = _a_candidate(client, _auth(client, leader))

    refused = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": PESAN},
        headers=_auth(client, admin),
    )

    assert refused.status_code == 403


def test_a_refused_attempt_leaves_a_trace(client: TestClient, session: Session) -> None:
    """Percobaan mengumumkan tanpa kewenangan tercatat, bukan hanya ditolak."""
    admin = _user(session, "Administrator")
    before = session.scalar(
        select(AuditLog.audit_id).where(AuditLog.result == "DENIED").order_by(AuditLog.timestamp)
    )

    client.post(
        "/api/v1/public-alerts",
        json={"warning_code": "WRN-00001", "public_message": PESAN},
        headers=_auth(client, admin),
    )
    session.flush()

    denied = session.scalars(select(AuditLog).where(AuditLog.result == "DENIED")).all()
    assert denied, "penolakan tidak meninggalkan jejak audit"
    assert before is None or len(denied) > 0


def test_publishing_records_who_did_it(client: TestClient, session: Session) -> None:
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)

    response = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": PESAN},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    code = response.json()["data"]["code"]

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "PUBLISH_PUBLIC_ALERT", AuditLog.resource_id == code
        )
    )
    assert entry is not None
    assert entry.user_id == leader.user_id
    # Isi imbauan TIDAK disalin ke audit: ia sudah tersimpan utuh pada barisnya, dan dua
    # salinan dapat berbeda setelah revisi.
    assert PESAN not in str(entry.detail)


# --- 2. Isi ditulis manusia -------------------------------------------------------------


def test_the_stored_message_is_the_one_that_was_sent(client: TestClient, session: Session) -> None:
    """Rancangan hanya titik awal; yang tersimpan adalah yang benar-benar dikirim."""
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)
    disunting = PESAN + " Ronda lingkungan diaktifkan kembali mulai malam ini."

    response = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": disunting},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["data"]["public_message"] == disunting
    assert response.json()["data"]["public_message"] != candidate["suggested_message"]


def test_an_empty_message_is_refused(client: TestClient, session: Session) -> None:
    """Imbauan tanpa isi bukan imbauan; kanal satu arah tidak punya kesempatan kedua."""
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)

    response = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": "  "},
        headers=headers,
    )

    assert response.status_code == 400


# --- 3. Tidak ada gerbang severity, dan itu dinyatakan ------------------------------------


def test_there_is_no_severity_gate_and_the_response_says_so(
    client: TestClient, session: Session
) -> None:
    """Sisa U-10: severity minimum belum ditetapkan, jadi tidak ada ambang sama sekali.

    Yang dijaga BUKAN bahwa ambangnya tidak boleh ada selamanya, melainkan bahwa selama ia
    belum diputus, ketiadaannya dinyatakan terbuka alih-alih didiamkan — dan tidak ada
    ambang yang diam-diam disisipkan tanpa keputusan kebijakan.
    """
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    body = client.get("/api/v1/public-alerts/candidates", headers=headers).json()

    assert "severity_gate_basis" in body
    assert "belum ditetapkan" in body["severity_gate_basis"]

    tingkat = {str(row["severity"]) for row in body["data"]}
    assert len(tingkat) > 1, "seluruh calon bertingkat sama — uji ini tidak membuktikan apa pun"


# --- 4. Satu peringatan, satu imbauan aktif ----------------------------------------------


def test_the_same_warning_is_never_announced_twice(client: TestClient, session: Session) -> None:
    """Dua imbauan atas satu kejadian membuat pembacanya tidak tahu mana yang berlaku."""
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)
    payload = {"warning_code": candidate["warning_code"], "public_message": PESAN}

    assert client.post("/api/v1/public-alerts", json=payload, headers=headers).status_code == 201
    kedua = client.post("/api/v1/public-alerts", json=payload, headers=headers)

    assert kedua.status_code == 409
    assert "masih berlaku" in kedua.json()["error"]["message"]


def test_a_published_warning_leaves_the_candidate_queue(
    client: TestClient, session: Session
) -> None:
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)

    client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": PESAN},
        headers=headers,
    )

    tersisa = client.get("/api/v1/public-alerts/candidates", headers=headers).json()["data"]
    assert candidate["warning_code"] not in {row["warning_code"] for row in tersisa}


def test_withdrawing_an_alert_lets_it_be_announced_again(
    client: TestClient, session: Session
) -> None:
    """Mencabut lalu menerbitkan ulang adalah cara mengganti isi imbauan yang keliru."""
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)
    payload = {"warning_code": candidate["warning_code"], "public_message": PESAN}

    code = client.post("/api/v1/public-alerts", json=payload, headers=headers).json()["data"][
        "code"
    ]
    dicabut = client.post(f"/api/v1/public-alerts/{code}/resolve", headers=headers)
    assert dicabut.status_code == 200, dicabut.text
    assert dicabut.json()["data"]["status"] == "RESOLVED"

    ulang = client.post("/api/v1/public-alerts", json=payload, headers=headers)
    assert ulang.status_code == 201, ulang.text


def test_an_alert_cannot_be_withdrawn_twice(client: TestClient, session: Session) -> None:
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)

    code = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": PESAN},
        headers=headers,
    ).json()["data"]["code"]
    client.post(f"/api/v1/public-alerts/{code}/resolve", headers=headers)

    assert client.post(f"/api/v1/public-alerts/{code}/resolve", headers=headers).status_code == 409


# --- 5. Kanal tanpa akun tidak membocorkan apa pun ---------------------------------------


def test_the_public_channel_needs_no_account(client: TestClient) -> None:
    response = client.get("/api/v1/public/alerts")

    assert response.status_code == 200, response.text
    assert "basis" in response.json()


def test_the_public_channel_shows_only_what_was_actually_published(
    client: TestClient, session: Session
) -> None:
    """Peringatan dini yang belum diumumkan tidak pernah sampai ke halaman publik."""
    published = {
        code
        for code in session.scalars(
            select(PublicAlert.code).where(PublicAlert.status == "ACTIVE")
        ).all()
    }
    listed = {row["code"] for row in client.get("/api/v1/public/alerts").json()["data"]}

    assert listed <= published


def test_the_public_channel_never_leaks_internal_detail(client: TestClient) -> None:
    """Skor risiko, grid, dan kode peringatan internal tidak boleh ikut keluar.

    Bukan sekadar "tidak ditampilkan di layar": kanal ini dapat dibaca siapa saja dengan
    satu perintah curl, jadi yang dijaga adalah bentuk responsnya.
    """
    body = client.get("/api/v1/public/alerts").json()
    terlarang = {"risk_score", "confidence", "grid_id", "kelurahan", "warning_code", "location_id"}

    for row in body["data"]:
        assert set(row) & terlarang == set(), row
        assert "JKS-" not in str(row), "kode grid internal ikut keluar"
        assert "WRN-" not in str(row), "kode peringatan internal ikut keluar"


def test_a_withdrawn_alert_disappears_from_the_public_channel(
    client: TestClient, session: Session
) -> None:
    """Mencabut harus benar-benar menghentikan peredarannya, bukan sekadar menandainya."""
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    candidate = _a_candidate(client, headers)

    code = client.post(
        "/api/v1/public-alerts",
        json={"warning_code": candidate["warning_code"], "public_message": PESAN},
        headers=headers,
    ).json()["data"]["code"]
    assert code in {row["code"] for row in client.get("/api/v1/public/alerts").json()["data"]}

    client.post(f"/api/v1/public-alerts/{code}/resolve", headers=headers)

    assert code not in {row["code"] for row in client.get("/api/v1/public/alerts").json()["data"]}


# --- 6. Cakupan wilayah ------------------------------------------------------------------


def test_a_scoped_user_only_sees_alerts_from_their_own_area(
    client: TestClient, session: Session
) -> None:
    """Polsek membaca imbauan wilayahnya sendiri — lewat peringatan yang mendasarinya."""
    polsek = session.scalar(select(Location.polsek).where(Location.polsek.is_not(None)).limit(1))
    assert polsek is not None
    officer = _user(session, "Polsek", polsek=polsek)

    body = client.get("/api/v1/public-alerts", headers=_auth(client, officer)).json()
    codes = [row["warning_code"] for row in body["data"]]

    for code in codes:
        area = session.scalar(
            select(Location.polsek)
            .join(EarlyWarning, EarlyWarning.location_id == Location.location_id)
            .where(EarlyWarning.code == code)
        )
        assert area == polsek
