"""Evaluasi bulanan — Modul 5 "Menilai prediksi, rekomendasi, dan tindak lanjut".

KETEPATAN PREDIKSI. Setelah bulan sasaran berakhir: kejadian aktual di kelurahan pilihan
dibagi seluruh kejadian aktual yang dapat dipetakan (punya kelurahan) pada bulan dan cakupan
yang sama = CAKUPAN. Setiap peringkat yang dibekukan dinilai pada N kelurahan teratas; N =
jumlah yang ditetapkan Pimpinan bila ada, selain itu `evaluation.default_top_n`. Model dan
seluruh pembanding peta historis dihitung dengan N dan batas data yang SAMA.

PAI (Predictive Accuracy Index, Chainey dkk. 2008) = porsi kejadian yang tercakup dibagi
porsi LUAS kelurahan yang ditandai. Luas dari config/ranking/kelurahan-area.yaml —
perkiraan dari poligon peta, PROPOSED sampai luas resmi tersedia.

UJI HISTORIS (`backtest`). Seluruh bulan di luar masa latih model, satu per satu: setiap
metode memilih N kelurahan dari yang sudah diketahui sebelum bulan itu, lalu dicocokkan
dengan kejadian aktualnya. Konsistensi keunggulan model terhadap tiap pembanding diuji
dengan UJI TANDA SATU ARAH atas hasil bulanan (bulan seri tidak dihitung).

MUTU REKOMENDASI. Rekap usulan diterima / direvisi / ditolak beserta alasannya.

PELAKSANAAN. Per kelurahan yang ditetapkan Pimpinan: kejadian aktual bulan itu dan kegiatan
yang tercatat.

Kejadian bulan sasaran dibaca melewati batas tampilan data (`visibility.all_incidents`),
seperti evaluasi mundur — hanya untuk pencocokan, bukan layar.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from math import comb
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, MonthlyProduct, MonthlyRanking
from ..seeding.paths import REPO_ROOT
from . import config_cache, visibility
from . import monthly_model as model
from . import monthly_ranking as ranking

AREA_FILE = REPO_ROOT / "config" / "ranking" / "kelurahan-area.yaml"

BASIS = (
    "Cakupan = kejadian aktual bulan sasaran di N kelurahan teratas / seluruh kejadian aktual "
    "yang dapat dipetakan pada cakupan yang sama. N = jumlah yang ditetapkan Pimpinan, atau "
    "default_top_n. Model dan pembanding peta historis memakai N dan batas data yang sama. "
    "PAI = porsi kejadian tercakup / porsi luas kelurahan yang ditandai; luas kelurahan adalah "
    "perkiraan dari poligon peta (PROPOSED)."
)

BACKTEST_BASIS = (
    "Uji historis: untuk setiap bulan di luar masa latih model, tiap metode memilih N "
    "kelurahan hanya dari kejadian yang sudah dilaporkan sebelum bulan itu, lalu dicocokkan "
    "dengan kejadian aktual bulan itu. Parameter model tidak diubah selama uji; hanya "
    "riwayatnya yang diperbarui tiap bulan. Uji tanda satu arah menghitung peluang memperoleh "
    "sekurangnya sebanyak itu bulan unggul bila model dan pembanding sebenarnya setara "
    "(bulan seri tidak dihitung). Ini ketepatan penunjukan wilayah, bukan jumlah kejahatan "
    "yang dicegah."
)


def _default_top_n() -> int:
    return ranking.load_config().default_top_n


@lru_cache(maxsize=1)
def kelurahan_areas() -> dict[str, float]:
    """Luas kelurahan (km²); kosong bila berkasnya belum dibangkitkan."""
    if not AREA_FILE.exists():
        return {}
    raw: dict[str, Any] = config_cache.load_yaml(AREA_FILE)
    return {str(name): float(value) for name, value in (raw.get("kelurahan") or {}).items()}


def _area_share(selected: list[str], universe: list[str]) -> float | None:
    """Porsi luas kelurahan pilihan terhadap seluruh kelurahan yang dinilai."""
    areas = kelurahan_areas()
    if not areas or any(name not in areas for name in universe):
        return None
    total = sum(areas[name] for name in universe)
    return sum(areas[name] for name in selected) / total if total else None


def pai(covered: int, total: int, area_share: float | None) -> float | None:
    if not total or not area_share:
        return None
    return round((covered / total) / area_share, 2)


def sign_test(wins: int, losses: int) -> float | None:
    """Uji tanda satu arah: P(X >= wins) untuk X ~ Binomial(wins + losses, 0,5)."""
    trials = wins + losses
    if trials == 0:
        return None
    tail = sum(comb(trials, k) for k in range(wins, trials + 1))
    return round(tail / float(2**trials), 4)


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


def _coverage(
    selected: list[str], actual: dict[str, int], universe: list[str] | None = None
) -> dict[str, Any]:
    total = sum(actual.values())
    covered = sum(actual.get(name, 0) for name in selected)
    share = _area_share(selected, universe) if universe else None
    return {
        "selected": selected,
        "covered": covered,
        "mappable_total": total,
        "coverage_pct": round(covered / total * 100, 2) if total else None,
        "area_pct": round(share * 100, 2) if share is not None else None,
        "pai": pai(covered, total, share),
    }


def _polsek_of(session: Session) -> dict[str, str]:
    return {
        str(kelurahan): str(polsek)
        for kelurahan, polsek in session.execute(
            select(Location.kelurahan, Location.polsek)
            .where(Location.kelurahan.is_not(None))
            .group_by(Location.kelurahan, Location.polsek)
        ).all()
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
    config = ranking.load_config()
    polsek_of = _polsek_of(session)
    universe = sorted(name for name, owner in polsek_of.items() if polsek in (None, owner))
    actual_cache: dict[str, tuple[dict[str, int], int]] = {}
    history_cache: dict[str, model.IncidentHistory] = {}

    def actual_for(scope: str) -> tuple[dict[str, int], int]:
        if scope not in actual_cache:
            actual_cache[scope] = _actual_by_kelurahan(session, start, scope, polsek)
        return actual_cache[scope]

    def history_for(scope: str) -> model.IncidentHistory:
        if scope not in history_cache:
            history_cache[scope] = ranking.load_history(session, scope, everything=True)
        return history_cache[scope]

    def within(names: list[str]) -> list[str]:
        return [name for name in names if polsek is None or polsek_of.get(name) == polsek]

    target = model.month_index(start)
    methods: list[dict[str, Any]] = []
    for row in frozen:
        actual, unmapped = actual_for(row.scope)
        methods.append(
            {
                "method": row.method,
                "method_label": config.methods.get(row.method, {}).get("label", row.method),
                "scope": row.scope,
                "frozen": True,
                "data_cutoff": row.data_cutoff,
                "model_version": row.model_version,
                "top_n": top_n,
                "unmappable": unmapped,
                **_coverage(within([r.kelurahan for r in row.rows[:top_n]]), actual, universe),
            }
        )
        # Pembanding: model dan peta historis lain pada N dan batas data yang sama, bila
        # belum beku. Riwayat dibaca tanpa batas tampilan, tetapi `data_cutoff` peringkat
        # beku tetap membatasi apa yang boleh diketahui.
        for other in config.methods:
            if other == row.method or any(
                m["method"] == other and m["scope"] == row.scope for m in methods
            ):
                continue
            try:
                chosen = ranking.top_selection(
                    history_for(row.scope), other, target, top_n, config, row.data_cutoff
                )
            except ranking.RankingError:
                continue
            methods.append(
                {
                    "method": other,
                    "method_label": config.methods[other]["label"],
                    "scope": row.scope,
                    "frozen": False,
                    "data_cutoff": row.data_cutoff,
                    "model_version": None,
                    "top_n": top_n,
                    "unmappable": unmapped,
                    **_coverage(within(chosen), actual, universe),
                }
            )

    decision: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    if product is not None:
        actual, _ = actual_for(str(product.facts.get("scope", "ALL_3C")))
        decided = [
            item
            for item in product.items
            if item.selected and (polsek is None or item.polsek == polsek)
        ]
        decision = {
            "status": product.status,
            "priority_count": product.priority_count,
            **_coverage([item.kelurahan for item in decided], actual, universe),
            "items": [
                {
                    "kelurahan": item.kelurahan,
                    "kecamatan": item.kecamatan,
                    "actual": actual.get(item.kelurahan, 0),
                    "actions": len(item.actions),
                    "decided_action": item.decided_action,
                }
                for item in decided
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


def _last_complete_month(history: model.IncidentHistory) -> int | None:
    """Bulan terakhir yang datanya sudah utuh: bulan kejadian termuda bila tanggalnya hari
    terakhir bulan itu, selain itu bulan sebelumnya."""
    if history.last_date is None:
        return None
    index = model.month_index(history.last_date)
    return index if history.last_date == model.default_cutoff(index + 1) else index - 1


def backtest(
    session: Session,
    scope: str | None = None,
    first: date | None = None,
    last: date | None = None,
    top_n: int | None = None,
    polsek: str | None = None,
) -> dict[str, Any]:
    """Uji historis model terhadap seluruh pembanding, bulan demi bulan (Tabel 12 naskah)."""
    config = ranking.load_config()
    scope = scope or config.default_scope
    if scope not in config.scopes:
        raise ranking.RankingError(f"Cakupan {scope} tidak dikenal.")
    top_n = top_n or config.default_top_n
    history = ranking.load_history(session, scope, everything=True)
    first_test = model.month_index(config.model.train_until) + 1
    start = max(model.month_index(first), first_test) if first else first_test
    complete = _last_complete_month(history)
    end = min(model.month_index(last), complete) if last and complete is not None else complete
    if last and complete is None:
        end = model.month_index(last)
    polsek_of = _polsek_of(session)
    universe = sorted(name for name, owner in polsek_of.items() if polsek in (None, owner))

    card: dict[str, Any]
    try:
        card = {"available": True, **model.train(history, config.model).describe()}
    except model.ModelUnavailable as error:
        card = {"available": False, "reason": str(error)}
    names = [m for m in config.methods if config.kind(m) != "model" or card["available"]]

    monthly: list[dict[str, Any]] = []
    for month in range(start, (end if end is not None else start - 1) + 1):
        actual = {name: history.count(name, month, date.max) for name in universe}
        results: dict[str, Any] = {}
        for method in names:
            try:
                chosen = ranking.top_selection(history, method, month, top_n, config)
            except ranking.RankingError:
                continue
            chosen = [name for name in chosen if name in actual]
            results[method] = {
                "selected": chosen,
                "covered": sum(actual[name] for name in chosen),
                "area_share": _area_share(chosen, universe),
            }
        monthly.append(
            {
                "month": model.month_from_index(month).isoformat()[:7],
                "total": sum(actual.values()),
                "methods": results,
            }
        )

    def summarise(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = sum(row["total"] for row in rows)
        out: list[dict[str, Any]] = []
        for method in names:
            present = [row for row in rows if method in row["methods"]]
            if len(present) != len(rows) or not rows:
                continue  # metode tidak berlaku pada seluruh bulan periode ini
            covered = sum(row["methods"][method]["covered"] for row in present)
            shares = [row["methods"][method]["area_share"] for row in present]
            share = sum(shares) / len(shares) if all(s is not None for s in shares) else None
            out.append(
                {
                    "method": method,
                    "method_label": config.methods[method]["label"],
                    "kind": config.kind(method),
                    "covered": covered,
                    "total": total,
                    "coverage_pct": round(covered / total * 100, 2) if total else None,
                    "area_pct": round(share * 100, 2) if share is not None else None,
                    "pai": pai(covered, total, share),
                }
            )
        tests: list[dict[str, Any]] = []
        primary = next((m for m in names if config.kind(m) == "model"), None)
        if primary and any(entry["method"] == primary for entry in out):
            for entry in out:
                if entry["method"] == primary:
                    continue
                wins = losses = ties = 0
                for row in rows:
                    gap = (
                        row["methods"][primary]["covered"]
                        - row["methods"][entry["method"]]["covered"]
                    )
                    wins += gap > 0
                    losses += gap < 0
                    ties += gap == 0
                tests.append(
                    {
                        "against": entry["method"],
                        "against_label": entry["method_label"],
                        "wins": wins,
                        "losses": losses,
                        "ties": ties,
                        "p_value": sign_test(wins, losses),
                    }
                )
        return {"label": label, "months": len(rows), "methods": out, "sign_tests": tests}

    periods: list[dict[str, Any]] = []
    years = sorted({row["month"][:4] for row in monthly})
    for year in years:
        rows = [row for row in monthly if row["month"].startswith(year)]
        span = f"{rows[0]['month']} s.d. {rows[-1]['month']}"
        periods.append({"span": span, **summarise(year, rows)})
    if len(years) > 1:
        span = f"{monthly[0]['month']} s.d. {monthly[-1]['month']}"
        periods.append({"span": span, **summarise("Seluruh masa uji", monthly)})

    # Skenario tetap (naskah Tabel 12): informasi berhenti pada akhir masa latih. Hanya
    # berlaku selama horizon yang dilatih (12 bulan pertama setelah masa latih).
    fixed: list[dict[str, Any]] = []
    fixed_months = [
        m
        for m in range(first_test, first_test + config.model.max_horizon)
        if end is not None and start <= m <= end
    ]
    fixed_methods = (
        ("MODEL_FIXED", "Model AI, informasi sampai akhir masa latih"),
        ("ANNUAL", f"Peta tahun {ranking.annual_year(config)}"),
        ("Q4_FIXED", f"Peta Oktober-Desember {ranking.annual_year(config)}"),
    )
    if fixed_months and card["available"]:
        total = 0
        covered = dict.fromkeys((name for name, _ in fixed_methods), 0)
        for month in fixed_months:
            actual = {name: history.count(name, month, date.max) for name in universe}
            total += sum(actual.values())
            for name, _ in fixed_methods:
                values = (
                    ranking.scores(history, name, month, config.model.train_until, config)
                    if name == "ANNUAL"
                    else ranking.fixed_scores(history, name, month, config)
                )
                covered[name] += sum(
                    actual[k] for k in ranking.order(values)[:top_n] if k in actual
                )
        fixed = [
            {
                "method": name,
                "method_label": label,
                "covered": covered[name],
                "total": total,
                "coverage_pct": round(covered[name] / total * 100, 2) if total else None,
            }
            for name, label in fixed_methods
        ]

    for row in monthly:
        for entry in row["methods"].values():
            share = entry.pop("area_share")
            entry["area_pct"] = round(share * 100, 2) if share is not None else None
    areas = kelurahan_areas()
    return {
        "scope": scope,
        "top_n": top_n,
        "kelurahan_total": len(universe),
        "first_month": monthly[0]["month"] if monthly else None,
        "last_month": monthly[-1]["month"] if monthly else None,
        "model": card,
        "annual_year": ranking.annual_year(config),
        "periods": periods,
        "fixed": {
            "span": f"{model.month_from_index(fixed_months[0]).isoformat()[:7]} s.d. "
            f"{model.month_from_index(fixed_months[-1]).isoformat()[:7]}"
            if fixed_months
            else None,
            "methods": fixed,
        },
        "monthly": monthly,
        "area_source": "config/ranking/kelurahan-area.yaml (perkiraan dari poligon peta)"
        if areas
        else None,
        "basis": BACKTEST_BASIS,
    }
