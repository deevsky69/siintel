"""Evaluasi bulanan — Modul 5 "Menilai prediksi, rekomendasi, dan tindak lanjut".

KETEPATAN PREDIKSI. Setelah bulan sasaran berakhir: kejadian aktual di kelurahan pilihan
dibagi seluruh kejadian aktual yang dapat dipetakan (punya kelurahan) pada bulan dan cakupan
yang sama = CAKUPAN. Setiap peringkat yang dibekukan dinilai pada N kelurahan teratas; N =
jumlah yang ditetapkan Pimpinan bila ada, selain itu `evaluation.default_top_n`. Pembanding
peta historis (3 bulan, 12 bulan) dihitung dengan N dan batas data yang SAMA.

MUTU REKOMENDASI. Rekap usulan diterima / direvisi / ditolak beserta alasannya, dan tahap
yang dikembalikan KBO/Kasat.

PELAKSANAAN. Per kelurahan yang ditetapkan Pimpinan: kejadian aktual bulan itu dan kegiatan
yang tercatat.

PAI belum dihitung: luas kelurahan belum tersedia di API (lokasi disimpan sebagai titik).
Kejadian bulan sasaran dibaca melewati batas tampilan data (`visibility.all_incidents`),
seperti evaluasi mundur — hanya untuk pencocokan, bukan layar.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, MonthlyProduct, MonthlyRanking
from . import monthly_ranking as ranking
from . import visibility

BASIS = (
    "Cakupan = kejadian aktual bulan sasaran di N kelurahan teratas / seluruh kejadian aktual "
    "yang dapat dipetakan pada cakupan yang sama. N = jumlah yang ditetapkan Pimpinan, atau "
    "default_top_n. Pembanding peta historis memakai N dan batas data yang sama. PAI belum "
    "dihitung: luas kelurahan belum tersedia di API."
)


def _default_top_n() -> int:
    raw: dict[str, Any] = yaml.safe_load(ranking.CONFIG_FILE.read_text(encoding="utf-8"))
    return int((raw.get("evaluation") or {}).get("default_top_n", 6))


def _actual_by_kelurahan(
    session: Session, month: Any, scope: str, polsek: str | None = None
) -> tuple[dict[str, int], int]:
    """Kejadian aktual bulan sasaran per kelurahan, dan jumlah yang tidak dapat dipetakan."""
    start = ranking.month_start(month)
    end = ranking.add_months(start, 1) - timedelta(days=1)
    base = (
        select(Location.kelurahan, func.count())
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_type.in_(ranking.THREATS),
            CrimeIncident.incident_date >= start,
            CrimeIncident.incident_date <= end,
        )
    )
    if scope == "VEHICLE":
        base = base.where(CrimeIncident.vehicle_object.is_(True))
    if polsek is not None:
        base = base.where(Location.polsek == polsek)
    mapped = base.where(
        Location.kelurahan.is_not(None), CrimeIncident.area_pending.is_(False)
    ).group_by(Location.kelurahan)
    rows = session.execute(visibility.all_incidents(mapped)).all()
    counts = {str(k): int(c) for k, c in rows}
    unmapped_q = (
        select(func.count())
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_type.in_(ranking.THREATS),
            CrimeIncident.incident_date >= start,
            CrimeIncident.incident_date <= end,
            (Location.kelurahan.is_(None)) | (CrimeIncident.area_pending.is_(True)),
        )
    )
    if scope == "VEHICLE":
        unmapped_q = unmapped_q.where(CrimeIncident.vehicle_object.is_(True))
    if polsek is not None:
        unmapped_q = unmapped_q.where(Location.polsek == polsek)
    unmapped = int(session.scalar(visibility.all_incidents(unmapped_q)) or 0)
    return counts, unmapped


def _coverage(selected: list[str], actual: dict[str, int]) -> dict[str, Any]:
    total = sum(actual.values())
    covered = sum(actual.get(name, 0) for name in selected)
    return {
        "selected": selected,
        "covered": covered,
        "mappable_total": total,
        "coverage_pct": round(covered / total * 100, 2) if total else None,
    }


def evaluate(session: Session, month: Any, polsek: str | None = None) -> dict[str, Any]:
    """`polsek` membatasi SELURUH angka ke wilayah itu (pengguna Polsek): kejadian aktual,
    kelurahan pilihan, dan kelurahan prioritas di luar polseknya tidak ikut dihitung."""
    start = ranking.month_start(month)
    product = session.scalar(select(MonthlyProduct).where(MonthlyProduct.target_month == start))
    frozen = session.scalars(
        select(MonthlyRanking)
        .where(MonthlyRanking.target_month == start)
        .order_by(MonthlyRanking.scope, MonthlyRanking.method)
    ).all()
    top_n = product.priority_count if product and product.priority_count else _default_top_n()
    actual_cache: dict[str, tuple[dict[str, int], int]] = {}

    def actual_for(scope: str) -> tuple[dict[str, int], int]:
        if scope not in actual_cache:
            actual_cache[scope] = _actual_by_kelurahan(session, start, scope, polsek)
        return actual_cache[scope]

    def within(rows: Any) -> list[str]:
        return [r.kelurahan for r in rows if polsek is None or r.polsek == polsek]

    methods: list[dict[str, Any]] = []
    for row in frozen:
        actual, unmapped = actual_for(row.scope)
        selected = within(row.rows[:top_n])
        methods.append(
            {
                "method": row.method,
                "scope": row.scope,
                "frozen": True,
                "data_cutoff": row.data_cutoff,
                "top_n": top_n,
                "unmappable": unmapped,
                **_coverage(selected, actual),
                "pai": None,
            }
        )
        # Pembanding: metode historis lain pada N dan batas data yang sama, bila belum beku.
        for other in ("HISTORY_3M", "HISTORY_12M"):
            if other == row.method or any(
                m["method"] == other and m["scope"] == row.scope for m in methods
            ):
                continue
            computed = ranking.compute(session, start, other, row.scope, row.data_cutoff)
            methods.append(
                {
                    "method": other,
                    "scope": row.scope,
                    "frozen": False,
                    "data_cutoff": computed.data_cutoff,
                    "top_n": top_n,
                    "unmappable": unmapped,
                    **_coverage(within(computed.rows[:top_n]), actual),
                    "pai": None,
                }
            )

    decision: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    if product is not None:
        actual, _ = actual_for(str(product.facts.get("scope", "ALL_3C")))
        chosen = [
            item
            for item in product.items
            if item.selected and (polsek is None or item.polsek == polsek)
        ]
        decision = {
            "status": product.status,
            "priority_count": product.priority_count,
            **_coverage([item.kelurahan for item in chosen], actual),
            "items": [
                {
                    "kelurahan": item.kelurahan,
                    "kecamatan": item.kecamatan,
                    "actual": actual.get(item.kelurahan, 0),
                    "actions": len(item.actions),
                    "decided_action": item.decided_action,
                }
                for item in chosen
            ],
        }
        tally = {"ACCEPTED": 0, "REVISED": 0, "REJECTED": 0}
        reasons: list[dict[str, str]] = []
        for item in product.items:
            if item.analyst_status in tally:
                tally[item.analyst_status] += 1
            if item.analyst_reason:
                reasons.append(
                    {
                        "kelurahan": item.kelurahan,
                        "status": str(item.analyst_status),
                        "reason": item.analyst_reason,
                    }
                )
        returns = [
            {"stage": s.stage, "reason": s.reason, "acted_at": s.acted_at}
            for s in product.stages
            if s.outcome == "REJECTED"
        ]
        quality = {"analyst": tally, "reasons": reasons, "returned": returns}

    return {
        "target_month": start.isoformat()[:7],
        "top_n": top_n,
        "methods": methods,
        "decision": decision,
        "quality": quality,
        "basis": BASIS,
    }
