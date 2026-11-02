"""SIGAP WARGA: ringkasan wilayah publik dan Survey Rasa Aman."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers import reviews as reviews_router
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AreaReview, AuditLog, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


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
    reviews_router.limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reviews_router.limiter.reset()


def _kelurahan(session: Session) -> Location:
    row = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    )
    assert row is not None
    return row


def _login(client: TestClient, session: Session, role_name: str) -> dict[str, str]:
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
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- ringkasan wilayah -------------------------------------------------------------------


def test_public_summary_is_open_simple_and_free_of_predictions(client: TestClient) -> None:
    response = client.get("/api/v1/public/areas/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PROPOSED" and "tertil" in body["basis"]
    assert len(body["months"]) == 12
    assert body["areas"], "master kelurahan kosong"
    area = body["areas"][0]
    assert set(area) == {
        "kelurahan", "kecamatan", "polsek", "total", "level", "by_threat", "by_month",
        "rating", "rating_count",
    }  # fmt: skip
    assert area["level"] in {"RENDAH", "SEDANG", "TINGGI"}
    assert len(area["by_month"]) == 12
    # Tidak ada skor, prediksi, koordinat, maupun kode kejadian pada respons publik.
    text = response.text
    for forbidden in ("risk_score", "confidence", "prediction", "latitude", "KJD-"):
        assert forbidden not in text, forbidden
    levels = {row["level"] for row in body["areas"]}
    assert levels <= {"RENDAH", "SEDANG", "TINGGI"}
    assert body["kecamatan"] and body["kecamatan"][0]["level"] in levels | {
        "RENDAH",
        "SEDANG",
        "TINGGI",
    }


# --- survey rasa aman --------------------------------------------------------------------


def test_a_review_is_anonymous_pending_and_rate_limited(
    client: TestClient, session: Session
) -> None:
    area = _kelurahan(session)
    body = {
        "kecamatan": area.kecamatan,
        "kelurahan": area.kelurahan,
        "rating": 4,
        "comment": "Cukup aman, lampu jalan terang.",
    }
    response = client.post("/api/v1/public/reviews", json=body)
    assert response.status_code == 201, response.text
    code = response.json()["code"]
    assert code.startswith("ULS-") and response.json()["status"] == "PENDING"

    review = session.scalar(select(AreaReview).where(AreaReview.code == code))
    assert review is not None and review.status == "PENDING"
    assert not any(c.name in ("name", "phone", "chat_id") for c in AreaReview.__table__.columns)

    # Identitas ditolak, nilai di luar 1-5 ditolak, kelurahan asing ditolak.
    assert client.post("/api/v1/public/reviews", json={**body, "nama": "Budi"}).status_code == 400
    assert client.post("/api/v1/public/reviews", json={**body, "rating": 9}).status_code == 400
    assert (
        client.post("/api/v1/public/reviews", json={**body, "kelurahan": "Antah"}).status_code
        == 400
    )

    # Belum tayang: tidak muncul di kanal publik, dan rata-rata belum ada.
    shown = client.get("/api/v1/public/reviews", params={"kelurahan": area.kelurahan}).json()
    assert code not in [row["code"] for row in shown["data"]]

    # Kuota 3/jam per alamat.
    client.post("/api/v1/public/reviews", json=body)
    client.post("/api/v1/public/reviews", json=body)
    assert client.post("/api/v1/public/reviews", json=body).status_code == 429

    entry = session.scalar(select(AuditLog).where(AuditLog.resource_id == code))
    assert entry is not None and entry.action == "SUBMIT_AREA_REVIEW" and entry.user_id is None


def test_moderation_publishes_and_only_published_count(
    client: TestClient, session: Session
) -> None:
    area = _kelurahan(session)
    body = {
        "kecamatan": area.kecamatan,
        "kelurahan": area.kelurahan,
        "rating": 5,
        "comment": "Patroli sering lewat.",
    }
    code = client.post("/api/v1/public/reviews", json=body).json()["code"]

    assert client.get("/api/v1/reviews").status_code == 401
    assert (
        client.get("/api/v1/reviews", headers=_login(client, session, "Polsek")).status_code == 403
    )

    admin = _login(client, session, "Administrator")
    queue = client.get("/api/v1/reviews?status=PENDING", headers=admin).json()
    assert code in [row["code"] for row in queue["data"]]

    published = client.post(
        f"/api/v1/reviews/{code}/moderate", json={"decision": "PUBLISH"}, headers=admin
    )
    assert published.status_code == 200 and published.json()["status"] == "PUBLISHED"
    assert (
        client.post(
            f"/api/v1/reviews/{code}/moderate", json={"decision": "PUBLISH"}, headers=admin
        ).status_code
        == 409
    )

    shown = client.get("/api/v1/public/reviews", params={"kelurahan": area.kelurahan}).json()
    assert code in [row["code"] for row in shown["data"]]
    assert shown["average"] is not None and shown["count"] >= 1
    # Nilai rata-rata juga tampil pada ringkasan wilayah.
    summary = client.get("/api/v1/public/areas/summary").json()
    mine = next(row for row in summary["areas"] if row["kelurahan"] == area.kelurahan)
    assert mine["rating_count"] >= 1

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "MODERATE_AREA_REVIEW", AuditLog.resource_id == code
        )
    )
    assert entry is not None and entry.detail["to"] == "PUBLISHED"


def test_moderation_queue_appears_in_the_administrator_notifications(
    client: TestClient, session: Session
) -> None:
    area = _kelurahan(session)
    client.post(
        "/api/v1/public/reviews",
        json={"kecamatan": area.kecamatan, "kelurahan": area.kelurahan, "rating": 2},
    )
    feed = client.get(
        "/api/v1/notifications", headers=_login(client, session, "Administrator")
    ).json()
    group = next(g for g in feed["groups"] if g["kind"] == "REVIEW")
    assert group["total"] >= 1 and group["href"] == "/ops/survey"
