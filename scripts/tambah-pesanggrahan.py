#!/usr/bin/env python3
"""Melengkapi dataset peragaan dengan Kecamatan Pesanggrahan.

MENGAPA INI ADA

    Jakarta Selatan memiliki **sepuluh** kecamatan. Dataset peragaan hanya memuat sembilan;
    Pesanggrahan beserta kelima kelurahannya tidak ada sama sekali. Cacat itu baru terlihat
    ketika batas wilayah sungguhan dipasang pada peta (`scripts/bangun-batas-wilayah.py`)
    dan sebuah kecamatan tergambar kosong tanpa alasan.

    Keputusan melengkapinya diambil pemilik proyek pada 8 September 2026. Ia keputusan
    tentang ISI dataset peragaan, bukan keputusan teknis (CLAUDE.md §17).

MENGAPA SKRIP DAN BUKAN BARIS YANG DITEMPEL

    Data yang ditambahkan menyentuh dua belas berkas yang saling menunjuk: kejadian, skor
    risiko, prediksi, peringatan, rekomendasi, keputusan, tindakan, evaluasi, laporan warga,
    umpan balik, patroli, dan intelijen. Menempelkannya dengan tangan berarti dua belas
    kesempatan memutus keterkaitan tanpa ada yang menyadarinya.

    Skrip ini juga menjadi jawaban atas pertanyaan "dari mana angka Pesanggrahan berasal" —
    pertanyaan yang pantas diajukan siapa pun yang memeriksa dataset peragaan.

BAGAIMANA ANGKANYA DITENTUKAN

    Tidak dikarang. Setiap sebaran — jenis kejadian, modus, sasaran, jam, status, kelas
    risiko — **dipelajari dari sembilan kecamatan yang sudah ada**, lalu ditiru. Volumenya
    mengikuti laju per sel grid: 1.200 kejadian pada 33 sel berarti ±36 kejadian per sel,
    dan Pesanggrahan mendapat empat sel.

    Koordinat sel diambil dari **batas kelurahan sungguhan** (OpenStreetMap, lewat
    `data/batas-osm/`), bukan dikira-kira. Titiknya dijamin berada di dalam kelurahannya —
    kalau tidak, peta akan menggambar kejadian Pesanggrahan di wilayah tetangga.

INVARIAN YANG DIJAGA

    - `risk_score = round(Σ(bobot × faktor))` memakai bobot `dummy-v1` yang berlaku.
    - `risk_class` mengikuti ambang `dummy-v1`, tidak dihitung ulang di tempat lain.
    - Peringatan dini hanya terbit pada skor ≥ 70, dengan tingkat menurut ambang yang sama.
    - Setiap prediksi menunjuk baris `risk_scores` pendamping yang benar-benar ada.
    - Seluruh `grid_id` menunjuk `locations`, seluruh kunci asing menunjuk barisnya.

    Skrip menolak berjalan bila Pesanggrahan sudah ada, sehingga menjalankannya dua kali
    tidak menggandakan apa pun.

Jalankan:  python3 scripts/tambah-pesanggrahan.py
"""

from __future__ import annotations

import csv
import gzip
import json
import random
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "sample"
BOUNDARIES = ROOT / "data" / "batas-osm" / "kelurahan.json.gz"
WEIGHTS_FILE = ROOT / "config" / "risk" / "risk-weights.yaml"
THRESHOLDS_FILE = ROOT / "config" / "risk" / "warning-thresholds.yaml"

KECAMATAN = "Pesanggrahan"
POLSEK = "Polsek Pesanggrahan"

#: Empat sel grid untuk empat kelurahan.
#:
#: Bukan kelima-limanya, dan itu mengikuti pola yang sudah ada: Kebayoran Baru memiliki
#: sepuluh kelurahan dan hanya lima sel, Tebet tujuh kelurahan dan empat sel. Grid peragaan
#: memang tidak menutupi setiap kelurahan, dan berpura-pura sebaliknya di satu kecamatan
#: saja akan membuat Pesanggrahan tampak lebih terpantau daripada tetangganya.
CELLS = [
    ("Ulujami", "Permukiman"),
    ("Petukangan Utara", "Pertokoan"),
    ("Pesanggrahan", "Jalan"),
    ("Bintaro", "Pusat Aktivitas"),
]

#: Seed tetap. Menjalankan ulang skrip ini pada dataset yang sama menghasilkan baris yang
#: sama persis — syarat agar datanya dapat diperiksa, bukan sekadar dipercaya.
SEED = 20260908

TZ = "+07:00"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def header(name: str) -> list[str]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        fields = csv.DictReader(handle).fieldnames
    if fields is None:
        raise SystemExit(f"{name}: berkas kosong, tidak ada baris judul")
    return list(fields)


