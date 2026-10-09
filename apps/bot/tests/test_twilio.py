"""Kanal Twilio: tanda tangan, pemetaan form → Incoming, pesan keluar, dan rute webhook."""

from __future__ import annotations

from urllib.parse import urlencode

from lapor_bot import twilio
from lapor_bot.core import Reply
from lapor_bot.webhook import WebhookServer


def test_signature_matches_twilio_algorithm() -> None:
    # Vektor dihitung dengan pustaka resmi `twilio.request_validator.RequestValidator`
    # (token 12345): URL + parameter terurut, HMAC-SHA1, base64.
    url = "https://mycompany.com/myapp.php?foo=1&bar=2"
    params = {
        "CallSid": "CA1234567890ABCDE",
        "Caller": "+12349013030",
        "Digits": "1234",
        "From": "+12349013030",
        "To": "+18005551212",
    }
    assert twilio.signature("12345", url, params) == "0/KCTR6DLpKmkAf8muzZqo1nDgQ="
    assert twilio.signature_valid("12345", url, params, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=")
    assert not twilio.signature_valid("12345", url, params, "salah")
    assert not twilio.signature_valid("", url, params, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=")


def test_form_parsing_maps_text_location_and_media() -> None:
    def fetch(url: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        return filename, b"isi", media_type

    text = twilio.incoming_from(
        twilio.form(urlencode({"Body": "2", "From": "whatsapp:+628"}).encode()), fetch
    )
    assert text.text == "2"
    location = twilio.incoming_from({"Latitude": "-6.2", "Longitude": "106.8"}, fetch)
    assert (location.latitude, location.longitude) == (-6.2, 106.8)
    media = twilio.incoming_from(
        {
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/x",
            "MediaContentType0": "image/jpeg",
        },
        fetch,
    )
    assert media.attachment is not None and media.attachment.filename == "lampiran.jpeg"
    assert twilio.phone_of("whatsapp:+628123") == "+628123"


def test_outgoing_adds_numbered_choices_and_location_hint() -> None:
    text = twilio.outgoing(Reply("Pilih:", choices=("Tebet", "Cilandak"), request_location=True))
    assert "1. Tebet\n2. Cilandak" in text and "ikon lampiran" in text
    assert "ikon lampiran" not in twilio.outgoing(Reply("halo"))


def test_webhook_rejects_unsigned_posts_and_registers_route() -> None:
    channel = twilio.TwilioChannel(
        "AC1", "token", "+14155238886", "https://x.id/webhook/twilio", backend=None
    )  # type: ignore[arg-type]
    server = WebhookServer(0)
    channel.register(server)
    assert server.paths == ("/webhook/twilio",)
    handler = server._posts["/webhook/twilio"]
    raw = urlencode({"From": "whatsapp:+628", "Body": "halo"}).encode()
    assert handler(raw, {}, "/webhook/twilio")[0] == 401
    good = twilio.signature("token", "https://x.id/webhook/twilio", twilio.form(raw))
    status, content_type, body = handler(raw, {"x-twilio-signature": good}, "/webhook/twilio")
    assert status == 200 and b"<Response>" in body


def test_channel_requires_all_four_settings() -> None:
    import pytest

    with pytest.raises(ValueError):
        twilio.TwilioChannel("AC1", "", "+1", "https://x", backend=None)  # type: ignore[arg-type]
