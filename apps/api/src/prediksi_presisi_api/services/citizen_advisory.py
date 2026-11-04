"""Imbauan kehati-hatian warga per kelurahan untuk satu bulan — untuk grup WhatsApp.

Keputusan pemilik proyek 4 November 2026: bot dimasukkan ke grup warga (RT/RW, Babin);
imbauan bulan berjalan dikirim OTOMATIS awal bulan tanpa persetujuan, dan atas permintaan
lewat /rekomendasi (bulan depan).

APA YANG DIKIRIM — DAN APA YANG TIDAK

    Sumbernya `outlook.build_outlook` (perkiraan singkat satu bulan ke depan: pola bulan
    kalender yang sama pada tahun-tahun sebelumnya; PROPOSED, bukan model terlatih). Dari
    situ diambil slot yang jatuh pada kelurahan yang diminta; bila kelurahan itu tidak
    menonjol untuk suatu jenis, dipakai jam puncak Polres untuk jenis itu dan DIKATAKAN
    begitu. Tips per jenis dibaca dari `config/recommendation/citizen-advice.yaml`.

    Yang TIDAK pernah ikut: skor risiko, confidence, fungsi/taktik kepolisian, titik
    kejadian. Batas informasi publik 2 November 2026 tetap berlaku; yang ini adalah
    imbauan, bukan rekomendasi operasional. Versi lengkap tetap di /ops.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import yaml
from sqlalchemy.orm import Session

from ..seeding.paths import REPO_ROOT
from . import clock, outlook

ADVICE_FILE = REPO_ROOT / "config" / "recommendation" / "citizen-advice.yaml"
#: Imbauan hanya memuat beberapa jenis teratas supaya terbaca di ponsel.
MAX_ITEMS = 4


@dataclass(frozen=True)
class Advice:
    status: str
    intro: str
    outro: str
    labels: dict[str, str]
    tips: dict[str, list[str]]

    def label(self, threat: str) -> str:
        return self.labels.get(threat, threat.replace("_", " ").title())

    def tips_for(self, threat: str) -> list[str]:
        return self.tips.get(threat) or self.tips.get("default") or []


def load_advice() -> Advice:
    raw: dict[str, Any] = yaml.safe_load(ADVICE_FILE.read_text(encoding="utf-8")) or {}
    return Advice(
        status=str(raw.get("status", "PROPOSED")),
        intro=str(raw.get("intro", "")),
        outro=str(raw.get("outro", "")),
        labels={str(k).upper(): str(v) for k, v in dict(raw.get("labels") or {}).items()},
        tips={
            str(k).upper() if str(k) != "default" else "default": [str(t) for t in (v or [])]
            for k, v in dict(raw.get("tips") or {}).items()
        },
    )


def month_after(today: date) -> tuple[int, int]:
    """Bulan setelah `today` — untuk /rekomendasi ("bulan depan")."""
    year, month = today.year, today.month + 1
    if month == 13:
        year, month = year + 1, 1
    return year, month


def current_month() -> tuple[int, int]:
    """Bulan berjalan menurut WAKTU SEBENARNYA (imbauan dikirim kepada warga hari ini)."""
    today = clock.citizen_now().astimezone(clock.JAKARTA).date()
    return today.year, today.month


def build_advisory(session: Session, year: int, month: int, kelurahan: str) -> dict[str, Any]:
    """Imbauan satu kelurahan untuk satu bulan. `items` kosong bila tidak ada pola sama sekali."""
    advice = load_advice()
    source = outlook.build_outlook(session, year, month, None)
    wanted = kelurahan.strip().casefold()
    items: list[dict[str, Any]] = []
    for threat in source["threats"]:
        if not threat["basis_incidents"]:
            continue
        local = [slot for slot in threat["slots"] if str(slot["kelurahan"]).casefold() == wanted]
        if local:
            top = local[0]
            items.append(
                {
                    "threat_type": threat["threat_type"],
                    "label": advice.label(str(threat["threat_type"])),
                    "block_label": top["block_label"],
                    "incidents": int(top["incidents"]),
                    "scope": "kelurahan",
                    "tips": advice.tips_for(str(threat["threat_type"])),
                }
            )
        elif threat["peak_block"]:
            items.append(
                {
                    "threat_type": threat["threat_type"],
                    "label": advice.label(str(threat["threat_type"])),
                    "block_label": threat["peak_block"],
                    "incidents": int(threat["basis_with_hour"]),
                    "scope": "polres",
                    "tips": advice.tips_for(str(threat["threat_type"])),
                }
            )
    # Yang menonjol di kelurahan ini didahulukan, lalu yang jumlahnya terbanyak.
    items.sort(key=lambda item: (item["scope"] != "kelurahan", -item["incidents"]))
    return {
        "kelurahan": kelurahan.strip(),
        "target_month": source["target_month"],
        "target_label": source["target_label"],
        "basis_labels": source["basis_labels"],
        "status": advice.status,
        "items": items[:MAX_ITEMS],
        "intro": advice.intro,
        "outro": advice.outro,
    }


def render_text(advisory: dict[str, Any]) -> str:
    """Teks WhatsApp: pendek, bernomor, tanpa angka internal selain jumlah kejadian historis."""
    kelurahan = advisory["kelurahan"]
    bulan = advisory["target_label"]
    lines = [
        f"*IMBAUAN KAMTIBMAS — {kelurahan.upper()} — {bulan.upper()}*",
        advisory["intro"].format(kelurahan=kelurahan, bulan=bulan),
        "",
    ]
    items = advisory["items"]
    if not items:
        lines.append(
            f"Belum ada pola kejadian yang dapat dijadikan imbauan untuk {bulan}. "
            "Tetap waspada dan laporkan hal mencurigakan."
        )
    basis = ", ".join(advisory["basis_labels"]) if advisory["basis_labels"] else "—"
    for index, item in enumerate(items, start=1):
        scope = (
            ""
            if item["scope"] == "kelurahan"
            else " (pola se-Polres; kelurahan ini tidak menonjol)"
        )
        lines.append(
            f"{index}. *{item['label']}* — jam rawan {item['block_label']} "
            f"({item['incidents']} kejadian pada {basis}){scope}"
        )
        lines.extend(f"   • {tip}" for tip in item["tips"][:3])
        lines.append("")
    lines.append(advisory["outro"])
    lines.append(f"_Peragaan · imbauan {advisory['status']}, bukan perintah; data posisi arsip._")
    return "\n".join(lines).strip()
