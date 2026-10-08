"""Rekomendasi dicocokkan dengan kejadian nyata tahun sasaran (permintaan pemilik proyek
8 Oktober 2026): "apakah hasil rekomendasi sejalan dengan data real 2026 atau tidak".

Setiap rekomendasi lahir dari satu prediksi: JENIS ancaman, KELURAHAN, dan JENDELA JAM
(enam jam) pada satu hari di awal 2026, disusun dari pola sampai 2025. Aplikasi diperagakan
seolah berdiri di awal 2026 (`services/visibility.py`); kejadian 2026 tersimpan dan hanya
dibaca oleh pencocokan seperti ini.

DUA CARA MEMBACA "SEJALAN", KEDUANYA DISAJIKAN

1. **Jendela harfiah** — adakah kejadian jenis itu di kelurahan itu pada enam jam yang
   persis diprediksi (1–2 Januari 2026)? Ini ukuran yang paling ketat dan hampir selalu
   kosong: satu kelurahan rata-rata mengalami beberapa kejadian setahun, sehingga peluang
   satu jendela enam jam terisi sangat kecil (catatan 016). Angkanya tetap disebut supaya
   tidak ada yang mengira disembunyikan.
2. **Pola tahun berjalan** — rekomendasi berbunyi "patroli jenis X di kelurahan Y pada blok
   jam Z". Sepanjang 2026 yang sudah tercatat: berapa kejadian X di Y, dan berapa bagian
   di antaranya jatuh pada blok Z? Bila Y memang tetap mengalami X dan blok Z memuat
   bagian yang lebih besar daripada porsi jamnya (6/24 = 25%), rekomendasi itu SEJALAN
   dengan kenyataan — tempat dan jamnya sama-sama terbukti. Bila tempatnya terbukti tetapi
   jamnya tidak: SEBAGIAN. Bila kelurahan itu tidak mengalami X sama sekali: TIDAK SEJALAN.

Aturan pada butir 2 berstatus PROPOSED: batas "lebih besar daripada porsi jamnya" adalah
pilihan teknis yang masuk akal, bukan ketentuan yang ditetapkan pemilik proyek (CLAUDE.md
§11, §26). Setiap baris membawa angkanya sendiri sehingga dapat dihitung ulang dengan tangan.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, Prediction, Recommendation
from . import visibility

WIB = ZoneInfo("Asia/Jakarta")

VERDICT_ALIGNED = "SEJALAN"
VERDICT_PARTIAL = "SEBAGIAN"
VERDICT_NOT_ALIGNED = "TIDAK_SEJALAN"
VERDICT_UNEVALUABLE = "BELUM_DAPAT_DINILAI"

OUTCOME_BASIS = (
    "Tiap rekomendasi dicocokkan dengan kejadian nyata tahun sasaran yang sudah tercatat "
    "(di luar batas tampilan layar). Jendela harfiah: ada kejadian jenis itu di kelurahan itu "
    "pada enam jam yang persis diprediksi. Pola tahun berjalan: kejadian jenis itu di kelurahan "
    "itu sepanjang tahun sasaran, dan bagian yang jatuh pada blok jam yang direkomendasikan, "
    "dibandingkan porsi jamnya (lama blok / 24 jam). SEJALAN = tempat dan jam terbukti "
    "(bagian blok >= porsi jam dan >= 1 kejadian); SEBAGIAN = tempat terbukti, jam tidak; "
    "TIDAK SEJALAN = kelurahan itu tidak mengalami jenis itu sama sekali. Kejadian tanpa jam "
    "dihitung untuk tempat, tidak untuk jam. Aturan ini PROPOSED (U-03)."
)


def parse_time_window(window: str | None) -> tuple[int, int] | None:
    """'18:00-23:59' -> (18, 24); '00:00-06:00' -> (0, 6). None bila tidak terbaca."""
    if not window or "-" not in window:
        return None
    try:
        start_text, end_text = window.split("-", 1)
        start = int(start_text.strip()[:2])
        end_hour, end_minute = end_text.strip().split(":")[:2]
        end = int(end_hour) + (1 if int(end_minute) >= 59 else 0)
    except ValueError:
        return None
    if not (0 <= start < end <= 24):
        return None
    return start, end


@dataclass(frozen=True)
class _Actual:
    threat_type: str
    kelurahan: str | None
    incident_date: date
    hour: int | None
    occurred_at: datetime


def _actuals(session: Session, year: int, threats: tuple[str, ...]) -> list[_Actual]:
    rows = session.execute(
        visibility.all_incidents(
            select(
                CrimeIncident.incident_type,
                Location.kelurahan,
                CrimeIncident.incident_date,
                CrimeIncident.incident_time,
                CrimeIncident.time_known,
                CrimeIncident.occurred_at,
            )
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(
                CrimeIncident.incident_date >= date(year, 1, 1),
                CrimeIncident.incident_date <= date(year, 12, 31),
                CrimeIncident.incident_type.in_(threats),
            )
        )
    ).all()
    return [
        _Actual(
            threat_type=threat,
            kelurahan=kelurahan,
            incident_date=incident_date,
            hour=incident_time.hour if (time_known and incident_time is not None) else None,
            occurred_at=occurred_at,
        )
        for threat, kelurahan, incident_date, incident_time, time_known, occurred_at in rows
    ]


def evaluate_recommendations(session: Session, polsek: str | None) -> dict[str, Any]:
    """Setiap rekomendasi (semua status) beserta kenyataan tahun sasarannya."""
    query = (
        select(Recommendation, Prediction, Location)
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .order_by(Recommendation.code)
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    triples = session.execute(query).all()
    if not triples:
        return _empty(None)

    years = {prediction.window_start.astimezone(WIB).year for _, prediction, _ in triples}
    threats = tuple(sorted({prediction.threat_type for _, prediction, _ in triples}))
    actuals: list[_Actual] = []
    for year in sorted(years):
        actuals.extend(_actuals(session, year, threats))
    observed_to = max((row.incident_date for row in actuals), default=None)

    # Peringkat kelurahan per (tahun, jenis): 1 = paling banyak kejadian.
    area_counts: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in actuals:
        if row.kelurahan:
            area_counts[(row.incident_date.year, row.threat_type)][row.kelurahan] += 1
    area_rank: dict[tuple[int, str, str], int] = {}
    for key, per_area in area_counts.items():
        ordered = sorted(per_area.items(), key=lambda item: (-item[1], item[0]))
        for rank, (kelurahan, _count) in enumerate(ordered, start=1):
            area_rank[(key[0], key[1], kelurahan)] = rank

    rows: list[dict[str, Any]] = []
    tally: dict[str, int] = defaultdict(int)
    window_hits = 0
    for recommendation, prediction, location in triples:
        year = prediction.window_start.astimezone(WIB).year
        hours = parse_time_window(prediction.time_window)
        same_area = [
            row
            for row in actuals
            if row.threat_type == prediction.threat_type
            and row.kelurahan == location.kelurahan
            and row.incident_date.year == year
        ]
        timed = [row for row in same_area if row.hour is not None]
        in_block = (
            [row for row in timed if hours[0] <= row.hour < hours[1]]  # type: ignore[operator]
            if hours
            else []
        )
        literal_hit = any(
            prediction.window_start <= row.occurred_at <= prediction.window_end for row in timed
        )
        expected_share = round(100 * (hours[1] - hours[0]) / 24, 1) if hours else None
        block_share = round(100 * len(in_block) / len(timed), 1) if timed else None

        if hours is None or location.kelurahan is None:
            verdict = VERDICT_UNEVALUABLE
        elif not same_area:
            verdict = VERDICT_NOT_ALIGNED
        elif in_block and block_share is not None and block_share >= (expected_share or 0):
            verdict = VERDICT_ALIGNED
        else:
            verdict = VERDICT_PARTIAL
        tally[verdict] += 1
        window_hits += 1 if literal_hit else 0

        rows.append(
            {
                "code": recommendation.code,
                "status": recommendation.status,
                "priority": recommendation.priority,
                "recommended_function": recommendation.recommended_function,
                "prediction_code": prediction.code,
                "threat_type": prediction.threat_type,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "time_window": prediction.time_window,
                "window_start": prediction.window_start,
                "window_end": prediction.window_end,
                "risk_score": prediction.risk_score,
                "target_year": year,
                "literal_window_hit": literal_hit,
                "area_incidents": len(same_area),
                "area_timed_incidents": len(timed),
                "area_unknown_time": len(same_area) - len(timed),
                "block_incidents": len(in_block),
                "block_share_percent": block_share,
                "expected_share_percent": expected_share,
                "area_rank": area_rank.get(
                    (year, prediction.threat_type, location.kelurahan or "")
                ),
                "area_rank_of": len(area_counts.get((year, prediction.threat_type), {})),
                "verdict": verdict,
            }
        )

    return {
        **_empty(observed_to),
        "target_years": sorted(years),
        "rows": rows,
        "summary": {
            "total": len(rows),
            "aligned": tally[VERDICT_ALIGNED],
            "partial": tally[VERDICT_PARTIAL],
            "not_aligned": tally[VERDICT_NOT_ALIGNED],
            "unevaluable": tally[VERDICT_UNEVALUABLE],
            "literal_window_hits": window_hits,
            "aligned_percent": round(100 * tally[VERDICT_ALIGNED] / len(rows), 1) if rows else None,
        },
    }


def _empty(observed_to: date | None) -> dict[str, Any]:
    return {
        "target_years": [],
        "observed_to": observed_to.isoformat() if observed_to else None,
        "rows": [],
        "summary": {
            "total": 0,
            "aligned": 0,
            "partial": 0,
            "not_aligned": 0,
            "unevaluable": 0,
            "literal_window_hits": 0,
            "aligned_percent": None,
        },
        "status": "PROPOSED",
        "basis": OUTCOME_BASIS,
    }
