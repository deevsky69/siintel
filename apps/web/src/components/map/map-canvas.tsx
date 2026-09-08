"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { DistrictShape } from "@/lib/geo";
import {
  isWithinMap,
  KECAMATAN_SHAPES,
  MAP_VIEWBOX,
  polygonPoints,
  projectLatLon,
  toPercent,
} from "@/lib/geo";
import type { HistoricalPoint, MapDistrict } from "@/lib/map-data";
import { RISK_HEX, RISK_LABELS } from "@/lib/risk";
import type { HistoricalMonths, MapLayer } from "./area";
import {
  DEFAULT_HISTORICAL_MONTHS,
  HISTORICAL_HEX,
  historicalOpacity,
  mapHref,
  PREDICTIVE_HEX,
  pointRadius,
  predictiveOpacity,
  toRiskClass,
} from "./area";

/**
 * Bidang gambar peta — dipakai halaman peta maupun panel ringkas dashboard.
 *
 * Wilayah digambar sebagai SVG, tanpa tile server dan tanpa pustaka peta. Setiap wilayah
 * adalah **tautan sungguhan** ke `/peta?wilayah=…`, sehingga pilihan dapat disalin,
 * dibuka di tab lain, dan dibagikan saat paparan. Menyorot dengan tetikus atau papan ketik
 * tidak memuat ulang apa pun; hanya klik yang mengubah alamat.
 *
 * Ini satu-satunya bagian peta yang berjalan di peramban, semata karena wilayah yang
 * sedang disorot adalah keadaan sesaat yang tidak pantas masuk ke alamat.
 *
 * Tiga layer digambar dengan cara yang berbeda **dengan sengaja**:
 *
 * - `historical` — **cacah kejadian**, bukan skor. Diwarnai kuning-jingga dengan kepekatan
 *   relatif terhadap wilayah terbanyak pada jendela yang tampil, sebab cacah tidak punya
 *   kelas dan tidak boleh diberi satu pun di sini. Hanya layer ini yang menggambar titik.
 * - `current` — diwarnai menurut `risk_class` yang dikirim backend. Kelas tidak pernah
 *   dihitung ulang di sini (CLAUDE.md §12).
 * - `predictive` — prediksi **tidak menyimpan kelas risiko** dan tidak diberi kelas oleh
 *   API, karena ambangnya masih DEMO / PROPOSED (U-01). Layer ini karenanya memakai satu
 *   warna dengan kepekatan mengikuti skor, bukan tangga warna risiko, dan layar
 *   menyatakan bahwa yang ditampilkan adalah skor mentah tanpa kelas resmi.
 *
 * Ketiganya memakai warna yang berjauhan supaya tidak ada layer yang terbaca sebagai
 * layer lain saat dipandang sekilas dari kursi belakang ruang paparan.
 */

/** Warna wilayah tanpa data — sewarna garis panel, jelas berbeda dari tangga risiko. */
// Warna peta menunjuk variabel tema. Peta adalah satu-satunya tempat warna digambar
// lewat atribut SVG dan bukan kelas Tailwind, jadi ia perlu rujukannya sendiri.
const NO_DATA_FILL = "rgb(var(--line))";
const EDGE = "rgb(var(--surface-app))";
const EDGE_SELECTED = "rgb(var(--accent))";
const EDGE_ACTIVE = "rgb(var(--accent-soft))";
const LABEL_TEXT = "rgb(var(--text))";
const LABEL_TEXT_MUTED = "rgb(var(--text-faint))";

/**
 * Angka besar di tengah wilayah pada layer yang sedang tampil; `null` bila tidak ada data.
 *
 * Pada layer historis angka ini adalah **cacah kejadian**, bukan skor 0–100. Keduanya
 * digambar di tempat yang sama, jadi satuannya dinyatakan di legenda dan di tooltip —
 * angka telanjang 214 dan 78 mustahil dibedakan hanya dari rupanya.
 */
