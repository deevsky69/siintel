"""Keputusan Pimpinan atas rencana patroli (`POST /patrol-plan/decisions`, migration 0011).

Human-in-the-loop: usulan dihitung sistem, yang berlaku ditentukan keputusan terakhir.
Yang dijaga: hanya pemegang `commander_decision:approve` yang memutus, usulan disalin saat
diputus, MODIFIED hanya dapat MEMILIH slot usulan (bukan menambah), penolakan wajib
beralasan, keputusan terakhir yang berlaku, dan pencocokan mengikuti rencana yang berlaku.
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
from prediksi_presisi_api.models import AuditLog, CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import patrol_plan as planning
from prediksi_presisi_api.services import visibility

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")

CUTOFF = date(2098, 12, 31)
PLAN = "/api/v1/patrol-plan"
DECISIONS = "/api/v1/patrol-plan/decisions"


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


def _user(session: Session, role_name: str) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
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


def _plant(session: Session, location: Location, day: date, hour: int, count: int) -> None:
    for _ in range(count):
        session.add(
            CrimeIncident(
                code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
                incident_type="CURANMOR",
                occurred_at=datetime.combine(day, time(hour=hour), tzinfo=UTC),
                incident_date=day,
                incident_time=time(hour=hour),
                time_known=True,
                location_id=location.location_id,
                data_source="UJI",
            )
        )
    session.flush()


@pytest.fixture
def proposal(session: Session) -> list[dict[str, object]]:
    """Dua slot usulan CURANMOR pada tahun dasar 2098, dan tiga kejadian 2099 pada slot pertama."""
    rules = planning.load_rules()
    rows = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    ).all()
    first, second = rows[0], rows[1]
    _plant(session, first, date(2098, 3, 3), 19, rules.minimum_incidents + 2)
    _plant(session, second, date(2098, 4, 4), 19, rules.minimum_incidents)
    _plant(session, first, date(2099, 5, 5), 20, 3)
    return [
        {"threat_type": "CURANMOR", "kelurahan": first.kelurahan, "block_start": 18},
        {"threat_type": "CURANMOR", "kelurahan": second.kelurahan, "block_start": 18},
    ]


# ---------------------------------------------------------------------------
# Kewenangan
# ---------------------------------------------------------------------------


def test_only_the_approving_role_may_decide(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(DECISIONS, json={"decision": "APPROVED"}, headers=headers)
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# Keputusan
# ---------------------------------------------------------------------------


def test_approval_snapshots_the_proposal_and_becomes_the_plan_in_force(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    leader = _user(session, "Pimpinan")
    headers = _auth(client, leader)
    before = client.get(PLAN, headers=headers).json()
    assert before["decision"] is None

    response = client.post(
        DECISIONS, json={"decision": "APPROVED", "reason": "sesuai kapasitas"}, headers=headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"].startswith("PPD-")
    assert body["decision"] == "APPROVED"
    assert body["target_year"] == 2099 and body["scope"] is None
    assert body["proposed_slots"] == body["slots_in_force"] >= 2

    after = client.get(PLAN, headers=headers).json()
    assert after["decision"]["code"] == body["code"]
    assert after["in_force"]["slots"] == body["slots_in_force"]

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "APPROVE_PATROL_PLAN", AuditLog.user_id == leader.user_id)
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None and entry.resource_type == "patrol_plan"
    assert entry.detail is not None and entry.detail["decision_code"] == body["code"]


def test_modification_keeps_only_the_chosen_slots_and_evaluation_follows(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.post(
        DECISIONS,
        json={"decision": "MODIFIED", "reason": "satu regu saja", "kept_slots": [proposal[0]]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["slots_in_force"] == 1

    plan = client.get(PLAN, headers=headers).json()
    assert plan["in_force"]["slots"] == 1
    assert plan["in_force"]["keys"][0]["kelurahan"] == proposal[0]["kelurahan"]
    # Usulan asli tetap utuh dan tetap ditampilkan berdampingan.
    assert sum(len(t["slots"]) for t in plan["threats"]) >= 2

    evaluation = client.get(f"{PLAN}/evaluation", headers=headers).json()
    assert evaluation["evaluated_plan"] == "in_force"
    curanmor = next(r for r in evaluation["per_threat"] if r["threat_type"] == "CURANMOR")
    assert curanmor["slots"] == 1 and curanmor["slots_hit"] == 1


def test_modification_cannot_add_slots_outside_the_proposal(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.post(
        DECISIONS,
        json={
            "decision": "MODIFIED",
            "kept_slots": [
                {"threat_type": "CURANMOR", "kelurahan": "Kelurahan Khayalan", "block_start": 0}
            ],
        },
        headers=headers,
    )
    assert response.status_code == 422, response.text
    assert "tidak ada pada usulan" in response.json()["error"]["message"]


def test_keeping_every_slot_is_an_approval_not_a_modification(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    plan = client.get(PLAN, headers=headers).json()
    every = [
        {
            "threat_type": s["threat_type"],
            "kelurahan": s["kelurahan"],
            "block_start": s["block_start"],
        }
        for t in plan["threats"]
        for s in t["slots"]
    ]
    response = client.post(
        DECISIONS, json={"decision": "MODIFIED", "kept_slots": every}, headers=headers
    )
    assert response.status_code == 422, response.text
    assert "APPROVED" in response.json()["error"]["message"]


def test_rejection_requires_a_reason_and_leaves_nothing_in_force(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    refused = client.post(DECISIONS, json={"decision": "REJECTED"}, headers=headers)
    assert refused.status_code == 422, refused.text

    response = client.post(
        DECISIONS, json={"decision": "REJECTED", "reason": "kapasitas belum ada"}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["slots_in_force"] == 0
    evaluation = client.get(f"{PLAN}/evaluation", headers=headers).json()
    assert evaluation["overall"]["slots"] == 0


def test_the_latest_decision_is_the_one_in_force_and_history_is_kept(
    client: TestClient, session: Session, proposal: list[dict[str, object]]
) -> None:
    headers = _auth(client, _user(session, "Pimpinan"))
    first = client.post(
        DECISIONS, json={"decision": "REJECTED", "reason": "tunggu"}, headers=headers
    ).json()
    second = client.post(DECISIONS, json={"decision": "APPROVED"}, headers=headers).json()

    plan = client.get(PLAN, headers=headers).json()
    assert plan["decision"]["code"] == second["code"]

    history = client.get(DECISIONS, headers=headers).json()["data"]
    codes = [row["code"] for row in history]
    assert codes.index(second["code"]) < codes.index(first["code"])
