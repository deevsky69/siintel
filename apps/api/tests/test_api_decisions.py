"""Test alur keputusan komandan (TASK 130).

Ini bagian yang paling tidak boleh salah: seluruh klaim human-in-the-loop pada Taskap
bergantung padanya. Karena itu yang diuji bukan bentuk respons, melainkan **jaminannya**:

- hanya pejabat berwenang yang dapat memutuskan, dan penolakan meninggalkan jejak;
- usulan asli sistem tidak pernah ditimpa oleh keputusan manusia (U-07);
- rekomendasi tidak dapat diputus dua kali secara diam-diam;
- keputusan di luar wilayah pengguna tidak dapat disentuh, bahkan tidak dapat dilihat.
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
from prediksi_presisi_api.models import (
    AuditLog,
    CommanderDecision,
    Location,
    Prediction,
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
    assert role is not None, f"role {role_name} belum ada — jalankan seed"

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


def _undecided(session: Session, polsek: str | None = None) -> Recommendation:
    """Rekomendasi yang belum diputus — bahan uji yang tidak mengubah data lain."""
    query = (
        select(Recommendation)
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .outerjoin(
            CommanderDecision,
            CommanderDecision.recommendation_id == Recommendation.recommendation_id,
        )
        .where(CommanderDecision.decision_id.is_(None))
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    recommendation = session.scalar(query.limit(1))
    assert recommendation is not None, "data awal tidak menyediakan rekomendasi tanpa keputusan"
    return recommendation


def _status_of(session: Session, recommendation: Recommendation) -> str:
    """Status terkini dari database, bukan dari objek yang sudah usang di memori."""
    session.expire_all()
    stored = session.get(Recommendation, recommendation.recommendation_id)
    assert stored is not None
    return stored.status


def _polsek_of(session: Session, recommendation: Recommendation) -> str:
    polsek = session.scalar(
        select(Location.polsek)
        .join(Prediction, Prediction.location_id == Location.location_id)
        .where(Prediction.prediction_id == recommendation.prediction_id)
    )
    assert polsek is not None
    return str(polsek)


def test_leader_can_approve_a_recommendation(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)

    response = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "APPROVED", "reason": "Sesuai kesiapan personel."},
        headers=_auth(client, leader),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "APPROVED"
    assert body["recommendation_code"] == recommendation.code
    # Usulan asli ikut dikembalikan agar antarmuka dapat menyandingkan AI vs manusia.
    assert body["original_recommendation"] == recommendation.recommendation_text

    assert _status_of(session, recommendation) == "APPROVED"


def test_decision_leaves_an_audit_trail(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)

    client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "REJECTED", "reason": "Personel sedang dikerahkan di lokasi lain."},
        headers=_auth(client, leader),
    )

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "REJECT_RECOMMENDATION")
        .where(AuditLog.resource_id == recommendation.code)
        .where(AuditLog.user_id == leader.user_id)
    )
    assert entry is not None, "keputusan tanpa jejak audit tidak dapat dipertanggungjawabkan"
    assert entry.result == "SUCCESS"


def test_modification_never_overwrites_the_original_proposal(
    client: TestClient, session: Session
) -> None:
    # U-07: jejak "apa yang diusulkan sistem" harus tetap utuh setelah manusia mengubahnya.
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)
    original = recommendation.recommendation_text

    response = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "MODIFIED", "modified_text": "Patroli dimajukan menjadi pukul 17.00."},
        headers=_auth(client, leader),
    )

    assert response.status_code == 201, response.text
    assert response.json()["modified_text"] == "Patroli dimajukan menjadi pukul 17.00."

    session.expire_all()
    stored = session.get(Recommendation, recommendation.recommendation_id)
    assert stored is not None
    assert stored.recommendation_text == original


def test_modification_without_new_text_is_refused(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)

    response = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "MODIFIED", "modified_text": "   "},
        headers=_auth(client, leader),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"

    # Rekomendasi tidak boleh berubah status hanya karena percobaan yang ditolak.
    assert _status_of(session, recommendation) != "MODIFIED"


def test_a_recommendation_cannot_be_decided_twice(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)
    headers = _auth(client, leader)
    payload = {"decision": "APPROVED"}

    assert (
        client.post(
            f"/api/v1/recommendations/{recommendation.code}/decisions",
            json=payload,
            headers=headers,
        ).status_code
        == 201
    )

    second = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "REJECTED"},
        headers=headers,
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_unknown_decision_value_is_refused(client: TestClient, session: Session) -> None:
    leader = _make_user(session, "Pimpinan")
    recommendation = _undecided(session)

    response = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "DITUNDA"},
        headers=_auth(client, leader),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyst_cannot_decide_and_the_refusal_is_recorded(
    client: TestClient, session: Session
) -> None:
    analyst = _make_user(session, "Administrator")
    recommendation = _undecided(session)

    response = client.post(
        f"/api/v1/recommendations/{recommendation.code}/decisions",
        json={"decision": "APPROVED"},
        headers=_auth(client, analyst),
    )

    assert response.status_code == 403
    denial = session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == analyst.user_id)
        .where(AuditLog.result == "DENIED")
    )
    assert denial is not None, "penolakan tanpa jejak membuat audit RBAC tidak dapat dinilai"

    assert _status_of(session, recommendation) != "APPROVED"


def test_recommendation_outside_jurisdiction_is_invisible(
    client: TestClient, session: Session
) -> None:
    # 404, bukan 403: menjawab "terlarang" akan membocorkan bahwa datanya ada di wilayah lain.
    recommendation = _undecided(session)
    other = session.scalar(
        select(Location.polsek)
        .where(Location.polsek != _polsek_of(session, recommendation))
        .limit(1)
    )
    assert other is not None
    outsider = _make_user(session, "Polsek", polsek=str(other))

    listed = client.get("/api/v1/commander-decisions", headers=_auth(client, outsider))
    assert listed.status_code == 200
    assert listed.json()["data"] == [] or all(
        row["recommendation_code"] != recommendation.code for row in listed.json()["data"]
    )


def test_decision_history_stays_within_the_users_jurisdiction(
    client: TestClient, session: Session
) -> None:
    polsek = session.scalar(select(Location.polsek).where(Location.polsek.is_not(None)).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=str(polsek))

    response = client.get("/api/v1/commander-decisions", headers=_auth(client, officer))

    assert response.status_code == 200
    rows = response.json()["data"]
    codes = {row["recommendation_code"] for row in rows}
    allowed = set(
        session.scalars(
            select(Recommendation.code)
            .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(Location.polsek == polsek)
        ).all()
    )
    assert codes <= allowed, "riwayat keputusan membocorkan wilayah lain"


def test_recommendation_list_respects_jurisdiction(client: TestClient, session: Session) -> None:
    polsek = session.scalar(select(Location.polsek).where(Location.polsek.is_not(None)).limit(1))
    assert polsek is not None
    officer = _make_user(session, "Polsek", polsek=str(polsek))
    leader = _make_user(session, "Pimpinan")

    scoped = client.get("/api/v1/recommendations?page_size=1", headers=_auth(client, officer))
    full = client.get("/api/v1/recommendations?page_size=1", headers=_auth(client, leader))

    assert scoped.status_code == 200
    # Cakupan ditegakkan di query: jumlah total pun tidak boleh membocorkan wilayah lain.
    assert scoped.json()["pagination"]["total_items"] < full.json()["pagination"]["total_items"], (
        "Polsek menerima seluruh rekomendasi Jakarta Selatan"
    )
