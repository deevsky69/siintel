"""Model prediksi bulanan — gradient boosting per kelurahan (naskah Taskap Lampiran 8 E).

Sejak 19 November 2026 mengikuti "Protokol Replikasi Prediksi" pada naskah final:

    Baris pembelajaran   kelurahan × bulan sasaran × horizon (jarak bulan antara akhir riwayat
                         dan bulan sasaran, 1–12). Bulan sasaran sejak riwayat mencapai enam
                         bulan sampai akhir masa latih. Bobot baris = 1 / jumlah horizon yang
                         tersedia untuk bulan sasaran itu.
    Sasaran              jumlah kejadian terlapor pada kelurahan dan bulan sasaran, menurut
                         data yang tersedia sampai `train_until`.
    Masukan              rerata kejadian 1, 3, 6, 12 bulan terakhir yang tersedia; rerata
                         sepanjang riwayat; selisih rerata 3 dan 12 bulan; rerata kelurahan
                         lain sekecamatan pada 3 dan 12 bulan; horizon; sinus dan kosinus
                         bulan sasaran.
    Pengaturan           HistGradientBoostingRegressor, kerugian Poisson, 100 iterasi, 7 daun,
                         minimum 40 sampel per daun, laju belajar 0,05, L2 = 2, seed 42, tanpa
                         penghentian dini. scikit-learn dikunci pada 1.8.0 (versi naskah).

BATAS INFORMASI

    Tanggal kejadian menentukan bulannya; tanggal LAPORAN menentukan kapan kejadian itu
    boleh dipakai. Riwayat hanya memuat kejadian yang sudah dilaporkan sebelum bulan setelah
    akhir riwayat. Model tidak pernah melihat kejadian setelah `train_until`.

DIBEKUKAN

    Parameter dan masa latih ada di config/ranking/monthly.yaml. Pelatihan deterministik;
    sidik data latih ikut tercatat di `model_version`. Skor bulanan berikutnya hanya
    memperbarui RIWAYAT (horizon 1), bukan parameter.

ALASAN (CLAUDE.md §27)

    Kerugian Poisson bekerja pada skala logaritma: perkiraan = exp(nilai awal + jumlah nilai
    daun). Kontribusi tiap masukan dihitung dari pohon model itu sendiri — pada setiap
    percabangan yang dilewati, selisih nilai simpul anak dan induk dicatat atas nama masukan
    yang dipakai bercabang. Jumlahnya, dipangkatkan, tepat sama dengan perkiraan model;
    karena itu kontribusi dibaca sebagai PENGALI (mis. +35%), bukan tambahan jumlah.

Modul ini murni hitungan — tidak menyentuh database.
"""

from __future__ import annotations

import hashlib
import math
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

FEATURES: tuple[str, ...] = (
    "mean_1",
    "mean_3",
    "mean_6",
    "mean_12",
    "mean_all",
    "diff_3_12",
    "kec_3",
    "kec_12",
    "horizon",
    "month_sin",
    "month_cos",
)

FEATURE_LABELS: dict[str, str] = {
    "mean_1": "Kejadian bulan terakhir",
    "mean_3": "Rerata 3 bulan terakhir",
    "mean_6": "Rerata 6 bulan terakhir",
    "mean_12": "Rerata 12 bulan terakhir",
    "mean_all": "Rerata sepanjang riwayat",
    "diff_3_12": "Selisih rerata 3 dan 12 bulan",
    "kec_3": "Kelurahan lain sekecamatan, 3 bulan",
    "kec_12": "Kelurahan lain sekecamatan, 12 bulan",
    "horizon": "Jarak ke bulan sasaran",
    "month_sin": "Pola bulanan",
    "month_cos": "Pola bulanan",
}

HISTORY_MONTHS = 12


class ModelUnavailable(ValueError):
    """Model tidak dapat dilatih dari data yang ada (riwayat belum cukup)."""


def month_index(day: date) -> int:
    return day.year * 12 + day.month - 1


def month_from_index(index: int) -> date:
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