export function layerValue(district: MapDistrict, layer: MapLayer): number | null {
  if (layer === "historical") return district.historical?.incidents ?? null;
  const area = layer === "current" ? district.current : district.predictive;
  return area?.risk_score ?? null;
}

/**
 * Isi tooltip saat kursor melewati satu wilayah.
 *
 * Aturannya diambil dari cara aplikasi pemantauan lain menyusun tooltip peta — Grafana
 * Geomap, ArcGIS Dashboards, Datadog, ESRI Operations Dashboard: **cukup untuk memutuskan
 * apakah perlu diklik, tidak lebih.** Susunannya seragam di mana-mana:
 *
 * ```text
 * identitas  →  angka utama  →  status  →  satu pembanding  →  isyarat klik
 * ```
 *
 * Tiga hal yang sengaja TIDAK masuk ke sini:
 *
 * 1. **Apa pun yang harus diklik.** Tooltip mengikuti kursor dan hilang begitu kursor
 *    bergeser; tautan di dalamnya mustahil diraih. Karena itu seluruh lapisannya
 *    `pointer-events-none`.
 * 2. **Rincian lengkap.** Riwayat, daftar prediksi, dan peringatan aktif adalah isi panel
 *    **klik**. Menaruhnya di hover membuat kotak yang menutupi peta yang sedang dibaca.
 * 3. **Angka yang menuntut pembanding.** Satu angka tanpa acuan tidak dapat dinilai
 *    sekilas, dan tooltip tidak punya ruang untuk menjelaskan acuannya.
 */
export type TooltipRow = { label: string; value: string };

export function tooltipRows(district: MapDistrict, layer: MapLayer): TooltipRow[] {
  if (layer === "historical") {
    const area = district.historical;
    if (!area) return [{ label: "Kejadian", value: "tidak ada catatan" }];
    const dominant = area.by_threat_type[0];
    return [
      { label: "Kejadian", value: `${area.incidents}` },
      ...(dominant
        ? [{ label: "Terbanyak", value: `${dominant.threat_type} (${dominant.incidents})` }]
        : []),
    ];
  }

  if (layer === "predictive") {
    const area = district.predictive;
    if (!area) return [{ label: "Prediksi", value: "tidak ada" }];
    return [
      { label: "Skor prediksi", value: `${area.risk_score}/100` },
      { label: "Ancaman", value: area.threat_type },
      ...(area.time_window ? [{ label: "Jendela", value: area.time_window }] : []),
      // Prediksi tidak berkelas (U-01), dan ketiadaannya disebut supaya tidak terbaca
      // sebagai kelas yang kebetulan tidak muat.
      { label: "Kelas", value: "belum ditetapkan" },
    ];
  }

  const area = district.current;
  if (!area) return [{ label: "Risiko", value: "tidak ada data" }];
  const risk = toRiskClass(area.risk_class);
  const dominant = area.threats[0];
  return [
    { label: "Skor risiko", value: `${area.risk_score}/100` },
    ...(risk ? [{ label: "Kelas", value: RISK_LABELS[risk] }] : []),
    ...(dominant ? [{ label: "Ancaman utama", value: dominant.threat_type }] : []),
    ...(dominant?.time_window ? [{ label: "Jam rawan", value: dominant.time_window }] : []),
  ];
}

/**
 * Keterangan ringkas satu wilayah — dipakai panel ringkas dan pembaca layar.
 *
 * Pada layer prediktif keterangan berhenti di angka: menyebut kelas di sini akan
 * mengarang kelas yang tidak dikirim API.
 */
