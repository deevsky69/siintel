"""Peringkat bulanan 65 kelurahan — Modul 2–3 "Mekanisme dan Fungsi SIGAP" (6 Nov 2026).

APA YANG DIHITUNG

    Untuk bulan sasaran M, setiap kelurahan mendapat perkiraan jumlah kejadian = rata-rata
    bulanan pada `basis_months` bulan kalender terakhir sebelum M (peta 3 bulan atau 12 bulan;
    keputusan pemilik proyek 2A: 3 bulan dulu). Seluruh kelurahan diurutkan dari perkiraan
    tertinggi; seri menurut abjad nama kelurahan — persis dokumen mekanisme.

    Hanya kejadian yang sudah DILAPORKAN sampai `data_cutoff` yang dipakai (tanggal laporan
    menentukan kapan kejadian boleh dipakai; tanggal kejadian menentukan bulannya). Kejadian
    yang kelurahannya belum pasti (`area_pending`) tidak ikut, tetapi jumlahnya disimpan.

    IKW (frekuensi 12 bulan, tren, konsistensi) dihitung di samping peringkat dengan bobot
    dari config/ranking/monthly.yaml — PROPOSED, tidak menentukan urutan.

Hasilnya DIBEKUKAN (`monthly_rankings`) sebelum bulan berjalan supaya dapat dievaluasi apa
adanya. Metode MODEL belum tersedia: dokumen sendiri membolehkan peta historis sampai model
berikutnya selesai diuji.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, MonthlyRanking, MonthlyRankingRow
from ..seeding.paths import REPO_ROOT
from . import clock, visibility
from .risk_engine import _known_by

CONFIG_FILE = REPO_ROOT / "config" / "ranking" / "monthly.yaml"
THREATS = ("CURANMOR", "CURAT", "CURAS")
IKW_MONTHS = 12

BASIS = (
    "Peringkat bulan sasaran = rata-rata kejadian bulanan per kelurahan pada bulan-bulan "
    "kalender terakhir sebelum bulan sasaran (3 atau 12 bulan), hanya dari kejadian yang sudah "
    "dilaporkan sampai batas data; seri diurutkan menurut nama kelurahan. Bukan model terlatih. "
    "IKW (frekuensi 12 bulan, tren, konsistensi) tampil di samping dan berstatus PROPOSED."
)


class RankingError(ValueError):
    pass


@dataclass(frozen=True)
class RankingConfig:
    version: str
    status: str
    default_method: str
    methods: dict[str, dict[str, Any]]
    scopes: tuple[str, ...]
    default_scope: str
    ikw_weights: dict[str, float]
    categories: dict[str, tuple[int, int]]


@lru_cache(maxsize=1)
def load_config() -> RankingConfig:
    if not CONFIG_FILE.exists():
        raise RankingError("config/ranking/monthly.yaml tidak ditemukan")
    raw: dict[str, Any] = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    return RankingConfig(
        version=str(raw["version"]),
        status=str(raw.get("status", "UNKNOWN")),
        default_method=str(raw["default_method"]),
        methods={str(k): dict(v) for k, v in raw["methods"].items()},
        scopes=tuple(str(s) for s in raw["scopes"]),
        default_scope=str(raw["default_scope"]),
        ikw_weights={str(k): float(v) for k, v in raw["ikw"]["weights"].items()},
        categories={str(k): (int(v[0]), int(v[1])) for k, v in raw["ikw"]["categories"].items()},
    )


def add_months(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def parse_month(text: str) -> date:
    try:
        year, month = text.split("-")[:2]
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError) as error:
        raise RankingError("Bulan harus berbentuk YYYY-MM.") from error


def suggested_target_month(session: Session) -> date:
    """Bulan setelah batas data yang tersedia: bulan berikutnya dari batas tampilan, atau
    dari kejadian terakhir bila tanpa batas."""
    cutoff = visibility.display_cutoff()
    if cutoff is None:
        last = session.scalar(select(func.max(CrimeIncident.incident_date)))
        cutoff = last or clock.reference_now().astimezone(clock.JAKARTA).date()
    return add_months(month_start(cutoff), 1)


@dataclass
class RankedArea:
    rank: int
    kelurahan: str
    kecamatan: str
    polsek: str
    predicted_count: float
    ikw: float | None
    ikw_category: str | None
    basis: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "kelurahan": self.kelurahan,
            "kecamatan": self.kecamatan,
            "polsek": self.polsek,
            "predicted_count": self.predicted_count,
            "ikw": self.ikw,
            "ikw_category": self.ikw_category,
            "basis": self.basis,
        }


@dataclass
class ComputedRanking:
    target_month: date
    method: str
    scope: str
    data_cutoff: date
    model_version: str
    basis_from: date
    basis_to: date
    pending_count: int
    rows: list[RankedArea]

    def as_dict(self) -> dict[str, Any]:
        config = load_config()
        return {
            "target_month": self.target_month.isoformat()[:7],
            "method": self.method,
            "method_label": config.methods[self.method]["label"],
            "scope": self.scope,
            "data_cutoff": self.data_cutoff,
            "model_version": self.model_version,
            "basis_from": self.basis_from,
            "basis_to": self.basis_to,
            "pending_count": self.pending_count,
            "ikw_status": config.status,
            "data": [row.as_dict() for row in self.rows],
        }


def _category(config: RankingConfig, value: float) -> str | None:
    for name, (low, high) in config.categories.items():
        if low <= round(value) <= high:
            return name
    return None


def compute(
    session: Session,
    target_month: date,
    method: str | None = None,
    scope: str | None = None,
    data_cutoff: date | None = None,
) -> ComputedRanking:
    config = load_config()
    method = method or config.default_method
    scope = scope or config.default_scope
    if method not in config.methods:
        raise RankingError(f"Metode {method} tidak dikenal.")
    if method == "MODEL":
        raise RankingError("Metode MODEL belum tersedia; pakai peta historis (keputusan 2A).")
    if scope not in config.scopes:
        raise RankingError(f"Cakupan {scope} tidak dikenal.")
    target_month = month_start(target_month)
    basis_months = int(config.methods[method]["basis_months"])
    basis_to = target_month - timedelta(days=1)
    cutoff = data_cutoff or basis_to
    if cutoff > basis_to:
        cutoff = basis_to
    basis_from = add_months(target_month, -basis_months)
    ikw_from = add_months(target_month, -IKW_MONTHS)

    areas = session.execute(
        select(Location.kelurahan, Location.kecamatan, Location.polsek)
        .where(Location.kelurahan.is_not(None))
        .group_by(Location.kelurahan, Location.kecamatan, Location.polsek)
    ).all()

    month_key = func.to_char(CrimeIncident.incident_date, "YYYY-MM")
    query = (
        select(Location.kelurahan, month_key, func.count())
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            Location.kelurahan.is_not(None),
            CrimeIncident.incident_type.in_(THREATS),
            CrimeIncident.incident_date >= ikw_from,
            CrimeIncident.incident_date <= basis_to,
            CrimeIncident.area_pending.is_(False),
            _known_by(cutoff),
        )
        .group_by(Location.kelurahan, month_key)
    )
    if scope == "VEHICLE":
        query = query.where(CrimeIncident.vehicle_object.is_(True))
    series: dict[str, dict[str, int]] = defaultdict(dict)
    for kelurahan, month, count in session.execute(query).all():
        series[str(kelurahan)][str(month)] = int(count)

    months12 = [add_months(ikw_from, i).isoformat()[:7] for i in range(IKW_MONTHS)]
    basis_keys = months12[-basis_months:]
    pending_count = int(
        session.scalar(
            select(func.count())
            .select_from(CrimeIncident)
            .where(
                CrimeIncident.area_pending.is_(True),
                CrimeIncident.incident_type.in_(THREATS),
                CrimeIncident.incident_date >= basis_from,
                CrimeIncident.incident_date <= basis_to,
                _known_by(cutoff),
            )
        )
        or 0
    )

    totals12 = {str(k): sum(series[str(k)].get(m, 0) for m in months12) for k, _, _ in areas}
    peak12 = max(totals12.values(), default=0) or 1
    rows: list[RankedArea] = []
    for kelurahan, kecamatan, polsek in areas:
        name = str(kelurahan)
        counts = [series[name].get(m, 0) for m in months12]
        predicted = sum(series[name].get(m, 0) for m in basis_keys) / basis_months
        mean3 = sum(counts[-3:]) / 3
        mean9 = sum(counts[:-3]) / 9
        trend = max(-1.0, min(1.0, (mean3 - mean9) / max(mean9, 1.0)))
        frequency = totals12[name] / peak12 * 100
        trend_score = 50 + 50 * trend
        consistency = sum(1 for c in counts if c > 0) / IKW_MONTHS * 100
        ikw = (
            config.ikw_weights["frequency"] * frequency
            + config.ikw_weights["trend"] * trend_score
            + config.ikw_weights["consistency"] * consistency
        )
        rows.append(
            RankedArea(
                rank=0,
                kelurahan=name,
                kecamatan=str(kecamatan),
                polsek=str(polsek),
                predicted_count=round(predicted, 2),
                ikw=round(ikw, 1),
                ikw_category=_category(config, ikw),
                basis={
                    "months": dict(zip(months12, counts, strict=True)),
                    "basis_total": sum(series[name].get(m, 0) for m in basis_keys),
                    "total_12m": totals12[name],
                    "trend": round(trend, 2),
                    "consistency_months": sum(1 for c in counts if c > 0),
                },
            )
        )
    rows.sort(key=lambda row: (-row.predicted_count, row.kelurahan))
    for index, row in enumerate(rows, start=1):
        row.rank = index
    return ComputedRanking(
        target_month=target_month,
        method=method,
        scope=scope,
        data_cutoff=cutoff,
        model_version=f"{method.lower()}@{config.version}",
        basis_from=basis_from,
        basis_to=basis_to,
        pending_count=pending_count,
        rows=rows,
    )


def stored(session: Session, target_month: date, method: str, scope: str) -> MonthlyRanking | None:
    return session.scalar(
        select(MonthlyRanking).where(
            MonthlyRanking.target_month == month_start(target_month),
            MonthlyRanking.method == method,
            MonthlyRanking.scope == scope,
        )
    )


def freeze(session: Session, computed: ComputedRanking, user_id: Any) -> MonthlyRanking:
    if stored(session, computed.target_month, computed.method, computed.scope) is not None:
        raise RankingError("Peringkat bulan, metode, dan cakupan ini sudah dibekukan.")
    ranking = MonthlyRanking(
        target_month=computed.target_month,
        method=computed.method,
        scope=computed.scope,
        data_cutoff=computed.data_cutoff,
        model_version=computed.model_version,
        basis_from=computed.basis_from,
        basis_to=computed.basis_to,
        pending_count=computed.pending_count,
        generated_at=clock.citizen_now(),
        generated_by=user_id,
        rows=[
            MonthlyRankingRow(
                rank=row.rank,
                kelurahan=row.kelurahan,
                kecamatan=row.kecamatan,
                polsek=row.polsek,
                predicted_count=row.predicted_count,
                ikw=row.ikw,
                ikw_category=row.ikw_category,
                basis=row.basis,
            )
            for row in computed.rows
        ],
    )
    session.add(ranking)
    session.flush()
    return ranking


def stored_as_dict(ranking: MonthlyRanking) -> dict[str, Any]:
    config = load_config()
    return {
        "ranking_id": str(ranking.ranking_id),
        "target_month": ranking.target_month.isoformat()[:7],
        "method": ranking.method,
        "method_label": config.methods.get(ranking.method, {}).get("label", ranking.method),
        "scope": ranking.scope,
        "data_cutoff": ranking.data_cutoff,
        "model_version": ranking.model_version,
        "basis_from": ranking.basis_from,
        "basis_to": ranking.basis_to,
        "pending_count": ranking.pending_count,
        "generated_at": ranking.generated_at,
        "ikw_status": config.status,
        "data": [
            {
                "rank": row.rank,
                "kelurahan": row.kelurahan,
                "kecamatan": row.kecamatan,
                "polsek": row.polsek,
                "predicted_count": float(row.predicted_count),
                "ikw": float(row.ikw) if row.ikw is not None else None,
                "ikw_category": row.ikw_category,
                "basis": row.basis,
            }
            for row in ranking.rows
        ],
    }


def frozen_months(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(MonthlyRanking.target_month, MonthlyRanking.method, MonthlyRanking.scope).order_by(
            MonthlyRanking.target_month.desc(), MonthlyRanking.method
        )
    ).all()
    return [
        {"target_month": m.isoformat()[:7], "method": method, "scope": scope}
        for m, method, scope in rows
    ]
