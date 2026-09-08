"""Test lokasi tepat dan lampiran laporan masyarakat (revisi 8 September 2026).

Yang diuji di sini bukan bentuk responsnya melainkan **janji yang dibuat kepada pelapor**,
karena janji itulah yang membuat keputusan menerima berkas dapat dipertanggungjawabkan:

1. **Metadata berkas benar-benar dilucuti.** Foto ponsel membawa koordinat GPS dan nomor
   seri kamera di EXIF. Kalau ini tidak bekerja, pelapor yang tidak mengetik namanya tetap
   dapat dikenali — dan tidak ada di layar mana pun yang akan menunjukkannya.
2. **Asal koordinat selalu tercatat.** Titik pusat kecamatan dan titik peranti terlihat
   sama sebagai sepasang angka, padahal yang pertama berjarak kilometer dari kejadian.
3. **Hanya yang berwenang memverifikasi yang dapat membuka lampiran**, dan setiap
   pembukaan meninggalkan jejak.
4. **Masa retensi benar-benar dijalankan**, dan jejak bahwa ia dijalankan tetap ada.
"""

from __future__ import annotations

import io
import os
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers.public_intake import limiter, load_report_categories
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    CitizenReport,
    CitizenReportAttachment,
    Location,
    Role,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import attachments as store
