"""Alur percakapan, diuji tanpa jaringan lewat backend palsu."""

from __future__ import annotations

from typing import Any

from lapor_bot.backend import BackendError, Kelurahan, Options
from lapor_bot.core import (
    CHOICE_CANCEL,
    CHOICE_NEXT,
    CHOICE_SEND,
    CHOICE_SKIP,
    Attachment,
    Conversation,
    Incoming,
    Step,
    nearest_kelurahan,
    pick,
    progress_message,
)


class FakeBackend:
    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []
        self.staged: list[str] = []
        self.quota_hit = False

    def options(self) -> Options:
        return Options(
            categories=["Kejahatan Jalanan", "Pencurian Kendaraan"],
            kecamatan=["Tebet", "Cilandak"],
            areas={
                "Tebet": [
                    Kelurahan("Tebet Timur", -6.2270, 106.8580),
                    Kelurahan("Manggarai", -6.2090, 106.8500),
                ]
            },
            max_description=60,
            max_attachments=2,
        )

    def submit(self, channel: str, chat_id: str, report: dict[str, Any]) -> dict[str, Any]:
        if self.quota_hit:
            raise BackendError(429, "Terlalu banyak laporan dari percakapan ini.")
        self.submitted.append({**report, "channel": channel, "chat_id": chat_id})
        return {
            "ticket": "RPT-0901",
            "status": "RECEIVED",
            "status_label": "Diterima",
            "kelurahan": "Tebet Timur",
        }

    def stage_attachment(
        self, channel: str, chat_id: str, filename: str, content: bytes, media_type: str
    ) -> str:
        handle = f"h{len(self.staged) + 1}"
        self.staged.append(handle)
        return handle

    def reports_of(self, channel: str, chat_id: str) -> list[dict[str, Any]]:
        return [
            {"ticket": "RPT-0901", "status_label": "Diverifikasi", "category": "Kejahatan Jalanan"}
        ]

    def updates(self, channel: str) -> list[dict[str, Any]]:
        return []

    def ack(self, channel: str, ticket: str, status: str) -> None:
        return None


def talk() -> tuple[Conversation, FakeBackend]:
    backend = FakeBackend()
    return Conversation(backend, "TELEGRAM", "42"), backend


def test_pick_accepts_number_or_text_case_insensitively() -> None:
    choices = ("Tebet", "Cilandak")
    assert pick(choices, "2") == "Cilandak"
    assert pick(choices, "tebet") == "Tebet"
    assert pick(choices, "9") is None
    assert pick(choices, "Jakarta") is None


def test_nearest_kelurahan_uses_distance() -> None:
    rows = FakeBackend().options().areas["Tebet"]
    assert nearest_kelurahan(rows, -6.2275, 106.8585) == "Tebet Timur"
    assert nearest_kelurahan([], 0, 0) is None


def test_full_flow_with_shared_location_and_photo() -> None:
    chat, backend = talk()
    first = chat.handle(Incoming(text="/start"))
    assert "TANPA nama" in first.text and first.choices == (
        "Kejahatan Jalanan",
        "Pencurian Kendaraan",
    )

    assert chat.handle(Incoming(text="2")).choices == ("Tebet", "Cilandak")
    where = chat.handle(Incoming(text="Tebet"))
    assert where.request_location is True and where.choices[-1] == CHOICE_SKIP

    told = chat.handle(Incoming(latitude=-6.2275, longitude=106.8585, accuracy_m=12.0))
    assert "Tebet Timur" in told.text and chat.step is Step.DESCRIPTION

    assert "terlalu pendek" in chat.handle(Incoming(text="pendek")).text
    assert "terlalu panjang" in chat.handle(Incoming(text="x" * 61)).text
    photo = chat.handle(Incoming(text="Motor dicuri di depan warung saat hujan."))
    assert photo.choices == (CHOICE_NEXT,)

    staged = chat.handle(Incoming(attachment=Attachment("a.jpg", b"xx", "image/jpeg")))
    assert "Lampiran 1" in staged.text
    chat.handle(Incoming(attachment=Attachment("b.jpg", b"yy", "image/jpeg")))
    full = chat.handle(Incoming(attachment=Attachment("c.jpg", b"zz", "image/jpeg")))
    assert "sudah 2" in full.text and len(backend.staged) == 2

    summary = chat.handle(Incoming(text=CHOICE_NEXT))
    assert summary.choices == (CHOICE_SEND, CHOICE_CANCEL)
    assert "Pencurian Kendaraan" in summary.text and "Lampiran: 2" in summary.text

    done = chat.handle(Incoming(text="kirim"))
    assert "RPT-0901" in done.text and chat.step is Step.IDLE
    sent = backend.submitted[0]
    assert sent["channel"] == "TELEGRAM" and sent["chat_id"] == "42"
    assert sent["latitude"] == -6.2275 and sent["accuracy_m"] == 12.0
    assert "kelurahan" not in sent  # API yang menetapkan kelurahan terdekat
    assert sent["attachments"] == ["h1", "h2"]


def test_flow_with_chosen_kelurahan_and_no_photo() -> None:
    chat, backend = talk()
    chat.handle(Incoming(text="mulai"))
    chat.handle(Incoming(text="1"))
    chat.handle(Incoming(text="1"))
    chat.handle(Incoming(text="Manggarai"))
    chat.handle(Incoming(text="Ada keributan di gang sejak sore."))
    chat.handle(Incoming(text=CHOICE_NEXT))
    chat.handle(Incoming(text=CHOICE_SEND))
    assert backend.submitted[0]["kelurahan"] == "Manggarai"
    assert "latitude" not in backend.submitted[0]


def test_skip_location_and_cancel_midway() -> None:
    chat, backend = talk()
    chat.handle(Incoming(text="/mulai"))
    chat.handle(Incoming(text="1"))
    chat.handle(Incoming(text="Tebet"))
    chat.handle(Incoming(text=CHOICE_SKIP))
    assert chat.step is Step.DESCRIPTION
    cancelled = chat.handle(Incoming(text="/batal"))
    assert "dibatalkan" in cancelled.text and chat.step is Step.IDLE
    assert backend.submitted == []


def test_status_and_help_commands_work_anytime() -> None:
    chat, _ = talk()
    assert "RPT-0901 — Diverifikasi" in chat.handle(Incoming(text="/status")).text
    assert "/batal" in chat.handle(Incoming(text="/bantuan")).text


def test_quota_error_is_relayed_as_plain_words() -> None:
    chat, backend = talk()
    chat.handle(Incoming(text="/mulai"))
    chat.handle(Incoming(text="1"))
    chat.handle(Incoming(text="1"))
    chat.handle(Incoming(text=CHOICE_SKIP))
    chat.handle(Incoming(text="Ada keributan di gang sejak sore."))
    chat.handle(Incoming(text=CHOICE_NEXT))
    backend.quota_hit = True
    assert "Terlalu banyak" in chat.handle(Incoming(text=CHOICE_SEND)).text


def test_progress_message_names_ticket_and_status() -> None:
    text = progress_message({"ticket": "RPT-0901", "status_label": "Diteruskan"})
    assert "RPT-0901" in text and "Diteruskan" in text