@dataclass(frozen=True)
class ModelParams:
    version: str
    train_until: date
    data_from: date = date(2023, 1, 1)
    min_history_months: int = 6
    max_horizon: int = 12
    max_iter: int = 100
    max_leaf_nodes: int = 7
    min_samples_leaf: int = 40
    learning_rate: float = 0.05
    l2_regularization: float = 2.0
    random_state: int = 42
    min_training_rows: int = 300

    @classmethod
    def from_config(cls, raw: Mapping[str, Any]) -> ModelParams:
        return cls(
            version=str(raw["version"]),
            train_until=date.fromisoformat(str(raw["train_until"])),
            data_from=date.fromisoformat(str(raw.get("data_from", "2023-01-01"))),
            min_history_months=int(raw.get("min_history_months", 6)),
            max_horizon=int(raw.get("max_horizon", 12)),
            max_iter=int(raw.get("max_iter", 100)),
            max_leaf_nodes=int(raw.get("max_leaf_nodes", 7)),
            min_samples_leaf=int(raw.get("min_samples_leaf", 40)),
            learning_rate=float(raw.get("learning_rate", 0.05)),
            l2_regularization=float(raw.get("l2_regularization", 2.0)),
            random_state=int(raw.get("random_state", 42)),
            min_training_rows=int(raw.get("min_training_rows", 300)),
        )


class IncidentHistory:
    """Kejadian per kelurahan dan bulan, dengan tanggal mulai diketahuinya.

    `incidents` berisi (kelurahan, tanggal kejadian, tanggal diketahui). `areas` memetakan
    SELURUH kelurahan ke kecamatannya — kelurahan tanpa kejadian tetap ikut diperingkat.
    `data_from` adalah awal data yang utuh: kejadian sebelum itu (baris tercecer) diabaikan
    dan jendela riwayat tidak pernah menjangkau lebih awal darinya.
    """

    def __init__(
        self,
        incidents: Iterable[tuple[str, date, date]],
        areas: Mapping[str, str],
        data_from: date | None = None,
    ) -> None:
        self.areas: dict[str, str] = dict(areas)
        floor = month_index(data_from) if data_from else None
        #: Tanggal kejadian termuda — menentukan bulan terakhir yang sudah utuh.
        self.last_date: date | None = None
        self._known: dict[str, dict[int, list[date]]] = defaultdict(lambda: defaultdict(list))
        first: int | None = None
        for kelurahan, occurred, known in incidents:
            if kelurahan not in self.areas:
                continue
            index = month_index(occurred)
            if floor is not None and index < floor:
                continue
            self._known[kelurahan][index].append(known)
            first = index if first is None or index < first else first
            if self.last_date is None or occurred > self.last_date:
                self.last_date = occurred
        for months in self._known.values():
            for dates in months.values():
                dates.sort()
        #: Bulan pertama data: `data_from`, atau bulan kejadian tertua bila lebih muda.
        self.first_month: int | None = (
            first if floor is None or first is None else max(first, floor)
        )
        self._siblings: dict[str, list[str]] = defaultdict(list)
        for kelurahan, kecamatan in self.areas.items():
            self._siblings[kecamatan].append(kelurahan)

    def count(self, kelurahan: str, month: int, cutoff: date) -> int:
        """Kejadian kelurahan pada bulan itu yang sudah diketahui sampai `cutoff`."""
        dates = self._known.get(kelurahan, {}).get(month)
        return bisect_right(dates, cutoff) if dates else 0

    def series(self, kelurahan: str, target: int, cutoff: date) -> list[int]:
        """Sampai dua belas bulan sebelum bulan sasaran, terlama lebih dulu — lebih pendek
        bila data belum sepanjang itu. Dipakai IKW dan dasar peringkat."""
        available = HISTORY_MONTHS
        if self.first_month is not None:
            available = max(0, min(HISTORY_MONTHS, target - self.first_month))
        return [self.count(kelurahan, target - back, cutoff) for back in range(available, 0, -1)]

    def _full(self, kelurahan: str, last: int, cutoff: date) -> list[int]:
        """Seluruh riwayat dari awal data sampai bulan `last`, terlama lebih dulu."""
        first = self.first_month if self.first_month is not None else last + 1
        return [self.count(kelurahan, month, cutoff) for month in range(first, last + 1)]

    def features(
        self, kelurahan: str, target: int, cutoff: date | None = None, horizon: int = 1
    ) -> list[float]:
        """Masukan model untuk satu kelurahan: riwayat berakhir `horizon` bulan sebelum bulan
        sasaran, hanya dari kejadian yang sudah diketahui sampai `cutoff` (bawaan: hari
        terakhir bulan riwayat)."""
        last = target - horizon
        known = cutoff or default_cutoff(last + 1)
        own = self._full(kelurahan, last, known)
        siblings = [name for name in self._siblings[self.areas[kelurahan]] if name != kelurahan]
        others = [0.0] * len(own)
        for sibling in siblings:
            for position, value in enumerate(self._full(sibling, last, known)):
                others[position] += value
        if siblings:
            others = [value / len(siblings) for value in others]
        # Januari = 0: sudut 2π·(bulan−1)/12, seperti pada replikasi naskah.
        angle = 2 * math.pi * (target % 12) / 12
        return [
            _mean(own, 1),
            _mean(own, 3),
            _mean(own, 6),
            _mean(own, 12),
            _mean(own, len(own)),
            _mean(own, 3) - _mean(own, 12),
            _mean(others, 3),
            _mean(others, 12),
            float(horizon),
            math.sin(angle),
            math.cos(angle),
        ]


