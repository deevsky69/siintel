"""Kanal WhatsApp lewat WAHA (WhatsApp HTTP API, https://github.com/devlikeapro/waha).

UNTUK PERAGAAN SAJA — keputusan pemilik proyek 3 November 2026 (pilihan A):

    WAHA adalah klien WhatsApp Web TIDAK RESMI yang dibungkus REST API. Meta tidak mengizinkan
    bot/klien tidak resmi; nomor yang dipakai dapat diblokir sewaktu-waktu. Karena itu kanal
    ini hanya dijalankan dengan NOMOR CADANGAN untuk peragaan dan uji coba internal, bukan
    nomor resmi Polres, dan bukan kanal warga umum. Kanal resmi tetap WhatsApp Business
    Platform (Cloud API) atau Twilio — lihat `whatsapp.py` dan `twilio.py`.

MEKANISMENYA

    WAHA berjalan sebagai kontainer di jaringan internal (tidak dipublikasikan). Satu "sesi"
    = satu nomor WhatsApp yang dipasangkan lewat kode QR. Setiap pesan masuk didorong WAHA ke
    webhook kita (`/webhook/waha`, JSON, di jaringan internal — tidak lewat Traefik), dan
    balasan dikirim lewat REST WAHA (`sendSeen` lalu `sendText`). Bot membuat sesinya sendiri
    bila belum ada, lengkap dengan konfigurasi webhook bertanda tangan.

    Tidak ada tombol interaktif (WAHA menyatakan tombol rusak; daftar pilihan rapuh), jadi
    pilihan ditampilkan sebagai daftar bernomor, sama seperti jalur Twilio. Lokasi diterima
    dari `payload.location` (pelapor memakai ikon lampiran → Lokasi).

KEAMANAN

    Setiap POST webhook diverifikasi tanda tangan `X-Webhook-Hmac` (HMAC-SHA512 heksadesimal
    atas isi mentah, kunci = `WAHA_WEBHOOK_HMAC_KEY`) SEBELUM dibaca. Kunci API WAHA hanya
    dikirim ke host WAHA sendiri; berkas media hanya diunduh dari host itu.

Dari sisi API SIGAP kanal ini adalah `WHATSAPP` juga: pengenal percakapannya nomor telepon
(`+62…`), sama seperti Cloud API dan Twilio, sehingga tabel kontak dan kabarnya satu. Pengenal
tersembunyi WhatsApp (`…@lid`) diteruskan apa adanya bila WAHA tidak memberi nomornya.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .backend import Backend, BackendError
from .core import Attachment, Conversation, Incoming, Reply, group_command, progress_message
from .webhook import Response, WebhookServer, run_later
from .whatsapp import render

log = logging.getLogger("lapor_bot.waha")
CHANNEL = "WHATSAPP"
WEBHOOK_PATH = "/webhook/waha"
MAX_FILE_BYTES = 16 * 1024 * 1024
#: Awalan jalur berkas media yang disajikan WAHA.
MEDIA_PATH = "/api/files/"
LOCATION_HINT = (
    "\n\nUntuk membagikan lokasi: tekan ikon lampiran (klip) di WhatsApp, pilih Lokasi, lalu kirim."
)
#: Jeda antar percobaan membuat sesi saat WAHA belum siap (detik).
SESSION_RETRY_SECONDS = 15
#: Status sesi yang perlu dinyalakan lagi, dan aksi POST /api/sessions/{name}/<aksi>-nya.
RESTART_ACTION = {"FAILED": "restart", "STOPPED": "start"}
#: Jangan menyalakan ulang sesi yang sama lebih sering dari ini (detik).
RESTART_COOLDOWN_SECONDS = 120


def signature_valid(key: str, raw: bytes, header: str) -> bool:
    """`X-Webhook-Hmac`: HMAC-SHA512 heksadesimal atas isi mentah; perbandingan waktu-tetap."""
    if not key or not header:
        return False
    expected = hmac.new(key.encode(), raw, hashlib.sha512).hexdigest()
    return hmac.compare_digest(header.strip().lower(), expected)


def is_group(from_: str) -> bool:
    return from_.endswith("@g.us")


def chat_id_of(from_: str) -> str | None:
    """`628123@c.us` → `+628123`; `…@lid` apa adanya; grup/status/kosong → None."""
    if not from_ or "@" not in from_:
        return None
    user, _, host = from_.partition("@")
    if host == "c.us" and user.isdigit():
        return f"+{user}"
    if host == "lid" and user:
        return from_
    return None


def to_waha_chat(chat: str) -> str:
    """Kebalikan `chat_id_of`: `+628123` → `628123@c.us`; selain itu apa adanya."""
    if chat.startswith("+") and chat[1:].isdigit():
        return f"{chat[1:]}@c.us"
    return chat


def incoming_from(payload: dict[str, Any], fetch: Any) -> Incoming:
    location = payload.get("location") or {}
    if location.get("latitude") not in (None, "") and location.get("longitude") not in (None, ""):
        return Incoming(
            latitude=float(location["latitude"]), longitude=float(location["longitude"])
        )
    media = payload.get("media") or {}
    url = media.get("url")
    if payload.get("hasMedia") and url:
        media_type = str(media.get("mimetype") or "application/octet-stream")
        ext = media_type.split("/")[-1].split(";")[0] or "bin"
        filename = str(media.get("filename") or f"lampiran.{ext}")
        filename, content, media_type = fetch(str(url), filename, media_type)
        return Incoming(attachment=Attachment(filename, content, media_type))
    return Incoming(text=str(payload.get("body") or ""))


def outgoing(reply: Reply) -> str:
    text = render(reply)
    if reply.request_location:
        text += LOCATION_HINT
    return text


class WahaChannel:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        session: str,
        hmac_key: str,
        webhook_url: str,
        backend: Backend,
        notify_interval: int = 30,
    ) -> None:
        if not (base_url and api_key and session and webhook_url):
            raise ValueError(
                "WAHA_BASE_URL, WAHA_API_KEY, WAHA_SESSION, dan WAHA_WEBHOOK_URL wajib."
            )
        if not hmac_key:
            raise ValueError(
                "WAHA_WEBHOOK_HMAC_KEY wajib: tanpa itu siapa pun di jaringan dapat mengirim "
                "pesan palsu ke webhook."
            )
        self._base = base_url.rstrip("/")
        self._session = session
        self._hmac_key = hmac_key
        self._webhook_url = webhook_url
        self._http = httpx.Client(base_url=self._base, headers={"X-Api-Key": api_key}, timeout=40.0)
        self._backend = backend
        self._interval = notify_interval
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()
        self._last_restart: float = -RESTART_COOLDOWN_SECONDS

    # -- sesi -------------------------------------------------------------------------

    def ensure_session(self) -> str:
        """Memastikan sesi ada di WAHA dengan webhook bertanda tangan; mengembalikan statusnya.

        Sesi yang sudah ada dibiarkan (konfigurasinya tidak ditimpa — mengubah konfigurasi
        memulai ulang sesi). Memasangkan nomor (QR) tetap langkah manusia: `scripts/waha-qr.sh`.
        """
        response = self._http.get(f"/api/sessions/{self._session}")
        if response.status_code == 404:
            response = self._http.post(
                "/api/sessions",
                json={
                    "name": self._session,
                    "start": True,
                    "config": {
                        "webhooks": [
                            {
                                "url": self._webhook_url,
                                "events": ["message"],
                                "hmac": {"key": self._hmac_key},
                                "retries": {"policy": "constant", "delaySeconds": 2, "attempts": 5},
                            }
                        ]
                    },
                },
            )
        if response.status_code >= 400:
            raise RuntimeError(f"WAHA sesi: {response.status_code} {response.text[:200]}")
        status = str(response.json().get("status") or "")
        action = RESTART_ACTION.get(status)
        if action and time.monotonic() - self._last_restart >= RESTART_COOLDOWN_SECONDS:
            # WAHA menghentikan paksa sesi yang QR-nya tidak dipindai ±3 menit (FAILED);
            # `start` ditolak ("already running"), yang bekerja `restart`. STOPPED cukup `start`.
            self._last_restart = time.monotonic()
            response = self._http.post(f"/api/sessions/{self._session}/{action}")
            if response.status_code >= 400:
                raise RuntimeError(f"WAHA {action}: {response.status_code} {response.text[:200]}")
            status = str(response.json().get("status") or "STARTING")
        return status

    def watch_session_forever(self) -> None:
        """Memastikan sesi ada dan mencatat perubahan statusnya; dijalankan di thread sendiri
        supaya tidak bergantung pada siapa pengirim kabar WHATSAPP (Cloud API/Twilio/WAHA)."""
        last: str | None = None
        while True:
            try:
                status = self.ensure_session()
                if status != last:
                    log.info("WAHA: sesi '%s' status %s", self._session, status)
                    if status == "SCAN_QR_CODE":
                        log.warning("WAHA: nomor belum dipasangkan — jalankan scripts/waha-qr.sh")
                    last = status
            except Exception as error:  # noqa: BLE001
                log.warning("WAHA belum siap (%s); mencoba lagi", str(error)[:160])
                last = None
            time.sleep(SESSION_RETRY_SECONDS)

    # -- kirim/terima -----------------------------------------------------------------

    def send(self, chat: str, reply: Reply) -> None:
        chat_id = to_waha_chat(chat)
        # Centang biru dulu — WAHA menyarankannya sebelum membalas pesan baru.
        seen = self._http.post("/api/sendSeen", json={"session": self._session, "chatId": chat_id})
        if seen.status_code >= 400:
            log.warning("WAHA sendSeen: %s %s", seen.status_code, seen.text[:120])
        response = self._http.post(
            "/api/sendText",
            json={"session": self._session, "chatId": chat_id, "text": outgoing(reply)},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"WAHA kirim: {response.status_code} {response.text[:200]}")

    def fetch(self, url: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        # WAHA menulis URL media dengan host sesuai WAHA_BASE_URL-nya (bawaan localhost),
        # yang tidak selalu sama dengan alamat yang dipakai bot. Hanya jalurnya yang dipakai,
        # dan harus jalur berkas WAHA; unduhan selalu ke host WAHA yang dikenal bot, sehingga
        # kunci API tidak pernah terkirim ke host lain.
        path = urlparse(url).path
        if not path.startswith(MEDIA_PATH):
            raise RuntimeError("Alamat media di luar WAHA.")
        response = self._http.get(path)
        if response.status_code >= 400:
            raise RuntimeError(f"WAHA media: {response.status_code}")
        if len(response.content) > MAX_FILE_BYTES:
            raise RuntimeError("Berkas terlalu besar.")
        return filename, response.content, media_type

    def _conversation(self, chat: str) -> Conversation:
        with self._lock:
            if chat not in self._conversations:
                self._conversations[chat] = Conversation(self._backend, CHANNEL, chat)
            return self._conversations[chat]

    def handle(self, event: dict[str, Any]) -> None:
        """Satu peristiwa webhook WAHA; hanya `message` dari percakapan langsung yang dijawab."""
        if event.get("event") != "message":
            return
        payload = event.get("payload") or {}
        if payload.get("fromMe"):
            return
        sender = str(payload.get("from") or "")
        if is_group(sender):
            # Di grup hanya perintah imbauan yang dilayani (4 November 2026); alur laporan
            # tidak pernah berjalan di hadapan seluruh anggota grup.
            self.handle_group(sender, str(payload.get("body") or ""))
            return
        chat = chat_id_of(sender)
        if chat is None:
            return
        try:
            reply = self._conversation(chat).handle(incoming_from(payload, self.fetch))
            self.send(chat, reply)
        except Exception:  # noqa: BLE001
            log.exception("WAHA: gagal menangani pesan dari satu percakapan")

    def handle_group(self, group_id: str, text: str) -> None:
        try:
            reply = group_command(self._backend, CHANNEL, group_id, text)
            if reply is not None:
                self.send(group_id, reply)
        except Exception:  # noqa: BLE001
            log.exception("WAHA: gagal menangani perintah grup")

    def register(self, server: WebhookServer) -> None:
        def on_post(raw: bytes, headers: dict[str, str], _path: str) -> Response:
            # Tanda tangan diperiksa SEBELUM apa pun dibaca dari isinya.
            if not signature_valid(self._hmac_key, raw, headers.get("x-webhook-hmac", "")):
                return 401, "text/plain", b""
            try:
                event = json.loads(raw or b"{}")
            except ValueError:
                return 200, "text/plain", b""
            # WAHA mengulang kiriman bila jawaban lambat/gagal; jawab dulu, proses kemudian.
            run_later(lambda: self.handle(event))
            return 200, "text/plain", b""

        def on_get(_query: dict[str, list[str]]) -> Response:
            return (
                200,
                "text/plain; charset=utf-8",
                b"Webhook SIGAP (WAHA, peragaan) aktif. WAHA mengirim POST ke alamat ini.",
            )

        server.route(WEBHOOK_PATH, get=on_get, post=on_post)

    def notify_forever(self) -> None:
        log.info("WAHA: memeriksa kabar perkembangan tiap %s detik", self._interval)
        while True:
            try:
                for row in self._backend.updates(CHANNEL):
                    self.send(str(row["chat_id"]), Reply(progress_message(row)))
                    self._backend.ack(CHANNEL, str(row["ticket"]), str(row["status"]))
            except BackendError as error:
                log.warning(
                    "WAHA: kabar ditunda, API menjawab %s (%s)", error.status, error.message
                )
            except Exception:  # noqa: BLE001
                log.exception("WAHA: pengiriman kabar gagal; mencoba lagi")
            time.sleep(self._interval)