def append(name: str, rows: list[dict[str, Any]]) -> None:
    """Menambahkan baris ke akhir berkas, dengan urutan kolom yang persis sama."""
    if not rows:
        return
    fields = header(name)
    unknown = set(rows[0]) - set(fields)
    if unknown:
        raise SystemExit(f"{name}: kolom tak dikenal {sorted(unknown)}")
    with (DATA / name).open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})
    print(f"  {name:<26} +{len(rows)}", file=sys.stderr)


def next_code(existing: list[str], prefix: str, width: int) -> Callable[[], str]:
    """Penerbit kode berurutan, melanjutkan dari yang tertinggi yang sudah ada."""
    highest = max((int(code.rsplit("-", 1)[1]) for code in existing if code), default=0)
    counter = {"value": highest}

    def issue() -> str:
        counter["value"] += 1
        return f"{prefix}-{counter['value']:0{width}d}"

    return issue


# ---------------------------------------------------------------------------------------
# Geometri: titik yang dijamin berada di dalam kelurahannya
# ---------------------------------------------------------------------------------------


def _rings(relation: dict[str, Any]) -> list[list[tuple[float, float]]]:
    segments = [
        [(point["lon"], point["lat"]) for point in member["geometry"]]
        for member in relation.get("members", [])
        if member["type"] == "way"
        and member.get("role") in ("outer", "")
        and member.get("geometry")
    ]
    rings: list[list[tuple[float, float]]] = []
    while segments:
        chain = segments.pop(0)
        joined = True
        while joined and chain[0] != chain[-1]:
            joined = False
            for index, candidate in enumerate(segments):
                if candidate[0] == chain[-1]:
                    chain = chain + candidate[1:]
                elif candidate[-1] == chain[-1]:
                    chain = chain + candidate[::-1][1:]
                elif candidate[-1] == chain[0]:
                    chain = candidate[:-1] + chain
                elif candidate[0] == chain[0]:
                    chain = candidate[::-1][:-1] + chain
                else:
                    continue
                segments.pop(index)
                joined = True
                break
        if len(chain) >= 4:
            rings.append(chain)
    return rings


