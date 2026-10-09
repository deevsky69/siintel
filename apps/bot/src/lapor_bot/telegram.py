"""Kanal Telegram — Bot API lewat long polling; tidak butuh alamat publik.

Keadaan percakapan per `chat_id` disimpan di memori. Tombol pilihan memakai keyboard
balasan (ReplyKeyboardMarkup) supaya pelapor tidak perlu mengetik; tombol "Bagikan lokasi"
memakai `request_location`, yang di Telegram menampilkan dialog lokasi perangkat.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from .backend import Backend, BackendError
from .core import Attachment, Conversation, Incoming, Reply, progress_message

log = logging.getLogger("lapor_bot.telegram")
CHANNEL = "TELEGRAM"
LOCATION_BUTTON = "📍 Bagikan lokasi"
MAX_FILE_BYTES = 20 * 1024 * 1024


def keyboard(reply: Reply) -> dict[str, Any]:
    """Keyboard balasan dari sebuah Reply; dua tombol per baris, lokasi di baris pertama."""
    if not reply.choices and not reply.request_location:
        return {"remove_keyboard": True}
    rows: list[list[dict[str, Any]]] = []
    if reply.request_location:
        rows.append([{"text": LOCATION_BUTTON, "request_location": True}])
    choices = list(reply.choices)
    for index in range(0, len(choices), 2):
        rows.append([{"text": label} for label in choices[index : index + 2]])
    return {"keyboard": rows, "resize_keyboard": True, "one_time_keyboard": True}


def incoming_from(message: dict[str, Any], fetch: Any) -> Incoming:
    """Pesan Telegram → Incoming. `fetch(file_id) -> (filename, bytes, media_type)`."""
    location = message.get("location")
    if location:
        return Incoming(
            latitude=float(location["latitude"]),
            longitude=float(location["longitude"]),
            accuracy_m=(
                float(location["horizontal_accuracy"])
                if location.get("horizontal_accuracy") is not None
                else None
            ),
        )
    photos = message.get("photo")
    if photos:
        largest = max(photos, key=lambda p: int(p.get("file_size") or 0))
        filename, content, media_type = fetch(largest["file_id"], "foto.jpg", "image/jpeg")
        return Incoming(attachment=Attachment(filename, content, media_type))
    for key in ("video", "document", "voice", "audio"):
        media = message.get(key)
        if media:
            filename, content, media_type = fetch(
                media["file_id"],
                media.get("file_name") or f"{key}.bin",
                media.get("mime_type") or "application/octet-stream",
            )
            return Incoming(attachment=Attachment(filename, content, media_type))
    return Incoming(text=message.get("text") or message.get("caption") or "")


class TelegramChannel:
    def __init__(self, token: str, backend: Backend, notify_interval: int = 30) -> None:
        self._api = httpx.Client(base_url=f"https://api.telegram.org/bot{token}", timeout=40.0)
        self._files = httpx.Client(
            base_url=f"https://api.telegram.org/file/bot{token}", timeout=60.0
        )
        self._backend = backend
        self._interval = notify_interval
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    # -- Bot API ---------------------------------------------------------------------

    def _call(self, method: str, **payload: Any) -> Any:
        response = self._api.post(f"/{method}", json=payload)
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description')}")
        return body["result"]

    def send(self, chat_id: str, reply: Reply) -> None:
        self._call("sendMessage", chat_id=chat_id, text=reply.text, reply_markup=keyboard(reply))

    def fetch(self, file_id: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        info = self._call("getFile", file_id=file_id)
        if int(info.get("file_size") or 0) > MAX_FILE_BYTES:
            raise BackendError(400, "Berkas terlalu besar untuk diteruskan.")
        content = self._files.get(f"/{info['file_path']}").content
        return filename, content, media_type

    # -- alur ------------------------------------------------------------------------

    def _conversation(self, chat_id: str) -> Conversation:
        with self._lock:
            if chat_id not in self._conversations:
                self._conversations[chat_id] = Conversation(self._backend, CHANNEL, chat_id)
            return self._conversations[chat_id]

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message or "chat" not in message:
            return
        chat_id = str(message["chat"]["id"])
        try:
            incoming = incoming_from(message, self.fetch)
        except BackendError as error:
            self.send(chat_id, Reply(error.message))
            return
        reply = self._conversation(chat_id).handle(incoming)
        self.send(chat_id, reply)

    def poll_forever(self) -> None:
        offset: int | None = None
        log.info("Telegram: menunggu pesan (long polling)")
        while True:
            try:
                updates = self._call(
                    "getUpdates", offset=offset, timeout=30, allowed_updates=["message"]
                )
                for update in updates:
                    offset = int(update["update_id"]) + 1
                    try:
                        self.handle_update(update)
                    except Exception:  # noqa: BLE001 — satu percakapan gagal tidak mematikan bot
                        log.exception(
                            "Telegram: gagal menangani pembaruan %s", update.get("update_id")
                        )
            except Exception:  # noqa: BLE001
                log.exception("Telegram: polling gagal; mencoba lagi")
                time.sleep(5)

    def notify_forever(self) -> None:
        log.info("Telegram: memeriksa kabar perkembangan tiap %s detik", self._interval)
        while True:
            try:
                for row in self._backend.updates(CHANNEL):
                    self.send(str(row["chat_id"]), Reply(progress_message(row)))
                    self._backend.ack(CHANNEL, str(row["ticket"]), str(row["status"]))
            except BackendError as error:
                # API belum siap (mis. migrasi masih berjalan saat deploy): satu baris
                # peringatan, bukan jejak tumpukan setiap 30 detik.
                log.warning(
                    "Telegram: kabar ditunda, API menjawab %s (%s)", error.status, error.message
                )
            except Exception:  # noqa: BLE001
                log.exception("Telegram: pengiriman kabar gagal; mencoba lagi")
            time.sleep(self._interval)
