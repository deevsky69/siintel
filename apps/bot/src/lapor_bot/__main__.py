"""Titik masuk: menjalankan kanal yang dikonfigurasi, masing-masing di thread sendiri."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from .backend import ApiBackend
from .config import Settings
from .core import Reply
from .telegram import TelegramChannel, bulletins_forever
from .twilio import TwilioChannel
from .waha import WahaChannel
from .webhook import WebhookServer
from .whatsapp import WhatsAppChannel

log = logging.getLogger("lapor_bot")


def main() -> None:
    settings = Settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # httpx mencatat URL penuh setiap permintaan pada tingkat INFO — dan URL Bot API
    # memuat token bot. Log kontainer bukan tempat rahasia; cukup peringatan ke atas.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    if not settings.messaging_api_key:
        log.error("MESSAGING_API_KEY kosong — bot tidak dapat berbicara dengan API. Berhenti.")
        raise SystemExit(2)
    backend = ApiBackend(settings.api_base, settings.messaging_api_key)
    threads: list[threading.Thread] = []

    telegram: TelegramChannel | None = None
    whatsapp_send: Callable[[str, Reply], None] | None = None
    if settings.telegram_bot_token:
        telegram = TelegramChannel(
            settings.telegram_bot_token, backend, settings.notify_interval_seconds
        )
        threads.append(threading.Thread(target=telegram.poll_forever, name="telegram", daemon=True))
        threads.append(
            threading.Thread(target=telegram.notify_forever, name="telegram-kabar", daemon=True)
        )
    else:
        log.warning("TELEGRAM_BOT_TOKEN kosong — kanal Telegram tidak dijalankan.")

    webhook = WebhookServer(settings.webhook_port)

    if all(
        (
            settings.whatsapp_access_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_verify_token,
            settings.whatsapp_app_secret,
        )
    ):
        whatsapp = WhatsAppChannel(
            settings.whatsapp_access_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_verify_token,
            settings.whatsapp_app_secret,
            backend,
            settings.notify_interval_seconds,
        )
        whatsapp.register(webhook)
        whatsapp_send = whatsapp.send
        threads.append(
            threading.Thread(target=whatsapp.notify_forever, name="whatsapp-kabar", daemon=True)
        )
    else:
        log.warning(
            "WHATSAPP_* belum lengkap (token, phone id, verify token, app secret) — "
            "kanal WhatsApp Cloud API tidak dijalankan."
        )

    if all(
        (
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_whatsapp_from,
            settings.twilio_webhook_url,
        )
    ):
        twilio = TwilioChannel(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_whatsapp_from,
            settings.twilio_webhook_url,
            backend,
            settings.notify_interval_seconds,
        )
        twilio.register(webhook)
        if whatsapp_send is None:
            whatsapp_send = twilio.send
        if not any(t.name == "whatsapp-kabar" for t in threads):
            # Kabar WHATSAPP dikirim oleh satu pengirim saja; Cloud API didahulukan bila ada.
            threads.append(
                threading.Thread(target=twilio.notify_forever, name="twilio-kabar", daemon=True)
            )
    else:
        log.warning("TWILIO_* belum lengkap — kanal Twilio tidak dijalankan.")

    if all((settings.waha_base_url, settings.waha_api_key, settings.waha_webhook_hmac_key)):
        # Klien tidak resmi: hanya peragaan dengan nomor cadangan (keputusan 3 November 2026).
        log.warning(
            "WAHA aktif — kanal WhatsApp TIDAK RESMI untuk peragaan; jangan pakai nomor resmi."
        )
        waha = WahaChannel(
            settings.waha_base_url,
            settings.waha_api_key,
            settings.waha_session,
            settings.waha_webhook_hmac_key,
            settings.waha_webhook_url,
            backend,
            settings.notify_interval_seconds,
        )
        waha.register(webhook)
        if whatsapp_send is None:
            whatsapp_send = waha.send
        if not any(t.name in ("whatsapp-kabar", "twilio-kabar") for t in threads):
            # Kabar WHATSAPP tetap satu pengirim; kanal resmi didahulukan bila ada.
            threads.append(
                threading.Thread(target=waha.notify_forever, name="waha-kabar", daemon=True)
            )
    else:
        log.info("WAHA_* kosong — kanal WAHA (peragaan) tidak dijalankan.")

    if telegram is not None or whatsapp_send is not None:
        threads.append(
            threading.Thread(
                target=bulletins_forever,
                kwargs={
                    "backend": backend,
                    "telegram": telegram,
                    "whatsapp_send": whatsapp_send,
                    "interval": max(60, settings.notify_interval_seconds * 4),
                },
                name="buletin",
                daemon=True,
            )
        )

    if webhook.paths:
        threads.append(threading.Thread(target=webhook.serve_forever, name="webhook", daemon=True))

    if not threads:
        log.warning("Tidak ada kanal yang dikonfigurasi; bot menunggu tanpa melakukan apa pun.")
        while True:
            time.sleep(300)
            log.warning(
                "Masih tanpa kanal. Isi TELEGRAM_BOT_TOKEN atau WHATSAPP_* lalu jalankan ulang."
            )

    for thread in threads:
        thread.start()
    while True:
        time.sleep(60)
        for thread in threads:
            if not thread.is_alive():
                log.error("Thread %s mati; keluar agar kontainer dijalankan ulang.", thread.name)
                raise SystemExit(1)


if __name__ == "__main__":
    main()
