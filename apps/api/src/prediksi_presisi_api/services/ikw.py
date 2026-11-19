"""Indeks Kerawanan Wilayah (IKW) — naskah Taskap final Bab IV B.4.2 dan Lampiran 9.

    IKW = 25 × (0,50 F + 0,35 D + 0,15 T)

    F  frekuensi     0 bila nihil dalam 12 bulan terakhir; selain itu 1–4 menurut kuartil
                     volume positif antarkelurahan. Frekuensi yang sama mendapat skor sama.
    D  dampak        skor tertinggi yang TERVERIFIKASI dalam tiga bulan terakhir:
                     1 percobaan tanpa kerugian atau cedera, 2 kehilangan atau kerusakan tanpa
                     cedera, 3 cedera, 4 cedera berat atau kematian; 0 bila tiada kejadian.
    T  keberulangan  jumlah bulan berkejadian dalam empat bulan terakhir (0–4).

Ketiganya berskala 0–4 dan bobotnya berjumlah 1; pengali 25 = 100/4 menjadikannya 0–100. Ini
skor kerawanan HISTORIS, bukan peluang kejahatan. Bobot dan batas kategori adalah asumsi awal
simulasi peneliti (config/ranking/monthly.yaml, PROPOSED).

STATUS mengikuti kelengkapan verifikasi dampak pada jendela tiga bulan:

    LENGKAP    seluruh laporan pada jendela itu dampaknya terverifikasi (atau tidak ada laporan)
    SEMENTARA  baru sebagian; D dari dampak tertinggi yang sudah terverifikasi
    DITAHAN    ada laporan, tetapi belum satu pun dampaknya terverifikasi — IKW tidak diterbitkan

Dampak berskor 4 selalu memicu telaah segera (`review_now`). Modul ini murni hitungan.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import quantiles
from typing import Any

FREQUENCY_MONTHS = 12
IMPACT_MONTHS = 3
RECURRENCE_MONTHS = 4
SCALE = 25.0

STATUS_COMPLETE = "LENGKAP"
STATUS_PROVISIONAL = "SEMENTARA"
STATUS_WITHHELD = "DITAHAN"


def impact_score(loss_status: str | None, injury_level: str | None) -> int | None:
    """Skor dampak 1–4 satu laporan, atau None bila isiannya belum cukup untuk dinilai."""
    if injury_level in ("SEVERE", "DEATH"):
        return 4
    if injury_level == "INJURY":
        return 3
    if loss_status == "PRESENT" and injury_level == "NONE":
        return 2
    if loss_status == "NONE" and injury_level == "NONE":
        return 1
    return None


def frequency_bounds(volumes: Sequence[int]) -> tuple[float, float, float] | None:
    """Batas kuartil (Q1, Q2, Q3) volume positif antarkelurahan; None bila semuanya nihil."""
    positive = sorted(v for v in volumes if v > 0)
    if not positive:
        return None
    if len(positive) == 1:
        return (float(positive[0]),) * 3
    q1, q2, q3 = quantiles(positive, n=4, method="inclusive")
    return float(q1), float(q2), float(q3)


def frequency_score(volume: int, bounds: tuple[float, float, float] | None) -> int:
    if volume <= 0 or bounds is None:
        return 0
    return 1 + sum(1 for bound in bounds if volume > bound)


@dataclass(frozen=True)
class IkwConfig:
    weights: Mapping[str, float]
    #: (nama, batas bawah inklusif) dari yang tertinggi, mis. (("TINGGI", 65), ("SEDANG", 35)).
    categories: tuple[tuple[str, float], ...]
    lowest: str

    def category(self, value: float) -> str:
        for name, floor in self.categories:
            if value >= floor:
                return name
        return self.lowest


def compute(
    volume_12m: int,
    bounds: tuple[float, float, float] | None,
    months_with_incidents: int,
    impacts: Sequence[int | None],
    config: IkwConfig,
) -> dict[str, Any]:
    """IKW satu kelurahan. `impacts` berisi skor dampak tiap laporan pada jendela tiga bulan;
    None = dampaknya belum terverifikasi."""
    verified = [score for score in impacts if score is not None]
    if not impacts or len(verified) == len(impacts):
        status = STATUS_COMPLETE
    elif verified:
        status = STATUS_PROVISIONAL
    else:
        status = STATUS_WITHHELD
    frequency = frequency_score(volume_12m, bounds)
    recurrence = max(0, min(RECURRENCE_MONTHS, months_with_incidents))
    impact = max(verified) if verified else 0
    value: float | None = None
    if status != STATUS_WITHHELD:
        value = SCALE * (
            config.weights["frequency"] * frequency
            + config.weights["impact"] * impact
            + config.weights["recurrence"] * recurrence
        )
    return {
        "value": round(value, 1) if value is not None else None,
        "category": config.category(value) if value is not None else None,
        "status": status,
        "frequency": frequency,
        "impact": impact if verified or not impacts else None,
        "recurrence": recurrence,
        "volume_12m": volume_12m,
        "impact_reports": len(impacts),
        "impact_verified": len(verified),
        "review_now": impact == 4,
    }
