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


def test_babin_contact_can_be_deleted_by_manager_only(client: TestClient, session: Session) -> None:
    """CRUD Babin (4 November 2026): hapus hanya oleh pemegang babin:manage, tercatat audit."""
    area = _kelurahan(session)
    admin = _login(client, session, "Administrator")
    assert (
        client.put(
            f"/api/v1/babin/{area.kelurahan}",
            json={"name": "Bripka Hapus", "phone_display": "021-0000000"},
            headers=admin,
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/v1/babin/{area.kelurahan}", headers=_login(client, session, "Pimpinan")
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/babin/{area.kelurahan}", headers=admin).status_code == 204
    assert client.delete(f"/api/v1/babin/{area.kelurahan}", headers=admin).status_code == 404
    public = client.get("/api/v1/public/babin", params={"kelurahan": area.kelurahan})
    assert public.status_code in (200, 404)
    if public.status_code == 200:
        assert public.json().get("data") in (None, {})


def test_group_link_accepts_only_official_whatsapp_invites(
    client: TestClient, session: Session
) -> None:
    """Tautan grup dirender sebagai href di halaman publik: skema lain ditolak di API."""
    area = _kelurahan(session)
    admin = _login(client, session, "Administrator")
    base = {"name": "Bripka Uji", "phone_display": "021-7654321"}
    bad = client.put(
        f"/api/v1/babin/{area.kelurahan}",
        json={**base, "whatsapp_group_link": "javascript:alert(1)"},
        headers=admin,
    )
    assert bad.status_code == 400
    good = client.put(
        f"/api/v1/babin/{area.kelurahan}",
        json={**base, "whatsapp_group_link": "https://chat.whatsapp.com/AbCdEf"},
        headers=admin,
    )
    assert good.status_code == 200
    assert good.json()["whatsapp_group_link"] == "https://chat.whatsapp.com/AbCdEf"


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


def test_citizen_group_registration_and_monthly_advisory_for_bot(
    client: TestClient, session: Session
) -> None:
    """Imbauan grup warga (4 November 2026): /daftar mendaftarkan grup ke kelurahan ber-Babin,
    bot menarik imbauan bulan berjalan untuk grup yang belum dikirimi, lalu menandainya."""
    from prediksi_presisi_api.services import citizen_advisory, clock

    key = BOT
    area = _kelurahan(session)
    admin = _login(client, session, "Administrator")
    # Belum ada kontak Babin → pendaftaran ditolak dengan petunjuk, bukan dibuat diam-diam.
    missing = client.post(
        "/api/v1/messaging/groups",
        json={"channel": "WHATSAPP", "chat_id": "120363@g.us", "kelurahan": area.kelurahan},
        headers=key,
    )
    assert missing.status_code == 404 and "Babinkamtibmas" in missing.text
    assert (
        client.put(
            f"/api/v1/babin/{area.kelurahan}",
            json={"name": "Bripka Grup", "phone_display": "021-1234567"},
            headers=admin,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/messaging/groups",
            json={"channel": "WHATSAPP", "chat_id": "628@c.us", "kelurahan": area.kelurahan},
            headers=key,
        ).status_code
        == 400
    )
    registered = client.post(
        "/api/v1/messaging/groups",
        json={"channel": "WHATSAPP", "chat_id": "120363@g.us", "kelurahan": area.kelurahan},
        headers=key,
    )
    assert registered.status_code == 200, registered.text
    assert client.post("/api/v1/messaging/groups", json={}).status_code in (401, 422)
    # Grup lain tidak dapat membajak pendaftaran; Babin kelurahan itu boleh memindahkannya.
    hijack = client.post(
        "/api/v1/messaging/groups",
        json={"channel": "WHATSAPP", "chat_id": "999999@g.us", "kelurahan": area.kelurahan},
        headers=key,
    )
    assert hijack.status_code == 409
    assert (
        client.put(
            f"/api/v1/babin/{area.kelurahan}",
            json={
                "name": "Bripka Grup",
                "phone_display": "021-1234567",
                "whatsapp_number": "6281200009999",
                "whatsapp_group_chat_id": "120363@g.us",
            },
            headers=admin,
        ).status_code
        == 200
    )
    moved = client.post(
        "/api/v1/messaging/groups",
        json={
            "channel": "WHATSAPP",
            "chat_id": "120363@g.us",
            "kelurahan": area.kelurahan,
            "sender": "6281200009999@c.us",
        },
        headers=key,
    )
    assert moved.status_code == 200

    # Bot mencari kelurahan grup lewat chat id-nya.
    found = client.get(
        "/api/v1/messaging/groups",
        params={"channel": "WHATSAPP", "chat_id": "120363@g.us"},
        headers=key,
    )
    assert found.status_code == 200 and found.json()["kelurahan"] == area.kelurahan
    assert (
        client.get(
            "/api/v1/messaging/groups",
            params={"channel": "WHATSAPP", "chat_id": "nope@g.us"},
            headers=key,
        ).status_code
        == 404
    )

    # /rekomendasi: teks bulan depan, tanpa skor/fungsi kepolisian.
    advisory = client.get(
        "/api/v1/messaging/advisory", params={"kelurahan": area.kelurahan}, headers=key
    )
    assert advisory.status_code == 200, advisory.text
    body = advisory.json()
    year, month = citizen_advisory.month_after(clock.citizen_now().astimezone(clock.JAKARTA).date())
    assert body["target_month"] == f"{year:04d}-{month:02d}"
    text = body["text"]
    assert "IMBAUAN KAMTIBMAS" in text and str(area.kelurahan).upper() in text
    for forbidden in ("SAMAPTA", "RESKRIM", "risk_score", "confidence", "patroli oleh"):
        assert forbidden not in text
    assert (
        client.get(
            "/api/v1/messaging/advisory", params={"kelurahan": "Nirwana"}, headers=key
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/messaging/advisory",
            params={"kelurahan": area.kelurahan, "month": "2026-13"},
            headers=key,
        ).status_code
        == 400
    )

    # Awal bulan: grup terdaftar masuk antrean sampai ditandai terkirim.
    pending = client.get("/api/v1/messaging/advisories/pending", headers=key).json()
    mine = next(row for row in pending["data"] if row["kelurahan"] == area.kelurahan)
    assert mine["chat_id"] == "120363@g.us" and mine["month"] == pending["month"]
    assert "IMBAUAN KAMTIBMAS" in mine["text"]
    sent = client.post(
        "/api/v1/messaging/advisories/sent",
        json={
            "kelurahan": area.kelurahan,
            "month": pending["month"],
            "delivery": {"whatsapp": "ok"},
        },
        headers=key,
    )
    assert sent.status_code == 200 and sent.json()["advisory_sent_month"] == pending["month"]
    again = client.get("/api/v1/messaging/advisories/pending", headers=key).json()
    assert all(row["kelurahan"] != area.kelurahan for row in again["data"])
    # Layar petugas melihat grupnya terdaftar.
    listing = client.get("/api/v1/babin", headers=admin).json()
    row = next(r for r in listing["data"] if r["kelurahan"] == area.kelurahan)
    assert row["whatsapp_group_chat_id"] == "120363@g.us"
