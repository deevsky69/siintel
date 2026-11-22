"""Peringkat bulanan 65 kelurahan — Modul 2–3 "Mekanisme dan Fungsi SIGAP".

APA YANG DIHITUNG

    Untuk bulan sasaran M, setiap kelurahan mendapat perkiraan jumlah kejadian, lalu seluruh
    kelurahan diurutkan dari perkiraan tertinggi; seri menurut abjad nama kelurahan.

        MODEL         gradient boosting (services/monthly_model.py) — metode utama sejak
                      17 November 2026, sesuai naskah Taskap Bab IV
        HISTORY_nM    rata-rata bulanan pada n bulan kalender terakhir sebelum M (peta)
        ANNUAL        peta satu tahun kalender yang tidak diperbarui (pembanding "lama")

    Hanya kejadian yang sudah DILAPORKAN sampai `data_cutoff` yang dipakai (tanggal laporan
    menentukan kapan kejadian boleh dipakai; tanggal kejadian menentukan bulannya). Kejadian
    yang kelurahannya belum pasti (`area_pending`) tidak ikut, tetapi jumlahnya disimpan.

    IKW (frekuensi 12 bulan, tren, konsistensi) dihitung di samping peringkat dengan bobot
    dari config/ranking/monthly.yaml — PROPOSED, tidak menentukan urutan.

MODEL HANYA BILA LEBIH TEPAT

    Naskah: "model hanya dipakai bila lebih tepat daripada peta titik rawan". `operational`
    menilai model dan seluruh pembanding pada bulan-bulan uji terakhir (di luar masa latih,
    batas data yang sama) dan mengembalikan metode yang dipakai sebagai dasar usulan beserta
    buktinya. Peta historis tetap menjadi dasar bila model belum unggul atau belum teruji.

Hasilnya DIBEKUKAN (`monthly_rankings`) sebelum bulan berjalan supaya dapat dievaluasi apa
adanya.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, MonthlyRanking, MonthlyRankingRow
from ..seeding.paths import REPO_ROOT
from . import clock, config_cache, ikw, kelurahan_area, visibility
from . import monthly_model as model
from .risk_engine import _known_by

CONFIG_FILE = REPO_ROOT / "config" / "ranking" / "monthly.yaml"
THREATS = ("CURANMOR", "CURAT", "CURAS")
IKW_MONTHS = 12
#: Penanda `data_source` pada laporan yang tanggal kejadiannya kosong di sumber.
UNDATED_MARK = "TANPA-TANGGAL-KEJADIAN"

BASIS = (
    "Peringkat bulan sasaran = perkiraan jumlah kejadian per kelurahan, hanya dari kejadian "
    "yang sudah dilaporkan sampai batas data; seri diurutkan menurut nama kelurahan. Metode "
    "MODEL adalah gradient boosting (kerugian Poisson) dengan masukan rerata 1, 3, 6, dan 12 "
    "bulan, rerata sepanjang riwayat, selisih rerata 3 dan 12 bulan, pola bulanan, dan "
    "kelurahan lain sekecamatan, mengikuti naskah Taskap Lampiran 8; parameternya dibekukan. "
    "Peta historis "
    "(3 bulan, 12 bulan, bulan sebelumnya, tahunan tetap) dihitung sebagai pembanding, dan "
    "model hanya menjadi dasar usulan bila cakupannya lebih tinggi daripada pembanding "
    "terbaik pada bulan-bulan uji terakhir. IKW = 25 x (0,50 F + 0,35 D + 0,15 T): frekuensi "
    "12 bulan, dampak terverifikasi 3 bulan, keberulangan 4 bulan, atas seluruh 3C; statusnya "
    "lengkap, sementara, atau ditahan mengikuti verifikasi dampak (PROPOSED)."
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
    ikw: ikw.IkwConfig
    model: model.ModelParams
    guard_months: int
    guard_min_months: int
    guard_min_margin_pct: float
    guard_min_pai: float
    guard_fallback: str
    default_top_n: int

    def kind(self, method: str) -> str:
        return str(self.methods[method].get("kind", "history"))

    def comparators(self) -> list[str]:
        """Metode pembanding (bukan model), urutan konfigurasi."""
        return [name for name in self.methods if self.kind(name) != "model"]


@lru_cache(maxsize=1)
def load_config() -> RankingConfig:
    if not CONFIG_FILE.exists():
        raise RankingError("config/ranking/monthly.yaml tidak ditemukan")
    raw: dict[str, Any] = config_cache.load_yaml(CONFIG_FILE)
    return RankingConfig(
        version=str(raw["version"]),
        status=str(raw.get("status", "UNKNOWN")),
        default_method=str(raw["default_method"]),
        methods={str(k): dict(v) for k, v in raw["methods"].items()},
        scopes=tuple(str(s) for s in raw["scopes"]),
        default_scope=str(raw["default_scope"]),
        ikw=ikw.IkwConfig(
            weights={str(k): float(v) for k, v in raw["ikw"]["weights"].items()},
            categories=tuple(
                sorted(
                    ((str(k), float(v)) for k, v in raw["ikw"]["categories"].items()),
                    key=lambda item: -item[1],
                )
            ),
            lowest=str(raw["ikw"].get("lowest", "RENDAH")),
        ),
        model=model.ModelParams.from_config(raw["model"]),
        guard_months=int(raw["guard"]["months"]),
        guard_min_months=int(raw["guard"]["min_months"]),
        guard_min_margin_pct=float(raw["guard"].get("min_margin_pct", 0.0)),
        guard_min_pai=float(raw["guard"].get("min_pai", 0.0)),
        guard_fallback=str(raw["guard"]["fallback"]),
        default_top_n=int((raw.get("evaluation") or {}).get("default_top_n", 6)),
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


def load_history(
    session: Session, scope: str, *, everything: bool = False
) -> model.IncidentHistory:
    """Seluruh kejadian 3C berkelurahan pada cakupan itu, dengan tanggal mulai diketahuinya.

    `everything=True` melewati batas tampilan data — hanya untuk evaluasi, yang memang harus
    melihat kejadian bulan sasaran.
    """
    config = load_config()
    areas = {
        str(kelurahan): str(kecamatan)
        for kelurahan, kecamatan in session.execute(
            select(Location.kelurahan, Location.kecamatan)
            .where(Location.kelurahan.is_not(None))
            .group_by(Location.kelurahan, Location.kecamatan)
        ).all()
    }
    query = (
        select(
            Location.kelurahan,
            CrimeIncident.incident_date,
            func.coalesce(CrimeIncident.reported_at, CrimeIncident.occurred_at),
        )
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            Location.kelurahan.is_not(None),
            CrimeIncident.incident_type.in_(THREATS),
            CrimeIncident.area_pending.is_(False),
            # Laporan tanpa tanggal kejadian (importer mengisinya dengan tanggal laporan dan
            # menandainya) tidak membentuk deret bulanan — naskah Tabel 6 mengecualikannya.
            func.coalesce(CrimeIncident.data_source, "").not_like(f"%{UNDATED_MARK}"),
        )
    )
    if scope == "VEHICLE":
        query = query.where(CrimeIncident.vehicle_object.is_(True))
    if everything:
        query = visibility.all_incidents(query)
    incidents: list[tuple[str, date, date]] = []
    for kelurahan, occurred, known in session.execute(query).all():
        known_on = (
            known.astimezone(clock.JAKARTA).date() if isinstance(known, datetime) else occurred
        )
        incidents.append((str(kelurahan), occurred, known_on))
    return model.IncidentHistory(incidents, areas, config.model.data_from)


def annual_year(config: RankingConfig) -> int:
    """Tahun peta tahunan tetap: tahun terakhir masa latih model."""
    return config.model.train_until.year


def _window(config: RankingConfig, method: str, target: int) -> tuple[date, date]:
    """(awal, akhir) bulan-bulan yang menjadi dasar perkiraan metode itu."""
    if config.kind(method) == "annual":
        year = annual_year(config)
        return date(year, 1, 1), date(year, 12, 31)
    months = int(config.methods[method]["basis_months"])
    return model.month_from_index(target - months), model.default_cutoff(target)


def scores(
    history: model.IncidentHistory,
    method: str,
    target: int,
    cutoff: date,
    config: RankingConfig | None = None,
) -> dict[str, float]:
    """Perkiraan jumlah kejadian per kelurahan menurut metode itu.

    Nilai TIDAK dibulatkan: peringkat disusun dari skor penuh (naskah Lampiran 8 E), dan
    pembulatan dua desimal hanya dilakukan saat disimpan — membulatkan dulu menciptakan seri
    yang tidak ada dan mengubah kelurahan pilihan."""
    config = config or load_config()
    kind = config.kind(method)
    if kind == "model":
        try:
            trained = model.train(history, config.model)
            return {
                p.kelurahan: p.predicted
                for p in model.predict_month(history, trained, target, cutoff, explain=False)
            }
        except model.ModelUnavailable as error:
            raise RankingError(str(error)) from error
    basis_from, basis_to = _window(config, method, target)
    if kind == "annual":
        if model.month_index(basis_to) >= target:
            raise RankingError(f"Peta tahunan {basis_to.year} belum utuh untuk bulan sasaran ini.")
        cutoff = min(cutoff, basis_to)
    first = model.month_index(basis_from)
    months = model.month_index(basis_to) - first + 1
    return {
        name: sum(history.count(name, first + i, cutoff) for i in range(months)) / months
        for name in history.areas
    }


def fixed_scores(
    history: model.IncidentHistory, method: str, target: int, config: RankingConfig
) -> dict[str, float]:
    """Skenario TETAP (naskah Tabel 12): seluruh informasi berhenti pada akhir masa latih.

    MODEL_FIXED  model dengan riwayat sampai `train_until` dan horizon = jarak ke bulan sasaran
    Q4_FIXED     peta tiga bulan terakhir masa latih (Oktober–Desember), tidak diperbarui
    """
    last = model.month_index(config.model.train_until)
    cutoff = config.model.train_until
    if method == "MODEL_FIXED":
        try:
            trained = model.train(history, config.model)
            return {
                p.kelurahan: p.predicted
                for p in model.predict_month(
                    history, trained, target, cutoff, horizon=target - last, explain=False
                )
            }
        except model.ModelUnavailable as error:
            raise RankingError(str(error)) from error
    if method == "Q4_FIXED":
        return {
            name: sum(history.count(name, last - back, cutoff) for back in range(3)) / 3
            for name in history.areas
        }
    raise RankingError(f"Metode {method} tidak dikenal.")


def order(values: dict[str, float]) -> list[str]:
    """Urutan peringkat: perkiraan tertinggi dulu, seri menurut nama kelurahan."""
    return [name for name, _ in sorted(values.items(), key=lambda item: (-item[1], item[0]))]


def compute(
    session: Session,
    target_month: date,
    method: str | None = None,
    scope: str | None = None,
    data_cutoff: date | None = None,
    history: model.IncidentHistory | None = None,
) -> ComputedRanking:
    config = load_config()
    method = method or config.default_method
    scope = scope or config.default_scope
    if method not in config.methods:
        raise RankingError(f"Metode {method} tidak dikenal.")
    if scope not in config.scopes:
        raise RankingError(f"Cakupan {scope} tidak dikenal.")
    target_month = month_start(target_month)
    target = model.month_index(target_month)
    last_day = target_month - timedelta(days=1)
    cutoff = min(data_cutoff, last_day) if data_cutoff else last_day
    history = history or load_history(session, scope)
    basis_from, basis_to = _window(config, method, target)
    predicted = scores(history, method, target, cutoff, config)

    explained: dict[str, model.Prediction] = {}
    model_version = f"{method.lower()}@{config.version}"
    if config.kind(method) == "model":
        trained = model.train(history, config.model)
        model_version = trained.version
        explained = {p.kelurahan: p for p in model.predict_month(history, trained, target, cutoff)}

    polsek_of = {
        str(kelurahan): str(polsek)
        for kelurahan, polsek in session.execute(
            select(Location.kelurahan, Location.polsek)
            .where(Location.kelurahan.is_not(None))
            .group_by(Location.kelurahan, Location.polsek)
        ).all()
    }
    pending_query = (
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
    if scope == "VEHICLE":
        pending_query = pending_query.where(CrimeIncident.vehicle_object.is_(True))
    pending_count = int(session.scalar(pending_query) or 0)

    months12 = [model.month_from_index(target - back) for back in range(IKW_MONTHS, 0, -1)]
    series = {
        name: [history.count(name, model.month_index(m), cutoff) for m in months12]
        for name in history.areas
    }
    basis_first = model.month_index(basis_from)
    basis_last = model.month_index(basis_to)
    indexes = _ikw_by_area(session, target, cutoff, config)
    rows: list[RankedArea] = []
    for rank, name in enumerate(order(predicted), start=1):
        counts = series[name]
        index = indexes.get(name)
        basis: dict[str, Any] = {
            "months": {m.isoformat()[:7]: c for m, c in zip(months12, counts, strict=True)},
            "basis_total": sum(
                history.count(name, month, min(cutoff, basis_to))
                for month in range(basis_first, basis_last + 1)
            ),
            "total_12m": sum(counts),
            "ikw": index,
        }
        if name in explained:
            basis.update(_explanation(explained[name]))
        rows.append(
            RankedArea(
                rank=rank,
                kelurahan=name,
                kecamatan=history.areas[name],
                polsek=polsek_of.get(name, ""),
                predicted_count=round(predicted[name], 2),
                ikw=index["value"] if index else None,
                ikw_category=index["category"] if index else None,
                basis=basis,
            )
        )
    return ComputedRanking(
        target_month=target_month,
        method=method,
        scope=scope,
        data_cutoff=cutoff,
        model_version=model_version,
        basis_from=basis_from,
        basis_to=basis_to,
        pending_count=pending_count,
        rows=rows,
    )


def _ikw_by_area(
    session: Session, target: int, cutoff: date, config: RankingConfig
) -> dict[str, dict[str, Any]]:
    """IKW tiap kelurahan untuk bulan sasaran, atas SELURUH 3C (naskah B.4.2) — terlepas dari
    cakupan peringkat. Hanya kejadian yang sudah dilaporkan sampai batas data."""
    first = model.month_from_index(target - ikw.FREQUENCY_MONTHS)
    last = model.default_cutoff(target)
    rows = session.execute(
        select(
            Location.kelurahan,
            CrimeIncident.incident_date,
            CrimeIncident.loss_status,
            CrimeIncident.injury_level,
            CrimeIncident.impact_status,
        )
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            Location.kelurahan.is_not(None),
            CrimeIncident.incident_type.in_(THREATS),
            CrimeIncident.area_pending.is_(False),
            CrimeIncident.incident_date >= first,
            CrimeIncident.incident_date <= last,
            func.coalesce(CrimeIncident.data_source, "").not_like(f"%{UNDATED_MARK}"),
            _known_by(cutoff),
        )
    ).all()
    names = [
        str(name)
        for name in session.scalars(
            select(Location.kelurahan).where(Location.kelurahan.is_not(None)).distinct()
        ).all()
    ]
    volume: dict[str, int] = dict.fromkeys(names, 0)
    months: dict[str, set[int]] = {name: set() for name in names}
    impacts: dict[str, list[int | None]] = {name: [] for name in names}
    for kelurahan, day, loss, injury, status in rows:
        name = str(kelurahan)
        if name not in volume:
            continue
        month = model.month_index(day)
        volume[name] += 1
        if target - month <= ikw.RECURRENCE_MONTHS:
            months[name].add(month)
        if target - month <= ikw.IMPACT_MONTHS:
            verified = status == "VERIFIED"
            impacts[name].append(ikw.impact_score(loss, injury) if verified else None)
    bounds = ikw.frequency_bounds(list(volume.values()))
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        entry = ikw.compute(volume[name], bounds, len(months[name]), impacts[name], config.ikw)
        entry["quartiles"] = list(bounds) if bounds else None
        result[name] = entry
    return result


def _explanation(prediction: model.Prediction) -> dict[str, Any]:
    """Alasan perkiraan model: masukan dan kontribusinya, dari pohon model itu sendiri.

    Model berkerugian Poisson bekerja pada skala logaritma, jadi kontribusi sebuah masukan
    adalah PENGALI atas perkiraan: `effect_pct` +35 berarti masukan itu menaikkan perkiraan
    35 persen dibanding tanpa pengaruhnya. `contribution` adalah nilai logaritmanya."""
    merged: dict[str, dict[str, Any]] = {}
    base = prediction.base
    for name in model.FEATURES:
        if name == "horizon":
            # Pada pemakaian rutin horizon selalu 1 — sama untuk semua kelurahan, jadi bukan
            # "alasan" sebuah kelurahan; pengaruhnya digabung ke nilai awal.
            base += prediction.contributions[name]
            continue
        label = model.FEATURE_LABELS[name]
        entry = merged.setdefault(label, {"label": label, "contribution": 0.0, "values": {}})
        entry["contribution"] += prediction.contributions[name]
        entry["values"][name] = round(prediction.features[name], 2)
    factors = sorted(merged.values(), key=lambda item: -abs(item["contribution"]))
    for item in factors:
        item["effect_pct"] = round((math.exp(item["contribution"]) - 1) * 100, 1)
        item["contribution"] = round(item["contribution"], 4)
    return {
        "source": "MODEL",
        "scale": "log",
        "model_base": round(base, 4),
        "factors": factors,
    }


@dataclass(frozen=True)
class MethodChoice:
    """Metode yang menjadi dasar usulan bulan itu, dan bukti di baliknya."""

    method: str
    reason: str
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"method": self.method, "reason": self.reason, "evidence": self.evidence}


def top_selection(
    history: model.IncidentHistory,
    method: str,
    target: int,
    top_n: int,
    config: RankingConfig,
    cutoff: date | None = None,
) -> list[str]:
    return order(scores(history, method, target, cutoff or model.default_cutoff(target), config))[
        :top_n
    ]


def operational(
    session: Session,
    target_month: date,
    scope: str | None = None,
    history: model.IncidentHistory | None = None,
) -> MethodChoice:
    """Metode dasar usulan untuk bulan sasaran: model bila terbukti lebih tepat, selain itu
    peta historis terbaik (atau `guard.fallback` bila bukti belum cukup)."""
    config = load_config()
    scope = scope or config.default_scope
    if config.kind(config.default_method) != "model":
        return MethodChoice(config.default_method, "Metode bawaan konfigurasi.", {})
    history = history or load_history(session, scope)
    target = model.month_index(month_start(target_month))
    known_until = model.default_cutoff(target)
    first_test = model.month_index(config.model.train_until) + 1
    months = [m for m in range(target - config.guard_months, target) if m >= first_test]
    fallback = config.guard_fallback
    evidence: dict[str, Any] = {
        "scope": scope,
        "top_n": config.default_top_n,
        "months": [model.month_from_index(m).isoformat()[:7] for m in months],
    }
    if len(months) < config.guard_min_months:
        return MethodChoice(
            fallback,
            f"Model belum dapat dinilai: baru {len(months)} bulan uji di luar masa latih "
            f"(perlu {config.guard_min_months}). Usulan memakai peta historis.",
            evidence,
        )
    methods = [config.default_method, *config.comparators()]
    covered = dict.fromkeys(methods, 0)
    total = 0
    shares: list[float | None] = []
    try:
        for month in months:
            actual = {name: history.count(name, month, known_until) for name in history.areas}
            total += sum(actual.values())
            for method in methods:
                try:
                    chosen = top_selection(history, method, month, config.default_top_n, config)
                except RankingError:
                    if config.kind(method) == "model":
                        raise
                    covered.pop(method, None)
                    continue
                if method in covered:
                    covered[method] += sum(actual[name] for name in chosen)
                if method == config.default_method:
                    shares.append(kelurahan_area.share(chosen))
    except RankingError as error:
        return MethodChoice(fallback, f"{error} Usulan memakai peta historis.", evidence)
    evidence["actual_total"] = total
    evidence["covered"] = covered
    best = max(
        (m for m in covered if m != config.default_method),
        key=lambda m: (covered[m], m == fallback),
    )
    evidence["best_comparator"] = best
    mine = covered[config.default_method]
    # Naskah revisi 7 sasaran 3.3.1: selisih cakupan dalam poin persen DAN PAI model.
    margin = round((mine - covered[best]) / total * 100, 2) if total else None
    share = sum(s for s in shares if s is not None) / len(shares) if shares else None
    if not shares or any(s is None for s in shares):
        share = None
    model_pai = round((mine / total) / share, 2) if total and share else None
    evidence["margin_pct"] = margin
    evidence["model_pai"] = model_pai
    evidence["criterion"] = criterion_config()
    summary = (
        f"Pada {len(months)} siklus uji terakhir model mencakup {mine} dari {total} kejadian; "
        f"pembanding terbaik ({config.methods[best]['label']}) {covered[best]}; selisih "
        f"{_id(margin)} poin persen; PAI model {_id(model_pai)}."
    )
    enough_margin = margin is not None and margin >= config.guard_min_margin_pct
    enough_pai = model_pai is not None and model_pai >= config.guard_min_pai
    evidence["met"] = bool(enough_margin and enough_pai)
    if enough_margin and enough_pai:
        return MethodChoice(
            config.default_method,
            f"{summary} Memenuhi ambang (selisih sekurang-kurangnya "
            f"{_id(config.guard_min_margin_pct)} poin persen dan PAI sekurang-kurangnya "
            f"{_id(config.guard_min_pai)}), sehingga model menjadi dasar prioritas.",
            evidence,
        )
    return MethodChoice(
        best,
        f"{summary} Belum memenuhi ambang (selisih sekurang-kurangnya "
        f"{_id(config.guard_min_margin_pct)} poin persen dan PAI sekurang-kurangnya "
        f"{_id(config.guard_min_pai)}), sehingga peringkat historis terbaik dipakai sebagai "
        "dasar prioritas sementara model diperbaiki.",
        evidence,
    )


def _id(value: float | None) -> str:
    """Angka dengan koma desimal; 'tidak dapat dihitung' bila kosong."""
    return "tidak dapat dihitung" if value is None else f"{value:.2f}".replace(".", ",")


def criterion_config() -> dict[str, Any]:
    """Ambang pemakaian model (naskah revisi 7 sasaran 3.3.1) untuk ditampilkan apa adanya."""
    config = load_config()
    return {
        "months": config.guard_months,
        "min_margin_pct": config.guard_min_margin_pct,
        "min_pai": config.guard_min_pai,
        "source": "Naskah Taskap revisi 7, sasaran 3.3.1 dan Lampiran L",
    }


def model_card(session: Session, scope: str | None = None) -> dict[str, Any] | None:
    """Keterangan model yang dipakai (versi, data latih, parameter, bobot masukan)."""
    config = load_config()
    scope = scope or config.default_scope
    try:
        trained = model.train(load_history(session, scope), config.model)
    except model.ModelUnavailable as error:
        return {"available": False, "reason": str(error), "scope": scope}
    return {"available": True, "scope": scope, **trained.describe()}


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
