"""Kanal WAHA (peragaan): tanda tangan, pemetaan payload → Incoming, pesan keluar, sesi."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from lapor_bot import waha
from lapor_bot.core import Reply
from lapor_bot.webhook import WebhookServer

DOC_BODY = b'{"event":"message","session":"default","engine":"WEBJS"}'
DOC_HMAC = (
    "208f8a55dde9e05519e898b10b89bf0d0b3b0fdf11fdbf09b6b90476301b98d8"
    "097c462b2b17a6ce93b6b47a136cf2e78a33a63f6752c2c1631777076153fa89"
)


def channel(**overrides: Any) -> waha.WahaChannel:
    kwargs: dict[str, Any] = {
        "base_url": "http://waha:3000",
        "api_key": "kunci",
        "session": "default",
        "hmac_key": "my-secret-key",
        "webhook_url": "http://bot:8080/webhook/waha",
        "backend": None,
    }
    kwargs.update(overrides)
    return waha.WahaChannel(**kwargs)


def test_signature_matches_documented_vector() -> None:
    # Vektor dari dokumentasi WAHA (how-to/events): HMAC-SHA512 heksadesimal atas isi mentah.
    assert waha.signature_valid("my-secret-key", DOC_BODY, DOC_HMAC)
    assert waha.signature_valid("my-secret-key", DOC_BODY, DOC_HMAC.upper())
    assert not waha.signature_valid("my-secret-key", DOC_BODY + b" ", DOC_HMAC)
    assert not waha.signature_valid("my-secret-key", DOC_BODY, "")
    assert not waha.signature_valid("", DOC_BODY, DOC_HMAC)


def test_chat_id_conversions() -> None:
    assert waha.chat_id_of("628123@c.us") == "+628123"
    assert waha.chat_id_of("12345678901234@lid") == "12345678901234@lid"
    assert waha.chat_id_of("628123-1600000000@g.us") is None
    assert waha.chat_id_of("status@broadcast") is None
    assert waha.chat_id_of("") is None
    assert waha.to_waha_chat("+628123") == "628123@c.us"
    assert waha.to_waha_chat("12345678901234@lid") == "12345678901234@lid"


def test_incoming_maps_text_location_and_media() -> None:
    def fetch(url: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        return filename, b"isi", media_type

    text = waha.incoming_from({"body": "2", "hasMedia": False}, fetch)
    assert text.text == "2"
    location = waha.incoming_from(
        {"body": "", "location": {"latitude": "-6.2", "longitude": 106.8, "live": False}}, fetch
    )
    assert (location.latitude, location.longitude) == (-6.2, 106.8)
    media = waha.incoming_from(
        {
            "body": "",
            "hasMedia": True,
            "media": {
                "url": "http://waha:3000/api/files/abc.jpg",
                "mimetype": "image/jpeg",
                "filename": None,
            },
        },
        fetch,
    )
    assert media.attachment is not None
    assert media.attachment.filename == "lampiran.jpeg"
    assert media.attachment.media_type == "image/jpeg"
    # Media yang gagal diunduh WAHA (url null) diperlakukan sebagai teks kosong, bukan error.
    none = waha.incoming_from({"body": "", "hasMedia": True, "media": {"url": None}}, fetch)
    assert none.attachment is None and none.text == ""


def test_outgoing_adds_numbered_choices_and_location_hint() -> None:
    text = waha.outgoing(Reply("Pilih:", choices=("Tebet", "Cilandak"), request_location=True))
    assert "1. Tebet\n2. Cilandak" in text and "ikon lampiran" in text
    assert "ikon lampiran" not in waha.outgoing(Reply("halo"))


def test_channel_requires_base_url_api_key_and_hmac_key() -> None:
    with pytest.raises(ValueError, match="WAHA_WEBHOOK_HMAC_KEY"):
        channel(hmac_key="")
    with pytest.raises(ValueError):
        channel(api_key="")
    with pytest.raises(ValueError):
        channel(base_url="")


def test_fetch_only_downloads_from_waha_host() -> None:
    chan = channel()
    with pytest.raises(RuntimeError, match="di luar WAHA"):
        chan.fetch("http://evil.example.com/api/files/x.jpg", "x.jpg", "image/jpeg")


def test_webhook_rejects_unsigned_posts_and_registers_route() -> None:
    chan = channel()
    server = WebhookServer(0)
    chan.register(server)
    assert server.paths == ("/webhook/waha",)
    assert server._gets["/webhook/waha"]({})[0] == 200
    post = server._posts["/webhook/waha"]
    assert post(DOC_BODY, {}, "/webhook/waha")[0] == 401
    assert post(DOC_BODY, {"x-webhook-hmac": "salah"}, "/webhook/waha")[0] == 401
    assert post(DOC_BODY, {"x-webhook-hmac": DOC_HMAC}, "/webhook/waha")[0] == 200


def test_handle_replies_to_direct_messages_only(monkeypatch: pytest.MonkeyPatch) -> None:
    chan = channel()
    sent: list[tuple[str, str]] = []

    class Stub:
        def handle(self, incoming: Any) -> Reply:
            return Reply(f"terima: {incoming.text}")

    monkeypatch.setattr(chan, "_conversation", lambda chat: Stub())
    monkeypatch.setattr(chan, "send", lambda chat, reply: sent.append((chat, reply.text)))

    def event(**payload: Any) -> dict[str, Any]:
        base = {"from": "628123@c.us", "fromMe": False, "body": "halo", "hasMedia": False}
        base.update(payload)
        return {"event": "message", "session": "default", "payload": base}

    chan.handle(event())
    chan.handle(event(fromMe=True))
    chan.handle(event(**{"from": "1-2@g.us"}))
    chan.handle({"event": "session.status", "payload": {"status": "WORKING"}})
    assert sent == [("+628123", "terima: halo")]


def test_send_marks_seen_then_sends_text() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content)))
        assert request.headers["x-api-key"] == "kunci"
        return httpx.Response(201, json={})

    chan = channel()
    chan._http = httpx.Client(base_url="http://waha:3000", transport=httpx.MockTransport(respond))
    chan._http.headers["X-Api-Key"] = "kunci"
    chan.send("+628123", Reply("Pilih:", choices=("A",)))
    assert [path for path, _ in calls] == ["/api/sendSeen", "/api/sendText"]
    assert calls[1][1]["chatId"] == "628123@c.us" and calls[1][1]["session"] == "default"
    assert "1. A" in calls[1][1]["text"]


def test_ensure_session_creates_missing_session_with_signed_webhook() -> None:
    calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, body))
        if request.method == "GET":
            return httpx.Response(404, json={"message": "Session not found"})
        return httpx.Response(201, json={"name": "default", "status": "STARTING"})

    chan = channel()
    chan._http = httpx.Client(base_url="http://waha:3000", transport=httpx.MockTransport(respond))
    assert chan.ensure_session() == "STARTING"
    assert [(m, p) for m, p, _ in calls] == [
        ("GET", "/api/sessions/default"),
        ("POST", "/api/sessions"),
    ]
    created = calls[1][2]
    assert created is not None and created["name"] == "default" and created["start"] is True
    hook = created["config"]["webhooks"][0]
    assert hook["url"] == "http://bot:8080/webhook/waha"
    assert hook["events"] == ["message"]
    assert hook["hmac"] == {"key": "my-secret-key"}


def test_ensure_session_leaves_existing_session_alone() -> None:
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(200, json={"name": "default", "status": "SCAN_QR_CODE"})

    chan = channel()
    chan._http = httpx.Client(base_url="http://waha:3000", transport=httpx.MockTransport(respond))
    assert chan.ensure_session() == "SCAN_QR_CODE"
    assert calls == ["GET"]


def test_documented_vector_is_plain_hmac_sha512() -> None:
    assert hmac.new(b"my-secret-key", DOC_BODY, hashlib.sha512).hexdigest() == DOC_HMAC
