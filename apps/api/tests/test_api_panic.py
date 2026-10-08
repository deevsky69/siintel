"""Tombol darurat warga (8 Oktober 2026): kanal publik, cakupan, penerimaan, notifikasi."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers import panic as panic_router
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


@pytest.fixture
def session() -> Iterator[Session]:
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
    panic_router.limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    panic_router.limiter.reset()


def _headers(
    client: TestClient, session: Session, role_name: str, polsek: str | None = None
) -> dict[str, str]:
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
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _a_kelurahan(session: Session) -> Location:
    location = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    )
    assert location is not None
    return location


def test_press_with_location_resolves_nearest_kelurahan_and_notifies(
    client: TestClient, session: Session
) -> None:
    cell = _a_kelurahan(session)
    pressed = client.post(
        "/api/v1/public/panic",
        json={
            "latitude": float(cell.latitude),
            "longitude": float(cell.longitude),
            "accuracy_m": 12.5,
            "note": "Ada orang membawa senjata",
        },
    )
    assert pressed.status_code == 201, pressed.text
    body = pressed.json()
    assert body["code"].startswith("PNC-") and body["status"] == "OPEN"
    assert body["kelurahan"] == cell.kelurahan and body["kecamatan"] == cell.kecamatan
    assert "110" in body["message"]

    # Pimpinan diberi tahu: kelompok PANIC paling atas pada antrean.
    pimpinan = _headers(client, session, "Pimpinan")
    feed = client.get("/api/v1/notifications", headers=pimpinan).json()
    assert feed["groups"][0]["kind"] == "PANIC"
    assert feed["groups"][0]["total"] >= 1
    assert any(item["code"] == body["code"] for item in feed["groups"][0]["items"])

    # Polsek wilayah itu melihat dan menerima; Pimpinan hanya membaca.
    polsek = _headers(client, session, "Polsek", polsek=cell.polsek)
    listed = client.get("/api/v1/panic", headers=polsek).json()
    assert any(row["code"] == body["code"] for row in listed["data"])
    assert listed["open_total"] >= 1
    assert (
        client.post(f"/api/v1/panic/{body['code']}/acknowledge", headers=pimpinan).status_code
        == 403
    )
    acked = client.post(f"/api/v1/panic/{body['code']}/acknowledge", headers=polsek)
    assert acked.status_code == 200 and acked.json()["status"] == "ACKNOWLEDGED"
    assert (
        client.post(f"/api/v1/panic/{body['code']}/acknowledge", headers=polsek).status_code == 409
    )
    closed = client.post(
        f"/api/v1/panic/{body['code']}/close", json={"note": "Tim tiba, aman."}, headers=polsek
    )
    assert closed.status_code == 200 and closed.json()["status"] == "CLOSED"
    assert closed.json()["closing_note"] == "Tim tiba, aman."

    # Setelah ditutup, hilang dari antrean.
    feed = client.get("/api/v1/notifications", headers=pimpinan).json()
    assert all(item["code"] != body["code"] for item in feed["groups"][0]["items"])


def test_press_without_location_is_accepted_but_only_whole_polres_sees_it(
    client: TestClient, session: Session
) -> None:
    pressed = client.post("/api/v1/public/panic", json={})
    assert pressed.status_code == 201, pressed.text
    code = pressed.json()["code"]
    assert pressed.json()["kelurahan"] is None

    admin = _headers(client, session, "Administrator")
    assert any(
        row["code"] == code for row in client.get("/api/v1/panic", headers=admin).json()["data"]
    )
    polsek = _headers(client, session, "Polsek", polsek=_a_kelurahan(session).polsek)
    assert all(
        row["code"] != code for row in client.get("/api/v1/panic", headers=polsek).json()["data"]
    )


def test_identity_fields_and_half_coordinates_are_refused(client: TestClient) -> None:
    assert client.post("/api/v1/public/panic", json={"nama": "Budi"}).status_code in (400, 422)
    assert client.post("/api/v1/public/panic", json={"latitude": -6.2}).status_code == 400


def test_polsek_outside_scope_gets_404_on_acknowledge(client: TestClient, session: Session) -> None:
    cell = _a_kelurahan(session)
    other = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None), Location.polsek != cell.polsek)
    )
    assert other is not None
    code = client.post(
        "/api/v1/public/panic",
        json={"latitude": float(cell.latitude), "longitude": float(cell.longitude)},
    ).json()["code"]
    outsider = _headers(client, session, "Polsek", polsek=other.polsek)
    assert client.post(f"/api/v1/panic/{code}/acknowledge", headers=outsider).status_code == 404
