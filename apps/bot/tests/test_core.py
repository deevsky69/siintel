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
    Reply,
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
        self.contact: dict[str, Any] | None = None
        self.bulletins: list[dict[str, Any]] = []
        self.acked_bulletins: dict[str, dict[str, str]] = {}
        self.groups: dict[str, str] = {}
        self.last_sender: str | None = None
        self.advisory_acks: dict[str, str] = {}
        self.advisory_deliveries: dict[str, dict[str, str]] = {}

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

    def babin(self, kelurahan: str) -> dict[str, Any] | None:
        return self.contact

    def pending_bulletins(self) -> list[dict[str, Any]]:
        return list(self.bulletins)

    def bulletin_sent(self, bulletin_id: str, delivery: dict[str, str]) -> None:
        self.acked_bulletins[bulletin_id] = delivery

    def register_group(
        self, channel: str, chat_id: str, kelurahan: str, sender: str | None = None
    ) -> dict[str, Any]:
        self.last_sender = sender
        if kelurahan.casefold() != "tebet timur":
            raise BackendError(404, "Kelurahan tidak dikenal pada master lokasi.")
        self.groups[chat_id] = "Tebet Timur"
        return {"kelurahan": "Tebet Timur", "kecamatan": "Tebet", "polsek": "Polsek Tebet"}

    def group_of(self, channel: str, chat_id: str) -> dict[str, Any] | None:
        kel = self.groups.get(chat_id)
        return (
            None
            if kel is None
            else {"kelurahan": kel, "kecamatan": "Tebet", "polsek": "Polsek Tebet"}
        )

    def advisory(self, kelurahan: str, month: str | None = None) -> dict[str, Any]:
        if kelurahan.casefold() != "tebet timur":
            raise BackendError(404, "Kelurahan tidak dikenal pada master lokasi.")
        return {"kelurahan": "Tebet Timur", "text": f"IMBAUAN {kelurahan} {month or 'depan'}"}

    def pending_advisories(self) -> list[dict[str, Any]]:
        return [
            {"kelurahan": kel, "chat_id": chat, "month": "2026-11", "text": f"IMBAUAN {kel}"}
            for chat, kel in self.groups.items()
            if self.advisory_acks.get(kel) != "2026-11"
        ]

    def advisory_sent(self, kelurahan: str, month: str, delivery: dict[str, str]) -> None:
        self.advisory_deliveries[kelurahan] = delivery
        if "ok" in delivery.values():
            self.advisory_acks[kelurahan] = month


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


def test_babin_command_walks_kecamatan_then_kelurahan_and_hides_delivery_targets() -> None:
    backend = FakeBackend()
    backend.contact = {
        "kelurahan": "Tebet Timur",
        "kecamatan": "Tebet",
        "polsek": "Tebet",
        "rank": "Bripka",
        "name": "Agus Santoso (dummy)",
        "phone_display": "0812-1111-2222",
        "whatsapp_group_link": None,
        "is_dummy": True,
    }
    chat = Conversation(backend, "TELEGRAM", "7")
    first = chat.handle(Incoming(text="/babin"))
    assert first.choices == ("Tebet", "Cilandak")
    second = chat.handle(Incoming(text="1"))
    assert second.choices == ("Tebet Timur", "Manggarai")
    final = chat.handle(Incoming(text="1"))
    assert "Bripka Agus Santoso (dummy)" in final.text and "0812-1111-2222" in final.text
    assert "data peragaan" in final.text and "6281" not in final.text
    assert chat.step is Step.IDLE


def test_dashboard_command_links_to_sigap_warga() -> None:
    chat, _ = talk()
    assert "sigap.awansurya.com" in chat.handle(Incoming(text="/dasbor")).text


def test_bulletins_are_delivered_to_group_and_babin_then_acknowledged() -> None:
    from lapor_bot.telegram import deliver_bulletins

    backend = FakeBackend()
    backend.bulletins = [
        {
            "id": "b1",
            "content": "BULETIN A",
            "telegram_chat_id": "-100",
            "whatsapp_number": "628100",
        },
        {"id": "b2", "content": "BULETIN B", "telegram_chat_id": None, "whatsapp_number": None},
    ]
    sent_tg: list[tuple[str, str]] = []
    sent_wa: list[tuple[str, str]] = []

    class Tg:
        def send(self, chat_id: str, reply: Reply) -> None:
            sent_tg.append((chat_id, reply.text))

    def wa(number: str, reply: Reply) -> None:
        sent_wa.append((number, reply.text))

    delivered = deliver_bulletins(backend, telegram=Tg(), whatsapp_send=wa)  # type: ignore[arg-type]
    assert delivered == 1
    assert sent_tg == [("-100", "BULETIN A")] and sent_wa == [("628100", "BULETIN A")]
    assert backend.acked_bulletins["b1"] == {"telegram": "ok", "whatsapp": "ok"}
    assert "catatan" in backend.acked_bulletins["b2"]


