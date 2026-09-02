import Link from "next/link";
import { Panel } from "@/components/panel";
import type { AreaDetail, MapData } from "@/lib/map-data";
import type { HistoricalMonths, MapLayer } from "./area";
import { HISTORICAL_MONTH_LABELS, HISTORICAL_MONTHS, MAP_LAYERS, mapHref } from "./area";
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
  months,
}: {
  data: MapData;
  selected: string | null;
  detail: AreaDetail | null;
  layer: MapLayer;
  months: HistoricalMonths;
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
                href={mapHref(selected, option.id, months)}
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
              {layer === "historical"
                ? `${data.historical.windowFrom} s.d. ${data.historical.windowTo}`
                : layer === "current"
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

          {/* Pemilih jendela hanya muncul pada layer historis: menampilkannya di layer
              lain akan menjanjikan pengaruh yang tidak ada. */}
          {layer === "historical" ? (
            <nav aria-label="Jendela waktu historis" className="flex flex-wrap items-center gap-2">
              <span className="stat-label">Jendela</span>
              {HISTORICAL_MONTHS.map((option) => (
                <Link
                  key={option}
                  href={mapHref(selected, "historical", option)}
                  scroll={false}
                  aria-current={months === option ? "true" : undefined}
                  className={`rounded border px-2 py-0.5 text-[11px] transition-colors ${
                    months === option
                      ? "border-risk-high/60 bg-risk-high/10 text-risk-high"
                      : "border-base-800 text-ink-muted hover:text-ink"
                  }`}
                >
                  {HISTORICAL_MONTH_LABELS[option]}
                </Link>
              ))}
              {data.historical.observedFrom === null ? (
                <span className="text-[10px] text-ink-faint">
                  Tidak ada kejadian tercatat pada jendela ini
                </span>
              ) : (
                <span className="text-[10px] text-ink-faint">
                  Data ditemukan {data.historical.observedFrom} s.d. {data.historical.observedTo}
                </span>
              )}
            </nav>
          ) : null}

          <MapCanvas
            districts={data.districts}
            layer={layer}
            selected={selected}
            historical={data.historical}
            months={months}
          />

          <RiskLegend
            layer={layer}
            historical={{
              peakIncidents: data.historical.peakIncidents,
              totalIncidents: data.historical.totalIncidents,
            }}
          />

          <p className="text-[10px] leading-relaxed text-ink-faint">
            Bentuk wilayah pada peta ini adalah <strong>perkiraan</strong> yang diturunkan dari
            koordinat titik lokasi, <strong>bukan batas administratif resmi</strong>.
          </p>

          <p className="text-[10px] leading-relaxed text-ink-faint">
            {layer === "historical"
              ? data.historicalBasis
              : layer === "current"
                ? data.currentRiskBasis
                : data.predictiveBasis}
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
