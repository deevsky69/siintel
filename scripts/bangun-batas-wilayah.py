#!/usr/bin/env python3
"""Membangun batas wilayah untuk peta dari OpenStreetMap.

MENGAPA SKRIP DAN BUKAN SEKALI TEMPEL

    Poligon peta sebelumnya adalah *perkiraan* — hasil pembagian Voronoi dari 33 titik
    lokasi, bukan batas sebenarnya. Penggantinya harus dapat diperiksa dan dibangun ulang:
    dari mana datanya, versi kapan, disederhanakan seberapa. Konstanta yang ditempel tanpa
    jejak akan menjadi angka yang tidak berani disentuh siapa pun.

SUMBER DAN LISENSI

    OpenStreetMap, diambil lewat Overpass API. Data OSM berlisensi ODbL 1.0; karya yang
    menampilkannya wajib mencantumkan "© Kontributor OpenStreetMap". Atribusi itu digambar
    di kaki peta, bukan hanya dicatat di sini.

TINGKAT ADMINISTRASI DI OSM

    Di DKI Jakarta penomorannya bergeser satu dibanding wilayah lain:

        level 5   kota administrasi / kabupaten     (Jakarta Selatan, Kota Bekasi, ...)
        level 6   kecamatan                          (Tebet, Cilandak, ...)
        level 7   kelurahan                          (Bukit Duri, Manggarai, ...)

PROYEKSI

    Equirectangular dengan lintang acuan di tengah wilayah, diskalakan agar **1 satuan
    gambar = 10 meter**. Satu proyeksi dipakai untuk SELURUH lapisan — kelurahan, kecamatan,
    dan wilayah hukum berada pada sistem koordinat yang sama. Menyelami peta karenanya hanya
    mengubah `viewBox`, bukan menghitung ulang bentuk, dan titik kejadian tetap jatuh di
    tempat yang sama pada setiap tingkat.

Jalankan:  uv run python scripts/bangun-batas-wilayah.py
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "batas-osm"
OUTPUT = ROOT / "apps" / "web" / "src" / "lib" / "wilayah.generated.ts"

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Wilayah hukum Polda Metro Jaya: DKI Jakarta seluruhnya, ditambah Depok, Bekasi
# (kota dan kabupaten), serta Tangerang (kota, kabupaten, dan Tangerang Selatan).
# Bogor TIDAK termasuk — ia berada di bawah Polda Jawa Barat.
POLDA_METRO_JAYA = {
    7626001: "Jakarta Barat",
    7625977: "Jakarta Pusat",
    5802438: "Jakarta Selatan",
    5802441: "Jakarta Timur",
    7626002: "Jakarta Utara",
    5802442: "Kepulauan Seribu",
    14525364: "Kota Depok",
    14509733: "Kota Bekasi",
    14765575: "Kabupaten Bekasi",
    7641583: "Kota Tangerang",
    7641584: "Kabupaten Tangerang",
    7641582: "Kota Tangerang Selatan",
}

JAKARTA_SELATAN = 5802438

# Toleransi penyederhanaan, dalam meter. Berbeda per lapisan karena keperluannya berbeda:
# lapisan wilayah hukum hanya perlu dikenali bentuknya, kelurahan perlu terlihat batasnya
# terhadap tetangga yang berjarak beberapa ratus meter.
TOLERANCE_M = {"polda": 120.0, "kecamatan": 30.0, "kelurahan": 15.0}

METRES_PER_UNIT = 10.0
EARTH_M_PER_DEG = 111_320.0


def overpass(query: str, cache_name: str) -> dict:
    """Menjalankan kueri Overpass, dengan singgahan di cakram supaya tidak diulang."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())

    body = urllib.parse.urlencode({"data": query}).encode()
    # Overpass membatasi laju permintaan per alamat IP, dan menolak dengan galat yang sama
    # rupanya seperti kueri yang salah. Jeda bertingkat membedakan keduanya: kueri yang
    # salah tetap gagal setelah menunggu, sedangkan yang ditolak karena laju akan lolos.
    for attempt, host in enumerate(OVERPASS * 3):
        if attempt:
            time.sleep(min(5 * attempt, 45))
        try:
            with urllib.request.urlopen(  # noqa: S310 — daftar host tetap di atas
                urllib.request.Request(host, data=body), timeout=300
            ) as response:
                payload = response.read().decode()
            if payload.lstrip().startswith("{"):
                path.write_text(payload)
                print(f"  diambil dari {host}", file=sys.stderr)
                return json.loads(payload)
        except Exception as error:  # noqa: BLE001 — cermin berikutnya yang dicoba
            print(f"  gagal {host}: {error}", file=sys.stderr)
    raise RuntimeError("seluruh cermin Overpass gagal")


