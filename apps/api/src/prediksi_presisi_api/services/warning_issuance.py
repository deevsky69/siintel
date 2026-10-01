"""Penerbitan peringatan dini dan rekomendasi dari prediksi yang DIPUBLIKASIKAN.

Sampai 1 Oktober 2026 kedua tabel ini hanya pernah diisi seeder dataset sintetis: tidak ada
satu baris kode runtime pun yang menerbitkan `early_warnings` atau `recommendations`. Begitu
data asli menggantikan data sintetis, rantai CLAUDE.md §9 putus tepat di tengah —

```text
PREDICTION  ->  EARLY WARNING  ->  RECOMMENDATION  ->  COMMANDER DECISION
```

— dan modul ini menyambungnya kembali. Ia dipanggil dari publikasi prediksi, bukan dari
penjalanan prediksi: hanya prediksi `PUBLISHED` yang boleh melahirkan peringatan
(`prediction_center.PUBLICATION_BASIS`).

TIGA ATURAN YANG MENENTUKAN BENTUKNYA

1. **Ambang terbit dan severity dibaca dari `config/risk/warning-thresholds.yaml`**, versi
   aktif, lewat `risk_engine.Thresholds.severity_for`. Tidak ada angka di sini
   (CLAUDE.md §12). Setiap peringatan menyimpan `threshold_version` supaya alasan
   terbitnya dapat ditelusuri meski ambangnya kelak berganti.
2. **Fungsi yang diusulkan dibaca dari `config/recommendation/function-rules.yaml`**,
   berstatus PROPOSED. Siapa yang bertindak atas sebuah peringatan adalah keputusan
   organisasi, bukan keputusan modul ini; yang dilakukan di sini hanya menerapkan aturan
   yang tertulis dan menyebut statusnya pada setiap respons.
3. **Satu prediksi melahirkan paling banyak satu peringatan dan satu rekomendasi.**
   Publikasi ulang ditolak di tingkat prediksi (409), dan modul ini tetap memeriksa
   peringatan yang sudah ada — dua lapis, karena peringatan ganda pada sel dan jendela yang
   sama membuat Warning Center menghitung dua kali satu keadaan.

Rekomendasi adalah USULAN. Kalimat penutupnya menyatakan itu dan tidak pernah bervariasi
(CLAUDE.md §13).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import EarlyWarning, Location, Prediction, Recommendation
from ..seeding.paths import REPO_ROOT
from . import clock
from . import risk_engine as risk

FUNCTION_RULES_FILE = REPO_ROOT / "config" / "recommendation" / "function-rules.yaml"

#: Status awal. Peringatan hidup sampai diterima/ditutup (`warning_actions`); rekomendasi
#: menunggu keputusan komandan (`decisions`).
WARNING_STATUS_INITIAL = "ACTIVE"
RECOMMENDATION_STATUS_INITIAL = "PENDING_REVIEW"

#: Kalimat penutup setiap rekomendasi — sengaja sama untuk semua baris (CLAUDE.md §13).
RECOMMENDATION_CLOSING = "Usulan, bukan perintah — keputusan tetap pada pejabat berwenang."

ISSUANCE_BASIS = (
    "Peringatan dini terbit dari prediksi PUBLISHED yang skornya mencapai "
    "early_warning.default.minimum_score pada config/risk/warning-thresholds.yaml versi "
    "aktif; severity mengikuti tangga pada versi yang sama dan tersimpan sebagai "
    "threshold_version. Satu prediksi melahirkan paling banyak satu peringatan dan satu "
    "rekomendasi. Fungsi yang diusulkan mengikuti config/recommendation/function-rules.yaml."
)

#: Nama faktor mesin penilaian dalam bahasa yang dibaca pejabat.
FACTOR_PHRASES: dict[str, str] = {
    "historical_factor": "kepadatan kejadian historis",
    "recent_trend_factor": "tren kejadian terkini",
    "temporal_factor": "pola jendela waktu",
    "spatial_factor": "konsentrasi spasial",
    "context_factor": "faktor kontekstual",
    "intelligence_factor": "laporan intelijen",
    "community_factor": "laporan masyarakat",
}


class IssuanceError(Exception):
    """Konfigurasi aturan fungsi tidak ada atau tidak lengkap."""


@dataclass(frozen=True)
class FunctionRule:
    function: str
    action: str


@dataclass(frozen=True)
class FunctionRules:
    status: str
    default_function: str
    rules: dict[str, FunctionRule]
    priority_by_severity: dict[str, str]

    def for_threat(self, threat_type: str) -> FunctionRule:
        rule = self.rules.get(threat_type.upper())
        if rule is not None:
            return rule
        return FunctionRule(function=self.default_function, action="Tingkatkan kegiatan preventif")

    def priority_for(self, severity: str) -> str | None:
        return self.priority_by_severity.get(severity.upper())


def load_function_rules() -> FunctionRules:
    """Membaca aturan fungsi dari config. Statusnya ikut dibawa supaya tampil di respons."""
    if not FUNCTION_RULES_FILE.exists():
        message = "config/recommendation/function-rules.yaml tidak ditemukan"
        raise IssuanceError(message)

    raw: dict[str, Any] = yaml.safe_load(FUNCTION_RULES_FILE.read_text(encoding="utf-8"))
    rules = {
        str(threat).upper(): FunctionRule(
            function=str(body["function"]).upper(), action=str(body["action"])
        )
        for threat, body in dict(raw.get("rules") or {}).items()
    }
    default_function = str(raw.get("default_function", "")).upper()
    if not default_function:
        message = "config/recommendation/function-rules.yaml tidak menyebut default_function"
        raise IssuanceError(message)

    return FunctionRules(
        status=str(raw.get("status", "UNKNOWN")),
        default_function=default_function,
        rules=rules,
        priority_by_severity={
            str(severity).upper(): str(priority).upper()
            for severity, priority in dict(raw.get("priority_by_severity") or {}).items()
        },
    )


# ---------------------------------------------------------------------------
# Penomoran
# ---------------------------------------------------------------------------


def _next_number(session: Session, model: type[EarlyWarning | Recommendation], prefix: str) -> int:
    """Nomor berikutnya menurut NILAI angkanya, bukan urutan teksnya.

    `WRN-10000` lebih kecil dari `WRN-9999` bila diurutkan sebagai teks; dengan 96
    peringatan sehari pada data asli, batas empat digit terlampaui dalam empat bulan.
    """
    latest = session.scalar(
        select(model.code)
        .where(model.code.regexp_match(f"^{prefix}-[0-9]+$"))
        .order_by(func.length(model.code).desc(), model.code.desc())
    )
    if latest is None:
        return 1
    return int(latest.rsplit("-", 1)[-1]) + 1


class _Numbering:
    """Penomoran untuk satu penerbitan — dibaca sekali, lalu bertambah di memori."""

    def __init__(self, session: Session) -> None:
        self.warning = _next_number(session, EarlyWarning, "WRN")
        self.recommendation = _next_number(session, Recommendation, "REC")

    def next_warning_code(self) -> str:
        code = f"WRN-{self.warning:04d}"
        self.warning += 1
        return code

    def next_recommendation_code(self) -> str:
        code = f"REC-{self.recommendation:04d}"
        self.recommendation += 1
        return code


# ---------------------------------------------------------------------------
# Kalimat rekomendasi
# ---------------------------------------------------------------------------


def dominant_factor_phrase(dominant_factors: list[dict[str, Any]]) -> str:
    """Faktor berkontribusi terbesar, siap dibaca; kosong bila tidak ada yang dapat dibaca.

    Mengarang faktor pengganti akan menjadi penjelasan fiktif (CLAUDE.md §27) — justru pada
    kalimat yang dibaca sebagai saran tindakan.
    """
    weighted = [
        row
        for row in dominant_factors
        if isinstance(row, dict) and row.get("weight") is not None and row.get("value") is not None
    ]
    if not weighted:
        return ""
    top = max(weighted, key=lambda row: float(row.get("contribution") or 0))
    name = str(top.get("factor", ""))
    return FACTOR_PHRASES.get(name, name.replace("_", " "))


def recommendation_text(prediction: Prediction, location: Location, action: str) -> str:
    """Usulan tindakan yang menyebut prediksi asalnya: WHAT, WHERE, WHEN, RISK, CONFIDENCE, WHY.

    Keenam unsur diambil dari baris prediksi yang dirujuk (CLAUDE.md §10), bukan kalimat
    tetap — satu kalimat yang sama untuk semua membuat layar rekomendasi terbaca sebagai
    maket, dan kolom `recommended_function` kehilangan artinya.
    """
    kelurahan = (location.kelurahan or "").strip()
    kecamatan = (location.kecamatan or "").strip()
    # Beberapa kelurahan bernama sama dengan kecamatannya (Jagakarsa, Pancoran, Tebet…),
    # dan "di Jagakarsa, Jagakarsa" terbaca seperti kalimat yang dirakit mesin yang rusak.
    tempat = (
        f"{kelurahan}, {kecamatan}"
        if kelurahan and kelurahan != kecamatan
        else (kelurahan or kecamatan)
    )
    factor = dominant_factor_phrase(prediction.dominant_factors)
    why = f", faktor terkuat {factor}" if factor else ""
    window = prediction.time_window or (
        f"{prediction.window_start.astimezone(clock.JAKARTA):%H:%M}-"
        f"{prediction.window_end.astimezone(clock.JAKARTA):%H:%M}"
    )

    return (
        f"{action} di {tempat} pada {window} WIB terhadap {prediction.threat_type}. "
        f"Dasar: prediksi {prediction.code} berskor {prediction.risk_score}/100 "
        f"dengan keyakinan {prediction.confidence}%{why}. "
        f"{RECOMMENDATION_CLOSING}"
    )


# ---------------------------------------------------------------------------
# Penerbitan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Issued:
    """Hasil untuk satu prediksi: apa yang terbit, atau mengapa tidak."""

    prediction_code: str
    warning_code: str | None
    recommendation_code: str | None
    severity: str | None
    reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "prediction": self.prediction_code,
            "warning": self.warning_code,
            "recommendation": self.recommendation_code,
            "severity": self.severity,
            "reason": self.reason,
        }


@dataclass
class IssuanceSummary:
    threshold_version: str
    threshold_status: str
    minimum_score: int
    function_rules_status: str
    issued: list[Issued]

    @property
    def warnings_issued(self) -> int:
        return sum(1 for item in self.issued if item.warning_code is not None)

    @property
    def below_threshold(self) -> int:
        return sum(
            1
            for item in self.issued
            if item.warning_code is None and item.reason is not None and "ambang" in item.reason
        )

    def as_dict(self, sample: int = 10) -> dict[str, Any]:
        return {
            "warnings_issued": self.warnings_issued,
            "recommendations_issued": self.warnings_issued,
            "below_threshold": self.below_threshold,
            "already_warned": len(self.issued) - self.warnings_issued - self.below_threshold,
            "threshold_version": self.threshold_version,
            "threshold_status": self.threshold_status,
            "minimum_score": self.minimum_score,
            "function_rules_status": self.function_rules_status,
            "sample": [item.as_dict() for item in self.issued[:sample]],
            "issuance_basis": ISSUANCE_BASIS,
        }


def _existing_warning(session: Session, prediction: Prediction) -> EarlyWarning | None:
    return session.scalar(
        select(EarlyWarning).where(EarlyWarning.prediction_id == prediction.prediction_id)
    )


def issue_for_predictions(
    session: Session,
    predictions: list[Prediction],
    *,
    thresholds: risk.Thresholds | None = None,
    rules: FunctionRules | None = None,
    write: bool = True,
) -> IssuanceSummary:
    """Menerbitkan peringatan + rekomendasi untuk prediksi yang mencapai ambang.

    `write=False` menghitung apa yang AKAN terbit tanpa menambah satu baris pun — dipakai
    `dry_run` publikasi massal. Pemanggil yang menutup transaksi.
    """
    thresholds = thresholds or risk.load_thresholds()
    rules = rules or load_function_rules()
    numbering = _Numbering(session) if write else None
    issued: list[Issued] = []

    for prediction in predictions:
        severity = thresholds.severity_for(prediction.risk_score)
        if severity is None:
            issued.append(
                Issued(
                    prediction_code=prediction.code,
                    warning_code=None,
                    recommendation_code=None,
                    severity=None,
                    reason=(
                        f"skor {prediction.risk_score} di bawah ambang terbit "
                        f"{thresholds.minimum_warning_score} (versi {thresholds.version})"
                    ),
                )
            )
            continue

        existing = _existing_warning(session, prediction)
        if existing is not None:
            issued.append(
                Issued(
                    prediction_code=prediction.code,
                    warning_code=None,
                    recommendation_code=None,
                    severity=existing.severity,
                    reason=f"prediksi sudah memiliki peringatan {existing.code}",
                )
            )
            continue

        rule = rules.for_threat(prediction.threat_type)
        if numbering is None:
            issued.append(
                Issued(
                    prediction_code=prediction.code,
                    warning_code="(akan terbit)",
                    recommendation_code="(akan terbit)",
                    severity=severity,
                    reason=None,
                )
            )
            continue

        warning = EarlyWarning(
            code=numbering.next_warning_code(),
            prediction_id=prediction.prediction_id,
            severity=severity,
            threat_type=prediction.threat_type,
            location_id=prediction.location_id,
            time_window=prediction.time_window,
            window_start=prediction.window_start,
            window_end=prediction.window_end,
            risk_score=prediction.risk_score,
            confidence=prediction.confidence,
            status=WARNING_STATUS_INITIAL,
            threshold_version=thresholds.version,
        )
        session.add(warning)
        session.flush()

        recommendation = Recommendation(
            code=numbering.next_recommendation_code(),
            prediction_id=prediction.prediction_id,
            warning_id=warning.warning_id,
            recommended_function=rule.function,
            recommendation_text=recommendation_text(prediction, prediction.location, rule.action),
            priority=rules.priority_for(severity),
            status=RECOMMENDATION_STATUS_INITIAL,
        )
        session.add(recommendation)
        session.flush()

        issued.append(
            Issued(
                prediction_code=prediction.code,
                warning_code=warning.code,
                recommendation_code=recommendation.code,
                severity=severity,
                reason=None,
            )
        )

    return IssuanceSummary(
        threshold_version=thresholds.version,
        threshold_status=thresholds.status,
        minimum_score=thresholds.minimum_warning_score,
        function_rules_status=rules.status,
        issued=issued,
    )
