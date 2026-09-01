"use client";

import { useMemo, useState } from "react";
import { Panel } from "@/components/panel";
import type { DistrictShape } from "@/lib/geo";
import { KECAMATAN_SHAPES, MAP_VIEWBOX, polygonPoints, toPercent } from "@/lib/geo";
import type { DistrictIntel, MapData } from "@/lib/map-data";
import { RISK_HEX, RISK_LABELS, riskClassOf } from "@/lib/risk";
import { DistrictDetail } from "./district-detail";
import { RiskLegend } from "./legend";

/**
 * Peta risiko kecamatan — digambar sebagai SVG, tanpa tile server dan tanpa pustaka peta.
 *
 * Warna tiap wilayah berasal dari skor risiko yang dikirim API; wilayah tanpa data dibiarkan
 * abu-abu dan menyatakan "tidak ada data", bukan diberi angka nol. Bentuk wilayah adalah
 * perkiraan (lihat `lib/geo.ts`), sehingga hal itu dinyatakan terbuka di layar.
 */

/** Warna wilayah tanpa data — sewarna garis panel, jelas berbeda dari tangga risiko. */
const NO_DATA_FILL = "#132339";

function label(district: DistrictIntel | undefined): string {
  if (!district || district.riskScore === null) return "tidak ada data";
  return `${district.riskScore}/100 · ${RISK_LABELS[riskClassOf(district.riskScore)]}`;
}

function ariaLabel(shape: DistrictShape, district: DistrictIntel | undefined): string {
  if (!district || district.riskScore === null) {
    return `${shape.kecamatan} — tidak ada data risiko`;
  }
  const risk = riskClassOf(district.riskScore);
  return `${shape.kecamatan} — skor risiko ${district.riskScore} dari 100, kelas ${RISK_LABELS[risk]}`;
}

export function RiskMap({ data }: { data: MapData }) {
  const byName = useMemo(
    () => new Map(data.districts.map((district) => [district.kecamatan, district])),
    [data.districts],
  );

  // Pilihan awal jatuh ke wilayah berisiko tertinggi yang memang punya data, supaya panel
  // rincian langsung berisi sesuatu dan tidak membuka paparan dengan layar kosong.
  const initial = useMemo(() => {
    const scored = data.districts.filter((district) => district.riskScore !== null);
    return scored.reduce<DistrictIntel | null>(
      (best, district) =>
        best === null || (district.riskScore ?? 0) > (best.riskScore ?? 0) ? district : best,
      null,
    );
  }, [data.districts]);

  const [selected, setSelected] = useState<string | null>(initial?.kecamatan ?? null);
  /** Wilayah yang sedang disentuh tetikus **atau** sedang menerima fokus papan ketik. */
  const [active, setActive] = useState<string | null>(null);

  const hovered = active === null ? undefined : byName.get(active);
  const hoveredShape = KECAMATAN_SHAPES.find((shape) => shape.kecamatan === active);

  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="col-span-12 xl:col-span-7">
        <Panel
          title="Live Kamtibmas Map"
          action={
            <span className="text-[10px] uppercase tracking-wider text-ink-faint">
              9 Kecamatan · Polres Metro Jakarta Selatan
            </span>
          }
          bodyClassName="flex flex-col gap-3"
        >
          <div className="relative">
            {/* biome-ignore lint/a11y/useSemanticElements: peta adalah SVG; tidak ada
                elemen HTML semantik yang dapat menggantikan wadah wilayah di dalamnya. */}
            <svg
              viewBox={`0 0 ${MAP_VIEWBOX.width} ${MAP_VIEWBOX.height}`}
              role="group"
              aria-label="Peta risiko kamtibmas per kecamatan"
              className="mx-auto max-h-[62vh] w-full"
            >
              {KECAMATAN_SHAPES.map((shape) => {
                const district = byName.get(shape.kecamatan);
                const risk =
                  district && district.riskScore !== null ? riskClassOf(district.riskScore) : null;
                const isSelected = selected === shape.kecamatan;
                const isActive = active === shape.kecamatan;

                return (
                  <g key={shape.kecamatan}>
                    {/* biome-ignore lint/a11y/useSemanticElements: <button> tidak dapat
                        berada di dalam <svg>. Wilayah tetap dapat difokus (tabIndex),
                        punya label, dan menanggapi Enter/Spasi seperti tombol. */}
                    <polygon
                      points={polygonPoints(shape)}
                      role="button"
                      tabIndex={0}
                      aria-label={ariaLabel(shape, district)}
                      aria-pressed={isSelected}
                      className="cursor-pointer transition-[fill-opacity]"
                      fill={risk ? RISK_HEX[risk] : NO_DATA_FILL}
                      fillOpacity={isSelected ? 0.85 : isActive ? 0.68 : 0.45}
                      stroke={isSelected ? "#22d3ee" : isActive ? "#67e8f9" : "#050b18"}
                      strokeWidth={isSelected || isActive ? 6 : 3}
                      strokeLinejoin="round"
                      onClick={() => setSelected(shape.kecamatan)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelected(shape.kecamatan);
                        }
                      }}
                      onMouseEnter={() => setActive(shape.kecamatan)}
                      onMouseLeave={() => setActive(null)}
                      onFocus={() => setActive(shape.kecamatan)}
                      onBlur={() => setActive(null)}
                    />
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
                    <text
                      x={shape.label[0]}
                      y={shape.label[1] + 40}
                      textAnchor="middle"
                      pointerEvents="none"
                      fontSize={34}
                      fontWeight={700}
                      fill={district?.riskScore === null || !district ? "#5b7796" : "#e6f0ff"}
                    >
                      {district?.riskScore ?? "—"}
                    </text>
                  </g>
                );
              })}
            </svg>

            {hoveredShape ? (
              <div
                // Tooltip hanya penguat visual: keterangan yang sama sudah ada pada
                // `aria-label` tiap wilayah, sehingga pembaca layar tidak kehilangan apa pun.
                aria-hidden="true"
                className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[135%] whitespace-nowrap rounded border border-base-700 bg-base-950/95 px-2.5 py-1.5 shadow-panel"
                style={toPercent(hoveredShape.label)}
              >
                <p className="font-heading text-xs font-semibold text-ink">
                  {hoveredShape.kecamatan}
                </p>
                <p className="font-mono text-[11px] text-ink-muted">{label(hovered)}</p>
              </div>
            ) : null}
          </div>

          <RiskLegend />

          <p className="text-[10px] leading-relaxed text-ink-faint">
            Bentuk wilayah pada peta ini adalah <strong>perkiraan</strong> yang diturunkan dari
            koordinat titik lokasi, <strong>bukan batas administratif resmi</strong>. Warna
            menunjukkan skor risiko tertinggi wilayah pada tanggal penilaian terakhir.
          </p>
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-5">
        <Panel title="Potensi Ancaman Wilayah" className="h-full">
          <DistrictDetail
            district={selected ? (byName.get(selected) ?? null) : null}
            horizon={data.horizon}
            assessmentDate={data.assessmentDate}
            weightsVersion={data.weightsVersion}
          />
        </Panel>
      </div>
    </div>
  );
}