def test_group_commands_register_then_serve_advisory_and_stay_silent_otherwise() -> None:
    from lapor_bot.core import group_command

    backend = FakeBackend()
    group = "120363@g.us"
    assert group_command(backend, "WHATSAPP", group, "halo semua") is None
    intro = group_command(backend, "WHATSAPP", group, "/mulai")
    assert intro is not None and "/daftar" in intro.text  # belum terdaftar → diarahkan
    need = group_command(backend, "WHATSAPP", group, "/rekomendasi")
    assert need is not None and "/daftar" in need.text
    bad = group_command(backend, "WHATSAPP", group, "/daftar Nirwana")
    assert bad is not None and "tidak dikenal" in bad.text
    ok = group_command(backend, "WHATSAPP", group, "/daftar tebet timur", "628@c.us")
    assert ok is not None and "Tebet Timur" in ok.text and backend.groups[group] == "Tebet Timur"
    assert backend.last_sender == "628@c.us"
    advisory = group_command(backend, "WHATSAPP", group, "/rekomendasi")
    assert advisory is not None and advisory.text == "IMBAUAN Tebet Timur depan"
    explicit = group_command(backend, "WHATSAPP", group, "/rekomendasi Tebet Timur")
    assert explicit is not None and "IMBAUAN" in explicit.text
    # /mulai, /bantuan, dan perintah tak dikenal → pengenalan: fitur, tautan, kontak Babin.
    backend.contact = {
        "kelurahan": "Tebet Timur",
        "rank": "Aipda",
        "name": "Budi (dummy)",
        "phone_display": "021-555",
        "is_dummy": True,
        "whatsapp_group_link": None,
    }
    for word in ("/mulai", "/bantuan", "/apaan"):
        info = group_command(backend, "WHATSAPP", group, word)
        assert info is not None
        assert "/rekomendasi" in info.text and "sigap.awansurya.com" in info.text
        assert "Aipda Budi (dummy)" in info.text and "021-555" in info.text
        assert "Tebet Timur" in info.text
    babin = group_command(backend, "WHATSAPP", group, "/babin")
    assert babin is not None and "021-555" in babin.text and "110" in babin.text
    # Grup yang belum terdaftar diarahkan ke /daftar, tanpa kontak.
    fresh = group_command(backend, "WHATSAPP", "lain@g.us", "/mulai")
    assert fresh is not None and "/daftar" in fresh.text and "021-555" not in fresh.text


def test_private_advisory_command_needs_a_kelurahan() -> None:
    chat, backend = talk()
    ask = chat.handle(Incoming(text="/rekomendasi"))
    assert "Sebutkan kelurahannya" in ask.text
    got = chat.handle(Incoming(text="/rekomendasi Tebet Timur"))
    assert got.text == "IMBAUAN Tebet Timur depan"
    assert "/rekomendasi" in chat.handle(Incoming(text="/bantuan")).text


def test_monthly_advisories_go_to_registered_groups_once() -> None:
    from lapor_bot.telegram import deliver_advisories

    backend = FakeBackend()
    backend.groups = {"g1@g.us": "Tebet Timur", "g2@g.us": "Manggarai"}
    sent: list[tuple[str, str]] = []

    def wa(chat_id: str, reply: Reply) -> None:
        if chat_id == "g2@g.us":
            raise RuntimeError("WAHA kirim: 500")
        sent.append((chat_id, reply.text))

    assert deliver_advisories(backend, whatsapp_send=None) == 0
    assert deliver_advisories(backend, whatsapp_send=wa) == 1
    assert sent == [("g1@g.us", "IMBAUAN Tebet Timur")]
    assert backend.advisory_deliveries["Manggarai"]["whatsapp"].startswith("gagal")
    # Bulan yang sama tidak dikirim dua kali ke grup yang sudah menerima.
    assert deliver_advisories(backend, whatsapp_send=wa) == 0
