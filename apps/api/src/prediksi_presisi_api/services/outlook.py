"""Perkiraan singkat satu bulan ke depan — di mana, jam berapa, dan apa rekomendasinya.

Permintaan pemilik proyek 9 Oktober 2026: ekspor .docx "perkiraan singkat kira-kira akan ada
ancaman di mana saja, jam berapa, dan apa rekomendasinya" untuk satu bulan ke depan.

DARI MANA PERKIRAANNYA — DINYATAKAN APA ADANYA

    Bukan model terlatih. Perkiraan bulan M disusun dari kejadian pada bulan kalender yang
    SAMA pada tahun-tahun sebelumnya yang tersedia (sampai batas tampilan data), dengan unit
    yang sama seperti rencana patroli: kelurahan × blok 3 jam × jenis. Slot diperingkat
    menurut jumlah kejadian; yang diusulkan adalah slot teratas sebanyak
    `max_slots_per_threat` dengan kejadian >= `minimum_incidents` (config/patrol/
    plan-rules.yaml — aturan yang sama, supaya dua layar tidak memakai dua aturan).

    Mengambil bulan yang sama, bukan dua belas bulan terakhir, adalah pilihan teknis:
    pola kamtibmas punya musim (mudik, tahun ajaran, akhir tahun). Pilihan ini PROPOSED,
    dan setiap slot membawa angkanya sendiri supaya dapat dihitung ulang dengan tangan.

    Rekomendasi per slot diturunkan dari config/recommendation/function-rules.yaml (fungsi
    dan tindakan per jenis ancaman) — aturan yang sama dengan rekomendasi harian.

Ini USULAN kepada Pimpinan, bukan perintah (CLAUDE.md §13–§14).
"""

from __future__ import annotations

import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from docx import Document
from docx.shared import Pt
from sqlalchemy.orm import Session

from ..api.analysis import HOUR_BLOCK_STARTS, hour_block_label
from . import clock
from . import patrol_plan as planning
from .warning_issuance import load_function_rules

MONTHS_ID = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)  # fmt: skip

OUTLOOK_BASIS = (
    "Perkiraan bulan sasaran disusun dari kejadian pada bulan kalender yang sama pada "
    "tahun-tahun sebelumnya yang tersedia (unit kelurahan x blok 3 jam x jenis), diperingkat "
    "menurut jumlah kejadian; slot teratas sebanyak max_slots_per_threat dengan kejadian >= "
    "minimum_incidents (config/patrol/plan-rules.yaml). Bukan model terlatih; pilihan 'bulan "
    "yang sama' adalah pilihan teknis bermusim (PROPOSED). Rekomendasi mengikuti "
    "config/recommendation/function-rules.yaml. Usulan kepada Pimpinan, bukan perintah."
)


