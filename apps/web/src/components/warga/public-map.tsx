"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { type AreaLevel, LEVEL_FILL } from "@/lib/warga";
import {
  type AreaShape,
  boundsOf,
  framingShapes,
  type MapLevel,
  polygonPoints,
  shapesAt,
  toPercent,
  viewBoxOf,
} from "@/lib/wilayah";

export type MapAreaDatum = { level: AreaLevel; total: number };

/**
 * Peta wilayah untuk warga — tiga warna, tanpa angka di atas peta.
 *
 * Bentuk wilayah dipakai bersama sisi kepolisian (`lib/wilayah`), tetapi yang digambar di
 * sini hanya tingkat RENDAH/SEDANG/TINGGI dari ringkasan publik. Tidak ada skor, prediksi,
 * maupun titik kejadian (keputusan pemilik proyek 2 November 2026). Setiap wilayah adalah
 * tautan: ketuk untuk membuka rinciannya di bawah peta.
 */
export function PublicMap({
  level,
  focus,
  data,
  selected,
  hrefPrefix,
  compact = false,
}: {
  level: MapLevel;
  focus?: string;
  data: ReadonlyMap<string, MapAreaDatum>;
  selected?: string | null;
  /** Awalan tautan; nama wilayah (ter-encode) ditempelkan di belakangnya. */
  hrefPrefix: string;
  compact?: boolean;
}) {
  const [active, setActive] = useState<string | null>(null);
  const shapes = useMemo(() => shapesAt(level, focus), [level, focus]);
  const bounds = useMemo(() => boundsOf(framingShapes(shapes)), [shapes]);
  const viewBox = useMemo(() => viewBoxOf(shapes, 0.04), [shapes]);
  const strokeWidth = Math.max(bounds.width, bounds.height) / 420;

  return (
    <div
      className="relative mx-auto w-full"
      style={{ aspectRatio: `${bounds.width} / ${bounds.height}` }}
    >
      {/* biome-ignore lint/a11y/useSemanticElements: peta SVG; tiap wilayah sudah tautan. */}
      <svg
        viewBox={viewBox}
        role="group"
        aria-label="Peta tingkat kerawanan per wilayah"
        className="h-full w-full"
      >
        {shapes.map((shape) => {
          const datum = data.get(shape.name);
          const isSelected = selected === shape.name;
          const isActive = active === shape.name;
          const fill = datum ? LEVEL_FILL[datum.level] : "rgb(170 165 152)";
          return (
            <Link
              key={shape.name}
              href={`${hrefPrefix}${encodeURIComponent(shape.name)}`}
              aria-label={`${shape.name}${datum ? `, kerawanan ${datum.level.toLowerCase()}` : ""}`}
              onMouseEnter={() => setActive(shape.name)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(shape.name)}
              onBlur={() => setActive(null)}
              scroll={false}
            >
              {shape.rings.map((ring) => (
                <polygon
                  key={`${shape.name}-${ring[0][0]},${ring[0][1]}`}
                  points={polygonPoints(ring)}
                  fill={fill}
                  fillOpacity={isSelected ? 0.85 : isActive ? 0.7 : 0.5}
                  stroke={isSelected ? "rgb(22 32 56)" : "white"}
                  strokeWidth={strokeWidth * (isSelected ? 2.5 : 1.2)}
                  strokeLinejoin="round"
                  className="cursor-pointer transition-[fill-opacity]"
                />
              ))}
            </Link>
          );
        })}
      </svg>
      {!compact
        ? shapes.map((shape) => <AreaLabel key={shape.name} shape={shape} bounds={bounds} />)
        : null}
    </div>
  );
}

function AreaLabel({ shape, bounds }: { shape: AreaShape; bounds: ReturnType<typeof boundsOf> }) {
  const { left, top } = toPercent(shape.label, bounds);
  return (
    <span
      aria-hidden="true"
      className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/85 px-1.5 py-0.5 text-[10px] font-semibold text-ink shadow-sm sm:text-[11px]"
      style={{ left, top }}
    >
      {shape.name}
    </span>
  );
}