export function districtSummary(district: MapDistrict, layer: MapLayer): string {
  if (layer === "historical") {
    const incidents = district.historical?.incidents;
    if (incidents === undefined) return "tidak ada kejadian tercatat";
    const dominant = district.historical?.by_threat_type[0];
    return dominant
      ? `${incidents} kejadian · terbanyak ${dominant.threat_type}`
      : `${incidents} kejadian`;
  }

  if (layer === "predictive") {
    const score = district.predictive?.risk_score;
    if (score === undefined) return "tidak ada prediksi";
    return `${score}/100 · skor prediksi, tanpa kelas`;
  }

  const area = district.current;
  if (!area) return "tidak ada data";
  const risk = toRiskClass(area.risk_class);
  return risk ? `${area.risk_score}/100 · ${RISK_LABELS[risk]}` : `${area.risk_score}/100`;
}

function ariaLabel(shape: DistrictShape, district: MapDistrict | undefined, layer: MapLayer) {
  if (!district) return `${shape.kecamatan} — tidak ada data`;

  if (layer === "historical") {
    const incidents = district.historical?.incidents;
    if (incidents === undefined) return `${shape.kecamatan} — tidak ada kejadian tercatat`;
    return `${shape.kecamatan} — ${incidents} kejadian pada jendela yang ditampilkan`;
  }

  if (layer === "predictive") {
    const area = district.predictive;
    if (!area) return `${shape.kecamatan} — tidak ada prediksi`;
    return `${shape.kecamatan} — skor prediksi ${area.risk_score} dari 100, tanpa kelas risiko`;
  }

  const area = district.current;
  if (!area) return `${shape.kecamatan} — tidak ada data risiko`;
  const risk = toRiskClass(area.risk_class);
  return risk
    ? `${shape.kecamatan} — skor risiko ${area.risk_score} dari 100, kelas ${RISK_LABELS[risk]}`
    : `${shape.kecamatan} — skor risiko ${area.risk_score} dari 100, kelas tidak dikenali`;
}

function fillOf(district: MapDistrict | undefined, layer: MapLayer): string {
  if (!district) return NO_DATA_FILL;
  if (layer === "historical") return district.historical ? HISTORICAL_HEX : NO_DATA_FILL;
  if (layer === "predictive") return district.predictive ? PREDICTIVE_HEX : NO_DATA_FILL;

  const risk = toRiskClass(district.current?.risk_class ?? null);
  return risk ? RISK_HEX[risk] : NO_DATA_FILL;
}

function opacityOf(
  district: MapDistrict | undefined,
  layer: MapLayer,
  emphasis: "selected" | "active" | "rest",
  peakIncidents = 0,
): number {
  // Sama seperti layer prediktif: kepekatan sedang memikul nilai, jadi penyorotan hanya
  // menambah sedikit dan sisanya dikerjakan garis tepi.
  if (layer === "historical" && district?.historical) {
    const base = historicalOpacity(district.historical.incidents, peakIncidents);
    return emphasis === "selected" ? Math.min(1, base + 0.12) : base;
  }

  // Layer prediktif memakai kepekatan sebagai skala nilai, jadi penyorotan tidak boleh
  // menimpanya; wilayah terpilih hanya dipertegas sedikit dan selebihnya oleh garis tepi.
  if (layer === "predictive" && district?.predictive) {
    const base = predictiveOpacity(district.predictive.risk_score);
    return emphasis === "selected" ? Math.min(1, base + 0.12) : base;
  }
  return emphasis === "selected" ? 0.85 : emphasis === "active" ? 0.68 : 0.45;
}

