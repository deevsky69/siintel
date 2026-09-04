"""Test notifikasi per peran (TASK 164).

Aturan yang diuji di sini hanya satu, tetapi ia menentukan seluruh modulnya:

**Notifikasi adalah pekerjaan yang menunggu Anda, bukan kabar tentang apa yang terjadi.**

Konsekuensinya dapat diuji: sumber notifikasi diikat ke permission **tindakan**, bukan
permission baca. Seorang Pimpinan yang dapat membaca laporan masyarakat tetapi tidak dapat
memverifikasinya **tidak** menerima notifikasi tentangnya — memberitahunya hanya menambah
kecemasan tanpa jalan keluar.

Test yang hanya memeriksa "notifikasi muncul" akan tetap hijau ketika ikatan itu longgar
menjadi permission baca, dan lencananya perlahan berubah menjadi umpan berita yang sama
bagi semua orang.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    CitizenReport,
    EarlyWarning,
    Location,
    Recommendation,
    Role,
    User,
)
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


def _feed(client: TestClient, user: User) -> dict[str, object]:
    response = client.get("/api/v1/notifications", headers=_auth(client, user))
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def _kinds(body: dict[str, object]) -> set[str]:
    groups = body["groups"]
    assert isinstance(groups, list)
    return {str(group["kind"]) for group in groups}


# --- Aturan pokok: terikat pada permission TINDAKAN --------------------------------------


def test_a_leader_is_told_about_decisions_only_they_can_make(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")

    kinds = _kinds(_feed(client, leader))

    assert "DECISION" in kinds, "Pimpinan memegang commander_decision:approve"


def test_a_leader_is_not_told_about_work_they_cannot_do(
    client: TestClient, session: Session
) -> None:
    """Inilah pembeda antara antrean tugas dan umpan berita.

    Pimpinan **dapat membaca** laporan masyarakat dan peringatan, tetapi tidak dapat
    memverifikasi maupun menerimanya. Memberitahunya hanya menambah kecemasan tanpa jalan
    keluar — dan lencana yang selalu merah berhenti dilihat orang.
    """
    leader = _make_user(session, "Pimpinan")

    kinds = _kinds(_feed(client, leader))

    assert "CITIZEN_REPORT" not in kinds, "Pimpinan tidak memegang citizen_report:write"
    assert "WARNING" not in kinds, "Pimpinan tidak memegang warning:acknowledge"
    assert "PREDICTION" not in kinds, "Pimpinan tidak memegang prediction:publish"


def test_a_polsek_officer_is_told_about_the_work_they_do(
    client: TestClient, session: Session
) -> None:
    polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    kinds = _kinds(_feed(client, officer))

    assert "WARNING" in kinds, "Polsek memegang warning:acknowledge"
    assert "CITIZEN_REPORT" in kinds, "Polsek memegang citizen_report:write"
    assert "DECISION" not in kinds, "yang memutuskan rekomendasi bukan Polsek"


def test_two_roles_receive_different_queues(client: TestClient, session: Session) -> None:
    """Permintaan pemilik proyek berbunyi 'sesuai fungsi masing-masing peran'.

    Bila kedua peran menerima daftar yang sama, seluruh modul ini gagal pada maksudnya —
    dan kegagalan itu tidak akan terlihat dari layar mana pun.
    """
    leader = _make_user(session, "Pimpinan")
    admin = _make_user(session, "Administrator")

    assert _kinds(_feed(client, leader)) != _kinds(_feed(client, admin))


# --- Angka harus benar ------------------------------------------------------------------


def test_the_counts_match_the_database(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    body = _feed(client, leader)
    groups = body["groups"]
    assert isinstance(groups, list)

    pending = session.scalar(
        select(func.count())
        .select_from(Recommendation)
        .where(Recommendation.status == "PENDING_REVIEW")
    )
    decisions = next(group for group in groups if group["kind"] == "DECISION")

    assert decisions["total"] == int(pending or 0)
    assert body["total"] == sum(int(group["total"]) for group in groups)


def test_a_scoped_officer_only_counts_their_own_jurisdiction(
    client: TestClient, session: Session
) -> None:
    polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    groups = _feed(client, officer)["groups"]
    assert isinstance(groups, list)
    warnings = next(group for group in groups if group["kind"] == "WARNING")

    expected = session.scalar(
        select(func.count())
        .select_from(EarlyWarning)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(EarlyWarning.status == "ACTIVE", Location.polsek == polsek)
    )
    everywhere = session.scalar(
        select(func.count()).select_from(EarlyWarning).where(EarlyWarning.status == "ACTIVE")
    )

    assert warnings["total"] == int(expected or 0)
    assert int(expected or 0) < int(everywhere or 0), (
        "data dummy tidak memuat peringatan di luar wilayah ini — "
        "pemeriksaan cakupan tidak menguji apa pun"
    )


def test_reports_without_a_location_stay_out_of_a_scoped_queue(
    client: TestClient, session: Session
) -> None:
    """Laporan tanpa lokasi tidak dapat dipastikan berada di wilayah siapa pun.

    Memasukkannya ke antrean petugas ber-cakupan berarti menugaskan pekerjaan yang belum
    tentu miliknya.
    """
    orphan = session.scalar(
        select(func.count())
        .select_from(CitizenReport)
        .where(CitizenReport.status == "RECEIVED", CitizenReport.location_id.is_(None))
    )
    assert orphan, "data dummy tidak memuat laporan tanpa lokasi — test ini sia-sia"

    polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=polsek)

    groups = _feed(client, officer)["groups"]
    assert isinstance(groups, list)
    reports = next(group for group in groups if group["kind"] == "CITIZEN_REPORT")

    scoped = session.scalar(
        select(func.count())
        .select_from(CitizenReport)
        .join(Location, Location.location_id == CitizenReport.location_id)
        .where(CitizenReport.status == "RECEIVED", Location.polsek == polsek)
    )
    assert reports["total"] == int(scoped or 0)


# --- Bentuk respons ---------------------------------------------------------------------


def test_empty_queues_are_kept_rather_than_dropped(client: TestClient, session: Session) -> None:
    """ "Nol peringatan menunggu" adalah kabar baik yang pantas terbaca.

    Menghilangkan barisnya membuat pengguna tidak dapat membedakan "tidak ada" dari
    "tidak diperiksa".
    """
    admin = _make_user(session, "Administrator")
    groups = _feed(client, admin)["groups"]
    assert isinstance(groups, list)

    for group in groups:
        assert "total" in group
        assert isinstance(group["items"], list)
        assert len(group["items"]) <= 3, "daftar contoh harus tetap pendek"


def test_every_group_offers_a_way_to_act(client: TestClient, session: Session) -> None:
    # Notifikasi tanpa jalan menuju pekerjaannya hanya pemberitahuan.
    admin = _make_user(session, "Administrator")
    groups = _feed(client, admin)["groups"]
    assert isinstance(groups, list)
    assert groups, "Administrator seharusnya punya beberapa antrean"

    for group in groups:
        assert group["href"], group["kind"]
        assert group["action"], group["kind"]


def test_the_feed_states_that_it_is_a_work_queue(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    assert "MENUNGGU ANDA" in str(_feed(client, leader)["basis"])
