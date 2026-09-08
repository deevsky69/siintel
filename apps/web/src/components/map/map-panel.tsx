import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import type { MapData } from "@/lib/map-data";
import { RISK_LABELS, RISK_TEXT } from "@/lib/risk";
import { mapHref, toRiskClass } from "./area";
import { RiskLegend } from "./legend";
import { MapCanvas } from "./map-canvas";

/**
 * Peta ringkas untuk dashboard.
 *
 * Dashboard adalah layar pertama saat paparan, jadi petanya harus menunjukkan sebaran
 * risiko yang sebenarnya — bukan tempat kosong yang menunggu dikerjakan. Yang ditampilkan
 * hanya layer risiko berjalan: pemilih layer dan panel rincian tetap menjadi milik halaman
 * `/peta`, dan setiap wilayah di sini adalah tautan langsung ke rinciannya di sana.
 */
export function MapPanel({ data }: { data: MapData }) {
  const scored = data.districts.filter((district) => district.current !== null);
  const top = scored.reduce<(typeof scored)[number] | null>(
    (best, district) =>
      best === null || (district.current?.risk_score ?? 0) > (best.current?.risk_score ?? 0)
        ? district
        : best,
    null,
  );
  const topRisk = toRiskClass(top?.current?.risk_class ?? null);

  return (
    <Panel
      title="Live Kamtibmas Map"
      className="h-full"
      bodyClassName="flex flex-col gap-3"
      action={
        <Link href="/peta" className="panel-action">
          Buka peta
        </Link>
      }
    >
      {scored.length === 0 ? (
        <EmptyState label="Tidak ada penilaian risiko yang dapat ditampilkan untuk kewenangan Anda." />
      ) : (
        <>
          <MapCanvas
            districts={data.districts}
            layer="current"
            selected={top?.kecamatan ?? null}
            maxHeight="46vh"
          />
          <RiskLegend />
          {top ? (
            <p className="text-xs text-ink-muted">
              Tertinggi:{" "}
              <Link
                href={mapHref(top.kecamatan)}
                className="font-heading font-semibold text-ink underline-offset-2 hover:underline"
              >
                {top.kecamatan}
              </Link>{" "}
              <span className={topRisk ? RISK_TEXT[topRisk] : "text-ink"}>
                {top.current?.risk_score}/100
                {topRisk ? ` · ${RISK_LABELS[topRisk]}` : ""}
              </span>
            </p>
          ) : null}
          <p className="text-2xs leading-relaxed text-ink-faint">{data.currentRiskBasis}</p>
        </>
      )}
    </Panel>
  );
}
