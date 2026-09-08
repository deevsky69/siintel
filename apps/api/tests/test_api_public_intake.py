"""Test kanal publik LAPOR PRESISI (TASK 160).

Ini satu-satunya endpoint yang melayani permintaan **tanpa autentikasi**, sehingga yang
diuji di sini bukan bentuk responsnya melainkan batas-batasnya:

1. **Benar-benar terbuka** — dapat dipakai tanpa token sama sekali.
2. **Tidak menjadi jendela ke dalam sistem** — pilihan isian tidak membocorkan data.
3. **Pelapor tidak menetapkan apa pun selain isi laporannya** — status, urgensi, dan
   verifikasi tidak dapat diisi dari luar.
4. **Identitas ditolak, bukan diabaikan diam-diam.**
5. **Ada pembatas laju** — kolom teks tanpa akun adalah tempat paling mudah dibanjiri.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers.public_intake import limiter, load_report_categories
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, CitizenReport, Location
from prediksi_presisi_api.services import clock

DATABASE_URL = os.environ.get("DATABASE_URL", "")

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
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()


def _a_kecamatan(session: Session) -> str:
    name = session.scalar(select(Location.kecamatan).where(Location.kecamatan.is_not(None)))
    assert name is not None
    return str(name)


def _payload(session: Session, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "category": load_report_categories()[0],
        "kecamatan": _a_kecamatan(session),
        "description": "Ada sekelompok orang berkumpul dan membuat keributan di gang.",
    }
    body.update(overrides)
    return body


# --- 1. Benar-benar terbuka -------------------------------------------------------------


def test_a_citizen_can_report_without_any_account(client: TestClient, session: Session) -> None:
    """Tidak ada header Authorization sama sekali — inilah inti kanal ini.

    Bila endpoint ini suatu saat menuntut token, seluruh rantai laporan masyarakat putus di
    pangkalnya dan tidak ada layar internal yang akan menunjukkannya.
    """
    response = client.post("/api/v1/public/citizen-reports", json=_payload(session))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["ticket"].startswith("RPT-")
    assert body["status"] == "RECEIVED"

    stored = session.scalar(select(CitizenReport).where(CitizenReport.code == body["ticket"]))
    assert stored is not None
    assert stored.status == "RECEIVED"


def test_the_form_options_are_readable_without_an_account(client: TestClient) -> None:
    response = client.get("/api/v1/public/report-options")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["categories"] == load_report_categories()
    assert body["kecamatan"]


# --- 2. Bukan jendela ke dalam sistem ---------------------------------------------------


def test_the_public_options_leak_nothing_beyond_the_choices(client: TestClient) -> None:
    """Kanal publik hanya boleh menjawab pilihan isian, bukan isi sistem.

    Satu field tambahan yang "kebetulan berguna" di sini adalah kebocoran yang tidak
    terlihat sebagai kebocoran, karena endpointnya memang dimaksudkan terbuka.
    """
    body = client.get("/api/v1/public/report-options").json()

    # Tiga kunci ditambahkan 8 September 2026 bersama fitur lampiran. Ketiganya adalah
    # BATAS dan KETERANGAN — apa yang boleh dikirim, seberapa besar, dan bagaimana
    # berkasnya diperlakukan — bukan isi sistem. Formulir memerlukannya untuk menolak
    # berkas terlalu besar sebelum jaringan dipakai sia-sia.
    assert set(body) == {
        "categories",
        "kecamatan",
        "max_description",
        "coordinate_basis",
        "intake_basis",
        "attachment_basis",
        "max_attachments",
        "max_attachment_bytes",
    }


def test_the_response_returns_a_ticket_and_nothing_about_other_reports(
    client: TestClient, session: Session
) -> None:
    body = client.post("/api/v1/public/citizen-reports", json=_payload(session)).json()

    # `coordinate_source` dan `attachments` ditambahkan 8 September 2026. Keduanya hanya
    # menggemakan apa yang baru saja DIKIRIM pelapor itu sendiri — dari mana koordinatnya
    # dan berapa berkas yang ia lampirkan — bukan sesuatu tentang laporan orang lain.
    assert set(body) == {
        "ticket",
        "status",
        "reported_at",
        "kecamatan",
        "message",
        "basis",
        "coordinate_source",
        "attachments",
    }


# --- 3. Pelapor tidak menetapkan penilaian petugas --------------------------------------


def test_a_reporter_cannot_set_the_scores_officers_assign(
    client: TestClient, session: Session
) -> None:
    """Membiarkan pelapor mengisi `urgency_score` berarti membiarkan siapa pun menaikkan
    prioritas laporannya sendiri."""
    response = client.post(
        "/api/v1/public/citizen-reports",
        json=_payload(session, urgency_score=100, verification_score=100, status="VERIFIED"),
    )

    assert response.status_code == 400, response.text
    assert "urgency_score" in response.text


def test_a_report_arrives_unverified(client: TestClient, session: Session) -> None:
    ticket = client.post("/api/v1/public/citizen-reports", json=_payload(session)).json()["ticket"]

    stored = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert stored is not None
    assert stored.status == "RECEIVED"
    assert stored.urgency_score is None
    assert stored.verification_score is None


# --- 4. Identitas ditolak, bukan diabaikan ----------------------------------------------


def test_identity_fields_are_refused_rather_than_silently_dropped(
    client: TestClient, session: Session
) -> None:
    """Membuang diam-diam terasa lebih ramah, tetapi menyesatkan orang yang menyerahkan
    datanya: ia menerima keberhasilan dan mengira namanya tersimpan."""
    response = client.post(
        "/api/v1/public/citizen-reports",
        json=_payload(session, nama_pelapor="Budi", nomor_telepon="0812xxxx"),
    )

    assert response.status_code == 400, response.text
    assert "nama_pelapor" in response.text


def test_no_identity_column_exists_to_store_it_in(session: Session) -> None:
    """Penjaga struktural: penolakan di atas hanya bermakna selama tabelnya memang tidak
    memiliki tempat untuk identitas."""
    columns = {column.name for column in CitizenReport.__table__.columns}

    for forbidden in ("nama", "name", "phone", "telepon", "email", "nik", "reporter"):
        assert not any(forbidden in column for column in columns), forbidden


# --- 5. Pembatas laju -------------------------------------------------------------------


def test_flooding_is_refused_after_the_hourly_quota(client: TestClient, session: Session) -> None:
    from prediksi_presisi_api.api.routers.public_intake import RATE_LIMIT_PER_HOUR

    for index in range(RATE_LIMIT_PER_HOUR):
        response = client.post("/api/v1/public/citizen-reports", json=_payload(session))
        assert response.status_code == 201, f"kiriman ke-{index + 1}: {response.text}"

    blocked = client.post("/api/v1/public/citizen-reports", json=_payload(session))

    assert blocked.status_code == 429, blocked.text
    assert "110" in blocked.text, "pesan penolakan harus menyebut jalur darurat"


# --- Validasi isi -----------------------------------------------------------------------


def test_an_unknown_category_is_refused_with_the_valid_list(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, category="Apa Saja")
    )

    assert response.status_code == 400, response.text
    assert load_report_categories()[0] in response.text


def test_an_unknown_kecamatan_is_refused(client: TestClient, session: Session) -> None:
    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, kecamatan="Bandung")
    )

    assert response.status_code == 400, response.text


def test_a_future_incident_time_is_refused(client: TestClient, session: Session) -> None:
    ahead = (clock.reference_now() + timedelta(hours=2)).isoformat()

    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, incident_time=ahead)
    )

    assert response.status_code == 400, response.text


def test_a_very_old_incident_is_pointed_to_the_proper_channel(
    client: TestClient, session: Session
) -> None:
    from prediksi_presisi_api.api.routers.public_intake import MAX_INCIDENT_AGE_DAYS

    old = (clock.reference_now() - timedelta(days=MAX_INCIDENT_AGE_DAYS + 1)).isoformat()

    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, incident_time=old)
    )

    assert response.status_code == 400, response.text
    assert "Polsek" in response.text


def test_an_empty_description_is_refused(client: TestClient, session: Session) -> None:
    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, description=".")
    )

    assert response.status_code == 400, response.text


# --- Jejak audit ------------------------------------------------------------------------


def test_a_public_submission_is_audited_without_inventing_a_user(
    client: TestClient, session: Session
) -> None:
    """Tidak ada pengguna di balik peristiwa ini, dan `user_id` dibiarkan kosong.

    Mengisinya dengan akun sistem akan membuat jejak audit menyatakan sesuatu yang tidak
    terjadi — dan jejak audit yang mengarang pelaku lebih buruk daripada tidak ada jejak.
    """
    ticket = client.post("/api/v1/public/citizen-reports", json=_payload(session)).json()["ticket"]

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.resource_id == ticket, AuditLog.action == "SUBMIT_CITIZEN_REPORT")
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None
    assert entry.user_id is None
    assert entry.result == "SUCCESS"
    assert entry.detail is not None
    assert entry.detail["channel"] == "PUBLIC"


def test_the_report_lands_where_officers_can_see_it(client: TestClient, session: Session) -> None:
    """Laporan publik harus benar-benar sampai ke antrean petugas, bukan berhenti di tabel.

    Tanpa ini, kanal publik dapat "berhasil" sepenuhnya sementara tidak ada seorang pun
    yang pernah melihat laporannya.
    """
    before = session.scalar(
        select(func.count()).select_from(CitizenReport).where(CitizenReport.status == "RECEIVED")
    )
    client.post("/api/v1/public/citizen-reports", json=_payload(session))
    after = session.scalar(
        select(func.count()).select_from(CitizenReport).where(CitizenReport.status == "RECEIVED")
    )

    assert after == int(before or 0) + 1


def test_the_rate_limit_counts_each_reporter_separately(
    client: TestClient, session: Session
) -> None:
    """Dua pelapor dari alamat berbeda tidak boleh saling membungkam.

    Ini penjaga terhadap kegagalan yang paling mudah terjadi pada susunan ini: permintaan
    berangkat dari container web, sehingga tanpa `X-Forwarded-For` backend melihat SATU
    alamat untuk seluruh dunia. Pembatasnya lalu memperlakukan semua pengunjung sebagai
    satu pengirim, dan sepuluh laporan dari siapa pun akan membungkam semua orang selama
    sejam — lebih buruk daripada tidak ada pembatas, dan tidak terlihat sampai ada yang
    benar-benar melapor.
    """
    from prediksi_presisi_api.api.routers.public_intake import RATE_LIMIT_PER_HOUR

    first = {"X-Forwarded-For": "203.0.113.10"}
    second = {"X-Forwarded-For": "198.51.100.20"}

    for _ in range(RATE_LIMIT_PER_HOUR):
        assert (
            client.post(
                "/api/v1/public/citizen-reports", json=_payload(session), headers=first
            ).status_code
            == 201
        )

    assert (
        client.post(
            "/api/v1/public/citizen-reports", json=_payload(session), headers=first
        ).status_code
        == 429
    ), "pelapor pertama sudah melewati jatahnya"

    assert (
        client.post(
            "/api/v1/public/citizen-reports", json=_payload(session), headers=second
        ).status_code
        == 201
    ), "pelapor kedua tidak boleh ikut terblokir"


def test_a_proxy_chain_is_read_from_its_first_entry(client: TestClient, session: Session) -> None:
    """`X-Forwarded-For` dapat berisi rantai; yang pertama adalah pelapornya."""
    chain = {"X-Forwarded-For": "203.0.113.30, 10.0.0.5, 10.0.0.6"}
    single = {"X-Forwarded-For": "203.0.113.30"}
    from prediksi_presisi_api.api.routers.public_intake import RATE_LIMIT_PER_HOUR

    for _ in range(RATE_LIMIT_PER_HOUR):
        assert (
            client.post(
                "/api/v1/public/citizen-reports", json=_payload(session), headers=chain
            ).status_code
            == 201
        )

    # Alamat yang sama, ditulis tanpa rantai — harus dihitung sebagai pengirim yang sama.
    assert (
        client.post(
            "/api/v1/public/citizen-reports", json=_payload(session), headers=single
        ).status_code
        == 429
    )
