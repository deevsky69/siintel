import { EmptyState } from "@/components/data-state";
import { RiskMap } from "@/components/map/risk-map";
import { Panel } from "@/components/panel";
import { getMapData } from "@/lib/map-data";

export const dynamic = "force-dynamic";

/**
 * Halaman peta wilayah (TASK 080–084).
 *
 * Seluruh warna dan angka pada peta berasal dari API `/risk-scores` dan `/predictions`.
 * Tidak ada nilai yang ditanam di kode; yang ditanam hanyalah **bentuk** wilayah, dan itu
 * pun dinyatakan terbuka sebagai perkiraan (lihat `lib/geo.ts`).
 */
export default async function PetaPage() {
  const data = await getMapData();
  const hasScores = data.districts.some((district) => district.riskScore !== null);

  if (!hasScores) {
    return (
      <Panel title="Live Kamtibmas Map">
        <EmptyState label="Tidak ada penilaian risiko yang dapat ditampilkan untuk kewenangan Anda." />
      </Panel>
    );
  }

  return <RiskMap data={data} />;
}