def month_label(year: int, month: int) -> str:
    return f"{MONTHS_ID[month - 1]} {year}"


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = (date(year + (month // 12), month % 12 + 1, 1) - timedelta(days=1)) if True else start
    return start, end


def default_target_month() -> tuple[int, int]:
    """Bulan setelah bulan waktu acuan (aplikasi berdiri di awal 2026 → Februari 2026)."""
    now = clock.reference_now().astimezone(clock.JAKARTA)
    year, month = now.year, now.month + 1
    if month == 13:
        year, month = year + 1, 1
    return year, month


@dataclass
class OutlookSlot:
    rank: int
    polsek: str
    kecamatan: str
    kelurahan: str
    block: int
    incidents: int
    share_percent: float
    function: str
    recommendation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "polsek": self.polsek,
            "kecamatan": self.kecamatan,
            "kelurahan": self.kelurahan,
            "block_start": self.block,
            "block_label": hour_block_label(self.block),
            "incidents": self.incidents,
            "share_percent": self.share_percent,
            "function": self.function,
            "recommendation": self.recommendation,
        }


def build_outlook(
    session: Session, year: int, month: int, polsek: str | None = None
) -> dict[str, Any]:
    rules = planning.load_rules()
    function_rules = load_function_rules()
    threats = planning._threats()  # jenis yang memang dinilai versi bobot aktif
    cutoff = planning._cutoff(session)

    # Bulan yang sama pada tahun-tahun sebelumnya, selama seluruh bulannya <= batas tampilan.
    basis_months: list[tuple[int, int]] = []
    by_unit: dict[planning.Unit, int] = defaultdict(int)
    by_block: dict[tuple[str, int], int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    with_hour: dict[str, int] = defaultdict(int)
    for past_year in range(year - 1, year - 6, -1):
        start, end = _month_bounds(past_year, month)
        if end > cutoff:
            continue
        observed = planning.observe(session, start, end, threats, polsek)
        if not observed.total:
            continue
        basis_months.append((past_year, month))
        for unit, count in observed.by_unit.items():
            by_unit[unit] += count
        for key, count in observed.by_block.items():
            by_block[key] += count
        for threat, count in observed.total.items():
            total[threat] += count
            with_hour[threat] += observed.with_hour.get(threat, 0)

    per_threat: list[dict[str, Any]] = []
    for threat in threats:
        rule = function_rules.for_threat(threat)
        candidates = sorted(
            ((unit, count) for unit, count in by_unit.items() if unit.threat_type == threat),
            key=lambda item: (-item[1], item[0].kelurahan, item[0].block),
        )
        known = with_hour.get(threat, 0)
        slots: list[OutlookSlot] = []
        for unit, count in candidates:
            if count < rules.minimum_incidents or len(slots) >= rules.max_slots_per_threat:
                break
            label = hour_block_label(unit.block)
            slots.append(
                OutlookSlot(
                    rank=len(slots) + 1,
                    polsek=unit.polsek,
                    kecamatan=unit.kecamatan,
                    kelurahan=unit.kelurahan,
                    block=unit.block,
                    incidents=count,
                    share_percent=round(100 * count / known, 1) if known else 0.0,
                    function=rule.function,
                    recommendation=(
                        f"{rule.action} oleh {rule.function} di Kelurahan {unit.kelurahan} "
                        f"({unit.kecamatan}) pada {label}."
                    ),
                )
            )
        blocks: list[dict[str, Any]] = [
            {
                "block_start": start,
                "block_label": hour_block_label(start),
                "incidents": by_block.get((threat, start), 0),
                "share_percent": (
                    round(100 * by_block.get((threat, start), 0) / known, 1) if known else 0.0
                ),
            }
            for start in HOUR_BLOCK_STARTS
        ]
        peak = max(blocks, key=lambda row: int(row["incidents"])) if known else None
        per_threat.append(
            {
                "threat_type": threat,
                "function": rule.function,
                "action": rule.action,
                "basis_incidents": total.get(threat, 0),
                "basis_with_hour": known,
                "peak_block": peak["block_label"] if peak and peak["incidents"] else None,
                "hour_profile": blocks,
                "slots": [slot.as_dict() for slot in slots],
            }
        )

    return {
        "target_month": f"{year:04d}-{month:02d}",
        "target_label": month_label(year, month),
        "basis_months": [f"{y:04d}-{m:02d}" for y, m in basis_months],
        "basis_labels": [month_label(y, m) for y, m in basis_months],
        "scope": polsek,
        "rules_version": rules.version,
        "status": "PROPOSED",
        "threats": per_threat,
        "basis": OUTLOOK_BASIS,
        "function_rules_status": function_rules.status,
    }


# ---------------------------------------------------------------------------
# .docx
# ---------------------------------------------------------------------------


def render_docx(outlook: dict[str, Any]) -> bytes:
    """Dokumen Word ringkas: judul, dasar, tabel per jenis, catatan human-in-the-loop."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    document.add_heading(f"Perkiraan Singkat Kerawanan — {outlook['target_label']}", level=1)
    scope = outlook.get("scope") or "Polres Metro Jakarta Selatan"
    document.add_paragraph(
        f"Lingkup: {scope}. Disusun {clock.reference_now().astimezone(clock.JAKARTA):%d %B %Y} "
        f"oleh PREDIKSI PRESISI. Status: {outlook['status']} — usulan kepada Pimpinan, "
        "bukan perintah."
    )
    basis = ", ".join(outlook["basis_labels"]) or "tidak ada bulan dasar yang tersedia"
    document.add_paragraph(f"Dasar: pola kejadian pada {basis}. {outlook['basis']}")

    for threat in outlook["threats"]:
        document.add_heading(threat["threat_type"], level=2)
        peak = threat["peak_block"] or "tidak dapat ditentukan"
        document.add_paragraph(
            f"Pada bulan dasar tercatat {threat['basis_incidents']} kejadian "
            f"({threat['basis_with_hour']} dengan jam). Blok jam paling rawan: {peak}. "
            f"Fungsi yang diusulkan: {threat['function']} — {threat['action']}."
        )
        if not threat["slots"]:
            document.add_paragraph(
                "Tidak ada kelurahan x blok jam yang memenuhi batas minimum kejadian; "
                "polanya tersebar. Patroli mengikuti pola jam di atas."
            )
            continue
        table = document.add_table(rows=1, cols=5)
        table.style = "Light Grid Accent 1"
        header = table.rows[0].cells
        for cell, text in zip(
            header, ("No", "Kelurahan (Kecamatan)", "Jam", "Kejadian", "Rekomendasi"), strict=True
        ):
            cell.text = text
        for slot in threat["slots"]:
            row = table.add_row().cells
            row[0].text = str(slot["rank"])
            row[1].text = f"{slot['kelurahan']} ({slot['kecamatan']})"
            row[2].text = slot["block_label"]
            row[3].text = f"{slot['incidents']} ({slot['share_percent']}%)"
            row[4].text = slot["recommendation"]

    document.add_heading("Catatan", level=2)
    document.add_paragraph(
        "Angka pada dokumen ini dihitung dari kejadian yang tercatat pada bulan yang sama "
        "tahun-tahun sebelumnya, bukan dari model terlatih, dan belum dievaluasi terhadap "
        "bulan sasaran. Keputusan penempatan patroli tetap pada Pimpinan (human-in-the-loop); "
        "setiap keputusan tercatat pada jejak audit."
    )
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
