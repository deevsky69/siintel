"""Rencana patroli tahunan dan pencocokannya (`services/patrol_plan.py`).

Dijalankan di atas fixture sampel dengan batas tampilan dipasang pada 31 Desember 2098:
kejadian yang ditanam di 2098 menjadi "tahun dasar", kejadian 2099 menjadi "tahun
sasaran" yang hanya terlihat oleh pencocokan.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import patrol_plan as planning
from prediksi_presisi_api.services import visibility

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")

CUTOFF = date(2098, 12, 31)


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    visibility.install()
    monkeypatch.setattr(visibility, "display_cutoff", lambda: CUTOFF)
    db = create_engine(DATABASE_URL, future=True)
    connection = db.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    db.dispose()


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
        status="ACTIVE",
        must_change_password=False,
        polsek=polsek,
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


def _kelurahan_location(session: Session, index: int = 0) -> Location:
    rows = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    ).all()
    assert len(rows) > index
    return rows[index]


def _plant(
    session: Session,
    location: Location,
    day: date,
    hour: int | None,
    *,
    threat: str = "CURANMOR",
    count: int = 1,
) -> None:
    for _ in range(count):
        session.add(
            CrimeIncident(
                code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
                incident_type=threat,
                occurred_at=datetime.combine(day, time(hour=hour or 0), tzinfo=UTC),
                incident_date=day,
                incident_time=None if hour is None else time(hour=hour),
                time_known=hour is not None,
                location_id=location.location_id,
                data_source="UJI",
            )
        )
    session.flush()


# ---------------------------------------------------------------------------
# Aturan dan aritmetika
# ---------------------------------------------------------------------------


def test_rules_are_proposed_and_read_from_config() -> None:
    rules = planning.load_rules()
    assert rules.status == "PROPOSED"
    assert rules.max_slots_per_threat >= 1 and rules.minimum_incidents >= 1


def test_basis_window_covers_whole_calendar_months() -> None:
    assert planning._basis_window(date(2025, 12, 31), 12) == (date(2025, 1, 1), date(2025, 12, 31))
    assert planning._basis_window(date(2025, 12, 31), 3) == (date(2025, 10, 1), date(2025, 12, 31))


def test_overlap_is_100_for_identical_shapes_and_none_without_data() -> None:
    assert planning._overlap({0: 10, 3: 30}, {0: 1, 3: 3}) == 100.0
    assert planning._overlap({0: 10, 3: 10}, {0: 20, 6: 20}) == 50.0
    assert planning._overlap({}, {0: 1}) is None


# ---------------------------------------------------------------------------
# Usulan
# ---------------------------------------------------------------------------


def test_slots_are_ranked_by_basis_year_incidents_and_carry_their_numbers(
    session: Session,
) -> None:
    rules = planning.load_rules()
    strong = _kelurahan_location(session, 0)
    weak = _kelurahan_location(session, 1)
    _plant(session, strong, date(2098, 3, 3), 19, count=rules.minimum_incidents + 2)
    _plant(session, weak, date(2098, 4, 4), 19, count=rules.minimum_incidents)
    # Di bawah batas minimum: tidak diusulkan, berapa pun peringkatnya.
    _plant(session, weak, date(2098, 5, 5), 4, count=rules.minimum_incidents - 1)
    # Tahun sasaran tidak boleh ikut menyusun usulan.
    _plant(session, weak, date(2099, 5, 5), 4, count=50)

    plan = planning.build_plan(session)
    assert plan.target_year == 2099
    assert (plan.basis_from, plan.basis_to) == (date(2098, 1, 1), CUTOFF)
    curanmor = next(item for item in plan.threats if item.threat_type == "CURANMOR")
    # Seluruh kejadian tahun dasar dihitung sebagai dasar — termasuk yang di bawah batas slot.
    assert curanmor.basis_total == 3 * rules.minimum_incidents + 1
    assert [slot.unit.kelurahan for slot in curanmor.slots] == [strong.kelurahan, weak.kelurahan]
    assert curanmor.slots[0].unit.block == 18
    assert curanmor.slots[0].incidents == rules.minimum_incidents + 2
    assert curanmor.slots[0].rank == 1
    assert "kejadian CURANMOR" in curanmor.slots[0].as_dict()["why"]
    assert curanmor.slots[-1].cumulative_share_percent == curanmor.covered_share_percent


def test_incidents_without_an_hour_or_kelurahan_are_counted_not_slotted(
    session: Session,
) -> None:
    location = _kelurahan_location(session, 0)
    _plant(session, location, date(2098, 2, 2), None, count=4)
    plan = planning.build_plan(session)
    curanmor = next(item for item in plan.threats if item.threat_type == "CURANMOR")
    assert curanmor.basis_unknown_time == 4
    assert all(slot.incidents > 0 for slot in curanmor.slots)


# ---------------------------------------------------------------------------
# Pencocokan
# ---------------------------------------------------------------------------


def test_evaluation_reads_the_target_year_beyond_the_display_cutoff(session: Session) -> None:
    rules = planning.load_rules()
    hit = _kelurahan_location(session, 0)
    miss = _kelurahan_location(session, 1)
    _plant(session, hit, date(2098, 3, 3), 19, count=rules.minimum_incidents + 1)
    _plant(session, miss, date(2098, 4, 4), 19, count=rules.minimum_incidents)
    _plant(session, hit, date(2099, 6, 6), 20, count=3)  # jatuh di slot usulan
    _plant(session, hit, date(2099, 6, 7), 2, count=1)  # kelurahan sama, blok lain
    _plant(session, hit, date(2099, 6, 8), None, count=2)  # tanpa jam: tak terevaluasi

    plan = planning.build_plan(session)
    result = planning.evaluate_plan(session, plan)
    curanmor = next(row for row in result["per_threat"] if row["threat_type"] == "CURANMOR")

    assert result["target_year"] == 2099
    assert result["target_observed_to"] == "2099-06-08"
    assert curanmor["slots"] == 2 and curanmor["slots_hit"] == 1
    assert curanmor["slot_hit_rate_percent"] == 50.0
    assert curanmor["actual_incidents"] == 6
    assert curanmor["actual_evaluable"] == 4
    assert curanmor["actual_unknown_time"] == 2
    assert curanmor["covered_incidents"] == 3
    assert curanmor["coverage_percent"] == 75.0
    assert curanmor["hour_similarity_percent"] is not None
    hit_row = next(row for row in curanmor["slot_results"] if row["kelurahan"] == hit.kelurahan)
    assert hit_row["hit"] is True and hit_row["actual_incidents"] == 3
    assert result["status"] == "PROPOSED"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


def test_the_plan_endpoint_serves_the_plan_with_its_basis(
    client: TestClient, session: Session
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.get("/api/v1/patrol-plan", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PROPOSED" and body["target_year"] == 2099
    assert {row["threat_type"] for row in body["threats"]} == {"CURANMOR", "CURAT", "CURAS"}
    assert "plan_basis" in body


def test_the_evaluation_endpoint_requires_its_own_permission(
    client: TestClient, session: Session
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.get("/api/v1/patrol-plan/evaluation", headers=headers)
    assert response.status_code == 200, response.text
    assert "similarity_basis" in response.json()


def test_a_polsek_account_only_sees_its_own_jurisdiction(
    client: TestClient, session: Session
) -> None:
    own = _kelurahan_location(session, 0).polsek
    polsek_user = _user(session, "Polsek", polsek=own)
    headers = _auth(client, polsek_user)
    response = client.get("/api/v1/patrol-plan", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] is not None
    for threat in body["threats"]:
        assert {slot["polsek"] for slot in threat["slots"]} <= {body["scope"]}
