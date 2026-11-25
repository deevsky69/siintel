#!/usr/bin/env python3
"""Mengambil batas kecamatan dari geoBoundaries (gbHumanitarian) untuk wilayah yang kecamatannya
BELUM dipetakan di OpenStreetMap: Kota Bekasi, Kabupaten Bekasi, dan sebagian Kota Depok.

SUMBER DAN LISENSI

    geoBoundaries gbHumanitarian, Indonesia ADM3 (kecamatan), keluaran 9469f09 — bersumber dari
    OCHA Regional Office for Asia and the Pacific / HDX atas data Badan Pusat Statistik.
    Lisensi Creative Commons Attribution 3.0 IGO: wajib menyebut sumbernya. Atribusi itu
    ditulis di kaki peta.

Berkas aslinya 26 MB untuk seluruh Indonesia. Yang disimpan di repositori hanya potongannya:
kecamatan yang titik dalamnya jatuh di tiga wilayah di atas (`data/batas-osm/kecamatan-hdx.json.gz`),
supaya peta dapat dibangun ulang persis sama tanpa mengunduh lagi. SHA-256 berkas asli
diperiksa sebelum dipakai.

Jalankan:  python3 scripts/ambil-batas-kecamatan-hdx.py [berkas-geojson-yang-sudah-diunduh]
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "batas-osm" / "kecamatan-hdx.json.gz"
URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbHumanitarian/IDN/ADM3/"
    "geoBoundaries-IDN-ADM3_simplified.geojson"
)
SHA256 = "e60e88b56c43016b0ad5dd33fe9b5d098a1072d7930eed40a4a1a633dd9b53f6"
REGIONS = ("Kota Bekasi", "Kabupaten Bekasi", "Kota Depok")

spec = importlib.util.spec_from_file_location("batas", ROOT / "scripts" / "bangun-batas-wilayah.py")
if spec is None or spec.loader is None:
    raise SystemExit("skrip induk tidak ditemukan")
batas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batas)


def main() -> None:
    if len(sys.argv) > 1:
        raw = Path(sys.argv[1]).read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=600) as response:  # noqa: S310 — alamat tetap
            raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"berkas sumber berubah: sha256 {digest}")
    features = json.loads(raw)["features"]

    polda = batas.overpass("", "polda.json")
    wanted = {
        batas.POLDA_METRO_JAYA[e["id"]]: batas.rings_of(e)
        for e in polda["elements"]
        if batas.POLDA_METRO_JAYA.get(e["id"]) in REGIONS
    }
    kept = []
    for feature in features:
        geometry = feature["geometry"]
        polygons = (
            [geometry["coordinates"]]
            if geometry["type"] == "Polygon"
            else geometry["coordinates"]
        )
        # Hanya cincin luar; koordinat dibulatkan enam desimal (± 0,1 m).
        rings = [[(round(x, 6), round(y, 6)) for x, y in polygon[0]] for polygon in polygons]
        rings = [ring for ring in rings if len(ring) >= 4]
        if not rings:
            continue
        rings.sort(key=batas.area_of, reverse=True)
        anchor = batas.interior_point(rings[0])
        region = next(
            (
                name
                for name, outline in wanted.items()
                if any(batas.inside(anchor, ring) for ring in outline)
            ),
            None,
        )
        if region:
            kept.append(
                {"name": str(feature["properties"]["shapeName"]), "region": region, "rings": rings}
            )
    kept.sort(key=lambda item: (item["region"], item["name"]))
    with gzip.open(OUT, "wt", encoding="utf-8") as handle:
        json.dump({"source": URL, "sha256": SHA256, "kecamatan": kept}, handle)
    for region in REGIONS:
        names = [item["name"] for item in kept if item["region"] == region]
        print(f"  {region}: {len(names)} — {names}", file=sys.stderr)
    print(f"Ditulis ke {OUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
