"""Mesin percakapan laporan — tidak tahu-menahu tentang Telegram atau WhatsApp.

Kanal mana pun menerjemahkan pesan masuk menjadi `Incoming` dan menampilkan `Reply`;
seluruh urutan pertanyaan, pemeriksaan isian, dan penyerahan ke API ada di sini supaya
Telegram dan WhatsApp bercakap dengan kata-kata yang sama dan diuji oleh test yang sama.

URUTAN PERTANYAAN (mengikuti formulir web/aplikasi, bukan menambah isian baru)

    jenis kejadian → kecamatan → lokasi (bagikan titik / pilih kelurahan / lewati)
    → uraian → foto (opsional, maksimal sesuai API) → ringkasan → kirim

Pilihan dapat dijawab dengan nomor urut ("2") atau teksnya; kanal yang punya tombol
(Telegram) menampilkannya sebagai tombol, yang tidak (WhatsApp) sebagai daftar bernomor.
Keadaan percakapan hidup di memori proses: bot yang dijalankan ulang melupakan percakapan
yang belum selesai, dan pelapor cukup mengetik /mulai lagi. Laporan yang sudah terkirim
tidak terpengaruh — ia ada di API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .backend import Backend, BackendError, Kelurahan, Options

CHOICE_SKIP = "Lewati"
CHOICE_NEXT = "Lanjut"
CHOICE_SEND = "Kirim"
CHOICE_CANCEL = "Batal"
COMMAND_START = ("/start", "/mulai", "mulai", "lapor", "/lapor")
COMMAND_STATUS = ("/status", "status")
COMMAND_CANCEL = ("/batal", "batal")
COMMAND_HELP = ("/bantuan", "bantuan", "/help", "help")
COMMAND_BABIN = ("/babin", "babin", "babinkamtibmas")
COMMAND_DASHBOARD = ("/dasbor", "dasbor", "/web", "web")
# 10 November 2026: perintahnya /info; /rekomendasi dan /imbauan tetap dikenali (tautan lama).
COMMAND_ADVISORY = ("/info", "info", "/rekomendasi", "rekomendasi", "/imbauan", "imbauan")
COMMAND_REGISTER = ("/daftar", "daftar")
DASHBOARD_URL = "https://sigap.awansurya.com"

MIN_DESCRIPTION = 10

INTRO = (
    "Selamat datang di SIGAP, kanal laporan masyarakat Polres Metro Jakarta Selatan.\n\n"
    "Laporan ini TANPA nama. Yang disimpan dari percakapan ini hanya pengenalnya, "
    "agar Anda menerima kabar perkembangan laporan Anda di sini.\n\n"
    "Untuk keadaan darurat yang mengancam jiwa, hubungi 110."
)
HELP = (
    "Perintah:\n"
    "/mulai — membuat laporan baru\n"
    "/status — melihat status laporan Anda\n"
    "/babin — kontak Babinkamtibmas kelurahan Anda\n"
    "/dasbor — peta kerawanan, lacak laporan, dan survey di SIGAP WARGA\n"
    "/info <kelurahan> — imbauan kehati-hatian bulan depan\n"
    "/batal — membatalkan laporan yang sedang diisi\n\n"
    "Keadaan darurat: hubungi 110."
)


class Step(Enum):
    IDLE = "idle"
    CATEGORY = "category"
    KECAMATAN = "kecamatan"
    LOCATION = "location"
    DESCRIPTION = "description"
    PHOTO = "photo"
    CONFIRM = "confirm"
    BABIN_KECAMATAN = "babin_kecamatan"
    BABIN_KELURAHAN = "babin_kelurahan"


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    media_type: str


@dataclass(frozen=True)
class Incoming:
    """Satu pesan dari pelapor, sudah dilepaskan dari bentuk kanalnya."""

    text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_m: float | None = None
    attachment: Attachment | None = None


@dataclass(frozen=True)
class Reply:
    text: str
    #: Pilihan yang ditawarkan; kanal menampilkannya sebagai tombol atau daftar bernomor.
    choices: tuple[str, ...] = ()
    #: Kanal diminta menampilkan tombol "bagikan lokasi".
    request_location: bool = False


@dataclass
class Draft:
    category: str | None = None
    kecamatan: str | None = None
    kelurahan: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_m: float | None = None
    description: str | None = None
    attachments: list[str] = field(default_factory=list)

    def nearest_label(self) -> str:
        if self.kelurahan and self.latitude is not None:
            return f"{self.kelurahan} (dari lokasi yang dibagikan)"
        if self.kelurahan:
            return self.kelurahan
        if self.latitude is not None:
            return "titik yang dibagikan"
        return "tidak disebut"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def nearest_kelurahan(rows: list[Kelurahan], latitude: float, longitude: float) -> str | None:
    if not rows:
        return None
    return min(rows, key=lambda k: haversine_km(latitude, longitude, k.latitude, k.longitude)).name


def pick(choices: tuple[str, ...], text: str) -> str | None:
    """Mencocokkan jawaban dengan pilihan: nomor urut atau teks (tanpa peduli huruf besar)."""
    wanted = text.strip()
    if wanted.isdigit():
        index = int(wanted) - 1
        return choices[index] if 0 <= index < len(choices) else None
    for choice in choices:
        if choice.casefold() == wanted.casefold():
            return choice
    return None


class Conversation:
    """Satu percakapan dengan satu pelapor."""

    def __init__(self, backend: Backend, channel: str, chat_id: str) -> None:
        self._backend = backend
        self._channel = channel
        self._chat_id = chat_id
        self._options: Options | None = None
        self.step = Step.IDLE
        self.draft = Draft()

    # -- pilihan -------------------------------------------------------------------

    def _opts(self) -> Options:
        if self._options is None:
            self._options = self._backend.options()
        return self._options

    def _location_choices(self) -> tuple[str, ...]:
        assert self.draft.kecamatan is not None  # noqa: S101
        names = [k.name for k in self._opts().areas.get(self.draft.kecamatan, [])]
        return (*names, CHOICE_SKIP)

    # -- alur ----------------------------------------------------------------------

    def handle(self, incoming: Incoming) -> Reply:
        text = (incoming.text or "").strip()
        lowered = text.casefold()
        try:
            if lowered in COMMAND_CANCEL:
                self._reset()
                return Reply("Laporan dibatalkan. Ketik /mulai untuk membuat laporan baru.")
            if lowered in COMMAND_STATUS:
                return self._status()
            if lowered in COMMAND_HELP:
                return Reply(HELP)
            if lowered in COMMAND_DASHBOARD:
                return Reply(
                    "SIGAP WARGA — peta kerawanan wilayah, lacak laporan, cek kendaraan, dan "
                    f"Survey Rasa Aman:\n{DASHBOARD_URL}"
                )
            if first_word(lowered) in COMMAND_ADVISORY:
                return advisory_reply(self._backend, rest_of(text))
            if lowered in COMMAND_BABIN:
                self._reset()
                self.step = Step.BABIN_KECAMATAN
                return Reply(
                    "Kontak Babinkamtibmas. Pilih kecamatan Anda:",
                    choices=tuple(self._opts().kecamatan),
                )
            if self.step in (Step.BABIN_KECAMATAN, Step.BABIN_KELURAHAN):
                return self._babin_step(text)
            if lowered in COMMAND_START or self.step is Step.IDLE:
                return self._start()
            return self._advance(incoming, text)
        except BackendError as error:
            if error.status == 429:
                return Reply(error.message)
            return Reply(
                f"Maaf, laporan belum dapat diproses: {error.message}\n"
                "Coba lagi beberapa saat, atau hubungi Polsek terdekat."
            )

    def _reset(self) -> None:
        self.step = Step.IDLE
        self.draft = Draft()

    def _babin_step(self, text: str) -> Reply:
        """Dua langkah: kecamatan → kelurahan → kontak. Nomor yang tampil nomor dinas."""
        if self.step is Step.BABIN_KECAMATAN:
            choice = pick(tuple(self._opts().kecamatan), text)
            if choice is None:
                return Reply("Pilih kecamatan dari daftar.", choices=tuple(self._opts().kecamatan))
            self.draft.kecamatan = choice
            self.step = Step.BABIN_KELURAHAN
            names = tuple(k.name for k in self._opts().areas.get(choice, []))
            return Reply("Pilih kelurahan:", choices=names)
        names = tuple(k.name for k in self._opts().areas.get(self.draft.kecamatan or "", []))
        choice = pick(names, text)
        if choice is None:
            return Reply("Pilih kelurahan dari daftar.", choices=names)
        contact = self._backend.babin(choice)
        self._reset()
        if not contact:
            return Reply(
                f"Kontak Babinkamtibmas Kelurahan {choice} belum tercatat. "
                "Hubungi Polsek setempat atau 110 untuk keadaan darurat."
            )
        return Reply("\n".join([*babin_lines(contact), "Keadaan darurat: hubungi 110."]))

    def _start(self) -> Reply:
        self._reset()
        self.step = Step.CATEGORY
        return Reply(
            f"{INTRO}\n\nApa jenis kejadian yang ingin Anda laporkan?",
            choices=tuple(self._opts().categories),
        )

    def _status(self) -> Reply:
        rows = self._backend.reports_of(self._channel, self._chat_id)
        if not rows:
            return Reply("Belum ada laporan dari percakapan ini. Ketik /mulai untuk melapor.")
        lines = [f"{row['ticket']} — {row['status_label']} ({row['category']})" for row in rows]
        return Reply("Laporan Anda:\n" + "\n".join(lines))

    def _advance(self, incoming: Incoming, text: str) -> Reply:
        if self.step is Step.CATEGORY:
            choice = pick(tuple(self._opts().categories), text)
            if choice is None:
                return Reply(
                    "Pilih salah satu jenis kejadian di bawah ini (nomor atau teksnya).",
                    choices=tuple(self._opts().categories),
                )
            self.draft.category = choice
            self.step = Step.KECAMATAN
            return Reply("Di kecamatan mana kejadiannya?", choices=tuple(self._opts().kecamatan))

        if self.step is Step.KECAMATAN:
            choice = pick(tuple(self._opts().kecamatan), text)
            if choice is None:
                return Reply(
                    "Pilih salah satu kecamatan di bawah ini.",
                    choices=tuple(self._opts().kecamatan),
                )
            self.draft.kecamatan = choice
            self.step = Step.LOCATION
            return Reply(
                "Bagikan lokasi kejadian lewat tombol lokasi, pilih kelurahannya, "
                f"atau ketik {CHOICE_SKIP}.",
                choices=self._location_choices(),
                request_location=True,
            )

        if self.step is Step.LOCATION:
            if incoming.latitude is not None and incoming.longitude is not None:
                self.draft.latitude = incoming.latitude
                self.draft.longitude = incoming.longitude
                self.draft.accuracy_m = incoming.accuracy_m
                assert self.draft.kecamatan is not None  # noqa: S101
                self.draft.kelurahan = nearest_kelurahan(
                    self._opts().areas.get(self.draft.kecamatan, []),
                    incoming.latitude,
                    incoming.longitude,
                )
                self.step = Step.DESCRIPTION
                where = self.draft.kelurahan or "titik itu"
                return Reply(
                    f"Lokasi diterima, perkiraan kelurahan: {where}.\n\n"
                    "Ceritakan apa yang terjadi (minimal 10 huruf)."
                )
            choice = pick(self._location_choices(), text)
            if choice is None:
                return Reply(
                    f"Bagikan lokasi, pilih kelurahan, atau ketik {CHOICE_SKIP}.",
                    choices=self._location_choices(),
                    request_location=True,
                )
            self.draft.kelurahan = None if choice == CHOICE_SKIP else choice
            self.step = Step.DESCRIPTION
            return Reply("Ceritakan apa yang terjadi (minimal 10 huruf).")

        if self.step is Step.DESCRIPTION:
            limit = self._opts().max_description
            if len(text) < MIN_DESCRIPTION:
                return Reply("Uraian terlalu pendek. Tulis minimal 10 huruf.")
            if len(text) > limit:
                return Reply(f"Uraian terlalu panjang (maksimal {limit} huruf). Persingkat, ya.")
            self.draft.description = text
            self.step = Step.PHOTO
            return Reply(
                f"Ada foto atau video? Kirim sekarang (maksimal {self._opts().max_attachments}), "
                f"atau ketik {CHOICE_NEXT}.",
                choices=(CHOICE_NEXT,),
            )

        if self.step is Step.PHOTO:
            if incoming.attachment is not None:
                if len(self.draft.attachments) >= self._opts().max_attachments:
                    return Reply(
                        f"Lampiran sudah {self._opts().max_attachments}. Ketik {CHOICE_NEXT}.",
                        choices=(CHOICE_NEXT,),
                    )
                handle = self._backend.stage_attachment(
                    self._channel,
                    self._chat_id,
                    incoming.attachment.filename,
                    incoming.attachment.content,
                    incoming.attachment.media_type,
                )
                self.draft.attachments.append(handle)
                return Reply(
                    f"Lampiran {len(self.draft.attachments)} diterima. Kirim lagi, "
                    f"atau ketik {CHOICE_NEXT}.",
                    choices=(CHOICE_NEXT,),
                )
            if pick((CHOICE_NEXT, CHOICE_SKIP), text) is None:
                return Reply(f"Kirim foto/video, atau ketik {CHOICE_NEXT}.", choices=(CHOICE_NEXT,))
            self.step = Step.CONFIRM
            return Reply(self._summary(), choices=(CHOICE_SEND, CHOICE_CANCEL))

        if self.step is Step.CONFIRM:
            choice = pick((CHOICE_SEND, CHOICE_CANCEL), text)
            if choice == CHOICE_CANCEL:
                self._reset()
                return Reply("Laporan dibatalkan. Ketik /mulai untuk membuat laporan baru.")
            if choice != CHOICE_SEND:
                return Reply(self._summary(), choices=(CHOICE_SEND, CHOICE_CANCEL))
            result = self._backend.submit(self._channel, self._chat_id, self._payload())
            self._reset()
            return Reply(
                f"Laporan diterima. Nomor tiket Anda: {result['ticket']}\n"
                f"Status: {result.get('status_label', result.get('status', ''))}\n"
                f"Wilayah: {result.get('kelurahan') or result.get('kecamatan') or '-'}\n\n"
                "Anda akan menerima kabar di sini bila statusnya berubah. "
                "Ketik /status kapan saja untuk memeriksanya.\n\n"
                "Bila keadaan mendesak, hubungi 110."
            )

        self._reset()
        return self._start()

    def _summary(self) -> str:
        d = self.draft
        return (
            "Ringkasan laporan:\n"
            f"Jenis: {d.category}\n"
            f"Kecamatan: {d.kecamatan}\n"
            f"Lokasi: {d.nearest_label()}\n"
            f"Uraian: {d.description}\n"
            f"Lampiran: {len(d.attachments)}\n\n"
            f"Ketik {CHOICE_SEND} untuk mengirim, atau {CHOICE_CANCEL}."
        )

    def _payload(self) -> dict[str, Any]:
        d = self.draft
        body: dict[str, Any] = {
            "category": d.category,
            "kecamatan": d.kecamatan,
            "description": d.description,
            "attachments": list(d.attachments),
        }
        if d.latitude is not None and d.longitude is not None:
            # Koordinat dikirim apa adanya; API sendiri yang menetapkan kelurahan terdekat
            # pada kecamatan itu (area_source = KELURAHAN_TERDEKAT). Yang ditampilkan ke
            # pelapor tadi hanya perkiraan dari daftar titik pusat kelurahan.
            body["latitude"] = d.latitude
            body["longitude"] = d.longitude
            if d.accuracy_m is not None:
                body["accuracy_m"] = d.accuracy_m
        elif d.kelurahan:
            body["kelurahan"] = d.kelurahan
        return body


def progress_message(row: dict[str, Any]) -> str:
    """Kabar perkembangan untuk satu laporan (dipakai kedua kanal)."""
    return (
        f"Kabar laporan {row['ticket']}: kini {row['status_label']}.\n"
        "Ketik /status untuk melihat seluruh laporan Anda."
    )


def bulletin_message(row: dict[str, Any]) -> str:
    """Teks buletin apa adanya dari API (sudah disetujui Pimpinan)."""
    return str(row["content"])


# ---------------------------------------------------------------------------
# Imbauan bulanan untuk grup warga (4 November 2026)
# ---------------------------------------------------------------------------


def first_word(text: str) -> str:
    return text.split(maxsplit=1)[0] if text.strip() else ""


def rest_of(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def advisory_reply(backend: Backend, kelurahan: str, month: str | None = None) -> Reply:
    """Teks imbauan bulan depan untuk satu kelurahan; tanpa kelurahan, diminta menyebutkannya."""
    if not kelurahan:
        return Reply(
            "Sebutkan kelurahannya, misalnya: /info Tebet Timur\n"
            "Di grup warga yang sudah didaftarkan (/daftar), cukup ketik /info."
        )
    try:
        data = backend.advisory(kelurahan, month)
    except BackendError as error:
        if error.status == 404:
            return Reply(f'Kelurahan "{kelurahan}" tidak dikenal. Periksa ejaannya.')
        return Reply(f"Imbauan belum dapat disusun: {error.message}")
    return Reply(str(data["text"]))


def babin_lines(contact: dict[str, Any]) -> list[str]:
    """Baris kontak Babin untuk warga: nomor dinas saja, tanpa tujuan buletin."""
    rank = f"{contact['rank']} " if contact.get("rank") else ""
    label = " (data peragaan)" if contact.get("is_dummy") else ""
    lines = [
        f"Babinkamtibmas Kelurahan {contact['kelurahan']}{label}: {rank}{contact['name']}",
        f"Nomor dinas: {contact['phone_display']}",
    ]
    if contact.get("whatsapp_group_link"):
        lines.append(f"Grup warga: {contact['whatsapp_group_link']}")
    return lines


def group_info(backend: Backend, channel: str, chat_id: str) -> Reply:
    """Pesan pengenalan di grup (permintaan pemilik proyek 4 November 2026): fitur bot,
    tautan SIGAP WARGA, dan kontak Babin kelurahan grup ini."""
    area = backend.group_of(channel, chat_id)
    lines = [
        "*SIGAP* — bot kamtibmas Polres Metro Jakarta Selatan.",
        "",
        "Di grup ini saya bisa:",
        "• /info — imbauan kehati-hatian bulan depan: jenis kejadian yang biasa "
        "terjadi di kelurahan ini, jam rawannya, dan tips pencegahan. Dikirim otomatis juga "
        "setiap awal bulan.",
        "• /babin — kontak Babinkamtibmas kelurahan ini.",
        "• /bantuan — pesan ini.",
        "",
        f"Peta kerawanan, lapor kejadian, lacak laporan, dan Survey Rasa Aman: {DASHBOARD_URL}",
        "Untuk melapor lewat WhatsApp, kirim pesan pribadi ke nomor ini dan ketik /mulai.",
        "",
    ]
    if area is None:
        lines.append(
            "Grup ini belum didaftarkan ke kelurahan mana pun. Ketik /daftar <nama kelurahan> "
            "agar imbauan bulanan dan kontak Babin sesuai wilayah grup."
        )
    else:
        lines.append(
            f"Grup ini terdaftar untuk Kelurahan {area['kelurahan']} ({area['kecamatan']})."
        )
        contact = backend.babin(str(area["kelurahan"]))
        if contact:
            lines.extend(babin_lines(contact))
        else:
            lines.append("Kontak Babinkamtibmas kelurahan ini belum tercatat.")
    lines.append("Keadaan darurat: hubungi 110.")
    return Reply("\n".join(lines))


def group_command(
    backend: Backend, channel: str, chat_id: str, text: str, sender: str | None = None
) -> Reply | None:
    """Perintah yang dilayani DI DALAM GRUP. Pesan biasa dibiarkan: alur laporan (tanpa nama,
    berisi lokasi dan foto) tidak boleh berjalan di hadapan seluruh anggota grup. Perintah
    yang tidak dikenal dijawab pesan pengenalan."""
    stripped = text.strip()
    command = first_word(stripped.casefold())
    if not command.startswith("/"):
        return None
    if command in COMMAND_REGISTER:
        kelurahan = rest_of(stripped)
        if not kelurahan:
            return Reply("Sebutkan kelurahannya, misalnya: /daftar Tebet Timur")
        try:
            area = backend.register_group(channel, chat_id, kelurahan, sender)
        except BackendError as error:
            return Reply(error.message)
        return Reply(
            f"Grup ini terdaftar untuk Kelurahan {area['kelurahan']} ({area['kecamatan']}). "
            "Imbauan kehati-hatian dikirim otomatis setiap awal bulan; ketik /info "
            "untuk imbauan bulan depan."
        )
    if command in COMMAND_ADVISORY:
        kelurahan = rest_of(stripped)
        if not kelurahan:
            registered = backend.group_of(channel, chat_id)
            if registered is None:
                return Reply(
                    "Grup ini belum didaftarkan. Ketik /daftar <nama kelurahan>, "
                    "atau sebutkan kelurahannya: /info Tebet Timur"
                )
            kelurahan = str(registered["kelurahan"])
        return advisory_reply(backend, kelurahan)
    if command in COMMAND_BABIN:
        registered = backend.group_of(channel, chat_id)
        if registered is None:
            return Reply("Grup ini belum didaftarkan. Ketik /daftar <nama kelurahan> dulu.")
        contact = backend.babin(str(registered["kelurahan"]))
        if not contact:
            return Reply(
                f"Kontak Babinkamtibmas Kelurahan {registered['kelurahan']} belum tercatat. "
                "Keadaan darurat: 110."
            )
        return Reply("\n".join([*babin_lines(contact), "Keadaan darurat: hubungi 110."]))
    # /mulai, /bantuan, /help, dan perintah lain yang tidak dikenal → pesan pengenalan.
    return group_info(backend, channel, chat_id)


def advisory_message(row: dict[str, Any]) -> str:
    return str(row["text"])