from prediksi_presisi_api.services import clock

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture(autouse=True)
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Direktori lampiran diarahkan ke folder sementara milik masing-masing test.

    Tanpa ini, test akan menulis ke direktori lampiran sungguhan — dan test yang
    meninggalkan berkas orang di cakram pengembang bukan test yang boleh ada.
    """
    monkeypatch.setenv("ATTACHMENT_DIR", str(tmp_path / "lampiran"))
    yield tmp_path


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
    name = session.scalar(
        select(Location.kecamatan).where(
            Location.kecamatan.is_not(None),
            Location.latitude.is_not(None),
        )
    )
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


def _make_user(session: Session, role_name: str, polsek: str | None = None) -> User:
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


def _photo_with_exif() -> bytes:
    """Sebuah JPEG yang benar-benar membawa EXIF berisi koordinat dan merek kamera."""
    image = Image.new("RGB", (24, 16), (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "PonselUji"  # Make
    exif[0x0110] = "Model-XYZ"  # Model
    # Koordinat ditulis sebagai pecahan derajat/menit/detik, bentuk yang dipakai kamera
    # ponsel sungguhan: 6°15'S 106°48'E — kira-kira Jakarta Selatan.
    exif[0x8825] = {  # GPSInfo
        1: "S",
        2: (6.0, 15.0, 0.0),
        3: "E",
        4: (106.0, 48.0, 0.0),
    }
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


# --- 1. Metadata benar-benar dilucuti ----------------------------------------------------


def test_the_uploaded_photo_actually_carries_exif_before_upload() -> None:
    """Penegasan atas bahan ujinya sendiri.

    Tanpa ini, test berikutnya dapat lulus hanya karena fotonya memang tidak pernah punya
    EXIF — memeriksa ketiadaan sesuatu yang tidak pernah ada.
    """
    exif = Image.open(io.BytesIO(_photo_with_exif())).getexif()

    assert exif.get(0x010F) == "PonselUji"
    assert exif.get_ifd(0x8825), "bahan uji harus membawa GPSInfo"


def test_exif_is_stripped_before_the_file_is_stored(client: TestClient, storage: Path) -> None:
    response = client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "IMAGE"

    stored = next((storage / "lampiran" / "_menunggu").glob(f"{body['handle']}.jpg"))
    exif = Image.open(stored).getexif()

    assert exif.get(0x010F) is None, "merek kamera masih tersimpan"
    assert exif.get(0x0110) is None, "model kamera masih tersimpan"
    assert not exif.get_ifd(0x8825), "koordinat GPS masih tersimpan di dalam berkas"


def test_the_stripped_photo_is_still_a_readable_image(client: TestClient, storage: Path) -> None:
    """Melucuti metadata tidak boleh merusak gambarnya.

    Pelucutan yang menghasilkan berkas rusak akan lolos test di atas dengan gemilang —
    berkas yang tidak dapat dibuka tentu tidak punya EXIF.
    """
    handle = client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    ).json()["handle"]

    stored = next((storage / "lampiran" / "_menunggu").glob(f"{handle}.jpg"))
    with Image.open(stored) as image:
        assert image.size == (24, 16)
        pixel = image.convert("RGB").getpixel((0, 0))
        assert isinstance(pixel, tuple)
        assert pixel[0] > 150, "warnanya harus tetap merah, bukan berkas rusak"


def test_an_unknown_file_type_is_refused(client: TestClient) -> None:
    response = client.post(
        "/api/v1/public/attachments",
        # Mengaku JPEG pada Content-Type; isinya bukan. Yang diperiksa adalah isinya.
        files={"berkas": ("jahat.jpg", b"#!/bin/sh\nrm -rf /\n", "image/jpeg")},
    )

    assert response.status_code == 400
    assert "tidak dikenali" in response.json()["error"]["message"].lower()


def test_a_file_beyond_the_size_limit_is_refused(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "MAX_ATTACHMENT_BYTES", 512)

    response = client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("besar.png", _big_png(), "image/png")},
    )

    assert response.status_code == 400
    assert "MB" in response.json()["error"]["message"]


def _big_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 400), (10, 200, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


# --- 2. Asal koordinat selalu tercatat ---------------------------------------------------


def test_without_a_shared_location_the_coordinate_comes_from_the_kecamatan(
    client: TestClient, session: Session
) -> None:
    body = client.post("/api/v1/public/citizen-reports", json=_payload(session)).json()

    report = session.scalar(select(CitizenReport).where(CitizenReport.code == body["ticket"]))
    assert report is not None
    assert report.coordinate_source == "KECAMATAN_CENTROID"
    assert report.gps_accuracy_m is None
    assert body["coordinate_source"] == "KECAMATAN_CENTROID"


def test_a_shared_location_is_stored_as_the_incident_point(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/api/v1/public/citizen-reports",
        json=_payload(session, latitude=-6.2411, longitude=106.8032, accuracy_m=12.5),
    )

    assert response.status_code == 201, response.text
    report = session.scalar(
        select(CitizenReport).where(CitizenReport.code == response.json()["ticket"])
    )
    assert report is not None
    assert report.coordinate_source == "REPORTER_GPS"
    assert float(report.latitude) == pytest.approx(-6.2411, abs=1e-6)
    assert float(report.longitude) == pytest.approx(106.8032, abs=1e-6)
    assert report.gps_accuracy_m is not None
    assert float(report.gps_accuracy_m) == pytest.approx(12.5)


def test_half_a_location_is_refused(client: TestClient, session: Session) -> None:
    """Lintang tanpa bujur bukan lokasi, dan menyimpannya berarti mengarang separuhnya."""
    response = client.post("/api/v1/public/citizen-reports", json=_payload(session, latitude=-6.24))

    assert response.status_code == 400
    assert "sekaligus" in response.json()["error"]["message"]


def test_accuracy_without_a_location_is_refused(client: TestClient, session: Session) -> None:
    response = client.post("/api/v1/public/citizen-reports", json=_payload(session, accuracy_m=10))

    assert response.status_code == 400


def test_the_coordinate_source_is_written_to_the_audit_trail(
    client: TestClient, session: Session
) -> None:
    """Berapa banyak data pribadi yang masuk lewat satu peristiwa harus dapat ditelusuri."""
    ticket = client.post(
        "/api/v1/public/citizen-reports",
        json=_payload(session, latitude=-6.24, longitude=106.8),
    ).json()["ticket"]

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "SUBMIT_CITIZEN_REPORT", AuditLog.resource_id == ticket
        )
    )
    assert entry is not None
    assert entry.detail is not None
    assert entry.detail["coordinate_source"] == "REPORTER_GPS"
    assert entry.detail["attachments"] == 0


# --- 3. Lampiran menempel pada laporan ---------------------------------------------------


def _submit_with_photo(client: TestClient, session: Session) -> str:
    handle = client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    ).json()["handle"]

    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, attachments=[handle])
    )
    assert response.status_code == 201, response.text
    return str(response.json()["ticket"])


def test_an_attachment_follows_its_report(
    client: TestClient, session: Session, storage: Path
) -> None:
    ticket = _submit_with_photo(client, session)

    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None
    rows = session.scalars(
        select(CitizenReportAttachment).where(CitizenReportAttachment.report_id == report.report_id)
    ).all()

    assert len(rows) == 1
    assert rows[0].kind == "IMAGE"
    assert rows[0].metadata_stripped_with == "pillow"
    # Berkasnya berpindah dari titipan ke penyimpanan tetap.
    assert (storage / "lampiran" / rows[0].storage_key).exists()
    assert not list((storage / "lampiran" / "_menunggu").glob("*.jpg"))


def test_an_unknown_handle_is_refused(client: TestClient, session: Session) -> None:
    """Handle tidak dapat ditebak, dan tebakan tidak boleh menempelkan berkas orang lain."""
    response = client.post(
        "/api/v1/public/citizen-reports",
        json=_payload(session, attachments=["handle-yang-dikarang"]),
    )

    assert response.status_code == 400
    assert "kedaluwarsa" in response.json()["error"]["message"].lower()


def test_a_handle_cannot_be_used_twice(client: TestClient, session: Session) -> None:
    handle = client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    ).json()["handle"]

    first = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, attachments=[handle])
    )
    second = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, attachments=[handle])
    )

    assert first.status_code == 201
    assert second.status_code == 400


@pytest.mark.parametrize(
    "handle",
    [
        # Sebelum handle diperiksa bentuknya, nilai-nilai ini dipakai sebagai POLA pada
        # `glob` dan mencocoki titipan siapa pun yang sedang menunggu — cukup untuk
        # menempelkan berkas orang lain ke laporan sendiri.
        "*",
        "?" * 43,
        "[a-z]*",
        "../lampiran/apa-saja",
        "",
    ],
)
def test_a_handle_is_a_name_and_never_a_pattern(
    client: TestClient, session: Session, handle: str
) -> None:
    """Titipan orang lain tidak boleh dapat diklaim dengan pola."""
    # Ada satu titipan menunggu — justru itu yang hendak dicuri.
    client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    )

    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, attachments=[handle])
    )

    assert response.status_code == 400, f"handle {handle!r} diterima"


def test_more_attachments_than_allowed_are_refused(client: TestClient, session: Session) -> None:
    handles = [
        client.post(
            "/api/v1/public/attachments",
            files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
        ).json()["handle"]
        for _ in range(store.MAX_ATTACHMENTS_PER_REPORT + 1)
    ]

    response = client.post(
        "/api/v1/public/citizen-reports", json=_payload(session, attachments=handles)
    )

    assert response.status_code == 400


# --- 4. Hanya yang berwenang memverifikasi yang dapat membukanya -------------------------


def test_a_role_without_the_triage_permission_cannot_open_attachments(
    client: TestClient, session: Session
) -> None:
    """Membaca lampiran bukan tindakan pasif: ia memperlihatkan wajah orang.

    Menurut `config/rbac/permissions.yaml`, hanya Polsek (wilayahnya sendiri) dan
    Administrator (seluruhnya) memegang `citizen_report:write`. Pimpinan memutuskan
    rekomendasi, tidak memverifikasi laporan warga — dan karena itu tidak punya alasan
    melihat wajah orang di dalam berkasnya.
    """
    ticket = _submit_with_photo(client, session)
    leader = _make_user(session, "Pimpinan")

    response = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments", headers=_auth(client, leader)
    )

    assert response.status_code == 403


def test_a_verifier_sees_the_attachment_list(client: TestClient, session: Session) -> None:
    ticket = _submit_with_photo(client, session)
    officer = _make_user(session, "Administrator")

    body = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments", headers=_auth(client, officer)
    ).json()

    assert len(body["data"]) == 1
    assert body["data"][0]["available"] is True
    assert body["data"][0]["metadata_stripped_with"] == "pillow"
    assert body["coordinate_source"] == "KECAMATAN_CENTROID"


def test_downloading_an_attachment_leaves_a_trail(client: TestClient, session: Session) -> None:
    ticket = _submit_with_photo(client, session)
    officer = _make_user(session, "Administrator")
    headers = _auth(client, officer)

    listed = client.get(f"/api/v1/citizen-reports/{ticket}/attachments", headers=headers).json()[
        "data"
    ][0]
    response = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments/{listed['attachment_id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    # Berkas yang dikirim adalah yang sudah bersih — bukan yang diunggah.
    assert not Image.open(io.BytesIO(response.content)).getexif().get(0x010F)

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "READ_CITIZEN_REPORT_ATTACHMENT",
            AuditLog.resource_id == listed["attachment_id"],
        )
    )
    assert entry is not None
    assert entry.user_id == officer.user_id


def test_a_report_outside_the_users_area_is_not_found_rather_than_forbidden(
    client: TestClient, session: Session
) -> None:
    """`404`, bukan `403`.

    Menjawab "ada tetapi tidak boleh" memberi tahu keberadaan sebuah laporan kepada orang
    yang tidak berhak mengetahuinya.
    """
    ticket = _submit_with_photo(client, session)
    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None
    home = session.scalar(select(Location.polsek).where(Location.location_id == report.location_id))
    elsewhere = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None), Location.polsek != home)
    )
    assert elsewhere is not None

    stranger = _make_user(session, "Polsek", polsek=str(elsewhere))

    response = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments", headers=_auth(client, stranger)
    )

    assert response.status_code == 404


# --- 5. Masa retensi benar-benar dijalankan ----------------------------------------------


def test_retention_deletes_the_file_but_keeps_the_record(
    client: TestClient, session: Session, storage: Path
) -> None:
    ticket = _submit_with_photo(client, session)
    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None

    now = clock.reference_now()
    report.status = store.CLOSED_STATUS
    report.closed_at = now - timedelta(days=store.RETENTION_DAYS_AFTER_CLOSED + 1)
    session.flush()

    attachment = session.scalar(
        select(CitizenReportAttachment).where(CitizenReportAttachment.report_id == report.report_id)
    )
    assert attachment is not None
    path = storage / "lampiran" / attachment.storage_key
    assert path.exists()

    purged = store.purge_expired(session, now)
    session.flush()

    assert len(purged) == 1
    assert not path.exists(), "berkasnya harus benar-benar hilang dari cakram"
    # Barisnya dipertahankan: jejak bahwa penghapusan itu dijalankan adalah bagian dari
    # pertanggungjawaban, dan menghapusnya berarti menghapus buktinya juga.
    session.refresh(attachment)
    assert attachment.purged_at is not None


def test_retention_leaves_an_open_report_alone(
    client: TestClient, session: Session, storage: Path
) -> None:
    """Berkas yang masih dibutuhkan pemeriksaan tidak boleh hilang di tengah jalan."""
    ticket = _submit_with_photo(client, session)
    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None
    # Laporan masih terbuka: `closed_at` kosong, dan usianya tidak menjadi soal.
    report.closed_at = None
    session.flush()

    purged = store.purge_expired(session, clock.reference_now())

    assert purged == []


def test_a_purged_attachment_answers_gone_rather_than_missing(
    client: TestClient, session: Session
) -> None:
    ticket = _submit_with_photo(client, session)
    officer = _make_user(session, "Administrator")
    headers = _auth(client, officer)
    listed = client.get(f"/api/v1/citizen-reports/{ticket}/attachments", headers=headers).json()[
        "data"
    ][0]

    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None
    now = clock.reference_now()
    report.status = store.CLOSED_STATUS
    report.closed_at = now - timedelta(days=store.RETENTION_DAYS_AFTER_CLOSED + 1)
    session.flush()
    store.purge_expired(session, now)
    session.flush()

    response = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments/{listed['attachment_id']}",
        headers=headers,
    )

    # 410, bukan 404: berkasnya pernah ada dan sengaja dimusnahkan. Keduanya berbeda arti
    # bagi pemeriksa yang mencari tahu ke mana perginya sebuah bukti.
    assert response.status_code == 410

    still_listed = client.get(
        f"/api/v1/citizen-reports/{ticket}/attachments", headers=headers
    ).json()["data"]
    assert len(still_listed) == 1
    assert still_listed[0]["available"] is False
    assert still_listed[0]["purged_at"] is not None


def test_unused_upload_handles_are_swept_away(client: TestClient, storage: Path) -> None:
    """Titipan yang tidak pernah dipakai tidak boleh menumpuk selamanya."""
    client.post(
        "/api/v1/public/attachments",
        files={"berkas": ("bukti.jpg", _photo_with_exif(), "image/jpeg")},
    )
    staging = storage / "lampiran" / "_menunggu"
    assert list(staging.glob("*.jpg"))

    removed = store.sweep_staging(
        clock.reference_now() + timedelta(minutes=store.STAGING_TTL_MINUTES + 1)
    )

    assert removed == 1
    assert not list(staging.glob("*.jpg"))
    assert not list(staging.glob("*.tanda"))
