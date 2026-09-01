import Link from "next/link";
import { Panel } from "@/components/panel";
import type { AreaDetail, MapData } from "@/lib/map-data";
import type { MapLayer } from "./area";
import { MAP_LAYERS, mapHref } from "./area";
import { DistrictDetail } from "./district-detail";
import { RiskLegend } from "./legend";
import { MapCanvas } from "./map-canvas";

/**
 * Halaman peta: bidang gambar, pemilih layer, legenda, dan panel rincian wilayah.
 *
 * Wilayah terpilih **dan** layer adalah parameter alamat (`/peta?wilayah=Tebet&layer=…`),
 * bukan keadaan di dalam komponen: rinciannya diambil di server dan tautannya dapat
 * dibagikan saat paparan. Hanya penyorotan yang berjalan di peramban — lihat `MapCanvas`.
 */
export function RiskMap({
  data,
  selected,
  detail,
  layer,
}: {
  data: MapData;
  selected: string | null;
  detail: AreaDetail | null;
  layer: MapLayer;
}) {
  const district = data.districts.find((row) => row.kecamatan === selected) ?? null;

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
          <nav aria-label="Layer peta" className="flex flex-wrap items-center gap-2">
            {MAP_LAYERS.map((option) => (
              <Link
                key={option.id}
                href={mapHref(selected, option.id)}
                scroll={false}
                aria-current={layer === option.id ? "true" : undefined}
                className={`rounded border px-2.5 py-1 text-[11px] uppercase tracking-wider transition-colors ${
                  layer === option.id
                    ? "border-accent/60 bg-accent/10 text-accent"
                    : "border-base-800 text-ink-muted hover:text-ink"
                }`}
              >
                {option.label}
              </Link>
            ))}
            <span className="text-[10px] text-ink-faint">
              {layer === "current"
                ? data.assessmentDate
                  ? `Penilaian ${data.assessmentDate}`
                  : "Belum ada tanggal penilaian"
                : `Horizon ${data.horizon}`}
              {/* Versi bobot ikut tampil supaya pertanyaan "bobotnya dari mana"
                  dapat dijawab dari layar, bukan dari ingatan (CLAUDE.md §25). */}
              {layer === "current" && data.weightsVersion
                ? ` · bobot ${data.weightsVersion}`
                : null}
            </span>
          </nav>

          <MapCanvas districts={data.districts} layer={layer} selected={selected} />

          <RiskLegend layer={layer} />

          <p className="text-[10px] leading-relaxed text-ink-faint">
            Bentuk wilayah pada peta ini adalah <strong>perkiraan</strong> yang diturunkan dari
            koordinat titik lokasi, <strong>bukan batas administratif resmi</strong>.
          </p>

          <p className="text-[10px] leading-relaxed text-ink-faint">
            {layer === "current" ? data.currentRiskBasis : data.predictiveBasis}
          </p>
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-5">
        <Panel title="Potensi Ancaman Wilayah" className="h-full">
          <DistrictDetail district={district} detail={detail} horizon={data.horizon} />
        </Panel>
      </div>
    </div>
  );
}
