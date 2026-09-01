"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { DistrictShape } from "@/lib/geo";
import { KECAMATAN_SHAPES, MAP_VIEWBOX, polygonPoints, toPercent } from "@/lib/geo";
import type { MapDistrict } from "@/lib/map-data";
import { RISK_HEX, RISK_LABELS } from "@/lib/risk";
import type { MapLayer } from "./area";
import { mapHref, PREDICTIVE_HEX, predictiveOpacity, toRiskClass } from "./area";

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
 * Dua layer digambar dengan cara yang berbeda **dengan sengaja**:
 *
 * - `current` — diwarnai menurut `risk_class` yang dikirim backend. Kelas tidak pernah
 *   dihitung ulang di sini (CLAUDE.md §12).
 * - `predictive` — prediksi **tidak menyimpan kelas risiko** dan tidak diberi kelas oleh
 *   API, karena ambangnya masih DEMO / PROPOSED (U-01). Layer ini karenanya memakai satu
 *   warna dengan kepekatan mengikuti skor, bukan tangga warna risiko, dan layar
 *   menyatakan bahwa yang ditampilkan adalah skor mentah tanpa kelas resmi.
 */

/** Warna wilayah tanpa data — sewarna garis panel, jelas berbeda dari tangga risiko. */
const NO_DATA_FILL = "#132339";

/** Skor wilayah pada layer yang sedang ditampilkan; `null` bila tidak ada data. */
export function layerScore(district: MapDistrict, layer: MapLayer): number | null {
  const area = layer === "current" ? district.current : district.predictive;
  return area?.risk_score ?? null;
}

/**
 * Keterangan ringkas satu wilayah — dipakai tooltip.
 *
 * Pada layer prediktif keterangan berhenti di angka: menyebut kelas di sini akan
 * mengarang kelas yang tidak dikirim API.
 */
export function districtSummary(district: MapDistrict, layer: MapLayer): string {
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
  if (layer === "predictive") return district.predictive ? PREDICTIVE_HEX : NO_DATA_FILL;

  const risk = toRiskClass(district.current?.risk_class ?? null);
  return risk ? RISK_HEX[risk] : NO_DATA_FILL;
}

function opacityOf(
  district: MapDistrict | undefined,
  layer: MapLayer,
  emphasis: "selected" | "active" | "rest",
): number {
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
}: {
  districts: MapDistrict[];
  layer: MapLayer;
  selected: string | null;
  className?: string;
  /** Angka besar di tengah wilayah; dapat dimatikan bila ruangnya sempit. */
  showScores?: boolean;
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
          layer === "predictive"
            ? "Peta skor prediksi kamtibmas per kecamatan"
            : "Peta risiko kamtibmas per kecamatan"
        }
        className={className}
      >
        {KECAMATAN_SHAPES.map((shape) => {
          const district = byName.get(shape.kecamatan);
          const isSelected = selected === shape.kecamatan;
          const isActive = active === shape.kecamatan;
          const score = district ? layerScore(district, layer) : null;

          return (
            <g key={shape.kecamatan}>
              <Link
                href={mapHref(shape.kecamatan, layer)}
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
                  )}
                  stroke={isSelected ? "#22d3ee" : isActive ? "#67e8f9" : "#050b18"}
                  strokeWidth={isSelected || isActive ? 6 : 3}
                  strokeLinejoin="round"
                />
              </Link>
              <text
                x={shape.label[0]}
                y={shape.label[1]}
                textAnchor="middle"
                pointerEvents="none"
                className="fill-ink font-heading"
                fontSize={26}
                fontWeight={600}
              >
                {shape.kecamatan}
              </text>
              {showScores ? (
                <text
                  x={shape.label[0]}
                  y={shape.label[1] + 40}
                  textAnchor="middle"
                  pointerEvents="none"
                  fontSize={34}
                  fontWeight={700}
                  fill={score === null ? "#5b7796" : "#e6f0ff"}
                >
                  {score ?? "—"}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>

      {hoveredShape && hovered ? (
        <div
          // Tooltip hanya penguat visual: keterangan yang sama sudah ada pada
          // `aria-label` tiap wilayah, sehingga pembaca layar tidak kehilangan apa pun.
          aria-hidden="true"
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[135%] whitespace-nowrap rounded border border-base-700 bg-base-950/95 px-2.5 py-1.5 shadow-panel"
          style={toPercent(hoveredShape.label)}
        >
          <p className="font-heading text-xs font-semibold text-ink">{hoveredShape.kecamatan}</p>
          <p className="font-mono text-[11px] text-ink-muted">{districtSummary(hovered, layer)}</p>
        </div>
      ) : null}
    </div>
  );
}
