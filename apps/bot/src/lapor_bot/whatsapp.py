"""Kanal WhatsApp — WhatsApp Business Platform (Meta Cloud API).

Berbeda dari Telegram, WhatsApp MENDORONG pesan ke webhook kita, sehingga kanal ini butuh
alamat publik (`/webhook/whatsapp`, dirutekan Traefik ke kontainer bot) dan tiga nilai dari
Meta: access token, phone number id, dan verify token pilihan sendiri. Tanpa ketiganya
kanal ini tidak dijalankan.

Pilihan ditampilkan sebagai daftar bernomor dalam teks, bukan "interactive list": daftar
interaktif dibatasi 10 baris dengan judul 24 huruf, dan nama jenis kejadian kita lebih
panjang dari itu. Tombol lokasi memakai `location_request_message`, yang membuka dialog
lokasi perangkat seperti di Telegram.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from .backend import Backend, BackendError
from .core import Attachment, Conversation, Incoming, Reply, progress_message

log = logging.getLogger("lapor_bot.whatsapp")
CHANNEL = "WHATSAPP"
GRAPH = "https://graph.facebook.com/v21.0"
MAX_FILE_BYTES = 20 * 1024 * 1024


def render(reply: Reply) -> str:
    """Teks pesan beserta pilihan bernomor."""
    if not reply.choices:
        return reply.text
    lines = [f"{index}. {label}" for index, label in enumerate(reply.choices, start=1)]
    return reply.text + "\n\n" + "\n".join(lines) + "\n\nBalas dengan nomornya."


def outgoing(to: str, reply: Reply) -> list[dict[str, Any]]:
    """Satu Reply → satu atau dua pesan Cloud API (teks, lalu permintaan lokasi bila diminta)."""
    messages: list[dict[str, Any]] = [
        {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": render(reply)}}
    ]
    if reply.request_location:
        messages.append(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "location_request_message",
                    "body": {"text": "Atau tekan tombol di bawah untuk membagikan lokasi."},
                    "action": {"name": "send_location"},
                },
            }
        )
    return messages


def incoming_messages(body: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Isi webhook → daftar (nomor pengirim, pesan)."""
    found: list[tuple[str, dict[str, Any]]] = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []) or []:
                found.append((str(message.get("from", "")), message))
    return found


def incoming_from(message: dict[str, Any], fetch: Any) -> Incoming:
    kind = message.get("type")
    if kind == "text":
        return Incoming(text=str(message.get("text", {}).get("body", "")))
    if kind == "location":
        location = message["location"]
        return Incoming(
            latitude=float(location["latitude"]), longitude=float(location["longitude"])
        )
    if kind == "interactive":
        inner = message.get("interactive", {})
        chosen = inner.get("list_reply") or inner.get("button_reply") or {}
        return Incoming(text=str(chosen.get("title", "")))
    if kind in ("image", "video", "audio", "document"):
        media = message[kind]
        filename, content, media_type = fetch(
            media["id"], media.get("filename") or f"{kind}.bin", media.get("mime_type") or ""
        )
        return Incoming(attachment=Attachment(filename, content, media_type))
    return Incoming(text="")


class WhatsAppChannel:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        verify_token: str,
        backend: Backend,
        notify_interval: int = 30,
    ) -> None:
        self._graph = httpx.Client(
            base_url=GRAPH, headers={"Authorization": f"Bearer {access_token}"}, timeout=40.0
        )
        self._phone_id = phone_number_id
        self._verify_token = verify_token
        self._backend = backend
        self._interval = notify_interval
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def send(self, to: str, reply: Reply) -> None:
        for payload in outgoing(to, reply):
            response = self._graph.post(f"/{self._phone_id}/messages", json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"WhatsApp kirim: {response.status_code} {response.text[:200]}")

    def fetch(self, media_id: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        info = self._graph.get(f"/{media_id}").json()
        if int(info.get("file_size") or 0) > MAX_FILE_BYTES:
            raise RuntimeError("Berkas terlalu besar.")
        content = self._graph.get(str(info["url"])).content
        return filename, content, media_type or str(info.get("mime_type") or "")

    def _conversation(self, chat_id: str) -> Conversation:
        with self._lock:
            if chat_id not in self._conversations:
                self._conversations[chat_id] = Conversation(self._backend, CHANNEL, chat_id)
            return self._conversations[chat_id]

    def handle_webhook(self, body: dict[str, Any]) -> None:
        for sender, message in incoming_messages(body):
            if not sender:
                continue
            try:
                reply = self._conversation(sender).handle(incoming_from(message, self.fetch))
                self.send(sender, reply)
            except Exception:  # noqa: BLE001
                log.exception("WhatsApp: gagal menangani pesan dari satu percakapan")

    def verify(self, query: dict[str, list[str]]) -> str | None:
        """Jawaban untuk verifikasi webhook Meta; None bila token tidak cocok."""
        if (
            query.get("hub.mode", [""])[0] == "subscribe"
            and query.get("hub.verify_token", [""])[0] == self._verify_token
        ):
            return query.get("hub.challenge", [""])[0]
        return None

    def serve_forever(self, port: int) -> None:
        channel = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                log.debug(format, *args)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path.rstrip("/") != "/webhook/whatsapp":
                    self.send_response(404)
                    self.end_headers()
                    return
                challenge = channel.verify(parse_qs(parsed.query))
                if challenge is None:
                    self.send_response(403)
                    self.end_headers()
                    return
                payload = challenge.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self) -> None:  # noqa: N802
                if urlparse(self.path).path.rstrip("/") != "/webhook/whatsapp":
                    self.send_response(404)
                    self.end_headers()
                    return
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                # Meta menuntut 200 segera; pemrosesan dilakukan setelah jawaban.
                self.send_response(200)
                self.end_headers()
                try:
                    body = json.loads(raw or b"{}")
                except ValueError:
                    return
                threading.Thread(target=channel.handle_webhook, args=(body,), daemon=True).start()

        server = ThreadingHTTPServer(("0.0.0.0", port), Handler)  # noqa: S104 — di dalam kontainer
        log.info("WhatsApp: webhook mendengarkan di port %s", port)
        server.serve_forever()

    def notify_forever(self) -> None:
        log.info("WhatsApp: memeriksa kabar perkembangan tiap %s detik", self._interval)
        while True:
            try:
                for row in self._backend.updates(CHANNEL):
                    self.send(str(row["chat_id"]), Reply(progress_message(row)))
                    self._backend.ack(CHANNEL, str(row["ticket"]), str(row["status"]))
            except BackendError as error:
                # API belum siap (mis. migrasi masih berjalan saat deploy): satu baris
                # peringatan, bukan jejak tumpukan setiap 30 detik.
                log.warning(
                    "WhatsApp: kabar ditunda, API menjawab %s (%s)", error.status, error.message
                )
            except Exception:  # noqa: BLE001
                log.exception("WhatsApp: pengiriman kabar gagal; mencoba lagi")
            time.sleep(self._interval)
