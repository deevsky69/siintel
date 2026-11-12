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
import { LevelBadge } from "./bits";

export type MapAreaDatum = { level: AreaLevel; total: number };

/**
 * Peta wilayah untuk warga — tiga warna, tanpa angka di atas peta.
 *
 * Bentuk wilayah dipakai bersama sisi kepolisian (`lib/wilayah`), tetapi yang digambar di
 * sini hanya tingkat RENDAH/SEDANG/TINGGI dari ringkasan publik. Tidak ada skor, prediksi,
 * maupun titik kejadian (keputusan pemilik proyek 2 November 2026). Setiap wilayah adalah
 * tautan: ketuk untuk membuka rinciannya.
 *
 * Dua tambahan untuk beranda (3 November 2026): `emphasis` meredupkan wilayah yang
 * tingkatnya berbeda dari yang dipilih (chip saring), dan `tip` menggambar kartu kecil di
 * jangkar label wilayah yang sedang disentuh atau difokus. Keduanya nilai biasa, bukan
 * fungsi, supaya komponen ini tetap dapat dipanggil dari Server Component.
 */
export function PublicMap({
  level,
  focus,
  data,
  selected,
  hrefPrefix,
  compact = false,
  emphasis = null,
  tip = false,
}: {
  level: MapLevel;
  focus?: string;
  data: ReadonlyMap<string, MapAreaDatum>;
  selected?: string | null;
  /** Awalan tautan; nama wilayah (ter-encode) ditempelkan di belakangnya. */
  hrefPrefix: string;
  compact?: boolean;
  /** Bila diisi, wilayah dengan tingkat lain diredupkan (transisi fill-opacity). */
  emphasis?: AreaLevel | null;
  /** Kartu kecil (nama, tingkat, jumlah) di atas wilayah yang disentuh/difokus. */
  tip?: boolean;
}) {
  const [active, setActive] = useState<string | null>(null);
  const shapes = useMemo(() => shapesAt(level, focus), [level, focus]);
  const bounds = useMemo(() => boundsOf(framingShapes(shapes)), [shapes]);
  const viewBox = useMemo(() => viewBoxOf(shapes, 0.04), [shapes]);
  const strokeWidth = Math.max(bounds.width, bounds.height) / 420;
  const activeShape = active ? shapes.find((shape) => shape.name === active) : undefined;

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
        className="h-full w-full overflow-visible"
      >
        {shapes.map((shape, index) => {
          const datum = data.get(shape.name);
          const isSelected = selected === shape.name;
          const isActive = active === shape.name;
          const dimmed = emphasis !== null && datum?.level !== emphasis;
          const fill = datum ? LEVEL_FILL[datum.level] : "rgb(170 165 152)";
          const opacity = dimmed ? 0.15 : isSelected ? 0.95 : isActive ? 0.9 : 0.7;
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
                  fillOpacity={opacity}
                  strokeWidth={strokeWidth * (isSelected ? 2.5 : 1.2)}
                  strokeLinejoin="round"
                  className={`warga-poly cursor-pointer${isSelected ? " is-selected" : ""}`}
                  style={{ animationDelay: `${Math.min(index, 40) * 35}ms` }}
                />
              ))}
            </Link>
          );
        })}
      </svg>
      {!compact
        ? shapes.map((shape) => (
            <AreaLabel
              key={shape.name}
              shape={shape}
              bounds={bounds}
              muted={emphasis !== null && data.get(shape.name)?.level !== emphasis}
            />
          ))
        : null}
      {tip && activeShape ? (
        <div
          className="warga-tip"
          style={toPercent(activeShape.label, bounds)}
          role="status"
          aria-live="polite"
        >
          <AreaTip name={activeShape.name} datum={data.get(activeShape.name)} />
        </div>
      ) : null}
    </div>
  );
}

function AreaLabel({
  shape,
  bounds,
  muted,
}: {
  shape: AreaShape;
  bounds: ReturnType<typeof boundsOf>;
  muted: boolean;
}) {
  const { left, top } = toPercent(shape.label, bounds);
  return (
    <span
      aria-hidden="true"
      className={`warga-map-label ${muted ? "opacity-30" : "opacity-100"}`}
      style={{ left, top }}
    >
      {shape.name}
    </span>
  );
}

function AreaTip({ name, datum }: { name: string; datum: MapAreaDatum | undefined }) {
  return (
    <>
      <span className="block text-xs font-bold text-ink">{name}</span>
      {datum ? (
        <span className="mt-0.5 flex items-center gap-2 text-[11px] text-ink-muted">
          <LevelBadge level={datum.level} />
          <span className="tabular-nums">{datum.total} kejadian</span>
        </span>
      ) : (
        <span className="text-[11px] text-ink-muted">belum ada data</span>
      )}
    </>
  );
}
