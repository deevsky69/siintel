"""Penerjemahan bentuk kanal: tombol Telegram, daftar bernomor WhatsApp, pesan masuk."""

from __future__ import annotations

from typing import Any

from lapor_bot import telegram, whatsapp
from lapor_bot.core import Reply


def test_telegram_keyboard_puts_location_first_and_two_choices_per_row() -> None:
    markup = telegram.keyboard(Reply("x", choices=("A", "B", "C"), request_location=True))
    assert markup["keyboard"][0] == [{"text": telegram.LOCATION_BUTTON, "request_location": True}]
    assert markup["keyboard"][1:] == [[{"text": "A"}, {"text": "B"}], [{"text": "C"}]]
    assert telegram.keyboard(Reply("x")) == {"remove_keyboard": True}


def test_telegram_incoming_maps_location_photo_and_text() -> None:
    def fetch(file_id: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        return filename, b"bytes-" + file_id.encode(), media_type

    location = telegram.incoming_from(
        {"location": {"latitude": -6.2, "longitude": 106.8, "horizontal_accuracy": 9}}, fetch
    )
    assert (location.latitude, location.longitude, location.accuracy_m) == (-6.2, 106.8, 9.0)

    photo = telegram.incoming_from(
        {"photo": [{"file_id": "s", "file_size": 10}, {"file_id": "l", "file_size": 99}]}, fetch
    )
    assert photo.attachment is not None and photo.attachment.content == b"bytes-l"

    assert telegram.incoming_from({"text": "/mulai"}, fetch).text == "/mulai"


def test_whatsapp_renders_numbered_choices_and_location_request() -> None:
    reply = Reply("Pilih:", choices=("Tebet", "Cilandak"), request_location=True)
    messages = whatsapp.outgoing("628123", reply)
    assert messages[0]["text"]["body"].endswith("1. Tebet\n2. Cilandak\n\nBalas dengan nomornya.")
    assert messages[1]["interactive"]["type"] == "location_request_message"
    assert len(whatsapp.outgoing("628123", Reply("halo"))) == 1


def test_whatsapp_webhook_parsing_and_incoming_kinds() -> None:
    body: dict[str, Any] = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "628123", "type": "text", "text": {"body": "2"}},
                                {
                                    "from": "628123",
                                    "type": "location",
                                    "location": {"latitude": -6.2, "longitude": 106.8},
                                },
                                {
                                    "from": "628123",
                                    "type": "interactive",
                                    "interactive": {"list_reply": {"id": "1", "title": "Tebet"}},
                                },
                            ]
                        }
                    }
                ]
            }
        ]
    }
    found = whatsapp.incoming_messages(body)
    assert [sender for sender, _ in found] == ["628123"] * 3

    def fetch(media_id: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        return filename, b"x", media_type

    text, location, choice = (whatsapp.incoming_from(m, fetch) for _, m in found)
    assert text.text == "2"
    assert (location.latitude, location.longitude) == (-6.2, 106.8)
    assert choice.text == "Tebet"


def test_whatsapp_webhook_signature_is_required_and_checked() -> None:
    import hashlib
    import hmac

    raw = b'{"entry": []}'
    good = "sha256=" + hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
    assert whatsapp.signature_valid("app-secret", raw, good) is True
    assert whatsapp.signature_valid("app-secret", raw + b" ", good) is False
    assert whatsapp.signature_valid("app-secret", raw, "") is False
    assert whatsapp.signature_valid("", raw, good) is False


def test_whatsapp_channel_refuses_to_start_without_app_secret() -> None:
    import pytest

    with pytest.raises(ValueError, match="WHATSAPP_APP_SECRET"):
        whatsapp.WhatsAppChannel("tok", "123", "rahasia", "", backend=None)  # type: ignore[arg-type]


def test_whatsapp_media_host_allowlist() -> None:
    assert whatsapp.media_host_allowed("https://lookaside.fbsbx.com/whatsapp_business/x") is True
    assert whatsapp.media_host_allowed("https://mmg.whatsapp.net/v/x") is True
    assert whatsapp.media_host_allowed("https://evil.example.com/x") is False
    assert whatsapp.MEDIA_ID.match("12345") and not whatsapp.MEDIA_ID.match("../x")


def test_whatsapp_cloud_webhook_routes_verify_and_signed_posts() -> None:
    import hashlib
    import hmac

    from lapor_bot.webhook import WebhookServer

    channel = whatsapp.WhatsAppChannel("tok", "123", "rahasia", "app-secret", backend=None)  # type: ignore[arg-type]
    server = WebhookServer(0)
    channel.register(server)
    assert server.paths == ("/webhook/whatsapp",)
    get = server._gets["/webhook/whatsapp"]
    assert (
        get({"hub.mode": ["subscribe"], "hub.verify_token": ["rahasia"], "hub.challenge": ["c"]})[2]
        == b"c"
    )
    assert (
        get({"hub.mode": ["subscribe"], "hub.verify_token": ["x"], "hub.challenge": ["c"]})[0]
        == 403
    )
    post = server._posts["/webhook/whatsapp"]
    raw = b'{"entry": []}'
    assert post(raw, {}, "/webhook/whatsapp")[0] == 401
    sig = "sha256=" + hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
    assert post(raw, {"x-hub-signature-256": sig}, "/webhook/whatsapp")[0] == 200


def test_whatsapp_verify_requires_matching_token() -> None:
    channel = whatsapp.WhatsAppChannel("tok", "123", "rahasia", "app-secret", backend=None)  # type: ignore[arg-type]
    good = {"hub.mode": ["subscribe"], "hub.verify_token": ["rahasia"], "hub.challenge": ["abc"]}
    bad = {"hub.mode": ["subscribe"], "hub.verify_token": ["salah"], "hub.challenge": ["abc"]}
    assert channel.verify(good) == "abc"
    assert channel.verify(bad) is None