def rings_of(relation: dict) -> list[list[tuple[float, float]]]:
    """Menyambung anggota relasi menjadi cincin tertutup.

    Relasi batas OSM tersusun dari ruas-ruas jalan yang **tidak berurutan**, dan arahnya
    boleh terbalik. Penyambungan mencocokkan ujung ke ujung sampai kembali ke titik awal.
    Cincin `inner` (kantong di dalam wilayah) dibuang: pada wilayah ini tidak ada kantong
    yang bermakna, dan menggambarnya menuntut aturan isi genap-ganjil yang tidak sepadan.
    """
    segments = [
        [(point["lon"], point["lat"]) for point in member["geometry"]]
        for member in relation.get("members", [])
        if member["type"] == "way" and member.get("role") in ("outer", "") and member.get("geometry")
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


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Douglas–Peucker. `tolerance` dalam satuan yang sama dengan titiknya."""
    if len(points) < 3:
        return points

    first, last = points[0], points[-1]
    index, worst = 0, 0.0
    for i in range(1, len(points) - 1):
        distance = perpendicular(points[i], first, last)
        if distance > worst:
            index, worst = i, distance

    if worst <= tolerance:
        return [first, last]
    return simplify(points[: index + 1], tolerance)[:-1] + simplify(points[index:], tolerance)


def perpendicular(point, start, end) -> float:
    (px, py), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def inside(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    """Uji titik di dalam poligon dengan pancaran sinar (ray casting)."""
    x, y = point
    result = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def interior_point(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """Satu titik yang dijamin berada DI DALAM poligon.

    Titik pusat massa tidak cukup: pada poligon cekung ia bisa jatuh di luar poligonnya
    sendiri. Cara ini menarik garis mendatar melalui tengah poligon, mengumpulkan potongan
    yang berada di dalamnya, lalu mengambil tengah potongan terpanjang.
    """
    centre = centroid_of(ring)
    if inside(centre, ring):
        return centre

    y = (min(p[1] for p in ring) + max(p[1] for p in ring)) / 2
    crossings = []
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            crossings.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
    crossings.sort()
    if len(crossings) < 2:
        return centre

    spans = [(crossings[i + 1] - crossings[i], i) for i in range(0, len(crossings) - 1, 2)]
    _, index = max(spans)
    return ((crossings[index] + crossings[index + 1]) / 2, y)


def area_of(ring: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(ring) - 1):
        total += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(total) / 2


def centroid_of(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """Titik pusat massa poligon; jatuh kembali ke rata-rata bila luasnya nol."""
    cx = cy = signed = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = x1 * y2 - x2 * y1
        signed += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(signed) < 1e-12:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    return (cx / (3 * signed), cy / (3 * signed))


def main() -> None:
    print("Mengambil batas wilayah dari OpenStreetMap…", file=sys.stderr)

    ids = " ".join(f"rel({osm_id});" for osm_id in POLDA_METRO_JAYA)
    polda = overpass(f"[out:json][timeout:600];({ids});out geom;", "polda.json")
    kecamatan = overpass(
        f"[out:json][timeout:600];area(36{JAKARTA_SELATAN:08d})->.a;"
        'rel(area.a)["boundary"="administrative"]["admin_level"="6"];out geom;',
        "kecamatan.json",
    )
    kelurahan = overpass(
        f"[out:json][timeout:600];area(36{JAKARTA_SELATAN:08d})->.a;"
        'rel(area.a)["boundary"="administrative"]["admin_level"="7"];out geom;',
        "kelurahan.json",
    )

    # Proyeksi ditetapkan dari bentang SELURUH wilayah hukum, sehingga satu sistem koordinat
    # berlaku untuk ketiga lapisan.
    everything = [
        point
        for element in polda["elements"]
        for ring in rings_of(element)
        for point in ring
    ]
    lons = [p[0] for p in everything]
    lats = [p[1] for p in everything]
    reference_lat = (min(lats) + max(lats)) / 2
    cos_reference = math.cos(math.radians(reference_lat))
    origin_lon, origin_lat = min(lons), max(lats)

    def project(lon: float, lat: float) -> tuple[float, float]:
        x = (lon - origin_lon) * cos_reference * EARTH_M_PER_DEG / METRES_PER_UNIT
        y = (origin_lat - lat) * EARTH_M_PER_DEG / METRES_PER_UNIT
        return (x, y)

    def build(
        elements: list[dict], layer: str, names: dict[int, str] | None = None, raw: bool = False
    ) -> list[dict]:
        tolerance = 0.0 if raw else TOLERANCE_M[layer] / METRES_PER_UNIT
        shapes = []
        for element in elements:
            name = (names or {}).get(element["id"]) or element["tags"].get("name")
            if not name:
                continue
            rings = [[project(*point) for point in ring] for ring in rings_of(element)]
            if not rings:
                continue
            if tolerance > 0:
                rings = [simplify(ring, tolerance) for ring in rings]
            # Cincin yang tersisa kurang dari empat titik bukan lagi bidang.
            rings = [ring for ring in rings if len(ring) >= 4]
            if not rings:
                continue
            rings.sort(key=area_of, reverse=True)
            anchor = centroid_of(rings[0])
            shapes.append(
                {
                    "name": name,
                    "rings": rings if raw else [
                        [(round(x, 1), round(y, 1)) for x, y in ring] for ring in rings
                    ],
                    "label": (round(anchor[0], 1), round(anchor[1], 1)),
                }
            )
        shapes.sort(key=lambda s: s["name"])
        return shapes

    layers = {
        "polda": build(polda["elements"], "polda", POLDA_METRO_JAYA),
        "kecamatan": build(kecamatan["elements"], "kecamatan"),
        "kelurahan": build(kelurahan["elements"], "kelurahan"),
    }

    # Induk tiap kelurahan ditentukan dari geometrinya sendiri — titik pusatnya jatuh di
    # kecamatan yang mana — bukan dari tag OSM. Tag `is_in` sering kosong atau usang,
    # sedangkan bentuknya tidak bisa berbohong tentang letaknya.
    # Induk tiap kelurahan ditentukan dari SATU titik yang dijamin ada di dalamnya, diuji
    # terhadap kecamatan yang belum disederhanakan.
    #
    # Dua cara lain sudah dicoba dan gagal, dan kegagalannya pantas dicatat supaya tidak
    # diulang. Menghitung berapa banyak simpul kelurahan yang jatuh di tiap kecamatan
    # terdengar lebih teliti, tetapi kelurahan bertetangga berbagi ratusan simpul yang
    # letaknya PERSIS di garis batas, dan uji pancaran sinar pada titik tepat di garis
    # hasilnya sembarang — "Bintaro" tercatat di Kebayoran Lama, padahal ia di Pesanggrahan.
    # Menanyakannya kepada Overpass satu per satu benar, tetapi sepuluh kueri beruntun
    # ditolak karena pembatasan laju.
    #
    # Hasilnya diperiksa silang dengan tag `wikipedia` OSM, yang berbentuk
    # "id:Duren Tiga, Pancoran, Jakarta Selatan" — komponen keduanya adalah kecamatan.
    # Tag itu ada pada 48 dari 65 kelurahan; ketidakcocokan menghentikan pembangunan.
    raw_kecamatan = build(kecamatan["elements"], "kecamatan", raw=True)
    raw_kelurahan = {s["name"]: s for s in build(kelurahan["elements"], "kelurahan", raw=True)}

    declared = {}
    for element in kelurahan["elements"]:
        parts = [p.strip() for p in element["tags"].get("wikipedia", "").split(",")]
        if len(parts) >= 3 and element["tags"].get("name"):
            declared[element["tags"]["name"]] = parts[1]

    mismatch = []
    for kelurahan_shape in layers["kelurahan"]:
        name = kelurahan_shape["name"]
        anchor = interior_point(raw_kelurahan[name]["rings"][0])
        parent = next(
            (
                candidate["name"]
                for candidate in raw_kecamatan
                if any(inside(anchor, ring) for ring in candidate["rings"])
            ),
            None,
        )
        if parent is None:
            raise SystemExit(f"kelurahan {name!r} tidak jatuh di kecamatan mana pun")
        if name in declared and declared[name] != parent:
            mismatch.append(f"{name}: geometri={parent} wikipedia={declared[name]}")
        kelurahan_shape["parent"] = parent

    if mismatch:
        raise SystemExit("induk kelurahan tidak cocok dengan tag OSM:\n  " + "\n  ".join(mismatch))
    print(f"  induk kelurahan cocok dengan tag OSM pada {len(declared)}/65", file=sys.stderr)

    orphan = {s["parent"] for s in layers["kelurahan"]}
    print(f"  kelurahan terpetakan ke {len(orphan)} kecamatan", file=sys.stderr)

    for layer, shapes in layers.items():
        points = sum(len(ring) for shape in shapes for ring in shape["rings"])
        print(f"  {layer}: {len(shapes)} wilayah, {points} titik", file=sys.stderr)

    OUTPUT.write_text(
        render(
            layers,
            {
                "referenceLatitude": reference_lat,
                "cosReferenceLatitude": cos_reference,
                "originLongitude": origin_lon,
                "originLatitude": origin_lat,
                "metresPerDegree": EARTH_M_PER_DEG,
                "metresPerUnit": METRES_PER_UNIT,
            },
        )
    )
    print(f"Ditulis ke {OUTPUT.relative_to(ROOT)}", file=sys.stderr)


def render(layers: dict[str, list[dict]], projection: dict[str, float]) -> str:
    def shape_literal(shape: dict) -> str:
        rings = ",".join(
            "[" + ",".join(f"[{x},{y}]" for x, y in ring) + "]" for ring in shape["rings"]
        )
        parent = (
            f', parent: {json.dumps(shape["parent"], ensure_ascii=False)}'
            if "parent" in shape
            else ""
        )
        return (
            f'  {{ name: {json.dumps(shape["name"], ensure_ascii=False)}{parent}, '
            f"label: [{shape['label'][0]},{shape['label'][1]}], rings: [{rings}] }},"
        )

    blocks = []
    for layer, shapes in layers.items():
        body = "\n".join(shape_literal(shape) for shape in shapes)
        blocks.append(
            f"export const {layer.upper()}_SHAPES: readonly AreaShape[] = [\n{body}\n];"
        )

    projection_literal = (
        "{\n"
        + "".join(f"  {key}: {value!r},\n" for key, value in projection.items())
        + "}"
    )

    return f'''// DIBANGKITKAN OLEH scripts/bangun-batas-wilayah.py — JANGAN DISUNTING TANGAN.
//
// Sumber: OpenStreetMap lewat Overpass API, diambil {json.dumps(_today())}.
// Lisensi: ODbL 1.0. Karya yang menampilkannya wajib mencantumkan
// "© Kontributor OpenStreetMap" — atribusi itu digambar di kaki peta.
//
// Koordinat berada pada satu sistem untuk SELURUH lapisan: 1 satuan = 10 meter, sumbu Y
// menghadap ke bawah (mengikuti SVG). Menyelami peta hanya mengubah `viewBox`.

/** Satu wilayah pada peta. `rings` boleh lebih dari satu untuk wilayah kepulauan. */
export type AreaShape = {{
  readonly name: string;
  /** Kecamatan induk — hanya ada pada lapisan kelurahan. */
  readonly parent?: string;
  /** Titik jangkar label — pusat massa cincin terbesar. */
  readonly label: readonly [number, number];
  readonly rings: readonly (readonly (readonly [number, number])[])[];
}};

/**
 * Tetapan proyeksi. Dipakai untuk menaruh titik berkoordinat lintang/bujur — kejadian,
 * laporan warga — pada sistem koordinat yang sama dengan poligon di bawah.
 */
export const PROJECTION = {projection_literal} as const;

{chr(10).join(blocks)}
'''


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


if __name__ == "__main__":
    main()
