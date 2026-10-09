"""Kanal WhatsApp — WhatsApp Business Platform (Meta Cloud API).

Berbeda dari Telegram, WhatsApp MENDORONG pesan ke webhook kita, sehingga kanal ini butuh
alamat publik (`/webhook/whatsapp`, dirutekan Traefik ke kontainer bot) dan tiga nilai dari
Meta: access token, phone number id, dan verify token pilihan sendiri. Tanpa ketiganya
kanal ini tidak dijalankan.

Setiap POST webhook diverifikasi lewat tanda tangan `X-Hub-Signature-256` (HMAC-SHA256
dengan app secret aplikasi Meta) SEBELUM dibaca: tanpa itu siapa pun yang tahu alamatnya
dapat mengirim pesan palsu atas nama nomor mana pun — membuat laporan dan menerima kabarnya.
Kanal menolak berjalan tanpa app secret.

Pilihan ditampilkan sebagai daftar bernomor dalam teks, bukan "interactive list": daftar
interaktif dibatasi 10 baris dengan judul 24 huruf, dan nama jenis kejadian kita lebih
panjang dari itu. Tombol lokasi memakai `location_request_message`, yang membuka dialog
lokasi perangkat seperti di Telegram.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .backend import Backend, BackendError
from .core import Attachment, Conversation, Incoming, Reply, progress_message
from .webhook import Response, WebhookServer, run_later

log = logging.getLogger("lapor_bot.whatsapp")
CHANNEL = "WHATSAPP"
GRAPH = "https://graph.facebook.com/v21.0"
WEBHOOK_PATH = "/webhook/whatsapp"
MAX_FILE_BYTES = 20 * 1024 * 1024
MEDIA_ID = re.compile(r"^[0-9]+$")
#: Host tempat Meta menyajikan media; token akses hanya dikirim ke sini.
MEDIA_HOSTS = (".fbsbx.com", ".whatsapp.net", ".facebook.com", "graph.facebook.com")


def signature_valid(app_secret: str, raw: bytes, header: str) -> bool:
    """Memeriksa `X-Hub-Signature-256: sha256=<hex>` dengan perbandingan waktu-tetap."""
    if not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header[len("sha256=") :], expected)


def media_host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h.lstrip(".") or host.endswith(h) for h in MEDIA_HOSTS)


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
        app_secret: str,
        backend: Backend,
        notify_interval: int = 30,
    ) -> None:
        if not app_secret:
            raise ValueError("WHATSAPP_APP_SECRET kosong: webhook tidak dapat diverifikasi.")
        self._app_secret = app_secret
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
        if not MEDIA_ID.match(media_id):
            raise RuntimeError("Pengenal media tidak sah.")
        info = self._graph.get(f"/{media_id}").json()
        if int(info.get("file_size") or 0) > MAX_FILE_BYTES:
            raise RuntimeError("Berkas terlalu besar.")
        url = str(info["url"])
        # Token akses hanya boleh dikirim ke host Meta; URL dari jawaban API tetap diperiksa.
        if not media_host_allowed(url):
            raise RuntimeError("Alamat media di luar host Meta.")
        content = self._graph.get(url).content
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

    def register(self, server: WebhookServer) -> None:
        """Mendaftarkan /webhook/whatsapp: GET verifikasi Meta, POST pesan bertanda tangan."""

        def on_get(query: dict[str, list[str]]) -> Response:
            challenge = self.verify(query)
            if challenge is None:
                return 403, "text/plain", b""
            return 200, "text/plain", challenge.encode()

        def on_post(raw: bytes, headers: dict[str, str], _path: str) -> Response:
            # Tanda tangan diperiksa SEBELUM apa pun dibaca dari isinya.
            if not signature_valid(self._app_secret, raw, headers.get("x-hub-signature-256", "")):
                return 401, "text/plain", b""
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return 200, "text/plain", b""
            # Meta menuntut 200 segera; pemrosesan dilakukan setelah jawaban.
            run_later(lambda: self.handle_webhook(body))
            return 200, "text/plain", b""

        server.route(WEBHOOK_PATH, get=on_get, post=on_post)

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
