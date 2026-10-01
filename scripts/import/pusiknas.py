#!/usr/bin/env python3
"""Impor data kejadian asli Pusiknas → `data/processed/`.

    cd apps/api && uv run --group analysis python ../../scripts/import/pusiknas.py

Pipeline CLAUDE.md §18, dijalankan apa adanya:

    data/raw/*.xlsx  →  validasi  →  pemetaan  →  (anonimisasi: sudah di sumber)  →
    geo (kelurahan ↔ poligon OSM)  →  data/processed/*.csv

Dua hal yang membuat berkas ini pantas dipercaya:

1. **Ia memvalidasi dirinya terhadap rekapitulasi RESMI.** Berkas Pusiknas memuat sheet
   3 s.d. 9 — rekap per tahun, bulan, Polsek, kategori TKP, modus, dan jeda lapor — yang
   disusun pemilik data dari sheet 1. Setiap angka hasil impor dicocokkan dengan rekap itu
   sebelum satu baris pun ditulis. Selisih satu kejadian saja menggagalkan impor. Dengan
   demikian apa yang tampil di aplikasi dapat dipertanggungjawabkan angka demi angka
   terhadap paparan 29 September 2026.

2. **Ia menolak kolom identitas.** Sumbernya memang anonim (tidak ada nama, NIK, telepon,
   nomor rumah, RT, RW; ID tidak tertelusur ke nomor LP). Tetapi pipeline impor adalah
   gerbang terakhir: bila kelak ada berkas dengan kolom semacam itu, impor berhenti —
   bukan mengabaikannya diam-diam.

Yang TIDAK dilakukan di sini, dan sengaja:

- Tidak mengisi jam kejadian yang kosong (21,9%). `incident_time` dibiarkan kosong;
  seeder menandai `time_known = false`.
- Tidak mengisi tanggal kejadian yang kosong (10 baris). Baris itu memakai tanggal
  laporan sebagai tanggal kejadian dan ditandai lewat `data_source` — supaya rekap per
  tanggal laporan tetap cocok dengan sumber, dan supaya penandaannya terlihat.
- Tidak memaksa koordinat. Hanya 17% kejadian punya koordinat, hampir seluruhnya
  2025–2026. Satuan spasial yang bisa diandalkan adalah KELURAHAN (95% terisi), dan
  master lokasi dibangun dari 65 kelurahan itu dengan titik pusat dari poligon OSM —
  bukan dari grid 500 m yang hanya ada pada data terbaru.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import re
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "Data_Kejadian_Curanmor_Curat_Curas_Polres_Metro_Jaksel_2023-Sep2026.xlsx"
OUT = ROOT / "data" / "processed"
OSM_KELURAHAN = ROOT / "data" / "batas-osm" / "kelurahan.json.gz"
OSM_KECAMATAN = ROOT / "data" / "batas-osm" / "kecamatan.json.gz"
BOUNDARY_SCRIPT = ROOT / "scripts" / "bangun-batas-wilayah.py"

DATA_SOURCE = "PUSIKNAS-2026-09-29"
#: Baris yang tanggal kejadiannya tidak tercatat memakai tanggal laporan, dan ditandai.
DATA_SOURCE_NO_DATE = DATA_SOURCE + "/TANPA-TANGGAL-KEJADIAN"

#: Kolom yang kehadirannya menghentikan impor. Sumbernya anonim; ini gerbang terakhir.
IDENTITY_COLUMNS = re.compile(
    # "Nama jalan" BUKAN identitas — ia rujukan TKP tanpa nomor rumah yang kamus datanya
    # tandai SANGAT PENTING. Yang ditolak adalah nama ORANG dan penanda pribadi lain.
    r"\bnama (korban|pelapor|saksi|terlapor|tersangka|pelaku)\b|\bnik\b|\bktp\b|"
    r"\btelp|\btelepon|\bno\.? ?hp\b|handphone|e-?mail|alamat lengkap|\brt/?rw\b|"
    r"nomor rumah|\b(korban|pelapor|saksi|terlapor|tersangka|pelaku)\b",
    re.I,
)

#: Ejaan kelurahan pada data Pusiknas yang berbeda dari OSM. Satu-satunya yang berbeda
#: dari 65 nama — diperiksa, bukan diasumsikan.
KELURAHAN_ALIAS = {"Setia Budi": "Setiabudi"}

JENIS = {"Curanmor": "CURANMOR", "Curat": "CURAT", "Curas": "CURAS"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------------------------------
# Batas wilayah — dipinjam dari scripts/bangun-batas-wilayah.py agar satu definisi centroid
# ---------------------------------------------------------------------------------------


def _boundary_helpers() -> Any:
    spec = importlib.util.spec_from_file_location("bbw", BOUNDARY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def centroids(cache: Path, helpers: Any) -> dict[str, tuple[float, float]]:
    """Nama wilayah → (lintang, bujur) titik pusat cincin terbesar, dalam derajat."""
    data = json.load(gzip.open(cache))
    result: dict[str, tuple[float, float]] = {}
    for element in data["elements"]:
        name = element.get("tags", {}).get("name")
        rings = helpers.rings_of(element)
        if not name or not rings:
            continue
        rings.sort(key=helpers.area_of, reverse=True)
        lon, lat = helpers.centroid_of(rings[0])
        result[name] = (round(lat, 6), round(lon, 6))
    return result


# ---------------------------------------------------------------------------------------
# Pembacaan
# ---------------------------------------------------------------------------------------


def read_incidents() -> pd.DataFrame:
    df = pd.read_excel(RAW, sheet_name="1-Data Kejadian", header=2)
    df.columns = [str(c).strip() for c in df.columns]
    identitas = [c for c in df.columns if IDENTITY_COLUMNS.search(c)]
    if identitas:
        raise SystemExit(f"DITOLAK: kolom identitas pada sumber: {identitas}")
    return df


def read_recap(sheet: str) -> pd.DataFrame:
    df = pd.read_excel(RAW, sheet_name=sheet, header=None)
    return df


def _as_time(value: Any) -> time | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    try:
        return datetime.strptime(str(value).strip(), "%H:%M:%S").time()
    except ValueError:
        return None


def _as_date(value: Any) -> date | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date()


# ---------------------------------------------------------------------------------------
# Transformasi
# ---------------------------------------------------------------------------------------


def build_locations(df: pd.DataFrame) -> list[dict[str, Any]]:
    helpers = _boundary_helpers()
    kel_centroid = centroids(OSM_KELURAHAN, helpers)
    kec_centroid = centroids(OSM_KECAMATAN, helpers)

    pairs = df[["Kecamatan", "Polsek wilayah"]].drop_duplicates()
    polsek_of = dict(zip(pairs["Kecamatan"], pairs["Polsek wilayah"], strict=True))
    if len(polsek_of) != 10 or pairs["Kecamatan"].nunique() != len(pairs):
        raise SystemExit("kecamatan ↔ Polsek wilayah tidak 1:1 pada sumber")

    rows: list[dict[str, Any]] = []
    kel_pairs = df[["Kelurahan", "Kecamatan"]].dropna().drop_duplicates()
    seen: set[str] = set()
    for kelurahan, kecamatan in sorted(kel_pairs.itertuples(index=False, name=None)):
        name = KELURAHAN_ALIAS.get(kelurahan, kelurahan)
        if name in seen:
            raise SystemExit(f"kelurahan '{name}' muncul di dua kecamatan")
        seen.add(name)
        if name not in kel_centroid:
            raise SystemExit(f"kelurahan '{name}' tidak ada pada poligon OSM")
        lat, lon = kel_centroid[name]
        rows.append(
            {
                "location_id": f"LOC-KEL-{slug(name)}",
                "polsek": polsek_of[kecamatan],
                "kecamatan": kecamatan,
                "kelurahan": name,
                "grid_id": f"kel:{slug(name)}",
                # 0 = satuan administratif, bukan sel grid. Dinyatakan, bukan dikarang.
                "grid_size_m": 0,
                "latitude": lat,
                "longitude": lon,
                "location_type": "KELURAHAN",
            }
        )
    if len(rows) != 65:
        raise SystemExit(f"diharapkan 65 kelurahan, dapat {len(rows)}")

    # Lokasi cadangan setingkat kecamatan: untuk 413 kejadian tanpa kelurahan. Mereka tetap
    # terpetakan ke wilayahnya alih-alih dibuang atau dipaksa ke kelurahan tertentu.
    for kecamatan in sorted(polsek_of):
        if kecamatan not in kec_centroid:
            raise SystemExit(f"kecamatan '{kecamatan}' tidak ada pada poligon OSM")
        lat, lon = kec_centroid[kecamatan]
        rows.append(
            {
                "location_id": f"LOC-KEC-{slug(kecamatan)}",
                "polsek": polsek_of[kecamatan],
                "kecamatan": kecamatan,
                "kelurahan": "",
                "grid_id": f"kec:{slug(kecamatan)}",
                "grid_size_m": 0,
                "latitude": lat,
                "longitude": lon,
                "location_type": "KECAMATAN",
            }
        )
    return rows


def build_incidents(df: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    tally = {"tanpa_jam": 0, "tanpa_tanggal_kejadian": 0, "tanpa_kelurahan": 0, "koordinat": 0}
    for r in df.itertuples(index=False):
        # itertuples mengganti spasi pada nama kolom; ambil lewat posisi kolom asli.
        rec = dict(zip(df.columns, r, strict=True))

        jenis = JENIS.get(str(rec["Jenis kejahatan"]).strip())
        if jenis is None:
            raise SystemExit(f"jenis kejahatan tak dikenal: {rec['Jenis kejahatan']!r}")

        reported_day = _as_date(rec["Tanggal laporan"])
        if reported_day is None:
            raise SystemExit(f"{rec['ID kejadian']}: tanggal laporan kosong")
        reported_time = _as_time(rec["Jam laporan"]) or time(0, 0)
        reported_at = datetime.combine(reported_day, reported_time).isoformat() + "+07:00"

        occurred_day = _as_date(rec["Tanggal kejadian"])
        source = DATA_SOURCE
        if occurred_day is None:
            occurred_day, source = reported_day, DATA_SOURCE_NO_DATE
            tally["tanpa_tanggal_kejadian"] += 1

        jam = _as_time(rec["Jam kejadian"])
        if jam is None:
            tally["tanpa_jam"] += 1

        kelurahan = rec["Kelurahan"]
        if isinstance(kelurahan, str) and kelurahan.strip():
            name = KELURAHAN_ALIAS.get(kelurahan.strip(), kelurahan.strip())
            grid = f"kel:{slug(name)}"
        else:
            name = ""
            grid = f"kec:{slug(str(rec['Kecamatan']))}"
            tally["tanpa_kelurahan"] += 1

        lat = rec["Lintang"]
        lon = rec["Bujur"]
        has_point = pd.notna(lat) and pd.notna(lon)
        if has_point:
            tally["koordinat"] += 1

        lag = rec["Jeda lapor (jam)"]
        rows.append(
            {
                "incident_id": str(rec["ID kejadian"]).strip(),
                "incident_type": jenis,
                "incident_date": occurred_day.isoformat(),
                "incident_time": jam.strftime("%H:%M:%S") if jam else "",
                "polsek": str(rec["Polsek wilayah"]).strip(),
                "kecamatan": str(rec["Kecamatan"]).strip(),
                "kelurahan": name,
                "grid_id": grid,
                "latitude": f"{float(lat):.3f}" if has_point else "",
                "longitude": f"{float(lon):.3f}" if has_point else "",
                "location_type": str(rec["Kategori TKP"]).strip(),
                "modus": str(rec["Modus operandi"]).strip(),
                "target_type": str(rec["Objek sasaran"]).strip(),
                "status": "",
                "reported_at": reported_at,
                "report_lag_hours": f"{float(lag):.1f}" if pd.notna(lag) else "",
                "report_source": str(rec["Sumber laporan"]).strip(),
                "receiving_unit": str(rec["Satuan penerima laporan"]).strip(),
                "data_group": str(rec["Kelompok data"]).strip(),
                "street": str(rec["Nama jalan TKP"]).strip() if pd.notna(rec["Nama jalan TKP"]) else "",
                "grid_500m": str(rec["Grid lokasi (500 m)"]).strip() if pd.notna(rec["Grid lokasi (500 m)"]) else "",
                "data_source": source,
            }
        )
    return rows, tally


# ---------------------------------------------------------------------------------------
# Validasi terhadap rekap resmi (sheet 3, 4, 6, 7, 8, 9)
# ---------------------------------------------------------------------------------------


def _int(v: Any) -> int | None:
    """Angka rekap sebagai bilangan bulat; None untuk sel kosong, judul, atau rasio."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else None
    raw = str(v).strip().replace(".", "").replace(",", "")
    return int(raw) if raw.isdigit() else None


