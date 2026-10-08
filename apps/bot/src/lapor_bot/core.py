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

MIN_DESCRIPTION = 10

INTRO = (
    "Selamat datang di LAPOR PRESISI, kanal laporan masyarakat Polres Metro Jakarta Selatan.\n\n"
    "Laporan ini TANPA nama. Yang disimpan dari percakapan ini hanya pengenalnya, "
    "agar Anda menerima kabar perkembangan laporan Anda di sini.\n\n"
    "Untuk keadaan darurat yang mengancam jiwa, hubungi 110."
)
HELP = (
    "Perintah:\n"
    "/mulai — membuat laporan baru\n"
    "/status — melihat status laporan Anda\n"
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
