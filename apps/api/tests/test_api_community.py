"""Test endpoint kanal masyarakat (TASK 024).

Dua hal yang dijaga di sini:

1. **Cakupan wilayah benar-benar ditegakkan backend.** Akun `OWN_JURISDICTION` tidak
   menerima laporan di luar polseknya, termasuk tidak dalam jumlah total pada agregat —
   dan tidak pula lewat laporan yang belum tertaut ke sel grid.
2. **Setiap respons membawa `basis` yang menyatakan laporan belum memengaruhi risk score.**
   Kalimat itu bagian dari kontrak API, bukan hiasan: menghapusnya membuat layar
   menyajikan urgensi dan verifikasi sintetis seolah hasil penilaian model
   (spesifikasi §4, CLAUDE.md §27).
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
from prediksi_presisi_api.api.routers.community import DATA_STATUS
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CitizenReport, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.seeding.public import seed_public_data

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

    # Seluruh test kelompok ini membaca laporan masyarakat, jadi datanya dipastikan ada
    # di dalam transaksi test — bukan diandaikan sudah ter-seed di database bersama.
    seed_public_data(opened)
    opened.flush()

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


def _a_polsek(session: Session) -> str:
    """Polsek yang benar-benar memiliki laporan, supaya perbandingan cakupan bermakna."""
    polsek = session.scalar(
        select(Location.polsek)
        .join(CitizenReport, CitizenReport.location_id == Location.location_id)
        .limit(1)
    )
    assert polsek is not None
    return str(polsek)


# --------------------------------------------------------------------------------------
# Otorisasi
# --------------------------------------------------------------------------------------


def test_citizen_reports_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/citizen-reports").status_code == 401
    assert client.get("/api/v1/community/summary").status_code == 401


def test_role_without_the_permission_is_refused(client: TestClient, session: Session) -> None:
    """Peran Fungsi tidak memegang `citizen_report:read` (docs/14 §6)."""
    officer = _make_user(session, "Fungsi", polsek=None)

    for path in ("/api/v1/citizen-reports", "/api/v1/community/summary"):
        response = client.get(path, headers=_auth(client, officer))
        assert response.status_code == 403, path


# --------------------------------------------------------------------------------------
# Cakupan wilayah
# --------------------------------------------------------------------------------------


def test_jurisdiction_scope_narrows_the_list_and_its_total(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    polsek = _a_polsek(session)
    local = _make_user(session, "Polsek", polsek=polsek)

    everything = client.get("/api/v1/citizen-reports?page_size=1", headers=_auth(client, leader))
    scoped = client.get("/api/v1/citizen-reports?page_size=1", headers=_auth(client, local))
    assert everything.status_code == 200, everything.text
    assert scoped.status_code == 200, scoped.text

    total_all = everything.json()["pagination"]["total_items"]
    total_scoped = scoped.json()["pagination"]["total_items"]
    assert 0 < total_scoped < total_all


def test_scoped_account_never_receives_a_report_from_another_polsek(
    client: TestClient, session: Session
) -> None:
    polsek = _a_polsek(session)
    local = _make_user(session, "Polsek", polsek=polsek)

    response = client.get("/api/v1/citizen-reports?page_size=200", headers=_auth(client, local))
    assert response.status_code == 200, response.text

    rows = response.json()["data"]
    assert rows
    assert {row["polsek"] for row in rows} == {polsek}


def test_unmapped_reports_stay_out_of_a_scoped_account(
    client: TestClient, session: Session
) -> None:
    """Laporan tanpa wilayah tidak boleh bocor ke akun yang dibatasi wilayah.

    Kebalikannya juga diperiksa: akun tanpa batas wilayah **harus** melihatnya, sebab
    laporan yang belum terpetakan justru bagian dari antrean triase yang perlu ditangani.
    """
    leader = _make_user(session, "Pimpinan")
    polsek = _a_polsek(session)
    local = _make_user(session, "Polsek", polsek=polsek)

    wide = client.get("/api/v1/community/summary", headers=_auth(client, leader)).json()
    scoped = client.get("/api/v1/community/summary", headers=_auth(client, local)).json()

    assert wide["unmapped_reports"] > 0
    assert scoped["unmapped_reports"] == 0
    assert scoped["total_reports"] < wide["total_reports"]


def test_summary_areas_never_leave_the_users_jurisdiction(
    client: TestClient, session: Session
) -> None:
    polsek = _a_polsek(session)
    local = _make_user(session, "Polsek", polsek=polsek)

    summary = client.get("/api/v1/community/summary", headers=_auth(client, local)).json()

    assert summary["top_areas"]
    assert {area["polsek"] for area in summary["top_areas"]} == {polsek}
    assert {row["polsek"] for row in summary["recent_reports"]} == {polsek}


# --------------------------------------------------------------------------------------
# Penyaringan dan bentuk respons
# --------------------------------------------------------------------------------------


def test_status_filter_only_returns_that_stage(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")

    response = client.get(
        "/api/v1/citizen-reports?status=CLOSED&page_size=200", headers=_auth(client, leader)
    )
    assert response.status_code == 200, response.text

    rows = response.json()["data"]
    assert rows
    assert {row["status"] for row in rows} == {"CLOSED"}


def test_category_filter_only_returns_that_category(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    summary = client.get("/api/v1/community/summary", headers=headers).json()
    category = next(iter(summary["per_category"]))

    response = client.get(
        "/api/v1/citizen-reports", headers=headers, params={"category": category, "page_size": 200}
    )
    assert response.status_code == 200, response.text

    rows = response.json()["data"]
    assert rows
    assert {row["category"] for row in rows} == {category}


def test_unknown_filter_gives_an_empty_page_not_an_error(
    client: TestClient, session: Session
) -> None:
    """Keadaan kosong adalah jawaban yang sah — layar wajib punya Empty state (§23)."""
    leader = _make_user(session, "Pimpinan")

    response = client.get("/api/v1/citizen-reports?status=TIDAK_ADA", headers=_auth(client, leader))
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []
    assert response.json()["pagination"]["total_items"] == 0


def test_reports_never_carry_a_reporter_identity(client: TestClient, session: Session) -> None:
    """Bentuk respons tidak boleh menumbuhkan kembali identitas yang tabelnya tolak."""
    leader = _make_user(session, "Pimpinan")

    rows = client.get("/api/v1/citizen-reports?page_size=50", headers=_auth(client, leader)).json()[
        "data"
    ]

    forbidden = {"reporter", "reporter_id", "reporter_name", "nama", "nik", "phone", "email"}
    for row in rows:
        assert not (set(row) & forbidden), sorted(set(row) & forbidden)


def test_every_response_states_that_reports_do_not_affect_risk_score(
    client: TestClient, session: Session
) -> None:
    """Spesifikasi §4: laporan wajib melewati validasi sebelum boleh memengaruhi risiko.

    Belum satu pun tahapan itu ada, dan API harus mengatakannya — bukan mendiamkannya.
    """
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    for path in ("/api/v1/citizen-reports?page_size=1", "/api/v1/community/summary"):
        body = client.get(path, headers=headers).json()
        assert body["status"] == DATA_STATUS, path
        assert "BELUM memengaruhi risk score" in body["basis"], path
        assert "sintetis" in body["basis"], path


def test_summary_counts_match_the_list_totals(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    summary = client.get("/api/v1/community/summary", headers=headers).json()
    listing = client.get("/api/v1/citizen-reports?page_size=1", headers=headers).json()

    assert summary["total_reports"] == listing["pagination"]["total_items"]
    assert sum(summary["per_status"].values()) == summary["total_reports"]
    assert sum(summary["per_category"].values()) == summary["total_reports"]


def test_feedback_block_follows_its_own_permission(client: TestClient, session: Session) -> None:
    """Umpan balik ikut cakupan `community_feedback:read`, bukan cakupan laporan."""
    leader = _make_user(session, "Pimpinan")
    polsek = _a_polsek(session)
    local = _make_user(session, "Polsek", polsek=polsek)

    wide = client.get("/api/v1/community/summary", headers=_auth(client, leader)).json()
    scoped = client.get("/api/v1/community/summary", headers=_auth(client, local)).json()

    assert wide["feedback"] is not None
    assert wide["feedback"]["total"] > 0
    assert scoped["feedback"] is not None
    assert scoped["feedback"]["total"] < wide["feedback"]["total"]
