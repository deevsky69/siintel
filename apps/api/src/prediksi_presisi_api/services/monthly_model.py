"""Model prediksi bulanan — gradient boosting per kelurahan (Modul 3, naskah Taskap Bab IV).

APA YANG DIPELAJARI

    Satu baris = satu kelurahan pada satu bulan sasaran. Masukannya hanya hal yang sudah
    diketahui SEBELUM bulan sasaran dimulai:

        riwayat 1, 3, 6, 12 bulan   rata-rata kejadian bulanan kelurahan itu
        tren                        rata-rata 3 bulan terakhir dikurangi bulan-bulan sebelumnya
        pola bulanan                bulan kalender sasaran (sin/cos)
        pola sekecamatan            rata-rata bulanan 1, 3, 12 bulan kelurahan LAIN di
                                    kecamatan itu

    Riwayat dinyatakan sebagai rata-rata bulanan supaya jendela yang belum sepanjang 12 bulan
    (bulan-bulan awal sejak `data_from`) tetap sebanding; baris latih dimulai setelah
    tersedia `min_history_months` bulan riwayat.

    Keluarannya perkiraan jumlah kejadian pada bulan sasaran.

BATAS INFORMASI

    Tanggal kejadian menentukan bulannya; tanggal LAPORAN menentukan kapan kejadian itu
    boleh dipakai. Baris latih untuk bulan T hanya memuat riwayat yang sudah dilaporkan
    sebelum T, dan labelnya dihitung dari yang sudah dilaporkan sampai `train_until`.
    Model yang sudah dilatih tidak pernah melihat kejadian setelah `train_until`.

DIBEKUKAN

    Parameter dan jendela latih ditetapkan di config/ranking/monthly.yaml. Pelatihan
    deterministik (`random_state` tetap), jadi data latih yang sama selalu menghasilkan
    model yang sama; sidik data latih ikut tercatat di `model_version` supaya perubahan data
    latih terlihat. Skor bulanan berikutnya hanya memperbarui RIWAYAT, bukan parameter.

ALASAN (CLAUDE.md §27)

    Kontribusi tiap masukan dihitung dari pohon model itu sendiri: pada setiap percabangan
    yang dilewati sebuah baris, selisih nilai simpul anak dan induk dicatat atas nama masukan
    yang dipakai bercabang. Jumlah seluruh kontribusi + nilai awal = perkiraan model, persis.

Modul ini murni hitungan — tidak menyentuh database — supaya dapat diuji dan dipakai skrip
uji historis dengan data yang sama.
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
    "lag_1",
    "lag_3",
    "lag_6",
    "lag_12",
    "trend",
    "month_sin",
    "month_cos",
    "kec_1",
    "kec_3",
    "kec_12",
)

FEATURE_LABELS: dict[str, str] = {
    "lag_1": "Kejadian bulan lalu",
    "lag_3": "Rata-rata 3 bulan terakhir",
    "lag_6": "Rata-rata 6 bulan terakhir",
    "lag_12": "Rata-rata 12 bulan terakhir",
    "trend": "Tren (3 bulan terakhir dibanding bulan-bulan sebelumnya)",
    "month_sin": "Pola bulanan",
    "month_cos": "Pola bulanan",
    "kec_1": "Kelurahan lain sekecamatan, bulan lalu",
    "kec_3": "Kelurahan lain sekecamatan, 3 bulan terakhir",
    "kec_12": "Kelurahan lain sekecamatan, 12 bulan terakhir",
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
    min_history_months: int = 3
    n_estimators: int = 300
    learning_rate: float = 0.03
    max_depth: int = 2
    min_samples_leaf: int = 20
    subsample: float = 1.0
    random_state: int = 20250101
    min_training_rows: int = 300

    @classmethod
    def from_config(cls, raw: Mapping[str, Any]) -> ModelParams:
        return cls(
            version=str(raw["version"]),
            train_until=date.fromisoformat(str(raw["train_until"])),
            data_from=date.fromisoformat(str(raw.get("data_from", "2023-01-01"))),
            min_history_months=int(raw.get("min_history_months", 3)),
            n_estimators=int(raw.get("n_estimators", 300)),
            learning_rate=float(raw.get("learning_rate", 0.03)),
            max_depth=int(raw.get("max_depth", 2)),
            min_samples_leaf=int(raw.get("min_samples_leaf", 20)),
            subsample=float(raw.get("subsample", 1.0)),
            random_state=int(raw.get("random_state", 20250101)),
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
        bila data belum sepanjang itu."""
        available = HISTORY_MONTHS
        if self.first_month is not None:
            available = max(0, min(HISTORY_MONTHS, target - self.first_month))
        return [self.count(kelurahan, target - back, cutoff) for back in range(available, 0, -1)]

    def features(self, kelurahan: str, target: int, cutoff: date) -> list[float]:
        own = self.series(kelurahan, target, cutoff)
        others = [0] * len(own)
        for sibling in self._siblings[self.areas[kelurahan]]:
            if sibling == kelurahan:
                continue
            for position, value in enumerate(self.series(sibling, target, cutoff)):
                others[position] += value
        angle = 2 * math.pi * (target % 12) / 12
        earlier = own[:-3]
        return [
            _mean(own, 1),
            _mean(own, 3),
            _mean(own, 6),
            _mean(own, 12),
            _mean(own, 3) - (sum(earlier) / len(earlier) if earlier else _mean(own, 3)),
            math.sin(angle),
            math.cos(angle),
            _mean(others, 1),
            _mean(others, 3),
            _mean(others, 12),
        ]