def _mean(values: list[Any], window: int) -> float:
    """Rata-rata `window` nilai terakhir, atau seluruhnya bila lebih pendek."""
    tail = values[-window:] if window > 0 else []
    return float(sum(tail)) / len(tail) if tail else 0.0


def default_cutoff(target: int) -> date:
    """Hari terakhir sebelum bulan sasaran."""
    return month_from_index(target) - timedelta(days=1)


def training_rows(
    history: IncidentHistory, params: ModelParams
) -> tuple[list[list[float]], list[float], list[float], list[int]]:
    """(masukan, sasaran, bobot, bulan sasaran) — setiap kelurahan × bulan sasaran × horizon
    yang riwayatnya sudah `min_history_months` bulan dan berakhir paling lambat pada
    `train_until`."""
    if history.first_month is None:
        raise ModelUnavailable("Belum ada kejadian untuk melatih model.")
    first = history.first_month
    last_target = month_index(params.train_until)
    if params.train_until != default_cutoff(last_target + 1):
        last_target -= 1  # bulan terakhir belum utuh pada batas latih
    names = sorted(history.areas)
    rows: list[list[float]] = []
    labels: list[float] = []
    weights: list[float] = []
    targets: list[int] = []
    for target in range(first + params.min_history_months, last_target + 1):
        horizons = [
            h
            for h in range(1, params.max_horizon + 1)
            if target - h - first + 1 >= params.min_history_months
        ]
        for horizon in horizons:
            for kelurahan in names:
                rows.append(history.features(kelurahan, target, None, horizon))
                labels.append(float(history.count(kelurahan, target, params.train_until)))
                weights.append(1 / len(horizons))
                targets.append(target)
    if len(rows) < params.min_training_rows:
        raise ModelUnavailable(
            f"Data latih belum cukup: {len(rows)} baris sampai {params.train_until.isoformat()}, "
            f"perlu sekurangnya {params.min_training_rows}."
        )
    if sum(labels) <= 0:
        raise ModelUnavailable("Data latih tidak memuat satu pun kejadian.")
    return rows, labels, weights, targets


def _fingerprint(
    rows: list[list[float]], labels: list[float], weights: list[float], params: ModelParams
) -> str:
    digest = hashlib.sha256()
    digest.update(repr(params).encode())
    for row, label, weight in zip(rows, labels, weights, strict=True):
        digest.update(repr((row, label, weight)).encode())
    return digest.hexdigest()[:10]


@dataclass
class TrainedModel:
    params: ModelParams
    fingerprint: str
    training_rows: int
    training_incidents: int
    first_target: date
    last_target: date
    importances: dict[str, float]
    _estimator: Any

    @property
    def version(self) -> str:
        return f"hgb-{self.params.version}#{self.fingerprint}"

    def predict(self, rows: list[list[float]]) -> list[float]:
        return [max(0.0, float(value)) for value in self._estimator.predict(rows)]

    def contributions(self, row: list[float]) -> tuple[float, dict[str, float]]:
        """(nilai awal, kontribusi per masukan) pada skala LOGARITMA: exp(nilai awal + jumlah
        kontribusi) = perkiraan model. Dibaca dari simpul pohon model yang sudah dilatih."""
        estimator = self._estimator
        base = float(estimator._baseline_prediction.ravel()[0])
        totals: dict[str, float] = dict.fromkeys(FEATURES, 0.0)
        for stage in estimator._predictors:
            nodes = stage[0].nodes
            index = 0
            while not nodes[index]["is_leaf"]:
                node = nodes[index]
                feature = int(node["feature_idx"])
                child = int(
                    node["left"] if row[feature] <= node["num_threshold"] else node["right"]
                )
                totals[FEATURES[feature]] += float(nodes[child]["value"] - node["value"])
                index = child
        # Nilai akar tiap pohon ikut membentuk perkiraan; dicatat pada nilai awal.
        base += sum(float(stage[0].nodes[0]["value"]) for stage in estimator._predictors)
        return base, totals

    def describe(self) -> dict[str, Any]:
        return {
            "model_version": self.version,
            "algorithm": "Gradient boosting (scikit-learn HistGradientBoostingRegressor, Poisson)",
            "train_until": self.params.train_until.isoformat(),
            "training_targets": f"{self.first_target.isoformat()[:7]} s.d. "
            f"{self.last_target.isoformat()[:7]}",
            "training_rows": self.training_rows,
            "training_incidents": self.training_incidents,
            "parameters": {
                "max_iter": self.params.max_iter,
                "max_leaf_nodes": self.params.max_leaf_nodes,
                "min_samples_leaf": self.params.min_samples_leaf,
                "learning_rate": self.params.learning_rate,
                "l2_regularization": self.params.l2_regularization,
                "random_state": self.params.random_state,
                "max_horizon": self.params.max_horizon,
                "min_history_months": self.params.min_history_months,
            },
            "features": [
                {
                    "name": name,
                    "label": FEATURE_LABELS[name],
                    "importance": round(self.importances[name], 4),
                }
                for name in FEATURES
            ],
        }


