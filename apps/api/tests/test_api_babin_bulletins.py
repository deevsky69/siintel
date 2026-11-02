"""Tahap 3: kontak Babinkamtibmas dan buletin mingguan (susun → setujui → kirim)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers import messaging
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import AuditLog, Babinkamtibmas, Bulletin, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.seeding.babin_dummy import seed_dummy_babin
from prediksi_presisi_api.services import bulletin as composing

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
KEY = "kunci-uji-bot"
BOT = {"X-Messaging-Key": KEY}
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
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(messaging, "get_settings", lambda: SimpleNamespace(messaging_api_key=KEY))
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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


def _kelurahan(session: Session) -> Location:
    row = session.scalar(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    )
    assert row is not None
    return row


def test_dummy_babin_is_one_per_kelurahan_labelled_and_idempotent(session: Session) -> None:
    added = seed_dummy_babin(session)
    assert added > 0
    assert seed_dummy_babin(session) == 0
    rows = session.scalars(select(Babinkamtibmas)).all()
    assert len(rows) == added and all(row.is_dummy and "(dummy)" in row.name for row in rows)


def test_public_contact_shows_service_number_but_never_delivery_targets(
    client: TestClient, session: Session
) -> None:
    seed_dummy_babin(session)
    area = _kelurahan(session)
    admin = _login(client, session, "Administrator")
    saved = client.put(
        f"/api/v1/babin/{area.kelurahan}",
        json={
            "name": "Bripka Uji",
            "rank": "Bripka",
            "phone_display": "021-7654321",
            "telegram_chat_id": "-1001",
            "whatsapp_number": "+62 812 0000 1111",
        },
        headers=admin,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["whatsapp_number"] == "6281200001111" and saved.json()["is_dummy"] is False

    public = client.get("/api/v1/public/babin", params={"kelurahan": area.kelurahan})
    assert public.status_code == 200
    data = public.json()["data"]
    assert data["name"] == "Bripka Uji" and data["phone_display"] == "021-7654321"
    assert "telegram_chat_id" not in data and "whatsapp_number" not in data

    assert (
        client.put(
            f"/api/v1/babin/{area.kelurahan}",
            json={"name": "x", "phone_display": "123456"},
            headers=_login(client, session, "Polsek"),
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/babin", headers=_login(client, session, "Pimpinan")).status_code == 200
    )


def test_bulletin_is_composed_from_the_week_then_approved_by_pimpinan_and_sent_by_bot(
    client: TestClient, session: Session
) -> None:
    area = _kelurahan(session)
    week = composing.last_full_week(date(2026, 1, 1))
    assert week.weekday() == 0 and week == date(2025, 12, 22)

    admin = _login(client, session, "Administrator")
    leader = _login(client, session, "Pimpinan")
    assert (
        client.post(
            "/api/v1/bulletins/generate", json={"week": week.isoformat()}, headers=leader
        ).status_code
        == 403
    )
    generated = client.post(
        "/api/v1/bulletins/generate", json={"week": week.isoformat()}, headers=admin
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["created"] > 0
    assert (
        client.post(
            "/api/v1/bulletins/generate", json={"week": "2026-01-01"}, headers=admin
        ).status_code
        == 400
    )

    listing = client.get(
        "/api/v1/bulletins", params={"week": week.isoformat()}, headers=leader
    ).json()
    mine = next(row for row in listing["data"] if row["kelurahan"] == area.kelurahan)
    assert mine["status"] == "DRAFT" and area.kelurahan.upper() in mine["content"]
    assert "SIGAP WARGA" in mine["content"] and mine["figures"]["week_start"] == week.isoformat()

    # Hanya Pimpinan yang menyetujui; Administrator ditolak.
    assert client.post(f"/api/v1/bulletins/{mine['id']}/approve", headers=admin).status_code == 403
    approved = client.post(f"/api/v1/bulletins/{mine['id']}/approve", headers=leader)
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    assert client.post(f"/api/v1/bulletins/{mine['id']}/approve", headers=leader).status_code == 409

    # Bot melihatnya beserta tujuan; tanpa kunci ditolak.
    assert client.get("/api/v1/messaging/bulletins/pending").status_code == 401
    pending = client.get("/api/v1/messaging/bulletins/pending", headers=BOT).json()["data"]
    assert mine["id"] in [row["id"] for row in pending]
    sent = client.post(
        f"/api/v1/messaging/bulletins/{mine['id']}/sent",
        json={"delivery": {"telegram": "ok", "whatsapp": "gagal: tidak ada nomor"}},
        headers=BOT,
    )
    assert sent.status_code == 200 and sent.json()["status"] == "SENT"
    assert mine["id"] not in [
        row["id"]
        for row in client.get("/api/v1/messaging/bulletins/pending", headers=BOT).json()["data"]
    ]
    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "SEND_BULLETIN", AuditLog.resource_id == mine["id"]
        )
    )
    assert entry is not None
    assert session.get(Bulletin, uuid.UUID(mine["id"])).sent_at is not None
