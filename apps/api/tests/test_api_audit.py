"""Test penelusuran jejak audit (TASK 142).

Yang paling penting di berkas ini bukan bentuk responsnya, melainkan dua sifat yang
membuat jejak audit bernilai sebagai bukti:

- ia **hanya-tambah** — tidak ada jalan mengubah maupun menghapusnya, termasuk bagi
  Administrator, sebab catatan yang dapat disunting bukan bukti;
- ia memuat **penolakan**, bukan hanya keberhasilan — audit yang hanya mencatat yang
  berhasil tidak dapat dipakai menilai apakah pembatasan kewenangan bekerja.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105

#: Metode HTTP yang mengubah keadaan. Tidak satu pun boleh ada pada jejak audit.
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

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


def _make_user(session: Session, role_name: str) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None, f"role {role_name} belum ada — jalankan seed"

    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
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


def test_the_audit_trail_offers_no_way_to_write() -> None:
    """Hanya-tambah bukan kesepakatan, melainkan ketiadaan jalan.

    Diperiksa terhadap skema OpenAPI, bukan `app.routes`. Penulisan pertama test ini
    menelusuri `app.routes` dan **lulus tanpa memeriksa apa pun**: versi FastAPI ini
    menyimpan router yang di-include sebagai satu objek `_IncludedRouter` alih-alih
    meratakan rutenya, sehingga himpunan yang diperiksa selalu kosong. Menambahkan
    endpoint DELETE sungguhan pun tidak membuatnya gagal.

    Karena itu ada dua penegasan di bawah: satu memastikan rute audit memang ditemukan,
    satu lagi memastikan tak satu pun di antaranya dapat menulis. Yang pertama menjaga
    yang kedua agar tidak kembali menjadi hiasan.
    """
    paths = app.openapi()["paths"]
    audit_paths = {path: spec for path, spec in paths.items() if "audit" in path}

    assert audit_paths, (
        "tidak ada rute audit yang ditemukan — pemeriksaan ini tidak memeriksa apa pun"
    )

    writable = {
        (path, method.upper())
        for path, spec in audit_paths.items()
        for method in spec
        if method.upper() in WRITE_METHODS
    }

    assert not writable, (
        f"jejak audit memiliki endpoint tulis {writable}; catatan yang dapat disunting bukan bukti"
    )


def _a_refusal(client: TestClient, session: Session) -> None:
    """Menimbulkan satu penolakan sungguhan, lalu memastikan ia tercatat.

    Percobaan masuk dengan kata sandi yang salah adalah jalur penolakan yang benar-benar
    ada di aplikasi, bukan baris yang disisipkan langsung ke tabel. Yang diuji karena itu
    tetap rantai penuhnya: permintaan ditolak → audit menulisnya → daftar audit
    menampilkannya.

    Sebelum pembantu ini ada, ketiga uji di bawah bergantung pada penolakan yang KEBETULAN
    sudah ada di basis data. Keduanya lulus selama seseorang pernah salah memasukkan kata
    sandi, dan gagal pada basis data yang baru di-seed — `data/sample/audit_logs.csv`
    tidak dimuat perintah seed mana pun, dan seluruh 400 barisnya pun berstatus SUCCESS.
    Uji yang hasilnya bergantung pada riwayat pemakaian tidak menguji apa pun.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "akun.tidak.ada", "password": "kata-sandi-yang-salah"},
    )
    assert response.status_code == 401, response.text
    session.flush()


def test_refusals_are_visible_not_just_successes(client: TestClient, session: Session) -> None:
    """Inilah yang membuat audit dapat dipakai menilai RBAC."""
    reader = _make_user(session, "Administrator")
    _a_refusal(client, session)

    response = client.get(
        "/api/v1/audit-logs?result=DENIED&page_size=5", headers=_auth(client, reader)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pagination"]["total_items"] > 0, (
        "tidak ada satu pun penolakan tercatat — audit tanpa DENIED tidak membuktikan apa pun"
    )
    assert all(row["result"] == "DENIED" for row in body["data"])


def test_system_events_are_marked_not_attributed(client: TestClient, session: Session) -> None:
    """Peristiwa tanpa pelaku ditandai apa adanya, bukan diisi nama pengganti."""
    reader = _make_user(session, "Administrator")
    session.add(
        AuditLog(action="SYSTEM_UJI", resource_type="system", result="SUCCESS", user_id=None)
    )
    session.flush()

    response = client.get("/api/v1/audit-logs?action=SYSTEM_UJI", headers=_auth(client, reader))

    rows = response.json()["data"]
    assert rows and rows[0]["username"] is None


def test_a_role_without_the_permission_is_refused(client: TestClient, session: Session) -> None:
    """Peran Polsek tidak berwenang membaca audit, dan penolakannya ikut tercatat.

    Kewenangan itu dicabut karena `audit_logs` tidak punya kolom lokasi, sehingga
    cakupan wilayah mustahil ditegakkan — memberikannya berarti memberi akses penuh.
    """
    officer = _make_user(session, "Polsek")

    response = client.get("/api/v1/audit-logs", headers=_auth(client, officer))

    assert response.status_code == 403
    denial = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == officer.user_id)
        .where(AuditLog.result == "DENIED")
    )
    assert denial is not None


def test_a_single_day_range_includes_that_whole_day(client: TestClient, session: Session) -> None:
    """Awal dan akhir yang sama harus mencakup seluruh hari itu.

    Tanpa perlakuan ini, memilih satu tanggal tidak mengembalikan apa pun — dan pengguna
    akan menyimpulkan tidak ada aktivitas pada hari itu.
    """
    reader = _make_user(session, "Administrator")
    # Satu peristiwa dipastikan ada lebih dulu; tanpa itu uji ini hanya berlaku pada basis
    # data yang kebetulan sudah dipakai.
    _a_refusal(client, session)
    latest = session.scalar(select(AuditLog.timestamp).order_by(AuditLog.timestamp.desc()))
    assert latest is not None
    day = latest.date()

    response = client.get(
        f"/api/v1/audit-logs?date_from={day}&date_to={day}", headers=_auth(client, reader)
    )

    assert response.status_code == 200
    assert response.json()["pagination"]["total_items"] > 0


def test_an_inverted_range_is_refused(client: TestClient, session: Session) -> None:
    reader = _make_user(session, "Administrator")
    today = date(2025, 12, 31)

    response = client.get(
        f"/api/v1/audit-logs?date_from={today}&date_to={today - timedelta(days=1)}",
        headers=_auth(client, reader),
    )

    assert response.status_code == 400


def test_the_summary_leads_with_refusals(client: TestClient, session: Session) -> None:
    reader = _make_user(session, "Administrator")
    _a_refusal(client, session)

    response = client.get("/api/v1/audit-logs/summary", headers=_auth(client, reader))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] > 0
    assert body["recent_refusals"], "ringkasan tidak menampilkan satu pun penolakan"
    assert all(row["result"] in {"DENIED", "FAILED"} for row in body["recent_refusals"])
    # Sifat yang membuat jejak ini bernilai dinyatakan pada responsnya, bukan hanya di kode.
    assert body["append_only_basis"]
    assert body["scope_basis"]


def test_the_summary_counts_agree_with_the_listing(client: TestClient, session: Session) -> None:
    """Ringkasan dan daftar harus menjawab angka yang sama."""
    reader = _make_user(session, "Administrator")
    headers = _auth(client, reader)

    summary = client.get("/api/v1/audit-logs/summary", headers=headers).json()
    listed = client.get("/api/v1/audit-logs?page_size=1", headers=headers).json()

    assert summary["total"] == listed["pagination"]["total_items"]
