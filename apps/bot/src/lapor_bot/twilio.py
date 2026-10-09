"""Kanal WhatsApp lewat Twilio — terutama **Twilio Sandbox for WhatsApp** untuk peragaan.

MEKANISMENYA

    Twilio memegang satu nomor WhatsApp bersama (sandbox). Orang yang ingin mencoba
    mengirim `join <dua-kata>` ke nomor itu sekali; sejak itu, setiap pesannya ke nomor
    Twilio DITERUSKAN Twilio ke webhook kita (`/webhook/twilio`, POST form-urlencoded),
    dan balasan kita dikirim lewat REST API Twilio. Tidak ada akun bisnis Meta yang perlu
    didaftarkan: Twilio-lah pelanggan Meta, kita pelanggan Twilio.

    Keterbatasan sandbox: nomor milik Twilio (bukan Polres), peserta harus `join` dulu
    dan keanggotaannya kedaluwarsa setelah 72 jam tanpa pesan, tidak ada tombol
    interaktif (pilihan jadi daftar bernomor), dan kabar perkembangan hanya sampai dalam
    24 jam sejak pesan terakhir pelapor. Untuk warga umum tetap diperlukan nomor resmi —
    yang juga bisa lewat Twilio, dengan akun bisnis Meta yang didaftarkan Twilio.

KEAMANAN

    Setiap POST diverifikasi tanda tangan `X-Twilio-Signature` (HMAC-SHA1 atas URL publik
    + seluruh parameter, kunci = auth token). Tanpa itu siapa pun dapat mengirim pesan palsu
    atas nama nomor mana pun. Berkas media diunduh dengan autentikasi akun.

Dari sisi API PREDIKSI PRESISI kanal ini adalah `WHATSAPP` juga: pengenal percakapannya
nomor telepon, sama seperti lewat Cloud API, sehingga tabel kontak dan kabarnya satu.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import threading
import time
from urllib.parse import parse_qs

import httpx

from .backend import Backend, BackendError
from .core import Attachment, Conversation, Incoming, Reply, progress_message
from .webhook import Response, WebhookServer, run_later
from .whatsapp import render

log = logging.getLogger("lapor_bot.twilio")
CHANNEL = "WHATSAPP"
WEBHOOK_PATH = "/webhook/twilio"
API = "https://api.twilio.com/2010-04-01"
MAX_FILE_BYTES = 16 * 1024 * 1024
LOCATION_HINT = (
    "\n\nUntuk membagikan lokasi: tekan ikon lampiran (klip) di WhatsApp, pilih Lokasi, lalu kirim."
)


def signature(auth_token: str, url: str, params: dict[str, str]) -> str:
    """Tanda tangan Twilio: base64(HMAC-SHA1(token, url + key1value1key2value2… terurut))."""
    payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(auth_token.encode(), payload.encode(), hashlib.sha1).digest()  # noqa: S324 — ketentuan Twilio
    return base64.b64encode(digest).decode()


def signature_valid(auth_token: str, url: str, params: dict[str, str], header: str) -> bool:
    if not auth_token or not header:
        return False
    return hmac.compare_digest(signature(auth_token, url, params), header)


def form(raw: bytes) -> dict[str, str]:
    return {
        k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True).items()
    }


def phone_of(address: str) -> str:
    """'whatsapp:+628123' -> '+628123'."""
    return address.split(":", 1)[1] if ":" in address else address


def incoming_from(params: dict[str, str], fetch) -> Incoming:  # type: ignore[no-untyped-def]
    if params.get("Latitude") and params.get("Longitude"):
        return Incoming(latitude=float(params["Latitude"]), longitude=float(params["Longitude"]))
    if int(params.get("NumMedia") or 0) > 0:
        media_type = params.get("MediaContentType0") or "application/octet-stream"
        ext = media_type.split("/")[-1].split(";")[0] or "bin"
        filename, content, media_type = fetch(params["MediaUrl0"], f"lampiran.{ext}", media_type)
        return Incoming(attachment=Attachment(filename, content, media_type))
    return Incoming(text=params.get("Body", ""))


def outgoing(reply: Reply) -> str:
    text = render(reply)
    if reply.request_location:
        text += LOCATION_HINT
    return text


class TwilioChannel:
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        public_url: str,
        backend: Backend,
        notify_interval: int = 30,
    ) -> None:
        if not (account_sid and auth_token and from_number and public_url):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, dan "
                "TWILIO_WEBHOOK_URL wajib."
            )
        self._sid = account_sid
        self._token = auth_token
        self._from = (
            from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        )
        self._public_url = public_url.rstrip("/")
        self._http = httpx.Client(auth=(account_sid, auth_token), timeout=40.0)
        self._backend = backend
        self._interval = notify_interval
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def send(self, phone: str, reply: Reply) -> None:
        response = self._http.post(
            f"{API}/Accounts/{self._sid}/Messages.json",
            data={"From": self._from, "To": f"whatsapp:{phone}", "Body": outgoing(reply)},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Twilio kirim: {response.status_code} {response.text[:200]}")

    def fetch(self, url: str, filename: str, media_type: str) -> tuple[str, bytes, str]:
        if not url.startswith("https://api.twilio.com/"):
            raise RuntimeError("Alamat media di luar Twilio.")
        response = self._http.get(url, follow_redirects=True)
        if len(response.content) > MAX_FILE_BYTES:
            raise RuntimeError("Berkas terlalu besar.")
        return filename, response.content, media_type

    def _conversation(self, phone: str) -> Conversation:
        with self._lock:
            if phone not in self._conversations:
                self._conversations[phone] = Conversation(self._backend, CHANNEL, phone)
            return self._conversations[phone]

    def handle(self, params: dict[str, str]) -> None:
        phone = phone_of(params.get("From", ""))
        if not phone:
            return
        try:
            reply = self._conversation(phone).handle(incoming_from(params, self.fetch))
            self.send(phone, reply)
        except Exception:  # noqa: BLE001
            log.exception("Twilio: gagal menangani pesan dari satu percakapan")

    def register(self, server: WebhookServer) -> None:
        def on_post(raw: bytes, headers: dict[str, str], _path: str) -> Response:
            params = form(raw)
            if not signature_valid(
                self._token, self._public_url, params, headers.get("x-twilio-signature", "")
            ):
                return 401, "text/plain", b""
            run_later(lambda: self.handle(params))
            # TwiML kosong: balasan dikirim lewat REST API, bukan di sini.
            return 200, "text/xml", b"<Response></Response>"

        server.route(WEBHOOK_PATH, post=on_post)

    def notify_forever(self) -> None:
        log.info("Twilio: memeriksa kabar perkembangan tiap %s detik", self._interval)
        while True:
            try:
                for row in self._backend.updates(CHANNEL):
                    self.send(str(row["chat_id"]), Reply(progress_message(row)))
                    self._backend.ack(CHANNEL, str(row["ticket"]), str(row["status"]))
            except BackendError as error:
                log.warning(
                    "Twilio: kabar ditunda, API menjawab %s (%s)", error.status, error.message
                )
            except Exception:  # noqa: BLE001
                log.exception("Twilio: pengiriman kabar gagal; mencoba lagi")
            time.sleep(self._interval)
