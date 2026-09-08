"""Test layar Pimpinan (TASK 150).

Yang dijaga di sini bukan bentuk respons, melainkan lima hal yang rusak tanpa terlihat:

1. **Cacah laporan cocok dengan database**, dan ketiga jenisnya dicacah terpisah.
2. **Laporan masyarakat tanpa lokasi tidak hilang diam-diam.** `JOIN` biasa membuangnya,
   dan layar akan menyebut angka yang lebih kecil daripada kenyataan tanpa ada yang tahu.
3. **Daftar "perlu perhatian" tetap memuat rekomendasi.** Tanpa jatah per jenis, seluruh
   barisnya terisi peringatan CRITICAL dan satu-satunya butir yang hanya dapat
   diselesaikan pimpinan tidak pernah terlihat.
4. **Tidak ada ambang di kode.** Nama status dan tingkat volume berasal dari config, dan
   responsnya selalu menyatakan bahwa pemetaan itu belum disetujui.
5. **Rekomendasi kebijakan benar-benar diturunkan dari data**, bukan kalimat tetap.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    CitizenReport,
    CrimeIncident,
    EarlyWarning,
    IntelligenceReport,
    Location,
    Permission,
    Recommendation,
    Role,
    RolePermission,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services.risk_engine import load_leadership_display

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


def _role_without(session: Session, missing: str) -> Role:
    """Role yang memegang seluruh permission kecuali satu — untuk menguji gerbangnya."""
    role = Role(
        code=f"ROLE-UJI-{uuid.uuid4().hex[:4]}", role_name=f"Uji {uuid.uuid4().hex[:4]}", level=6
    )
    session.add(role)
    session.flush()

    resource, _, action = missing.partition(":")
    for permission in session.scalars(select(Permission)).all():
        if permission.resource == resource and permission.action == action:
            continue
        session.add(
            RolePermission(
                role_id=role.role_id, permission_id=permission.permission_id, scope="ALL"
            )
        )
    session.flush()
    return role


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {user and response.json()['access_token']}"}


def _board(client: TestClient, user: User) -> dict[str, object]:
    response = client.get("/api/v1/dashboard/leadership", headers=_auth(client, user))
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


# --- 1. Cacah laporan -------------------------------------------------------------------


def test_reports_24h_counts_each_kind_against_the_database(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    body = _board(client, leader)
    reports = body["reports_24h"]
    assert isinstance(reports, dict)

    # Jendela diambil dari respons dan diurai kembali menjadi datetime: membandingkan
    # string ISO terhadap kolom timestamptz membuat PostgreSQL menolak querynya.
    start = datetime.fromisoformat(str(reports["window_start"]))
    end = datetime.fromisoformat(str(reports["window_end"]))

    incidents = session.scalar(
        select(func.count())
        .select_from(CrimeIncident)
        .where(CrimeIncident.occurred_at >= start, CrimeIncident.occurred_at <= end)
    )
    citizen = session.scalar(
        select(func.count())
        .select_from(CitizenReport)
        .where(CitizenReport.reported_at >= start, CitizenReport.reported_at <= end)
    )
    intelligence = session.scalar(
        select(func.count())
        .select_from(IntelligenceReport)
        .where(
            IntelligenceReport.report_date == date.fromisoformat(str(reports["intelligence_date"]))
        )
    )

    assert reports["crime_incidents"] == int(incidents or 0)
    assert reports["citizen_reports"] == int(citizen or 0)
    assert reports["intelligence_reports"] == int(intelligence or 0)
    assert reports["total"] == sum(
        int(reports[key])  # type: ignore[arg-type]
        for key in ("crime_incidents", "citizen_reports", "intelligence_reports")
    )


# --- 2. Laporan tanpa lokasi ------------------------------------------------------------


def test_reports_without_a_location_are_counted_not_dropped(
    client: TestClient, session: Session
) -> None:
    """Pimpinan tidak boleh menerima angka yang lebih kecil daripada isi database.

    Sebagian laporan masyarakat tidak punya `location_id`. `JOIN` biasa membuangnya tanpa
    jejak; yang terlihat di layar hanyalah angka yang lebih kecil, dan tidak ada cara
    membedakannya dari keadaan yang memang lebih sepi.
    """
    without_location = session.scalar(
        select(func.count())
        .select_from(CitizenReport)
        .where(CitizenReport.location_id.is_(None), CitizenReport.status == "RECEIVED")
    )
    assert without_location, "data dummy tidak memuat laporan tanpa lokasi — test ini sia-sia"

    expected = session.scalar(
        select(func.count()).select_from(CitizenReport).where(CitizenReport.status == "RECEIVED")
    )

    leader = _make_user(session, "Pimpinan")
    body = _board(client, leader)

    attention = body["needs_attention"]
    assert isinstance(attention, dict)
    citizen_item = next(item for item in attention["items"] if item["kind"] == "CITIZEN_REPORT")
    assert citizen_item["rank"] == int(expected or 0)


def test_reports_without_a_location_stay_hidden_from_a_scoped_user(
    client: TestClient, session: Session
) -> None:
    """Laporan tanpa lokasi tidak dapat dipastikan berada di wilayah siapa pun.

    Menampilkannya kepada pengguna Polsek berarti menebak — dan tebakan itu akan terbaca
    sebagai laporan di wilayahnya.
    """
    polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert polsek is not None

    officer = _make_user(session, "Polsek", polsek=polsek)
    body = _board(client, officer)

    scoped_expected = session.scalar(
        select(func.count())
        .select_from(CitizenReport)
        .join(Location, Location.location_id == CitizenReport.location_id)
        .where(CitizenReport.status == "RECEIVED", Location.polsek == polsek)
    )

    attention = body["needs_attention"]
    assert isinstance(attention, dict)
    citizen_items = [item for item in attention["items"] if item["kind"] == "CITIZEN_REPORT"]
    counted = citizen_items[0]["rank"] if citizen_items else 0
    assert counted == int(scoped_expected or 0)


# --- 3. Daftar perlu perhatian ----------------------------------------------------------


def test_attention_list_keeps_room_for_decisions_only_the_leader_can_make(
    client: TestClient, session: Session
) -> None:
    """Rekomendasi yang menunggu keputusan harus tetap terlihat.

    Ini penjaga terhadap regresi yang paling mudah terjadi: mengurutkan daftar menurut skor
    terlihat lebih obyektif, tetapi pada data ini seluruh barisnya lalu terisi peringatan
    CRITICAL, dan pimpinan tidak pernah melihat satu pun rekomendasi yang menunggunya.
    """
    pending = session.scalar(
        select(func.count())
        .select_from(Recommendation)
        .where(Recommendation.status == "PENDING_REVIEW")
    )
    active = session.scalar(
        select(func.count()).select_from(EarlyWarning).where(EarlyWarning.status == "ACTIVE")
    )
    assert pending and active, "data dummy tidak memuat keduanya — test ini tidak menguji apa pun"

    leader = _make_user(session, "Pimpinan")
    attention = _board(client, leader)["needs_attention"]
    assert isinstance(attention, dict)

    kinds = {item["kind"] for item in attention["items"]}
    assert "RECOMMENDATION" in kinds
    assert "EARLY_WARNING" in kinds


def test_attention_list_only_holds_what_still_waits_for_a_person(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    attention = _board(client, leader)["needs_attention"]
    assert isinstance(attention, dict)

    for item in attention["items"]:
        if item["kind"] != "EARLY_WARNING":
            continue
        warning = session.scalar(select(EarlyWarning).where(EarlyWarning.code == item["code"]))
        assert warning is not None
        assert warning.status == "ACTIVE", "peringatan yang sudah diterima tidak menunggu siapa pun"


# --- 4. Ambang berasal dari config ------------------------------------------------------


def test_area_status_uses_the_mapping_from_config_and_says_it_is_unapproved(
    client: TestClient, session: Session
) -> None:
    display = load_leadership_display()
    leader = _make_user(session, "Pimpinan")
    area_status = _board(client, leader)["area_status"]
    assert isinstance(area_status, dict)

    assert area_status["mapping_status"] == display.status
    assert display.status != "FINAL", "pemetaan ini belum disetujui siapa pun"
    assert "belum disetujui" in str(area_status["basis"])

    for area in area_status["areas"]:
        expected = display.status_for(str(area["risk_class"]))
        assert area["status"] == expected["status"], area
        assert area["label"] == expected["label"], area


def test_area_status_follows_the_same_definition_the_map_uses(
    client: TestClient, session: Session
) -> None:
    """Skor kecamatan = sel tertinggi, sama seperti `/map/current-risk`.

    Dua layar yang menjawab "berapa risiko di Tebet" dengan angka berbeda akan saling
    meruntuhkan, dan tidak ada di layar yang menunjukkan mana yang benar.
    """
    leader = _make_user(session, "Pimpinan")
    headers = _auth(client, leader)

    board = client.get("/api/v1/dashboard/leadership", headers=headers).json()
    map_layer = client.get("/api/v1/map/current-risk", headers=headers).json()

    on_map = {area["kecamatan"]: area["risk_score"] for area in map_layer["areas"]}
    for area in board["area_status"]["areas"]:
        assert area["risk_score"] == on_map[area["kecamatan"]], area["kecamatan"]


def test_top_areas_are_ranked_by_report_volume_using_config_thresholds(
    client: TestClient, session: Session
) -> None:
    display = load_leadership_display()
    leader = _make_user(session, "Pimpinan")
    top = _board(client, leader)["top_report_areas"]
    assert isinstance(top, dict)
    assert top["areas"], "data dummy tidak memuat laporan pada jendela ini"

    counts = [int(area["reports"]) for area in top["areas"]]
    assert counts == sorted(counts, reverse=True), "daftar harus menurun menurut jumlah laporan"
    assert top["peak_reports"] == counts[0]

    for area in top["areas"]:
        expected = display.volume_for(int(area["reports"]), int(top["peak_reports"]))
        assert area["level"] == expected["level"], area
        assert area["level_label"] == expected["level_label"], area

    assert "bukan kelas risiko" in str(top["basis"])


def test_the_leadership_screen_never_calls_report_volume_a_risk_class(
    client: TestClient, session: Session
) -> None:
    """Jumlah laporan tidak ditimbang dan tidak dinormalkan — ia tidak punya kelas risiko."""
    leader = _make_user(session, "Pimpinan")
    top = _board(client, leader)["top_report_areas"]
    assert isinstance(top, dict)

    for area in top["areas"]:
        assert "risk_class" not in area
        assert "risk_score" not in area


# --- 5. Rekomendasi kebijakan -----------------------------------------------------------


def test_policy_recommendations_are_derived_from_the_numbers_on_the_same_screen(
    client: TestClient, session: Session
) -> None:
    """Setiap butir menyebut angka asalnya, dan angkanya harus benar-benar cocok.

    Kalimat tetap yang kebetulan terdengar masuk akal adalah kegagalan yang paling sulit
    terlihat: ia tidak pernah salah dan tidak pernah berubah.
    """
    leader = _make_user(session, "Pimpinan")
    body = _board(client, leader)
    policy = body["policy"]
    assert isinstance(policy, dict)
    assert policy["recommendations"], "tidak satu pun rekomendasi terbentuk dari data ini"

    for row in policy["recommendations"]:
        assert row["source"] == "RULE", "belum ada model — menyebutnya keluaran AI itu fiktif"
        assert row["basis"], row
        # Saran yang dasarnya tidak dapat diperiksa sama saja dengan saran tanpa dasar.
        assert str(row["href"]).startswith("/"), row

    issues = body["prominent_issues"]
    assert isinstance(issues, dict)
    rising = [row for row in issues["issues"] if int(row["change"]) > 0]
    if rising:
        biggest = max(rising, key=lambda row: int(row["change"]))
        operations = [
            row for row in policy["recommendations"] if "Operasi khusus" in str(row["action"])
        ]
        assert operations, "kenaikan terbesar tidak menghasilkan rekomendasi apa pun"
        assert str(biggest["threat_type"]) in str(operations[0]["action"])
        assert str(biggest["incidents"]) in str(operations[0]["basis"])
        # Tautannya harus membawa penyaring ke jenis yang sama dengan yang disebut butir
        # ini — bukan ke analitik tanpa penyaring, yang justru menyembunyikan angkanya.
        assert operations[0]["href"] == f"/analitik?jenis={biggest['threat_type']}"

    top_area = body["priority_areas"][0] if body["priority_areas"] else None
    if top_area is not None:
        patrols = [
            row for row in policy["recommendations"] if "Tambah patroli" in str(row["action"])
        ]
        if patrols:
            assert patrols[0]["href"] == f"/wilayah/{quote(str(top_area['kecamatan']))}"


def test_prominent_issues_compare_against_the_previous_window_of_equal_length(
    client: TestClient, session: Session
) -> None:
    leader = _make_user(session, "Pimpinan")
    issues = _board(client, leader)["prominent_issues"]
    assert isinstance(issues, dict)

    current = (
        date.fromisoformat(str(issues["window_to"]))
        - date.fromisoformat(str(issues["window_from"]))
    ).days
    previous = (
        date.fromisoformat(str(issues["previous_to"]))
        - date.fromisoformat(str(issues["previous_from"]))
    ).days
    assert current == previous
    assert date.fromisoformat(str(issues["previous_to"])) < date.fromisoformat(
        str(issues["window_from"])
    )

    for row in issues["issues"]:
        assert row["change"] == int(row["incidents"]) - int(row["previous_incidents"])


# --- Kewenangan -------------------------------------------------------------------------


def test_a_scoped_user_only_sees_their_own_jurisdiction(
    client: TestClient, session: Session
) -> None:
    polsek = session.scalar(
        select(Location.polsek).where(Location.polsek.is_not(None)).order_by(Location.polsek)
    )
    assert polsek is not None

    officer = _make_user(session, "Polsek", polsek=polsek)
    body = _board(client, officer)

    allowed = set(
        session.scalars(
            select(Location.kecamatan).where(Location.polsek == polsek).distinct()
        ).all()
    )
    area_status = body["area_status"]
    top = body["top_report_areas"]
    assert isinstance(area_status, dict)
    assert isinstance(top, dict)

    assert {area["kecamatan"] for area in area_status["areas"]} <= allowed
    assert {area["kecamatan"] for area in top["areas"]} <= allowed


def test_the_screen_is_closed_without_dashboard_read(client: TestClient, session: Session) -> None:
    role = _role_without(session, "dashboard:read")
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

    response = client.get("/api/v1/dashboard/leadership", headers=_auth(client, user))

    assert response.status_code == 403, response.text