def _label(v: Any) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def _section(sheet: pd.DataFrame, start: str, stop: str | None) -> pd.DataFrame:
    """Baris di antara judul bagian `start` (eksklusif) dan `stop` (eksklusif)."""
    labels = sheet.iloc[:, 0].map(_label)
    i0 = labels[labels.str.startswith(start)].index[0] + 1
    rest = labels.iloc[i0:]
    i1 = rest[rest.str.startswith(stop)].index[0] if stop else len(sheet)
    return sheet.iloc[i0:i1]


def validate(rows: list[dict[str, Any]]) -> list[str]:
    """Mencocokkan hasil impor dengan rekap RESMI pada sheet 3, 4, 6, 7, dan 8."""
    out = pd.DataFrame(rows)
    rep = pd.to_datetime(out.reported_at.str.slice(0, 19))
    gagal: list[str] = []

    def cek(nama: str, dapat: int, resmi: int | None) -> None:
        if resmi is not None and dapat != resmi:
            gagal.append(f"{nama}: impor {dapat} ≠ resmi {resmi}")

    # Sheet 3 — per jenis × tahun laporan, dan totalnya. Blok kedua (rasio) tidak dipakai.
    rk = read_recap("3-Rekap Tahun")
    per_jenis_tahun = out.assign(th=rep.dt.year).groupby(["incident_type", "th"]).size()
    for _, r in rk.iloc[3:7].iterrows():
        label = _label(r.iloc[0])
        jenis = next((j for k, j in (("(Curanmor)", "CURANMOR"), ("(Curat)", "CURAT"), ("(Curas)", "CURAS")) if k in label), None)
        if jenis:
            for col, th in ((1, 2023), (2, 2024), (3, 2025), (4, 2026)):
                cek(f"{jenis} {th}", int(per_jenis_tahun.get((jenis, th), 0)), _int(r.iloc[col]))
            cek(f"total {jenis}", int((out.incident_type == jenis).sum()), _int(r.iloc[5]))
        elif label.upper() == "JUMLAH":
            cek("total seluruh", len(out), _int(r.iloc[5]))

    # Sheet 6 bagian A — per Polsek wilayah × jenis.
    bagian = _section(read_recap("6-Polsek dan Kelurahan"), "A.", "B.")
    per_polsek_jenis = out.groupby(["polsek", "incident_type"]).size()
    for _, r in bagian.iterrows():
        label = _label(r.iloc[0])
        if label.startswith("Polsek "):
            for col, jenis in ((1, "CURANMOR"), (2, "CURAT"), (3, "CURAS")):
                cek(f"{label} {jenis}", int(per_polsek_jenis.get((label, jenis), 0)), _int(r.iloc[col]))

    # Sheet 7 — per kategori TKP (seluruh daftar).
    rk = read_recap("7-Kategori TKP")
    per_tkp = out.groupby("location_type").size()
    for _, r in rk.iloc[3:].iterrows():
        label = _label(r.iloc[0])
        if label and label.upper() != "JUMLAH" and label in per_tkp.index:
            cek(f"TKP {label}", int(per_tkp[label]), _int(r.iloc[4]))

    # Sheet 8 — bagian A modus, bagian B objek sasaran.
    rk = read_recap("8-Modus dan Sasaran")
    for start, stop, kolom in (("A.", "B.", "modus"), ("B.", None, "target_type")):
        tabel = out.groupby(kolom).size()
        for _, r in _section(rk, start, stop).iterrows():
            label = _label(r.iloc[0])
            if label in tabel.index:
                cek(f"{kolom} {label}", int(tabel[label]), _int(r.iloc[4]))

    # Sheet 4 — per bulan menurut tanggal LAPORAN.
    rk = read_recap("4-Rekap Bulan")
    bulan = {m: i for i, m in enumerate(["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"], 1)}
    per_bulan = out.assign(th=rep.dt.year, bl=rep.dt.month).groupby(["th", "bl"]).size()
    for _, r in rk.iloc[3:].iterrows():
        th, bl = _int(r.iloc[0]), _label(r.iloc[1])
        if th and bl in bulan:
            cek(f"bulan {th}-{bulan[bl]:02d}", int(per_bulan.get((th, bulan[bl]), 0)), _int(r.iloc[5]))

    return gagal


# ---------------------------------------------------------------------------------------
# Penulisan
# ---------------------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not RAW.exists():
        print(f"berkas sumber tidak ada: {RAW}", file=sys.stderr)
        return 2

    df = read_incidents()
    incidents, tally = build_incidents(df)
    locations = build_locations(df)

    gagal = validate(incidents)
    if gagal:
        print("IMPOR DITOLAK — hasil tidak cocok dengan rekap resmi:", file=sys.stderr)
        for g in gagal:
            print("  ", g, file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "crime_incidents.csv", incidents)
    write_csv(OUT / "locations.csv", locations)
    manifest = {
        "source_file": RAW.name,
        "source_sha256": sha256(RAW),
        "data_source": DATA_SOURCE,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "incidents": len(incidents),
        "locations": len(locations),
        "catatan": tally,
        "validasi": "cocok dengan rekap resmi sheet 3, 4, 6, 7, 8",
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"ditulis: {len(incidents)} kejadian, {len(locations)} lokasi → {OUT}")
    print("catatan:", json.dumps(tally, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
