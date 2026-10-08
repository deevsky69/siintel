"""Kanal perpesanan (`routers/messaging.py`, 8 Oktober 2026).

Yang diuji adalah batas-batasnya: hanya layanan bot yang boleh memanggil; kuota dihitung
per percakapan; kontak tersimpan di tabel terpisah dan tidak bocor ke layar petugas; kabar
perkembangan muncul tepat ketika status berubah dan hilang setelah diakui.
"""

from __future__ import annotations

import io
import os
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.api.routers import messaging
from prediksi_presisi_api.api.routers.public_intake import load_report_categories
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    CitizenReport,
    CitizenReportContact,
    Location,
    Role,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
KEY = "kunci-uji-kanal-perpesanan"
PASSWORD = "KataSandiUji#2026"  # noqa: S105
HEADERS = {"X-Messaging-Key": KEY}


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
    messaging.limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    messaging.limiter.reset()


def _payload(session: Session, chat_id: str = "12345", **overrides: object) -> dict[str, object]:
    kecamatan = session.scalar(select(Location.kecamatan).where(Location.kecamatan.is_not(None)))
    body: dict[str, object] = {
        "channel": "TELEGRAM",
        "chat_id": chat_id,
        "category": load_report_categories()[0],
        "kecamatan": str(kecamatan),
        "description": "Ada sekelompok orang berkumpul dan membuat keributan di gang.",
    }
    body.update(overrides)
    return body


def test_the_channel_is_closed_without_a_configured_key(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(messaging, "get_settings", lambda: SimpleNamespace(messaging_api_key=""))
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/messaging/reports", json=_payload(session), headers=HEADERS
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503


def test_a_wrong_or_missing_key_is_refused(client: TestClient, session: Session) -> None:
    assert client.post("/api/v1/messaging/reports", json=_payload(session)).status_code == 401
    assert (
        client.post(
            "/api/v1/messaging/reports",
            json=_payload(session),
            headers={"X-Messaging-Key": "salah"},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/messaging/updates?channel=TELEGRAM").status_code == 401


def test_a_report_from_a_chat_stores_its_contact_separately(
    client: TestClient, session: Session
) -> None:
    response = client.post("/api/v1/messaging/reports", json=_payload(session), headers=HEADERS)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["ticket"].startswith("RPT-")
    assert "claim_token" not in body
    assert "contact_basis" in body

    report = session.scalar(select(CitizenReport).where(CitizenReport.code == body["ticket"]))
    assert report is not None and report.status == "RECEIVED"
    contact = session.scalar(
        select(CitizenReportContact).where(CitizenReportContact.report_id == report.report_id)
    )
    assert contact is not None
    assert contact.channel == "TELEGRAM" and contact.chat_id == "12345"
    assert contact.last_notified_status == "RECEIVED"

    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "SUBMIT_CITIZEN_REPORT", AuditLog.resource_id == body["ticket"]
        )
    )
    assert entry is not None and entry.detail["channel"] == "TELEGRAM"
    assert "chat_id" not in str(entry.detail)


def test_an_unknown_channel_and_identity_fields_are_refused(
    client: TestClient, session: Session
) -> None:
    assert (
        client.post(
            "/api/v1/messaging/reports",
            json=_payload(session, channel="SMS"),
            headers=HEADERS,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/messaging/reports",
            json=_payload(session, nama="Budi"),
            headers=HEADERS,
        ).status_code
        == 400
    )


def test_the_quota_is_counted_per_chat_not_per_network(
    client: TestClient, session: Session
) -> None:
    for _ in range(messaging.RATE_LIMIT_PER_HOUR):
        assert (
            client.post(
                "/api/v1/messaging/reports", json=_payload(session, "A"), headers=HEADERS
            ).status_code
            == 201
        )
    assert (
        client.post(
            "/api/v1/messaging/reports", json=_payload(session, "A"), headers=HEADERS
        ).status_code
        == 429
    )
    # Percakapan lain dari alamat jaringan yang sama tidak ikut terkena.
    assert (
        client.post(
            "/api/v1/messaging/reports", json=_payload(session, "B"), headers=HEADERS
        ).status_code
        == 201
    )


def test_a_chat_only_sees_its_own_reports(client: TestClient, session: Session) -> None:
    mine = client.post("/api/v1/messaging/reports", json=_payload(session, "X"), headers=HEADERS)
    client.post("/api/v1/messaging/reports", json=_payload(session, "Y"), headers=HEADERS)
    rows = client.get(
        "/api/v1/messaging/reports?channel=TELEGRAM&chat_id=X", headers=HEADERS
    ).json()["data"]
    assert [row["ticket"] for row in rows] == [mine.json()["ticket"]]
    assert "urgency_score" not in rows[0] and "chat_id" not in rows[0]


def test_updates_appear_when_status_changes_and_vanish_after_ack(
    client: TestClient, session: Session
) -> None:
    ticket = client.post(
        "/api/v1/messaging/reports", json=_payload(session, "Z"), headers=HEADERS
    ).json()["ticket"]
    assert (
        client.get("/api/v1/messaging/updates?channel=TELEGRAM", headers=HEADERS).json()["data"]
        == []
    )

    report = session.scalar(select(CitizenReport).where(CitizenReport.code == ticket))
    assert report is not None
    report.status = "VERIFIED"
    session.flush()

    pending = client.get("/api/v1/messaging/updates?channel=TELEGRAM", headers=HEADERS).json()[
        "data"
    ]
    assert [(row["ticket"], row["chat_id"], row["status"]) for row in pending] == [
        (ticket, "Z", "VERIFIED")
    ]
    # Kanal lain tidak melihatnya.
    assert (
        client.get("/api/v1/messaging/updates?channel=WHATSAPP", headers=HEADERS).json()["data"]
        == []
    )

    ack = client.post(
        "/api/v1/messaging/updates/ack",
        json={"ticket": ticket, "status": "VERIFIED", "channel": "TELEGRAM"},
        headers=HEADERS,
    )
    assert ack.status_code == 200
    assert (
        client.get("/api/v1/messaging/updates?channel=TELEGRAM", headers=HEADERS).json()["data"]
        == []
    )
    entry = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "NOTIFY_CITIZEN_REPORTER", AuditLog.resource_id == ticket
        )
    )
    assert entry is not None and entry.detail == {"channel": "TELEGRAM", "status": "VERIFIED"}


def test_an_attachment_from_a_chat_can_be_staged_and_claimed(
    client: TestClient, session: Session
) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (24, 16), (200, 30, 30)).save(buffer, format="JPEG")
    staged = client.post(
        "/api/v1/messaging/attachments",
        data={"channel": "TELEGRAM", "chat_id": "F"},
        files={"berkas": ("foto.jpg", buffer.getvalue(), "image/jpeg")},
        headers=HEADERS,
    )
    assert staged.status_code == 201, staged.text
    handle = staged.json()["handle"]
    submitted = client.post(
        "/api/v1/messaging/reports",
        json=_payload(session, "F", attachments=[handle]),
        headers=HEADERS,
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["attachments"] == 1


def test_officer_screens_never_receive_the_chat_id(client: TestClient, session: Session) -> None:
    client.post("/api/v1/messaging/reports", json=_payload(session, "RAHASIA-42"), headers=HEADERS)
    role = session.scalar(select(Role).where(Role.role_name == "Administrator"))
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
    listing = client.get(
        "/api/v1/citizen-reports?page_size=100", headers={"Authorization": f"Bearer {token}"}
    )
    assert listing.status_code == 200
    assert "RAHASIA-42" not in listing.text and "chat_id" not in listing.text