def _inside(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = point
    result = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def _interior(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """Satu titik yang PASTI di dalam poligon.

    Titik pusat massa tidak cukup: pada poligon cekung ia dapat jatuh di luar poligonnya
    sendiri. Cara ini menarik garis mendatar melalui tengah poligon lalu mengambil tengah
    potongan terpanjang yang berada di dalamnya.
    """
    cx = cy = signed = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = x1 * y2 - x2 * y1
        signed += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    centre = (
        (cx / (3 * signed), cy / (3 * signed))
        if abs(signed) > 1e-15
        else (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    )
    if _inside(centre, ring):
        return centre

    y = (min(p[1] for p in ring) + max(p[1] for p in ring)) / 2
    crossings = sorted(
        ring[i][0]
        + (ring[i + 1][0] - ring[i][0]) * (y - ring[i][1]) / (ring[i + 1][1] - ring[i][1])
        for i in range(len(ring) - 1)
        if (ring[i][1] > y) != (ring[i + 1][1] > y)
    )
    if len(crossings) < 2:
        return centre
    _, index = max((crossings[i + 1] - crossings[i], i) for i in range(0, len(crossings) - 1, 2))
    return ((crossings[index] + crossings[index + 1]) / 2, y)


def kelurahan_points() -> dict[str, tuple[float, float]]:
    """Titik (lintang, bujur) di dalam tiap kelurahan Pesanggrahan, dari batas OSM."""
    with gzip.open(BOUNDARIES, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    wanted = {name for name, _ in CELLS}
    points: dict[str, tuple[float, float]] = {}
    for element in payload["elements"]:
        name = element["tags"].get("name")
        if name not in wanted:
            continue
        rings = _rings(element)
        if not rings:
            continue
        rings.sort(
            key=lambda ring: abs(
                sum(
                    ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
                    for i in range(len(ring) - 1)
                )
            ),
            reverse=True,
        )
        longitude, latitude = _interior(rings[0])
        points[name] = (round(latitude, 3), round(longitude, 3))

    missing = wanted - set(points)
    if missing:
        raise SystemExit(f"batas kelurahan tidak ditemukan: {sorted(missing)}")
    return points


# ---------------------------------------------------------------------------------------
# Aturan penilaian, dibaca dari config — bukan disalin ke sini
# ---------------------------------------------------------------------------------------


def risk_rules() -> tuple[dict[str, float], list[dict[str, Any]], dict[str, Any]]:
    weights_raw = yaml.safe_load(WEIGHTS_FILE.read_text(encoding="utf-8"))
    version = str(weights_raw["active_version"])
    weights = weights_raw["versions"][version]["profiles"]["historical"]["weights"]

    thresholds_raw = yaml.safe_load(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    active = thresholds_raw["versions"][str(thresholds_raw["active_version"])]
    return dict(weights), active["risk_classes"], active["early_warning"]["default"]


def score_from(factors: dict[str, int], weights: dict[str, float]) -> int:
    """`risk_score = round(Σ(bobot × faktor))` — satu-satunya tempat rumus ini ditulis."""
    return round(sum(weights[name] * value for name, value in factors.items()))


def factors_for(target: int, weights: dict[str, float], rng: random.Random) -> dict[str, int]:
    """Lima faktor yang jumlah berbobotnya **tepat** `target`.

    Arahnya sengaja begini — skor ditentukan lebih dulu, faktor menyesuaikan — dan itu
    tampak terbalik sampai alasannya disebut: sebaran skor yang harus ditiru adalah sebaran
    skor NYATA pada sembilan kecamatan yang sudah ada. Membangkitkan lima faktor acak lalu
    menjumlahkannya menghasilkan sebaran yang jauh lebih sempit — rata-rata lima peubah acak
    selalu lebih memusat daripada peubah tunggalnya. Percobaan pertama menghasilkan hanya
    dua peringatan dini dari dua puluh dua prediksi, karena hampir tidak ada skor yang
    mencapai ambang 70.

    Yang dijaga tetap sama: `round(Σ(bobot × faktor)) == risk_score` benar secara
    konstruksi, bukan diperiksa belakangan.
    """
    names = list(weights)
    for _ in range(200):
        raw = {name: rng.randint(max(0, target - 22), min(100, target + 22)) for name in names}
        adjust = rng.choice(names)
        others = sum(weights[name] * raw[name] for name in names if name != adjust)
        needed = round((target - others) / weights[adjust])
        if 0 <= needed <= 100:
            raw[adjust] = needed
            if score_from(raw, weights) == target:
                return raw
    raise SystemExit(f"tidak dapat menyusun faktor untuk skor {target}")


def class_of(score: int, classes: list[dict[str, Any]]) -> str:
    for band in classes:
        if band["min"] <= score <= band["max"]:
            # Berkas CSV memakai huruf kapital di awal (`Moderate`), config memakai kapital
            # seluruhnya (`MODERATE`). Yang diikuti adalah bentuk pada data yang sudah ada.
            return str(band["class"]).title()
    raise SystemExit(f"skor {score} tidak masuk kelas mana pun")


# ---------------------------------------------------------------------------------------
# Sebaran yang dipelajari dari sembilan kecamatan yang sudah ada
# ---------------------------------------------------------------------------------------


def learn(rows: list[dict[str, str]], column: str) -> list[str]:
    """Nilai kolom apa adanya, sebagai kantong untuk diambil acak.

    Dikembalikan sebagai daftar penuh, bukan daftar nilai unik: yang ingin ditiru adalah
    **seberapa sering** tiap nilai muncul, bukan sekadar nilai apa saja yang mungkin.
    """
    return [row[column] for row in rows if row[column]]


def main() -> None:
    locations = read("locations.csv")
    if any(row["kecamatan"] == KECAMATAN for row in locations):
        raise SystemExit(
            f"{KECAMATAN} sudah ada pada data contoh — tidak ada yang perlu ditambahkan."
        )

    # `random` biasa, bukan `secrets`: yang dibangkitkan adalah data peragaan yang justru
    # HARUS dapat diulang persis. Keacakan kriptografis tidak dapat diulang, dan itu
    # kebalikan dari yang diperlukan di sini.
    rng = random.Random(SEED)  # noqa: S311
    weights, risk_classes, warning_rule = risk_rules()
    points = kelurahan_points()

    crimes = read("crime_incidents.csv")
    scores = read("risk_scores.csv")
    predictions = read("predictions.csv")
    warnings = read("early_warnings.csv")
    recommendations = read("recommendations.csv")
    decisions = read("commander_decisions.csv")
    patrols = read("patrol_activity.csv")
    intel = read("intelligence_reports.csv")

    per_cell = len(crimes) / len(locations)
    print(
        f"  {len(locations)} sel yang ada memikul {len(crimes)} kejadian "
        f"(±{per_cell:.0f} per sel); Pesanggrahan mendapat {len(CELLS)} sel",
        file=sys.stderr,
    )

    # ---- locations -------------------------------------------------------------------
    new_location = next_code([row["location_id"] for row in locations], "LOC", 3)
    next_grid = max(int(row["grid_id"].rsplit("-", 1)[1]) for row in locations)
    grid_size = locations[0]["grid_size_m"]

    cells: list[dict[str, str]] = []
    for kelurahan, kind in CELLS:
        next_grid += 1
        latitude, longitude = points[kelurahan]
        cells.append(
            {
                "location_id": new_location(),
                "polsek": POLSEK,
                "kecamatan": KECAMATAN,
                "kelurahan": kelurahan,
                "grid_id": f"JKS-{next_grid:03d}",
                "grid_size_m": grid_size,
                "latitude": f"{latitude}",
                "longitude": f"{longitude}",
                "location_type": kind,
            }
        )
    append("locations.csv", cells)

    def a_cell() -> dict[str, str]:
        return rng.choice(cells)

    def jitter(value: str) -> str:
        """Menggeser titik sel beberapa puluh meter agar kejadian tidak menumpuk persis.

        Besarnya ±0,0009° ≈ 100 meter, sebanding dengan sel 500 meter — cukup untuk
        memisahkan titik di peta tanpa memindahkannya ke kelurahan sebelah.
        """
        return f"{float(value) + rng.uniform(-0.0009, 0.0009):.6f}"

    # ---- crime_incidents ---------------------------------------------------------------
    new_incident = next_code([row["incident_id"] for row in crimes], "INC", 5)
    by_type: dict[str, dict[str, list[str]]] = {}
    for kind in {row["incident_type"] for row in crimes}:
        same = [row for row in crimes if row["incident_type"] == kind]
        by_type[kind] = {
            "modus": learn(same, "modus"),
            "target_type": learn(same, "target_type"),
            "hour": [row["incident_time"][:2] for row in same],
        }
    types = learn(crimes, "incident_type")
    statuses = learn(crimes, "status")
    first = min(date.fromisoformat(row["incident_date"]) for row in crimes)
    last = max(date.fromisoformat(row["incident_date"]) for row in crimes)
    span = (last - first).days

    new_crimes = []
    for _ in range(round(per_cell * len(CELLS))):
        cell = a_cell()
        kind = rng.choice(types)
        shape = by_type[kind]
        when = first + timedelta(days=rng.randint(0, span))
        new_crimes.append(
            {
                "incident_id": new_incident(),
                "incident_type": kind,
                "incident_date": when.isoformat(),
                "incident_time": f"{rng.choice(shape['hour'])}:{rng.randint(0, 59):02d}",
                "polsek": POLSEK,
                "kecamatan": KECAMATAN,
                "kelurahan": cell["kelurahan"],
                "grid_id": cell["grid_id"],
                "latitude": jitter(cell["latitude"]),
                "longitude": jitter(cell["longitude"]),
                "location_type": cell["location_type"],
                "modus": rng.choice(shape["modus"]),
                "target_type": rng.choice(shape["target_type"]),
                "status": rng.choice(statuses),
                "is_synthetic": "True",
            }
        )
    append("crime_incidents.csv", new_crimes)

    # ---- risk_scores -------------------------------------------------------------------
    #
    # Faktor dibangkitkan lebih dulu, skornya DIHITUNG dari faktor itu. Urutan sebaliknya —
    # memilih skor lalu mengarang faktor yang kebetulan menjumlah ke sana — adalah persis
    # temuan audit A-3 yang sudah pernah diperbaiki sekali.
    new_score = next_code([row["risk_score_id"] for row in scores], "RS", 5)
    assessment_dates = sorted({row["assessment_date"] for row in scores})
    windows = sorted({row["time_window"] for row in scores})
    threats = sorted({row["threat_type"] for row in scores})
    model_version = scores[0]["model_version"]
    weights_version = scores[0]["weights_version"]
    observed_scores = [int(row["risk_score"]) for row in scores]

    def window_bounds(day: str, window: str) -> tuple[str, str]:
        start_text, end_text = window.split("-")
        start = f"{day}T{start_text}{TZ}"
        if end_text == "23:59":
            # Jendela malam ditulis berakhir pada tengah malam hari berikutnya, mengikuti
            # baris yang sudah ada — bukan pada 23:59, yang akan menyisakan satu menit
            # tanpa jendela pada setiap hari.
            nxt = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
            return start, f"{nxt}T00:00{TZ}"
        return start, f"{day}T{end_text}{TZ}"

    # Kombinasi (sel, tanggal, jendela, ancaman) diambil TANPA pengulangan.
    #
    # Basis data menegakkan itu lewat kunci unik pada `risk_scores`
    # (location_id, threat_type, window_start, assessment_date), dan alasannya masuk akal:
    # dua penilaian berbeda untuk sel, ancaman, dan jendela yang sama pada hari yang sama
    # adalah dua jawaban atas satu pertanyaan, dan tidak ada cara memilih mana yang benar.
    #
    # Percobaan pertama mengundi keempatnya bebas dan ditolak basis data pada baris ke-164.
    # Itu cara kerja yang benar — kekangan menangkap data yang tidak koheren — tetapi data
    # yang hanya lolos karena kebetulan tidak bertabrakan bukan data yang boleh dikirim.
    combinations = [
        (cell["grid_id"], day, window, threat)
        for cell in cells
        for day in assessment_dates
        for window in windows
        for threat in threats
    ]
    wanted_scores = round(len(scores) / len(locations) * len(CELLS))
    if wanted_scores > len(combinations):
        raise SystemExit("kombinasi penilaian tidak cukup untuk jumlah baris yang diminta")
    chosen = rng.sample(combinations, wanted_scores)
    by_grid = {cell["grid_id"]: cell for cell in cells}

    new_scores: list[dict[str, Any]] = []
    for grid_id, day, window, threat in chosen:
        cell = by_grid[grid_id]
        # Skor diambil dari sebaran NYATA sembilan kecamatan yang sudah ada, bukan diundi
        # merata: Pesanggrahan yang seluruh selnya berskor sedang akan tampak lebih aman
        # daripada tetangganya tanpa ada yang pernah menilainya demikian.
        value = rng.choice(observed_scores)
        factors = factors_for(value, weights, rng)
        start, end = window_bounds(day, window)
        new_scores.append(
            {
                "risk_score_id": new_score(),
                "assessment_date": day,
                "grid_id": cell["grid_id"],
                "kecamatan": KECAMATAN,
                "kelurahan": cell["kelurahan"],
                "threat_type": threat,
                "time_window": window,
                "risk_score": str(value),
                "risk_class": class_of(value, risk_classes),
                **{name: str(number) for name, number in factors.items()},
                "model_version": model_version,
                "window_start": start,
                "window_end": end,
                "weights_version": weights_version,
            }
        )
    unique_key = {
        (row["grid_id"], row["threat_type"], row["time_window"], row["assessment_date"])
        for row in new_scores
    }
    if len(unique_key) != len(new_scores):
        raise SystemExit("penilaian ganda pada sel, ancaman, jendela, dan tanggal yang sama")
    append("risk_scores.csv", new_scores)

    # ---- predictions -------------------------------------------------------------------
    #
    # Tiap prediksi menunjuk satu baris `risk_scores` pendamping yang benar-benar ada
    # (temuan audit A-6), dan skornya diambil DARI baris itu — bukan diundi sendiri.
    # Prediksi yang skornya tidak berhubungan dengan penilaian apa pun tidak dapat
    # ditelusuri ke mana pun.
    new_prediction = next_code([row["prediction_id"] for row in predictions], "PRD", 5)
    horizons = sorted({row["forecast_horizon"] for row in predictions})

    # Horizon adalah JARAK dari tanggal prediksi ke hari yang diprediksi, bukan panjang
    # rentang yang dicakup (`prediction_engine.HORIZON_BASIS`). Jaraknya dibaca dari data
    # yang sudah ada, bukan ditulis ulang di sini: menyalin angka berarti dua tempat yang
    # harus tetap sama, dan yang kedua selalu ketinggalan.
    #
    # Percobaan pertama menyalin jendela dari baris penilaiannya, yang selalu jatuh pada
    # hari yang sama. Prediksi 7D-nya karena itu menunjuk jendela hari ini padahal
    # namanya menjanjikan tujuh hari lagi — dan mesin prediksi menolaknya.
    horizon_offset: dict[str, int] = {}
    for row in predictions:
        offset = (
            date.fromisoformat(row["window_start"][:10])
            - date.fromisoformat(row["prediction_date"])
        ).days
        known = horizon_offset.setdefault(row["forecast_horizon"], offset)
        if known != offset:
            raise SystemExit(f"jarak horizon {row['forecast_horizon']} tidak konsisten")
    statuses_pred = learn(predictions, "status")
    factor_names = [name for name in weights]

    # Skor prediksi ditiru dari sebaran skor PREDIKSI yang sudah ada, bukan diambil acak
    # dari kumpulan penilaian.
    #
    # Keduanya berbeda jauh, dan perbedaannya bukan kebetulan. Penilaian tersebar dari
    # rendah sampai kritis; prediksi tidak pernah berkelas Low sama sekali dan condong ke
    # atas — 47% di antaranya melewati ambang peringatan, dibanding 18% pada penilaian.
    # Yang diterbitkan sebagai prediksi memang sel yang sudah menonjol.
    #
    # Percobaan sebelumnya mengambil acak dari penilaian Moderate ke atas dan menghasilkan
    # peringatan dini separuh dari yang semestinya — Pesanggrahan akan tampak lebih tenang
    # daripada tetangganya tanpa ada yang pernah menilainya demikian.
    predicted_scores = [int(row["risk_score"]) for row in predictions]

    # Setiap prediksi memakai baris pendamping yang BERBEDA. Basis data menegakkan keunikan
    # (lokasi, ancaman, jendela, horizon, model, tanggal) pada `predictions`, dan memakai
    # baris pendamping yang sama dua kali adalah cara paling mudah melanggarnya.
    used_baselines: set[str] = set()

    new_predictions: list[dict[str, Any]] = []
    per_cell_pred = len(predictions) / len(locations)
    for index in range(round(per_cell_pred * len(CELLS))):
        target = rng.choice(predicted_scores)
        # Baris pendamping dipilih yang skornya sama persis; bila tidak ada, yang terdekat.
        # Dengan begitu skor prediksi selalu dapat ditelusuri ke penilaian yang benar-benar
        # menghasilkannya — bukan angka yang berdiri sendiri.
        available = [row for row in new_scores if row["risk_score_id"] not in used_baselines]
        exact = [row for row in available if int(row["risk_score"]) == target]
        basis = (
            rng.choice(exact)
            if exact
            else min(available, key=lambda row: abs(int(row["risk_score"]) - target))
        )
        used_baselines.add(basis["risk_score_id"])
        # WHY diturunkan dari faktor terbesar pada baris pendampingnya (temuan audit A-5),
        # sehingga penjelasannya berbeda per baris dan benar-benar berasal dari angkanya.
        ranked = sorted(factor_names, key=lambda name: int(basis[name]), reverse=True)[:3]
        total = sum(int(basis[name]) * weights[name] for name in ranked)
        dominant = [
            {
                "factor": {
                    "historical_factor": "historical_incident_density",
                    "recent_trend_factor": "recent_incident_trend",
                    "temporal_factor": "time_window_pattern",
                    "spatial_factor": "spatial_concentration",
                    "context_factor": "contextual_activity",
                }[name],
                "contribution": round(int(basis[name]) * weights[name] / total, 3),
                "source": "RULE",
            }
            for name in ranked
        ]
        horizon = horizons[index % len(horizons)]
        target_day = (
            date.fromisoformat(basis["assessment_date"]) + timedelta(days=horizon_offset[horizon])
        ).isoformat()
        window_start, window_end = window_bounds(target_day, basis["time_window"])

        new_predictions.append(
            {
                "prediction_id": new_prediction(),
                "prediction_date": basis["assessment_date"],
                "forecast_horizon": horizon,
                "threat_type": basis["threat_type"],
                "grid_id": basis["grid_id"],
                "kecamatan": KECAMATAN,
                "kelurahan": basis["kelurahan"],
                "time_window": basis["time_window"],
                "risk_score": basis["risk_score"],
                "confidence": rng.choice(learn(predictions, "confidence")),
                "dominant_factors": json.dumps(dominant),
                "model_version": model_version,
                "status": rng.choice(statuses_pred),
                "window_start": window_start,
                "window_end": window_end,
                "baseline_risk_score_code": basis["risk_score_id"],
            }
        )
    prediction_key = {
        (
            row["grid_id"],
            row["threat_type"],
            row["window_start"],
            row["forecast_horizon"],
            row["model_version"],
            row["prediction_date"],
        )
        for row in new_predictions
    }
    if len(prediction_key) != len(new_predictions):
        raise SystemExit("prediksi ganda pada kunci yang ditegakkan basis data")
    append("predictions.csv", new_predictions)

    # ---- early_warnings -------------------------------------------------------------------
    #
    # Peringatan TIDAK diundi. Ia terbit tepat pada prediksi yang skornya melewati ambang
    # `minimum_score`, dan tingkatnya diambil dari ambang yang sama. Mengundinya akan
    # membuat ada prediksi berskor 90 tanpa peringatan dan prediksi berskor 50 dengan
    # peringatan — dan tidak seorang pun dapat menjelaskan mengapa.
    new_warning = next_code([row["warning_id"] for row in warnings], "WRN", 4)
    threshold_version = warnings[0]["threshold_version"]
    warning_statuses = learn(warnings, "status")

    def severity_of(score: int) -> str | None:
        if score < int(warning_rule["minimum_score"]):
            return None
        for band in warning_rule["severities"]:
            if band["min"] <= score <= band["max"]:
                return str(band["severity"]).title()
        return None

    def minus_hours(moment: str, hours: int) -> str:
        parsed = datetime.fromisoformat(moment) - timedelta(hours=hours)
        return parsed.strftime("%Y-%m-%d %H:%M")

    new_warnings: list[dict[str, Any]] = []
    warned: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for prediction in new_predictions:
        severity = severity_of(int(prediction["risk_score"]))
        if severity is None:
            continue
        warning = {
            "warning_id": new_warning(),
            "prediction_id": prediction["prediction_id"],
            # Peringatan terbit tiga jam sebelum jendelanya dimulai, mengikuti pola data
            # yang ada: peringatan yang terbit setelah jendelanya berjalan tidak berguna.
            "created_at": minus_hours(prediction["window_start"], 3),
            "severity": severity,
            "threat_type": prediction["threat_type"],
            "grid_id": prediction["grid_id"],
            "kecamatan": KECAMATAN,
            "kelurahan": prediction["kelurahan"],
            "time_window": prediction["time_window"],
            "risk_score": prediction["risk_score"],
            "confidence": prediction["confidence"],
            "status": rng.choice(warning_statuses),
            "window_start": prediction["window_start"],
            "window_end": prediction["window_end"],
            "threshold_version": threshold_version,
        }
        new_warnings.append(warning)
        warned.append((prediction, warning))
    append("early_warnings.csv", new_warnings)

    # ---- recommendations ----------------------------------------------------------------
    new_recommendation = next_code([row["recommendation_id"] for row in recommendations], "REC", 4)
    functions = learn(recommendations, "recommended_function")
    rec_statuses = learn(recommendations, "status")
    # Isi sementara. `regenerate` menulis ulang SELURUH `recommendation_text` dari prediksi
    # yang dirujuk tiap baris — termasuk baris yang baru dibuat di sini — jadi kalimat apa
    # pun di tempat ini akan tergantikan. Yang penting kolomnya tidak kosong, karena
    # skemanya melarang NULL.
    rec_text = recommendations[0]["recommendation_text"]

    new_recommendations: list[dict[str, Any]] = []
    for prediction, warning in warned:
        new_recommendations.append(
            {
                "recommendation_id": new_recommendation(),
                "prediction_id": prediction["prediction_id"],
                "warning_id": warning["warning_id"],
                "recommended_function": rng.choice(functions),
                "recommendation_text": rec_text,
                # Prioritas mengikuti tingkat peringatannya, tidak diundi terpisah:
                # rekomendasi berprioritas rendah atas peringatan kritis adalah keadaan
                # yang tidak dapat dijelaskan kepada siapa pun.
                "priority": "Tinggi" if warning["severity"] == "Critical" else "Sedang",
                "status": rng.choice(rec_statuses),
                "created_at": minus_hours(prediction["window_start"], 2),
            }
        )
    append("recommendations.csv", new_recommendations)

    # ---- commander_decisions -------------------------------------------------------------
    #
    # Keputusan komandan dibangkitkan di sini; TINDAKAN operasionalnya tidak.
    #
    # Pembagian itu mengikuti sifat keduanya. Keputusan adalah perbuatan manusia — komandan
    # memilih rekomendasi mana yang ia putuskan, dan mana yang dibiarkan menunggu; tidak ada
    # aturan yang dapat menurunkannya dari data lain. Tindakan operasional sebaliknya
    # mengikuti keputusan secara pasti, dan `regenerate_operational()` sudah menurunkannya —
    # termasuk memastikan setiap keputusan yang menyetujui benar-benar berbuah tindakan.
    new_decision = next_code([row["decision_id"] for row in decisions], "DEC", 4)
    decision_reason = decisions[0]["reason"]
    decided_share = len(decisions) / max(len(recommendations), 1)

    new_decisions: list[dict[str, Any]] = []
    for recommendation in new_recommendations:
        # Rekomendasi yang masih "Pending Review" memang belum diputuskan siapa pun.
        # Keputusan harus SEPAKAT dengan status rekomendasinya: rekomendasi berstatus
        # "Approved" yang keputusannya "Rejected" adalah dua pernyataan yang saling
        # membantah di dalam satu rantai — persis yang dicari orang saat memeriksa
        # human-in-the-loop.
        if recommendation["status"] not in ("Approved", "Modified", "Rejected"):
            continue
        if rng.random() > decided_share:
            continue
        new_decisions.append(
            {
                "decision_id": new_decision(),
                "recommendation_id": recommendation["recommendation_id"],
                "decision": recommendation["status"],
                # Ditimpa `regenerate_operational()` dengan kode pengguna yang benar-benar
                # ada; diisi di sini supaya berkasnya tetap sah bila dibaca lebih dulu.
                "decision_by": decisions[0]["decision_by"],
                "decision_at": recommendation["created_at"],
                "reason": decision_reason,
                "modified_text": "",
            }
        )
    append("commander_decisions.csv", new_decisions)

    # ---- patrol_activity -----------------------------------------------------------------
    new_patrol = next_code([row["patrol_id"] for row in patrols], "PAT", 4)
    patrol_units = learn(patrols, "unit_id")
    patrol_types = learn(patrols, "activity_type")
    patrol_results = learn(patrols, "result")
    patrol_hours = [row["start_time"] for row in patrols]

    new_patrols: list[dict[str, Any]] = []
    per_cell_patrols = len(patrols) / len(locations)
    for _ in range(round(per_cell_patrols * len(CELLS))):
        cell = a_cell()
        when = first + timedelta(days=rng.randint(0, span))
        start_time = rng.choice(patrol_hours)
        end_hour = (int(start_time[:2]) + 2) % 24
        new_patrols.append(
            {
                "patrol_id": new_patrol(),
                "unit_id": rng.choice(patrol_units),
                "patrol_date": when.isoformat(),
                "start_time": start_time,
                "end_time": f"{end_hour:02d}:{start_time[3:]}",
                "grid_id": cell["grid_id"],
                "kecamatan": KECAMATAN,
                "activity_type": rng.choice(patrol_types),
                "result": rng.choice(patrol_results),
            }
        )
    append("patrol_activity.csv", new_patrols)

    # ---- intelligence_reports -------------------------------------------------------------
    new_intel = next_code([row["intelligence_id"] for row in intel], "INT", 4)
    intel_categories = learn(intel, "category")
    intel_reliability = learn(intel, "reliability")
    intel_impact = learn(intel, "impact")
    intel_statuses = learn(intel, "status")
    intel_confidence = learn(intel, "confidence")
    intel_urgency = learn(intel, "urgency")

    new_intels: list[dict[str, Any]] = []
    per_cell_intel = len(intel) / len(locations)
    for _ in range(round(per_cell_intel * len(CELLS))):
        cell = a_cell()
        when = first + timedelta(days=rng.randint(0, span))
        new_intels.append(
            {
                "intelligence_id": new_intel(),
                "report_date": when.isoformat(),
                "category": rng.choice(intel_categories),
                "kecamatan": KECAMATAN,
                "kelurahan": cell["kelurahan"],
                "grid_id": cell["grid_id"],
                "reliability": rng.choice(intel_reliability),
                "confidence": rng.choice(intel_confidence),
                "urgency": rng.choice(intel_urgency),
                "impact": rng.choice(intel_impact),
                "status": rng.choice(intel_statuses),
            }
        )
    append("intelligence_reports.csv", new_intels)

    # ---- Berkas turunan diserahkan kepada mesin yang sudah ada ---------------------------
    #
    # `citizen_reports`, `public_alerts`, `community_feedback`, `commander_decisions`,
    # `operational_actions`, dan `prediction_actual` TIDAK dibangkitkan di sini. Perintah
    # `seeding regenerate` membangunnya ulang dari data primer — lokasi, kejadian,
    # penilaian, prediksi, peringatan, rekomendasi — dan itulah satu-satunya tempat
    # aturannya ditulis.
    #
    # Membangkitkannya sendiri berarti menyalin aturan yang sudah ada ke tempat kedua, dan
    # tempat kedua selalu ketinggalan. Percobaan pertama melakukannya dan menghasilkan empat
    # pelanggaran sekaligus: keputusan menyetujui tanpa tindakan, evaluasi atas prediksi yang
    # belum terbit, false negative pada ancaman yang tidak pernah dinilai, dan laporan warga
    # yang berubah begitu mesin normalisasi dijalankan.
    print("\n  Membangun ulang berkas turunan…", file=sys.stderr)
    # Jalur lengkap `uv`, bukan namanya saja: memanggil lewat nama bergantung pada PATH,
    # yang berbeda antara shell pengembang dan proses yang menjalankan skrip ini.
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("perintah `uv` tidak ditemukan; pembangkitan ulang tidak dijalankan")

    result = subprocess.run(  # noqa: S603
        [uv, "run", "python", "-m", "prediksi_presisi_api.seeding", "regenerate"],
        cwd=ROOT / "apps" / "api",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"pembangkitan ulang gagal:\n{result.stderr[-2000:]}")
    for line in result.stdout.strip().splitlines():
        print(f"  {line}", file=sys.stderr)

    print(f"\n  {KECAMATAN} ditambahkan pada {len(CELLS)} sel grid.", file=sys.stderr)


if __name__ == "__main__":
    main()
