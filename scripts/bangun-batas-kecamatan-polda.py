#!/usr/bin/env python3
"""Membangun batas KECAMATAN untuk wilayah Polres lain di Polda Metro Jaya dari OpenStreetMap.

Pelengkap `bangun-batas-wilayah.py`, yang hanya membangun kecamatan dan kelurahan Jakarta
Selatan. Dipakai halaman rekap Polda (catatan 198): mengklik Polres lain membuka peta
kecamatannya. Yang dibangun HANYA GARIS BATAS — sistem tidak memegang angka per kecamatan
untuk Polres lain, dan peta itu tidak mewarnai apa pun.

Proyeksinya sama persis dengan skrip induk (dihitung dari bentang wilayah hukum pada
`polda.json`), sehingga kecamatan jatuh tepat di dalam poligon kota/kabupatennya.

Induk tiap kecamatan ditentukan dari geometri — titik di dalamnya jatuh di kota/kabupaten yang
mana — bukan dari tag. Kecamatan yang tidak jatuh di wilayah mana pun dibuang dan dilaporkan.

Keluaran ditulis ke berkas TERPISAH (`wilayah-polda.generated.ts`) dan hanya diimpor halaman
yang digambar di server, supaya paket peramban peta utama tidak ikut membesar.

Jalankan:  python3 scripts/bangun-batas-kecamatan-polda.py
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "apps" / "web" / "src" / "lib" / "wilayah-polda.generated.ts"

spec = importlib.util.spec_from_file_location("batas", ROOT / "scripts" / "bangun-batas-wilayah.py")
assert spec and spec.loader
batas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batas)

#: Setara kecamatan Jakarta Selatan (30 m): pada 60 m kecamatan kecil Jakarta Pusat saling tindih.
TOLERANCE_M = 25.0
HOME = batas.POLDA_METRO_JAYA[batas.JAKARTA_SELATAN]
HDX = ROOT / "data" / "batas-osm" / "kecamatan-hdx.json.gz"

#: Nama dari OpenStreetMap adalah data luar yang akan ditulis ke berkas sumber. Hanya huruf,
#: angka, spasi, titik, tanda hubung, dan apostrof yang diterima; nama lain menghentikan
#: pembangunan alih-alih ikut tertulis. Penulisannya sendiri memakai `json.dumps`.
SAFE_NAME = re.compile(r"^[\w .'’-]{1,80}$")


def literal(value: str) -> str:
    """Nilai teks sebagai literal yang aman untuk berkas TypeScript."""
    if not SAFE_NAME.match(value):
        raise SystemExit(f"nama wilayah tidak lazim, pembangunan dihentikan: {value!r}")
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    polda = batas.overpass("", "polda.json")  # selalu dari singgahan skrip induk
    regions = {
        osm_id: name for osm_id, name in batas.POLDA_METRO_JAYA.items() if name != HOME
    }
    areas = "".join(f"area({3600000000 + osm_id});" for osm_id in regions)
    kecamatan = batas.overpass(
        f"[out:json][timeout:900];({areas})->.a;"
        'rel(area.a)["boundary"="administrative"]["admin_level"="6"];out geom;',
        "kecamatan-polda.json",
    )

    everything = [p for e in polda["elements"] for ring in batas.rings_of(e) for p in ring]
    lons, lats = [p[0] for p in everything], [p[1] for p in everything]
    cos_reference = math.cos(math.radians((min(lats) + max(lats)) / 2))
    origin_lon, origin_lat = min(lons), max(lats)

    def project(lon: float, lat: float) -> tuple[float, float]:
        return (
            (lon - origin_lon) * cos_reference * batas.EARTH_M_PER_DEG / batas.METRES_PER_UNIT,
            (origin_lat - lat) * batas.EARTH_M_PER_DEG / batas.METRES_PER_UNIT,
        )

    parents = {
        regions[e["id"]]: [[project(*p) for p in ring] for ring in batas.rings_of(e)]
        for e in polda["elements"]
        if e["id"] in regions
    }
    tolerance = TOLERANCE_M / batas.METRES_PER_UNIT
    out: dict[str, list[dict]] = {name: [] for name in sorted(parents)}

    # Wilayah yang kecamatannya belum (lengkap) dipetakan di OpenStreetMap memakai potongan
    # geoBoundaries/HDX (lihat ambil-batas-kecamatan-hdx.py) — SELURUH kecamatan wilayah itu
    # dari satu sumber, supaya garis antarkecamatan tidak berasal dari dua pemetaan berbeda.
    hdx_regions: set[str] = set()
    if HDX.exists():
        with gzip.open(HDX, "rt", encoding="utf-8") as handle:
            for item in json.load(handle)["kecamatan"]:
                rings = [[project(*point) for point in ring] for ring in item["rings"]]
                rings = [batas.simplify(ring, tolerance) for ring in rings]
                rings = [ring for ring in rings if len(ring) >= 4]
                if not rings or item["region"] not in out:
                    continue
                hdx_regions.add(item["region"])
                label = batas.label_anchor(rings)
                out[item["region"]].append(
                    {
                        "name": item["name"],
                        "label": (round(label[0], 1), round(label[1], 1)),
                        "rings": [[(round(x, 1), round(y, 1)) for x, y in ring] for ring in rings],
                    }
                )
    dropped: list[str] = []
    seen: set[tuple[str, str]] = set()
    for element in kecamatan["elements"]:
        name = element.get("tags", {}).get("name")
        raw = [[project(*p) for p in ring] for ring in batas.rings_of(element)]
        raw = [ring for ring in raw if len(ring) >= 4]
        if not name or not raw:
            continue
        raw.sort(key=batas.area_of, reverse=True)
        anchor = batas.interior_point(raw[0])
        parent = next(
            (
                region
                for region, rings in parents.items()
                if any(batas.inside(anchor, ring) for ring in rings)
            ),
            None,
        )
        if parent is None:
            dropped.append(name)
            continue
        if parent in hdx_regions:
            continue
        if (parent, name) in seen:
            continue
        seen.add((parent, name))
        rings = [batas.simplify(ring, tolerance) for ring in raw]
        rings = [ring for ring in rings if len(ring) >= 4]
        if not rings:
            continue
        label = batas.label_anchor(rings)
        out[parent].append(
            {
                "name": name,
                "label": (round(label[0], 1), round(label[1], 1)),
                "rings": [[(round(x, 1), round(y, 1)) for x, y in ring] for ring in rings],
            }
        )
    lines = [
        "// DIBANGKITKAN OLEH scripts/bangun-batas-kecamatan-polda.py — JANGAN DISUNTING TANGAN.",
        "//",
        f'// Sumber: OpenStreetMap lewat Overpass API, diambil "{batas._today()}".',
        '// Lisensi: ODbL 1.0 — "© Kontributor OpenStreetMap" wajib dicantumkan di kaki peta.',
        "// Kota Bekasi, Kabupaten Bekasi, dan Kota Depok: geoBoundaries gbHumanitarian ADM3",
        "// (OCHA ROAP/HDX atas data BPS), CC BY 3.0 IGO — atribusinya juga di kaki peta.",
        "//",
        "// Batas KECAMATAN wilayah Polres lain di Polda Metro Jaya, pada sistem koordinat yang",
        "// sama dengan wilayah.generated.ts. Hanya garis batas: tidak ada angka per kecamatan.",
        "",
        'import type { AreaShape } from "./wilayah.generated";',
        "",
        "export const POLDA_KECAMATAN: Readonly<Record<string, readonly AreaShape[]>> = {",
    ]
    for region, shapes in out.items():
        shapes.sort(key=lambda s: s["name"])
        lines.append(f"  {literal(region)}: [")
        for shape in shapes:
            rings = ",".join(
                "[" + ",".join(f"[{x},{y}]" for x, y in ring) + "]" for ring in shape["rings"]
            )
            lines.append(
                f"    {{ name: {literal(shape['name'])}, parent: {literal(region)}, "
                f"label: [{shape['label'][0]},{shape['label'][1]}], rings: [{rings}] }},"
            )
        lines.append("  ],")
        points = sum(len(r) for s in shapes for r in s["rings"])
        print(f"  {region}: {len(shapes)} kecamatan, {points} titik", file=sys.stderr)
    lines += [
        "};",
        "",
        "/** Wilayah yang batas kecamatannya dari geoBoundaries/HDX (BPS), bukan OpenStreetMap. */",
        "export const POLDA_KECAMATAN_HDX: readonly string[] = ["
        + ", ".join(literal(name) for name in sorted(hdx_regions))
        + "];",
        "",
    ]
    OUTPUT.write_text("\n".join(lines))
    if dropped:
        print(f"  dibuang (di luar wilayah hukum): {len(dropped)} — {sorted(dropped)[:12]}", file=sys.stderr)
    print(f"Ditulis ke {OUTPUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
