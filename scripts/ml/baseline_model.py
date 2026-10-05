"""Model terlatih pertama: regresi logistik per (kelurahan x jenis x jendela 6 jam x hari).

Dijalankan OFFLINE (grup dependensi `analysis`: pandas, numpy). Yang dihasilkan bukan
aplikasi, melainkan dua hal yang menentukan apakah model layak masuk aplikasi:

1. Angka pembanding yang jujur terhadap baseline aturan (`services/backtest.py`):
   pada JUMLAH PERINGATAN PER HARI YANG SAMA, berapa precision dan recall model.
2. Artefak model (`config/model/<nama>.json`): koefisien, definisi fitur, rujukan data
   latih, dan hasil evaluasi — supaya skoring di aplikasi dapat dilakukan dengan aritmetika
   biasa tanpa pustaka numerik (CLAUDE.md §25: model_version, training_data_reference,
   feature_definition, evaluation_result).

KEJUJURAN WAKTU
    Setiap fitur untuk hari sasaran H dihitung hanya dari kejadian yang DILAPORKAN sampai
    H-1 (`reported_at`), bukan yang terjadi: p90 jarak lapor 3,4 hari. Jendela "N hari
    terakhir" karena itu jendela tanggal lapor — "apa yang diketahui dalam N hari terakhir".

Pakai:
    cd apps/api && uv run --group analysis python ../../scripts/ml/baseline_model.py \
        --train-from 2024-01-01 --train-to 2025-12-31 --test-from 2026-01-03 --test-to 2026-09-28
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
WINDOWS = {"00:00-06:00": 0, "06:00-12:00": 6, "12:00-18:00": 12, "18:00-23:59": 18}
WINDOW_HOURS = 6
THREATS = ("CURANMOR", "CURAT", "CURAS")
LOOKBACKS = (7, 30, 90, 365)

FEATURES = [
    # per unit (sel x jenis x jendela): kejadian yang dilaporkan dalam N hari terakhir
    "unit_7",
    "unit_30",
    "unit_90",
    "unit_365",
    # per sel x jenis (semua jendela)
    "cell_threat_30",
    "cell_threat_365",
    # per sel (semua jenis)
    "cell_365",
    # pola jendela jenis ini di seluruh wilayah (setahun)
    "threat_window_365",
    # kecamatan x jenis, 30 hari
    "kec_threat_30",
    # hari dalam pekan hari sasaran (Senin=0) sebagai satu nilai siklus (sin/cos)
    "dow_sin",
    "dow_cos",
]


def load(engine_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(engine_url)
    incidents = pd.read_sql(
        text(
            """
            select i.incident_date, i.reported_at, i.incident_time, i.time_known,
                   i.incident_type as threat, l.location_id, l.kecamatan, l.kelurahan,
                   l.grid_id
            from crime_incidents i join locations l using (location_id)
            where i.incident_type in ('CURANMOR','CURAT','CURAS')
            """
        ),
        engine,
    )
    cells = pd.read_sql(
        text("select location_id, grid_id, kecamatan, kelurahan from locations order by grid_id"),
        engine,
    )
    incidents["incident_date"] = pd.to_datetime(incidents["incident_date"]).dt.date
    reported = pd.to_datetime(incidents["reported_at"], utc=True).dt.tz_convert("Asia/Jakarta")
    incidents["reported_date"] = reported.dt.date
    # Tanpa reported_at (seharusnya tidak ada pada data asli): anggap dilaporkan hari itu.
    incidents["reported_date"] = incidents["reported_date"].fillna(incidents["incident_date"])
    hours = pd.to_datetime(incidents["incident_time"].astype(str), format="%H:%M:%S", errors="coerce").dt.hour
    incidents["window"] = np.where(
        incidents["time_known"], (hours // WINDOW_HOURS * WINDOW_HOURS).fillna(-1).astype(int), -1
    )
    return incidents, cells


def daily_matrix(frame: pd.DataFrame, key_cols: list[str], date_col: str, days: pd.DatetimeIndex) -> tuple[pd.DataFrame, np.ndarray]:
    """Matriks (kunci x hari) berisi cacah per hari, untuk jumlah bergulir yang cepat."""
    grouped = frame.groupby(key_cols + [date_col]).size().rename("n").reset_index()
    grouped[date_col] = pd.to_datetime(grouped[date_col])
    keys = grouped[key_cols].drop_duplicates().reset_index(drop=True)
    key_index = {tuple(row): i for i, row in enumerate(keys.itertuples(index=False, name=None))}
    day_index = {d: i for i, d in enumerate(days)}
    matrix = np.zeros((len(keys), len(days)), dtype=np.int32)
    for row in grouped.itertuples(index=False):
        k = key_index[tuple(getattr(row, c) for c in key_cols)]
        d = day_index.get(getattr(row, date_col))
        if d is not None:
            matrix[k, d] = row.n
    return keys, matrix


def rolling_sum(matrix: np.ndarray, lookback: int) -> np.ndarray:
    """Jumlah pada [t-lookback+1, t] untuk tiap t (inklusif hari t)."""
    cumulative = np.cumsum(matrix, axis=1)
    shifted = np.zeros_like(cumulative)
    shifted[:, lookback:] = cumulative[:, :-lookback]
    return cumulative - shifted


def build(
    incidents: pd.DataFrame, cells: pd.DataFrame, start: date, end: date, horizon: int = 1, step: int = 1
) -> pd.DataFrame:
    """Satu baris per (sel, jenis, jendela, hari sasaran) pada [start, end]."""
    first = min(incidents["reported_date"].min(), incidents["incident_date"].min())
    days = pd.date_range(pd.Timestamp(first) - pd.Timedelta(days=1), pd.Timestamp(end), freq="D")
    day_pos = {d.date(): i for i, d in enumerate(days)}

    known = incidents.copy()
    known["window"] = known["window"].astype(int)
    with_window = known[known["window"] >= 0]

    # Matriks menurut TANGGAL LAPOR (apa yang diketahui) untuk fitur.
    unit_keys, unit_m = daily_matrix(with_window, ["location_id", "threat", "window"], "reported_date", days)
    ct_keys, ct_m = daily_matrix(known, ["location_id", "threat"], "reported_date", days)
    c_keys, c_m = daily_matrix(known, ["location_id"], "reported_date", days)
    tw_keys, tw_m = daily_matrix(with_window, ["threat", "window"], "reported_date", days)
    kt_keys, kt_m = daily_matrix(known, ["kecamatan", "threat"], "reported_date", days)
    # Matriks menurut TANGGAL KEJADIAN untuk label.
    label_keys, label_m = daily_matrix(with_window, ["location_id", "threat", "window"], "incident_date", days)
    if horizon > 1:
        # Label horizon: jumlah pada [t, t+horizon-1] — jumlah bergulir ke depan.
        forward = np.zeros_like(label_m)
        cum = np.cumsum(label_m, axis=1)
        for t in range(label_m.shape[1]):
            hi = min(t + horizon - 1, label_m.shape[1] - 1)
            forward[:, t] = cum[:, hi] - (cum[:, t - 1] if t > 0 else 0)
        label_m = forward

    roll = {
        "unit": {n: rolling_sum(unit_m, n) for n in LOOKBACKS},
        "ct": {n: rolling_sum(ct_m, n) for n in (30, 365)},
        "c": {365: rolling_sum(c_m, 365)},
        "tw": {365: rolling_sum(tw_m, 365)},
        "kt": {30: rolling_sum(kt_m, 30)},
    }
    unit_idx = {tuple(r): i for i, r in enumerate(unit_keys.itertuples(index=False, name=None))}
    ct_idx = {tuple(r): i for i, r in enumerate(ct_keys.itertuples(index=False, name=None))}
    c_idx = {tuple(r): i for i, r in enumerate(c_keys.itertuples(index=False, name=None))}
    tw_idx = {tuple(r): i for i, r in enumerate(tw_keys.itertuples(index=False, name=None))}
    kt_idx = {tuple(r): i for i, r in enumerate(kt_keys.itertuples(index=False, name=None))}
    label_idx = {tuple(r): i for i, r in enumerate(label_keys.itertuples(index=False, name=None))}

    rows = []
    target = start
    while target <= end:
        as_of = target - timedelta(days=1)
        t = day_pos[as_of]
        tt = day_pos[target]
        dow = target.weekday()
        for cell in cells.itertuples(index=False):
            for threat in THREATS:
                for window in WINDOWS.values():
                    u = unit_idx.get((cell.location_id, threat, window))
                    ct = ct_idx.get((cell.location_id, threat))
                    c = c_idx.get((cell.location_id,))
                    tw = tw_idx.get((threat, window))
                    kt = kt_idx.get((cell.kecamatan, threat))
                    lab = label_idx.get((cell.location_id, threat, window))
                    rows.append(
                        (
                            target,
                            cell.grid_id,
                            cell.kecamatan,
                            cell.kelurahan,
                            threat,
                            window,
                            *(roll["unit"][n][u, t] if u is not None else 0 for n in LOOKBACKS),
                            roll["ct"][30][ct, t] if ct is not None else 0,
                            roll["ct"][365][ct, t] if ct is not None else 0,
                            roll["c"][365][c, t] if c is not None else 0,
                            roll["tw"][365][tw, t] if tw is not None else 0,
                            roll["kt"][30][kt, t] if kt is not None else 0,
                            np.sin(2 * np.pi * dow / 7),
                            np.cos(2 * np.pi * dow / 7),
                            int(label_m[lab, tt] > 0) if lab is not None else 0,
                        )
                    )
        target += timedelta(days=step)
    columns = ["target_date", "grid_id", "kecamatan", "kelurahan", "threat", "window", *FEATURES, "y"]
    return pd.DataFrame(rows, columns=columns)


def transform(frame: pd.DataFrame, stats: dict | None = None) -> tuple[np.ndarray, dict]:
    x = frame[FEATURES].to_numpy(dtype=float)
    count_cols = [i for i, f in enumerate(FEATURES) if not f.startswith("dow_")]
    x[:, count_cols] = np.log1p(x[:, count_cols])
    if stats is None:
        stats = {"mean": x.mean(axis=0).tolist(), "std": (x.std(axis=0) + 1e-9).tolist()}
    x = (x - np.array(stats["mean"])) / np.array(stats["std"])
    return x, stats


def train_logistic(x: np.ndarray, y: np.ndarray, l2: float = 1e-3, epochs: int = 300, lr: float = 0.5) -> tuple[np.ndarray, float]:
    """Regresi logistik dengan bobot kelas seimbang, gradien penuh (dataset ratusan ribu baris)."""
    n, k = x.shape
    w = np.zeros(k)
    b = 0.0
    pos = y.sum()
    weight_pos = (n - pos) / max(pos, 1)
    sample_w = np.where(y == 1, weight_pos, 1.0)
    sample_w = sample_w / sample_w.mean()
    for _ in range(epochs):
        z = x @ w + b
        p = 1 / (1 + np.exp(-z))
        g = (p - y) * sample_w
        w -= lr * (x.T @ g / n + l2 * w)
        b -= lr * g.mean()
    return w, b


def predict(x: np.ndarray, w: np.ndarray, b: float) -> np.ndarray:
    return 1 / (1 + np.exp(-(x @ w + b)))


def evaluate(frame: pd.DataFrame, score: np.ndarray, per_day: float) -> dict:
    """Precision/recall bila tiap hari sasaran diterbitkan sebanyak `per_day` peringatan teratas."""
    frame = frame.assign(score=score)
    k = int(round(per_day))
    hits = fps = fns = 0
    for _, day in frame.groupby("target_date"):
        top = day.nlargest(k, "score")
        h = int(top["y"].sum())
        hits += h
        fps += k - h
        fns += int(day["y"].sum()) - h
    return {
        "warnings_per_day": k,
        "hits": hits,
        "false_positives": fps,
        "false_negatives": fns,
        "precision": round(hits / (hits + fps), 4) if hits + fps else None,
        "recall": round(hits / (hits + fns), 4) if hits + fns else None,
    }


def auc(y: np.ndarray, s: np.ndarray) -> float:
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    pos = y == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-from", type=date.fromisoformat, required=True)
    parser.add_argument("--train-to", type=date.fromisoformat, required=True)
    parser.add_argument("--test-from", type=date.fromisoformat, required=True)
    parser.add_argument("--test-to", type=date.fromisoformat, required=True)
    parser.add_argument("--per-day", type=float, nargs="+", default=[77, 40, 20, 10])
    parser.add_argument("--name", default="logistik-v1")
    parser.add_argument("--horizon-days", type=int, default=1, help="label: ada kejadian dalam N hari ke depan")
    parser.add_argument("--step-days", type=int, default=1, help="jarak antar hari sasaran")
    parser.add_argument("--write", action="store_true", help="tulis artefak ke config/model/")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL belum diisi", file=sys.stderr)
        return 1
    incidents, cells = load(url)
    print(f"kejadian {len(incidents)}, sel {len(cells)}")

    train = build(incidents, cells, args.train_from, args.train_to, args.horizon_days, args.step_days)
    test = build(incidents, cells, args.test_from, args.test_to, args.horizon_days, args.step_days)
    print(f"latih {len(train)} baris ({int(train.y.sum())} positif) · uji {len(test)} baris ({int(test.y.sum())} positif)")

    x_train, stats = transform(train)
    x_test, _ = transform(test, stats)
    w, b = train_logistic(x_train, train["y"].to_numpy(dtype=float))
    s_test = predict(x_test, w, b)
    s_train = predict(x_train, w, b)

    report = {
        "auc_train": round(auc(train["y"].to_numpy(), s_train), 4),
        "auc_test": round(auc(test["y"].to_numpy(), s_test), 4),
        "at_warnings_per_day": [evaluate(test, s_test, k) for k in args.per_day],
        # Pembanding yang jujur: baseline "persistensi" = urutkan menurut kejadian unit 365 hari.
        "baseline_unit_365_at_warnings_per_day": [
            evaluate(test, test["unit_365"].to_numpy(dtype=float) + 1e-6 * test["unit_30"].to_numpy(dtype=float), k)
            for k in args.per_day
        ],
    }
    print(json.dumps(report, indent=2))
    print("koefisien (fitur terstandar):")
    for name, coef in sorted(zip(FEATURES, w, strict=True), key=lambda p: -abs(p[1])):
        print(f"  {name:>18} {coef:+.3f}")

    if args.write:
        artifact = {
            "model_version": args.name,
            "kind": "logistic_regression",
            "unit": "kelurahan x jenis x jendela 6 jam x hari sasaran",
            "label": "ada >=1 kejadian berjam tercatat pada unit itu di hari sasaran",
            "training_data_reference": {
                "source": "crime_incidents (Pusiknas, posisi 2026-09-29)",
                "train_target_days": [args.train_from.isoformat(), args.train_to.isoformat()],
                "test_target_days": [args.test_from.isoformat(), args.test_to.isoformat()],
                "rows_train": int(len(train)),
                "positives_train": int(train.y.sum()),
                "evidence_rule": "fitur dihitung dari kejadian yang DILAPORKAN sampai H-1 (reported_at)",
            },
            "feature_definition": {
                "names": FEATURES,
                "transform": "log1p pada fitur cacah, lalu standardisasi (mean/std dari data latih)",
                "mean": stats["mean"],
                "std": stats["std"],
            },
            "coefficients": dict(zip(FEATURES, [float(v) for v in w], strict=True)),
            "intercept": float(b),
            "evaluation_result": report,
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "status": "PROPOSED",
        }
        out = REPO / "config" / "model" / f"{args.name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
        print(f"artefak: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