def _mean(values: list[int], window: int) -> float:
    """Rata-rata `window` nilai terakhir, atau seluruhnya bila lebih pendek."""
    tail = values[-window:]
    return sum(tail) / len(tail) if tail else 0.0


def default_cutoff(target: int) -> date:
    """Hari terakhir sebelum bulan sasaran."""
    return month_from_index(target) - timedelta(days=1)


def training_rows(
    history: IncidentHistory, params: ModelParams
) -> tuple[list[list[float]], list[float], list[int]]:
    """Baris latih: setiap kelurahan × setiap bulan sasaran yang sudah punya sekurangnya
    `min_history_months` bulan riwayat dan berakhir paling lambat pada `train_until`."""
    if history.first_month is None:
        raise ModelUnavailable("Belum ada kejadian untuk melatih model.")
    first_target = history.first_month + params.min_history_months
    last_target = month_index(params.train_until)
    if params.train_until != default_cutoff(last_target + 1):
        last_target -= 1  # bulan terakhir belum utuh pada batas latih
    names = sorted(history.areas)
    rows: list[list[float]] = []
    labels: list[float] = []
    targets: list[int] = []
    for target in range(first_target, last_target + 1):
        cutoff = default_cutoff(target)
        for kelurahan in names:
            rows.append(history.features(kelurahan, target, cutoff))
            labels.append(float(history.count(kelurahan, target, params.train_until)))
            targets.append(target)
    if len(rows) < params.min_training_rows:
        raise ModelUnavailable(
            f"Data latih belum cukup: {len(rows)} baris sampai {params.train_until.isoformat()}, "
            f"perlu sekurangnya {params.min_training_rows}."
        )
    return rows, labels, targets


def _fingerprint(rows: list[list[float]], labels: list[float], params: ModelParams) -> str:
    digest = hashlib.sha256()
    digest.update(repr(params).encode())
    for row, label in zip(rows, labels, strict=True):
        digest.update(repr((row, label)).encode())
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
        return f"gbr-{self.params.version}#{self.fingerprint}"

    def predict(self, rows: list[list[float]]) -> list[float]:
        return [max(0.0, float(value)) for value in self._estimator.predict(rows)]

    def contributions(self, row: list[float]) -> tuple[float, dict[str, float]]:
        """(nilai awal, kontribusi per masukan); jumlah keduanya = perkiraan model."""
        estimator = self._estimator
        base = float(estimator.init_.predict([row])[0])
        totals: dict[str, float] = dict.fromkeys(FEATURES, 0.0)
        for stage in estimator.estimators_:
            tree = stage[0].tree_
            node = 0
            while tree.children_left[node] != -1:
                feature = int(tree.feature[node])
                child = (
                    tree.children_left[node]
                    if row[feature] <= tree.threshold[node]
                    else tree.children_right[node]
                )
                totals[FEATURES[feature]] += estimator.learning_rate * float(
                    tree.value[child][0][0] - tree.value[node][0][0]
                )
                node = int(child)
        return base, totals

    def describe(self) -> dict[str, Any]:
        return {
            "model_version": self.version,
            "algorithm": "Gradient boosting (scikit-learn GradientBoostingRegressor)",
            "train_until": self.params.train_until.isoformat(),
            "training_targets": f"{self.first_target.isoformat()[:7]} s.d. "
            f"{self.last_target.isoformat()[:7]}",
            "training_rows": self.training_rows,
            "training_incidents": self.training_incidents,
            "parameters": {
                "n_estimators": self.params.n_estimators,
                "learning_rate": self.params.learning_rate,
                "max_depth": self.params.max_depth,
                "min_samples_leaf": self.params.min_samples_leaf,
                "subsample": self.params.subsample,
                "random_state": self.params.random_state,
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
    rows, labels, targets = training_rows(history, params)
    fingerprint = _fingerprint(rows, labels, params)
    cached = _CACHE.get(fingerprint)
    if cached is not None:
        return cached
    from sklearn.ensemble import GradientBoostingRegressor

    estimator = GradientBoostingRegressor(
        loss="squared_error",
        n_estimators=params.n_estimators,
        learning_rate=params.learning_rate,
        max_depth=params.max_depth,
        min_samples_leaf=params.min_samples_leaf,
        subsample=params.subsample,
        random_state=params.random_state,
    )
    estimator.fit(rows, labels)
    model = TrainedModel(
        params=params,
        fingerprint=fingerprint,
        training_rows=len(rows),
        training_incidents=round(sum(labels)),
        first_target=month_from_index(targets[0]),
        last_target=month_from_index(targets[-1]),
        importances={
            name: float(value)
            for name, value in zip(FEATURES, estimator.feature_importances_, strict=True)
        },
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
    explain: bool = True,
) -> list[Prediction]:
    """Perkiraan seluruh kelurahan untuk bulan sasaran, dari riwayat sampai `cutoff`.
    `explain=False` melewatkan hitungan kontribusi (uji historis banyak bulan)."""
    if target <= month_index(model.params.train_until):
        raise ModelUnavailable(
            "Bulan sasaran berada di dalam masa latih model "
            f"(sampai {model.params.train_until.isoformat()}); perkiraannya bukan uji yang jujur."
        )
    limit = default_cutoff(target)
    cutoff = min(cutoff, limit) if cutoff else limit
    names = sorted(history.areas)
    rows = [history.features(name, target, cutoff) for name in names]
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