export function MapCanvas({
  districts,
  layer,
  selected,
  className = "mx-auto max-h-[62vh] w-full",
  showScores = true,
  historical,
  months = DEFAULT_HISTORICAL_MONTHS,
  linkTo = "map",
}: {
  districts: MapDistrict[];
  layer: MapLayer;
  selected: string | null;
  className?: string;
  /** Angka besar di tengah wilayah; dapat dimatikan bila ruangnya sempit. */
  showScores?: boolean;
  /**
   * Titik lokasi dan puncak cacah untuk layer historis.
   *
   * Opsional karena panel ringkas dashboard memakai bidang gambar yang sama tanpa pernah
   * menampilkan layer historis. Bila layer historis diminta tanpa data ini, wilayah tetap
   * digambar dan titiknya saja yang tidak muncul — bukan halaman yang gagal.
   */
  historical?: { points: HistoricalPoint[]; peakIncidents: number; peakPointIncidents: number };
  months?: HistoricalMonths;
  /**
   * Ke mana klik pada sebuah wilayah membawa pembaca.
   *
   * Berupa **kata kunci, bukan fungsi**, dan itu bukan pilihan gaya. Komponen ini berjalan
   * di peramban (`"use client"`), sedangkan pemanggilnya adalah komponen server; React
   * tidak dapat mengirim fungsi melintasi batas itu, dan permintaan gagal dengan 500 saat
   * dijalankan — bukan saat build, bukan saat test. Kata kunci ini dapat diserialkan, jadi
   * penyusunan alamatnya dikerjakan di sini, di sisi yang memang berjalan di peramban.
   *
   * - `map` — memilih wilayah pada halaman peta, membawa serta layer dan jendelanya;
   * - `home` — membuka rincian di beranda tanpa meninggalkan halamannya.
   */
  linkTo?: "map" | "home";
}) {
  const byName = useMemo(
    () => new Map(districts.map((district) => [district.kecamatan, district])),
    [districts],
  );

  /** Wilayah yang sedang disentuh tetikus **atau** sedang menerima fokus papan ketik. */
  const [active, setActive] = useState<string | null>(null);
  const hovered = active === null ? undefined : byName.get(active);
  const hoveredShape = KECAMATAN_SHAPES.find((shape) => shape.kecamatan === active);

  return (
    <div className="relative">
      {/* biome-ignore lint/a11y/useSemanticElements: peta adalah SVG; tidak ada
          elemen HTML semantik yang dapat menggantikan wadah wilayah di dalamnya. */}
      <svg
        viewBox={`0 0 ${MAP_VIEWBOX.width} ${MAP_VIEWBOX.height}`}
        role="group"
        aria-label={
          layer === "historical"
            ? "Peta cacah kejadian kamtibmas per kecamatan"
            : layer === "predictive"
              ? "Peta skor prediksi kamtibmas per kecamatan"
              : "Peta risiko kamtibmas per kecamatan"
        }
        className={className}
      >
        {KECAMATAN_SHAPES.map((shape) => {
          const district = byName.get(shape.kecamatan);
          const isSelected = selected === shape.kecamatan;
          const isActive = active === shape.kecamatan;
          const score = district ? layerValue(district, layer) : null;

          return (
            <g key={shape.kecamatan}>
              <Link
                href={
                  linkTo === "home"
                    ? `/?wilayah=${encodeURIComponent(shape.kecamatan)}`
                    : mapHref(shape.kecamatan, layer, months)
                }
                scroll={false}
                aria-label={ariaLabel(shape, district, layer)}
                aria-current={isSelected ? "true" : undefined}
                onMouseEnter={() => setActive(shape.kecamatan)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(shape.kecamatan)}
                onBlur={() => setActive(null)}
              >
                <polygon
                  points={polygonPoints(shape)}
                  className="cursor-pointer transition-[fill-opacity]"
                  fill={fillOf(district, layer)}
                  fillOpacity={opacityOf(
                    district,
                    layer,
                    isSelected ? "selected" : isActive ? "active" : "rest",
                    historical?.peakIncidents ?? 0,
                  )}
                  stroke={isSelected ? EDGE_SELECTED : isActive ? EDGE_ACTIVE : EDGE}
                  strokeWidth={isSelected || isActive ? 6 : 3}
                  strokeLinejoin="round"
                />
              </Link>
            </g>
          );
        })}
        {/* Titik kejadian digambar setelah seluruh wilayah supaya tidak tertimpa poligon
            tetangga, dan `pointerEvents="none"` supaya klik tetap mengenai wilayah di
            bawahnya — titik bukan tautan, wilayah tetap satu-satunya sasaran.

            Lingkarannya tidak membawa teks dan tidak dapat difokus, jadi tidak ada yang
            perlu disembunyikan dari pembaca layar: keterangan yang sama sudah dibawa
            `aria-label` tiap wilayah dan panel rincian. */}
        {layer === "historical" && historical ? (
          <g pointerEvents="none">
            {historical.points.map((point) => {
              const position = projectLatLon(point.latitude, point.longitude);
              // Titik di luar bidang gambar dibuang, bukan dijepitkan ke tepi: menjepitkan
              // akan menaruhnya di wilayah yang bukan wilayahnya.
              if (!isWithinMap(position)) return null;
              const radius = pointRadius(point.incidents, historical.peakPointIncidents);

              return (
                <circle
                  key={point.location_code}
                  cx={position[0]}
                  cy={position[1]}
                  r={radius}
                  fill={HISTORICAL_HEX}
                  fillOpacity={0.55}
                  stroke={EDGE}
                  strokeWidth={2}
                />
              );
            })}
          </g>
        ) : null}
      </svg>

      {/*
        Nama wilayah dan skornya digambar sebagai HTML di ATAS peta, bukan sebagai <text>
        di dalamnya.

        Alasannya ukuran huruf. Di dalam SVG, `font-size` adalah satuan gambar yang ikut
        mengecil bersama viewBox: label 26 satuan pada bidang selebar 1000 yang dipaksa
        masuk ke panel selebar 316 piksel tergambar 8,2 piksel — dan tetap 8,2 piksel di
        layar mana pun, karena petanya selalu menyesuaikan lebar induknya. Tidak ada nilai
        yang benar untuk semua ukuran layar.

        Sebagai HTML, ukurannya piksel sungguhan: sama terbacanya di ponsel dan di layar
        lebar. `pointer-events-none` menjaga klik tetap mengenai wilayah di bawahnya.
      */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        {KECAMATAN_SHAPES.map((shape) => {
          const district = byName.get(shape.kecamatan);
          const score = district ? layerValue(district, layer) : null;

          return (
            <div
              key={shape.kecamatan}
              className="absolute -translate-x-1/2 -translate-y-1/2 text-center leading-tight"
              style={toPercent(shape.label)}
            >
              <div className="font-heading text-2xs font-semibold text-ink drop-shadow-[0_1px_2px_rgb(var(--surface-app))] sm:text-xs">
                {shape.kecamatan}
              </div>
              {showScores ? (
                <div
                  className={`font-heading text-sm font-bold drop-shadow-[0_1px_2px_rgb(var(--surface-app))] sm:text-base ${
                    score === null ? "text-ink-faint" : "text-ink"
                  }`}
                >
                  {score ?? "—"}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {hoveredShape && hovered ? (
        <div
          // Tooltip hanya penguat visual: keterangan yang sama sudah ada pada
          // `aria-label` tiap wilayah, sehingga pembaca layar tidak kehilangan apa pun.
          aria-hidden="true"
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[135%] whitespace-nowrap rounded border border-base-700 bg-base-950/95 px-2.5 py-1.5 shadow-panel"
          style={toPercent(hoveredShape.label)}
        >
          <p className="font-heading text-xs font-semibold text-ink">{hoveredShape.kecamatan}</p>
          <dl className="mt-1 space-y-0.5">
            {tooltipRows(hovered, layer).map((row) => (
              <div key={row.label} className="flex items-baseline gap-3">
                <dt className="text-2xs text-ink-faint">{row.label}</dt>
                <dd className="ml-auto font-mono text-xs text-ink">{row.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-1.5 border-t border-base-800 pt-1 text-2xs uppercase tracking-wider text-ink-faint">
            Klik untuk rincian
          </p>
        </div>
      ) : null}
    </div>
  );
}