_CACHE: dict[str, TrainedModel] = {}


def train(history: IncidentHistory, params: ModelParams) -> TrainedModel:
    """Melatih (atau mengambil dari tembolok) model untuk riwayat dan parameter ini."""
    rows, labels, weights, targets = training_rows(history, params)
    fingerprint = _fingerprint(rows, labels, weights, params)
    cached = _CACHE.get(fingerprint)
    if cached is not None:
        return cached
    from sklearn.ensemble import HistGradientBoostingRegressor

    estimator = HistGradientBoostingRegressor(
        loss="poisson",
        max_iter=params.max_iter,
        max_leaf_nodes=params.max_leaf_nodes,
        min_samples_leaf=params.min_samples_leaf,
        learning_rate=params.learning_rate,
        l2_regularization=params.l2_regularization,
        random_state=params.random_state,
        early_stopping=False,
    )
    estimator.fit(rows, labels, sample_weight=weights)
    # Bobot masukan: seberapa sering tiap masukan dipakai bercabang, dari pohon model.
    used: dict[str, float] = dict.fromkeys(FEATURES, 0.0)
    for stage in estimator._predictors:
        for node in stage[0].nodes:
            if not node["is_leaf"]:
                used[FEATURES[int(node["feature_idx"])]] += 1.0
    total = sum(used.values()) or 1.0
    first = history.first_month or 0
    months = sorted(set(targets))
    model = TrainedModel(
        params=params,
        fingerprint=fingerprint,
        training_rows=len(rows),
        training_incidents=sum(
            history.count(name, month, params.train_until)
            for name in history.areas
            for month in range(first, months[-1] + 1)
        ),
        first_target=month_from_index(months[0]),
        last_target=month_from_index(months[-1]),
        importances={name: value / total for name, value in used.items()},
        _estimator=estimator,
    )
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[fingerprint] = model
    return model


@dataclass(frozen=True)
class Prediction:
    kelurahan: str
    predicted: float
    features: dict[str, float]
    base: float
    contributions: dict[str, float]


def predict_month(
    history: IncidentHistory,
    model: TrainedModel,
    target: int,
    cutoff: date | None = None,
    *,
    horizon: int = 1,
    explain: bool = True,
) -> list[Prediction]:
    """Perkiraan seluruh kelurahan untuk bulan sasaran. `horizon` 1 = bulan berikutnya
    (pemakaian rutin); lebih besar = riwayat berhenti lebih awal (skenario tetap).
    `explain=False` melewatkan hitungan kontribusi (uji historis banyak bulan)."""
    if target - horizon + 1 <= month_index(model.params.train_until) and horizon == 1:
        raise ModelUnavailable(
            "Bulan sasaran berada di dalam masa latih model "
            f"(sampai {model.params.train_until.isoformat()}); perkiraannya bukan uji yang jujur."
        )
    if not 1 <= horizon <= model.params.max_horizon:
        raise ModelUnavailable(f"Horizon {horizon} di luar yang dilatih.")
    limit = default_cutoff(target - horizon + 1)
    known = min(cutoff, limit) if cutoff else limit
    names = sorted(history.areas)
    rows = [history.features(name, target, known, horizon) for name in names]
    values = model.predict(rows)
    results: list[Prediction] = []
    for name, row, value in zip(names, rows, values, strict=True):
        base, contributions = model.contributions(row) if explain else (0.0, {})
        results.append(
            Prediction(
                kelurahan=name,
                predicted=value,
                features=dict(zip(FEATURES, row, strict=True)),
                base=base,
                contributions=contributions,
            )
        )
    return results
