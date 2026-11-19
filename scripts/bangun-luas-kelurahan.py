#!/usr/bin/env python3
"""Menghitung luas 65 kelurahan dari poligon peta, untuk Predictive Accuracy Index (PAI).

PAI = porsi kejadian yang tercakup / porsi LUAS wilayah yang ditandai (Chainey dkk., 2008).
Luas kelurahan belum ada di data lokasi (lokasi disimpan sebagai titik), jadi diturunkan
dari poligon yang sudah dipakai peta: apps/web/src/lib/wilayah.generated.ts, hasil
scripts/bangun-batas-wilayah.py dari OpenStreetMap (ODbL 1.0).

KETELITIAN

    Poligon itu sudah disederhanakan untuk digambar dan memakai proyeksi equirectangular
    (1 satuan = 10 meter). Luasnya karena itu PERKIRAAN — cukup untuk perbandingan porsi
    luas antarkelurahan, bukan angka resmi BPS/Pemprov. Bila luas resmi tersedia, ganti
    berkas keluaran dan catat sumbernya di `source`.

Jalankan:  python3 scripts/bangun-luas-kelurahan.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHAPES = ROOT / "apps" / "web" / "src" / "lib" / "wilayah.generated.ts"
OUTPUT = ROOT / "config" / "ranking" / "kelurahan-area.yaml"
UNIT_METRES = 10.0


def ring_area(ring: list[list[float]]) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def main() -> None:
    text = SHAPES.read_text(encoding="utf-8")
    taken = re.search(r'diambil "([0-9-]+)"', text)
    body = text[text.index("export const KELURAHAN_SHAPES") :]
    pattern = re.compile(
        r'\{ name: "([^"]+)", parent: "([^"]+)", label: \[[^\]]+\], rings: (\[\[\[.*?\]\]\]) \}'
    )
    areas: dict[str, tuple[str, float]] = {}
    for name, parent, rings in pattern.findall(body):
        units = sum(ring_area(ring) for ring in json.loads(rings))
        areas[name] = (parent, units * UNIT_METRES * UNIT_METRES / 1_000_000)
    if len(areas) != 65:
        raise SystemExit(f"Diharapkan 65 kelurahan, terbaca {len(areas)}.")
    total = sum(value for _, value in areas.values())
    lines = [
        "# DIBANGKITKAN OLEH scripts/bangun-luas-kelurahan.py — JANGAN DISUNTING TANGAN.",
        "#",
        "# Luas kelurahan (km²) untuk Predictive Accuracy Index. PERKIRAAN: dihitung dari",
        "# poligon peta yang sudah disederhanakan (OpenStreetMap, ODbL 1.0), bukan luas resmi.",
        f'source: "OpenStreetMap lewat apps/web/src/lib/wilayah.generated.ts, diambil '
        f'{taken.group(1) if taken else "?"}"',
        "status: PROPOSED",
        f"total_km2: {total:.3f}",
        "kelurahan:",
    ]
    for name in sorted(areas):
        parent, value = areas[name]
        lines.append(f'  "{name}": {value:.3f}  # {parent}')
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(areas)} kelurahan, total {total:.2f} km²")


if __name__ == "__main__":
    main()
