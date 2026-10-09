"""Titik masuk: menjalankan kanal yang dikonfigurasi, masing-masing di thread sendiri."""

from __future__ import annotations

import logging
import threading
import time

from .backend import ApiBackend
from .config import Settings
from .telegram import TelegramChannel
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
        threads.append(
            threading.Thread(
                target=whatsapp.serve_forever,
                args=(settings.whatsapp_webhook_port,),
                name="whatsapp",
                daemon=True,
            )
        )
        threads.append(
            threading.Thread(target=whatsapp.notify_forever, name="whatsapp-kabar", daemon=True)
        )
    else:
        log.warning(
            "WHATSAPP_* belum lengkap (token, phone id, verify token, app secret) — kanal WhatsApp tidak dijalankan."
        )

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
