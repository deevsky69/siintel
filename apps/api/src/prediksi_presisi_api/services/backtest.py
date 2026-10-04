"""Evaluasi mundur (backtest): prediksi "seolah pada hari H-1" dibandingkan kejadian hari H.

Success criteria #06 Taskap menuntut angka precision/recall yang dihitung — bukan
diandaikan. Sampai 1 Oktober 2026 tabel `prediction_actual` hanya pernah diisi seeder
sintetis, sehingga layar Prediction vs Actual memamerkan angka yang tidak pernah dihitung
siapa pun. Modul ini menghitungnya dari data asli.

CARA KERJANYA, HARI DEMI HARI

```text
untuk setiap hari sasaran H pada rentang evaluasi:
    as_of  = H - jarak horizon                       (24H -> H-1)
    bukti  = kejadian yang SUDAH DILAPORKAN sampai akhir as_of   (risk_engine._known_by)
    skor   = assess_historical(bukti, bobot aktif, H)            (sel x jenis x jendela)
    prediksi tingkat peringatan = skor >= minimum_score (warning-thresholds.yaml)
    kejadian nyata hari H dengan jam tercatat -> (sel, jenis, jendela)

    prediksi & ada kejadian pada sel+jenis+jendela  -> HIT
    prediksi & tidak ada kejadian                   -> FALSE_POSITIVE
    kejadian tanpa prediksi tingkat peringatan      -> FALSE_NEGATIVE   (CLAUDE.md §26)
    kejadian tanpa jam tercatat                     -> TIDAK DAPAT DIEVALUASI, dihitung terpisah
```

EMPAT HAL YANG MENENTUKAN KEJUJURAN ANGKANYA

1. **Bukti dibatasi menurut tanggal LAPOR, bukan tanggal kejadian.** p90 jarak lapor pada
   data asli 3,4 hari; kejadian Senin yang baru dilaporkan Kamis tidak boleh ikut menilai
   Selasa. Tanpa batas ini angka recall naik oleh pengetahuan dari masa depan.
2. **Unit evaluasi = (sel, jenis, jendela 6 jam) — persis unit prediksinya.** Kejadian
   yang jamnya tidak tercatat (21,9% data asli) tidak dapat ditempatkan pada jendela mana
   pun; ia TIDAK dihitung sebagai false negative dan TIDAK diabaikan diam-diam, melainkan
   dilaporkan sebagai "tidak dapat dievaluasi". Aturan pencocokan ini PROPOSED (U-03):
   mencocokkan menurut hari penuh atau menurut kecamatan akan memberi angka yang berbeda,
   dan mana yang bermakna operasional adalah keputusan pemilik proyek.
3. **Ambang "prediksi tingkat peringatan" = ambang terbit peringatan yang berlaku.** Yang
   dievaluasi adalah apa yang sistem benar-benar akan tampilkan sebagai peringatan, bukan
   angka ambang pilihan evaluator.
4. **Prediksi yang dievaluasi DITULIS** (`status = VALIDATED`, `prediction_date = as_of`)
   supaya setiap baris `prediction_actual` menunjuk prediksi yang benar-benar ada, lengkap
   dengan faktor dan bobotnya. Yang ditulis hanya yang mencapai ambang; menulis 832
   kombinasi per hari selama 271 hari hanya menambah 225 ribu baris yang tidak pernah
   dibandingkan dengan apa pun.

Tidak ada model terlatih di sini. `model_version` menyebut versi aturan yang sama dengan
Prediction Center (`rule-persistence-v1`): skor prediksi = skor penilaian terakhir yang
dapat dihitung pada as_of.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Prediction, PredictionActual
from . import audit, clock, visibility
from . import prediction_engine as engine
from . import risk_engine as risk

AUDIT_ACTION = "RUN_BACKTEST"
AUDIT_RESOURCE = "evaluation"

MATCH_HIT = "HIT"
MATCH_FALSE_POSITIVE = "FALSE_POSITIVE"
MATCH_FALSE_NEGATIVE = "FALSE_NEGATIVE"

MATCHING_BASIS = (
    "Unit pencocokan: sel (kelurahan/kecamatan) x jenis x jendela 6 jam, sama dengan unit "
    "prediksi. HIT bila ada kejadian jenis itu pada sel dan jendela yang diprediksi; "
    "FALSE_POSITIVE bila tidak ada; FALSE_NEGATIVE bila ada kejadian tanpa prediksi "
    "tingkat peringatan. Kejadian tanpa jam tercatat tidak dapat ditempatkan pada jendela "
    "dan dilaporkan terpisah sebagai tidak dapat dievaluasi. Aturan ini PROPOSED (U-03)."
)

EVIDENCE_BASIS = (
    "Bukti tiap hari dibatasi pada kejadian yang sudah DILAPORKAN sampai akhir hari "
    "prediksi (reported_at), bukan yang sudah terjadi: p90 jarak lapor 3,4 hari, dan "
    "mengikutkan kejadian yang belum diketahui berarti menilai dengan pengetahuan dari masa "
    "depan."
)


class BacktestError(Exception):
    """Rentang atau konfigurasi tidak memungkinkan evaluasi."""


@dataclass
class DayResult:
    target_date: date
    as_of: date
    predictions: int
    hits: int
    false_positives: int
    false_negatives: int
    unevaluable: int
    skipped_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_date": self.target_date.isoformat(),
            "as_of": self.as_of.isoformat(),
            "predictions": self.predictions,
            "hits": self.hits,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "unevaluable": self.unevaluable,
            "skipped_reason": self.skipped_reason,
        }


@dataclass
class BacktestSummary:
    start: date
    end: date
    horizon: str
    weights_version: str
    threshold_version: str
    minimum_score: int
    threat_types: tuple[str, ...]
    written: bool
    days: list[DayResult] = field(default_factory=list)

    @property
    def hits(self) -> int:
        return sum(day.hits for day in self.days)

    @property
    def false_positives(self) -> int:
        return sum(day.false_positives for day in self.days)

    @property
    def false_negatives(self) -> int:
        return sum(day.false_negatives for day in self.days)

    @property
    def unevaluable(self) -> int:
        return sum(day.unevaluable for day in self.days)

    @property
    def predictions(self) -> int:
        return sum(day.predictions for day in self.days)

    @property
    def precision(self) -> float | None:
        predicted = self.hits + self.false_positives
        return round(self.hits / predicted, 3) if predicted else None

    @property
    def recall(self) -> float | None:
        actual = self.hits + self.false_negatives
        return round(self.hits / actual, 3) if actual else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "horizon": self.horizon,
            "weights_version": self.weights_version,
            "threshold_version": self.threshold_version,
            "minimum_score": self.minimum_score,
            "threat_types": list(self.threat_types),
            "written": self.written,
            "days_evaluated": sum(1 for day in self.days if day.skipped_reason is None),
            "days_skipped": sum(1 for day in self.days if day.skipped_reason is not None),
            "predictions": self.predictions,
            "hits": self.hits,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "unevaluable_incidents": self.unevaluable,
            "precision": self.precision,
            "recall": self.recall,
            "matching_basis": MATCHING_BASIS,
            "evidence_basis": EVIDENCE_BASIS,
            "status": "PROPOSED",
        }


# ---------------------------------------------------------------------------
# Bahan
# ---------------------------------------------------------------------------


def _window_of(hour: int) -> str | None:
    for label, (start, end) in risk.TIME_WINDOWS.items():
        if start <= hour < end:
            return label
    return None


@dataclass(frozen=True)
class _Actual:
    incident_id: uuid.UUID
    location_id: uuid.UUID
    threat_type: str
    window: str | None


def _actuals(session: Session, target_date: date, threat_types: tuple[str, ...]) -> list[_Actual]:
    """Kejadian nyata hari sasaran, jenis yang dinilai, beserta jendelanya (bila jam ada)."""
    rows = session.execute(
        select(
            CrimeIncident.incident_id,
            CrimeIncident.location_id,
            CrimeIncident.incident_type,
            CrimeIncident.incident_time,
            CrimeIncident.time_known,
        ).where(
            CrimeIncident.incident_date == target_date,
            CrimeIncident.incident_type.in_(threat_types),
        )
    ).all()
    actuals: list[_Actual] = []
    for incident_id, location_id, threat, incident_time, time_known in rows:
        window = (
            _window_of(incident_time.hour) if time_known and incident_time is not None else None
        )
        actuals.append(_Actual(incident_id, location_id, str(threat), window))
    return actuals


def _next_evaluation_number(session: Session) -> int:
    latest = session.scalar(
        select(PredictionActual.code)
        .where(PredictionActual.code.regexp_match("^EVA-[0-9]+$"))
        .order_by(func.length(PredictionActual.code).desc(), PredictionActual.code.desc())
    )
    if latest is None:
        return 1
    return int(latest.rsplit("-", 1)[-1]) + 1


def _dominant_factors(cell: risk.CellAssessment, support: int) -> list[dict[str, Any]]:
    """WHY untuk prediksi evaluasi: faktor x bobot yang benar-benar menyusun skornya."""
    entries: list[dict[str, Any]] = [
        {
            "factor": factor.name,
            "value": factor.value,
            "weight": factor.weight,
            "contribution": round(factor.contribution, 2),
            "source": "RULE",
            "reason": factor.reason,
            "basis": risk.FACTOR_BASIS.get(factor.name),
        }
        for factor in cell.factors
        if factor.weight is not None
    ]
    entries.sort(key=lambda item: float(item["contribution"]), reverse=True)
    entries.append(
        {
            "factor": engine.CONFIDENCE_FACTOR,
            "value": support,
            "weight": None,
            "contribution": 0.0,
            "source": "RULE",
            "reason": None,
            "basis": engine.CONFIDENCE_BASIS,
        }
    )
    return entries


# ---------------------------------------------------------------------------
# Evaluasi
# ---------------------------------------------------------------------------


def run_backtest(
    session: Session,
    start: date,
    end: date,
    *,
    horizon: str = "24H",
    write: bool = True,
    user_id: uuid.UUID | None = None,
) -> BacktestSummary:
    """Mengevaluasi setiap hari pada [start, end]. Pemanggil yang menutup transaksi."""
    if end < start:
        message = f"rentang terbalik: {start.isoformat()} > {end.isoformat()}"
        raise BacktestError(message)
    offset = timedelta(days=engine.horizon_day_offset(horizon))
    if offset == timedelta(0):
        message = (
            f"horizon {horizon} menunjuk hari yang sama dengan tanggal prediksi; evaluasi "
            "mundur harian memerlukan jarak minimal satu hari (24H, 3D, 7D)"
        )
        raise BacktestError(message)

    # Evaluasi mundur membandingkan prediksi dengan kejadian pada periode uji, jadi ia
    # harus melihat kejadian di luar batas tampilan layar (services/visibility.py).
    visibility.see_everything(session)

    catalogue = risk.load_weights()
    thresholds = risk.load_thresholds()
    profile = catalogue.active.profiles.get(risk.PROFILE_HISTORICAL)
    if profile is None:
        message = (
            f"versi bobot aktif '{catalogue.active_version}' tidak memiliki profil "
            f"'{risk.PROFILE_HISTORICAL}'"
        )
        raise BacktestError(message)

    summary = BacktestSummary(
        start=start,
        end=end,
        horizon=horizon,
        weights_version=catalogue.active_version,
        threshold_version=thresholds.version,
        minimum_score=thresholds.minimum_warning_score,
        threat_types=profile.applies_to,
        written=write,
    )
    prediction_number = engine.next_code_number(session) if write else 0
    evaluation_number = _next_evaluation_number(session) if write else 0

    target = start
    while target <= end:
        as_of = target - offset
        day = DayResult(target, as_of, 0, 0, 0, 0, 0)
        summary.days.append(day)

        already = session.scalar(
            select(func.count())
            .select_from(Prediction)
            .where(
                Prediction.prediction_date == as_of,
                Prediction.forecast_horizon == horizon,
                Prediction.status == engine.STATUS_VALIDATED,
            )
        )
        if already:
            day.skipped_reason = (
                f"{already} prediksi VALIDATED sudah ada untuk {as_of.isoformat()}/{horizon}; "
                "evaluasi tidak diulang supaya tidak menghitung dua kali"
            )
            target += timedelta(days=1)
            continue

        evidence = risk.collect_evidence(session, as_of=as_of)
        assessment = risk.assess_historical(
            evidence, profile, thresholds, target, catalogue.active_version
        )
        support = engine.collect_support(session, as_of=as_of)
        busiest: dict[tuple[str, str], int] = defaultdict(int)
        for (_location, threat, window), count in support.items():
            busiest[(threat, window)] = max(busiest[(threat, window)], count)

        predicted: dict[tuple[uuid.UUID, str, str], risk.CellAssessment] = {
            (cell.location_id, cell.threat_type, cell.time_window): cell
            for cell in assessment.scored
            if cell.risk_score is not None and cell.risk_score >= thresholds.minimum_warning_score
        }
        actuals = _actuals(session, target, profile.applies_to)
        by_unit: dict[tuple[uuid.UUID, str, str], list[_Actual]] = defaultdict(list)
        for actual in actuals:
            if actual.window is None:
                day.unevaluable += 1
                continue
            by_unit[(actual.location_id, actual.threat_type, actual.window)].append(actual)

        day.predictions = len(predicted)
        for unit, cell in predicted.items():
            matches = by_unit.get(unit, [])
            if matches:
                day.hits += 1
            else:
                day.false_positives += 1
            if not write:
                continue

            count = support.get(unit, 0)
            confidence, _reason = engine.confidence_of(
                count, busiest.get((unit[1], unit[2]), 0), unit[1], unit[2]
            )
            prediction = Prediction(
                code=f"PRD-{prediction_number:05d}",
                prediction_date=as_of,
                forecast_horizon=horizon,
                threat_type=cell.threat_type,
                location_id=cell.location_id,
                time_window=cell.time_window,
                window_start=cell.window_start,
                window_end=cell.window_end,
                risk_score=cell.risk_score,
                confidence=confidence,
                dominant_factors=_dominant_factors(cell, count),
                model_version=engine.RULE_VERSION,
                baseline_risk_score_id=None,
                status=engine.STATUS_VALIDATED,
            )
            prediction_number += 1
            session.add(prediction)
            session.flush()

            first = matches[0] if matches else None
            session.add(
                PredictionActual(
                    code=f"EVA-{evaluation_number:05d}",
                    evaluation_date=target,
                    prediction_id=prediction.prediction_id,
                    actual_incident_id=None if first is None else first.incident_id,
                    actual_event=first is not None,
                    actual_threat_type=cell.threat_type,
                    actual_location_id=cell.location_id,
                    actual_window_start=cell.window_start,
                    actual_window_end=cell.window_end,
                    match_type=MATCH_HIT if first is not None else MATCH_FALSE_POSITIVE,
                    notes=(
                        f"{len(matches)} kejadian pada sel+jenis+jendela ini"
                        if matches
                        else "tidak ada kejadian pada sel+jenis+jendela ini"
                    ),
                )
            )
            evaluation_number += 1

        for unit, matches in by_unit.items():
            if unit in predicted:
                continue
            day.false_negatives += len(matches)
            if not write:
                continue
            for actual in matches:
                start_at, end_at = risk._window_bounds(target, unit[2])
                session.add(
                    PredictionActual(
                        code=f"EVA-{evaluation_number:05d}",
                        evaluation_date=target,
                        prediction_id=None,
                        actual_incident_id=actual.incident_id,
                        actual_event=True,
                        actual_threat_type=actual.threat_type,
                        actual_location_id=actual.location_id,
                        actual_window_start=start_at,
                        actual_window_end=end_at,
                        match_type=MATCH_FALSE_NEGATIVE,
                        notes=(
                            f"tidak ada prediksi berskor >= {thresholds.minimum_warning_score} "
                            f"pada sel+jenis+jendela ini (as_of {as_of.isoformat()})"
                        ),
                    )
                )
                evaluation_number += 1

        if write:
            session.flush()
        target += timedelta(days=1)

    audit.record(
        session,
        action=AUDIT_ACTION,
        resource_type=AUDIT_RESOURCE,
        resource_id=f"{start.isoformat()}..{end.isoformat()}/{horizon}",
        result=audit.RESULT_SUCCESS,
        user_id=user_id,
        detail={
            key: value
            for key, value in summary.as_dict().items()
            if key not in ("matching_basis", "evidence_basis")
        },
    )
    return summary


def reference_today() -> date:
    """Tanggal "sekarang" menurut jam acuan aplikasi — batas atas rentang evaluasi."""
    return clock.reference_now().date()
