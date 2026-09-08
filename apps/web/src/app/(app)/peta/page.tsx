import { EmptyState } from "@/components/data-state";
import { toHistoricalMonths, toMapLayer, toMapLevel } from "@/components/map/area";
import { RiskMap } from "@/components/map/risk-map";
import { Panel } from "@/components/panel";
import { getAreaDetail, getMapData, resolveSelectedDistrict } from "@/lib/map-data";

export const dynamic = "force-dynamic";

/**
 * Halaman peta wilayah (TASK 080–084).
 *
 * Seluruh warna dan angka berasal dari endpoint peta (`/map/historical`,
 * `/map/current-risk`, `/map/predictive-heatmap`, `/map/area/{kecamatan}`). Tidak ada nilai
 * yang ditanam di kode; yang ditanam hanyalah **bentuk** wilayah, dan itu pun dinyatakan
 * terbuka apa adanya (lihat `lib/wilayah.ts`).
 *
 * Wilayah terpilih (`?wilayah=`), layer (`?layer=`), jendela historis (`?bulan=`), dan
 * tingkat penyelaman (`?tingkat=`) adalah parameter alamat supaya
 * rinciannya diambil di server dan keadaan peta dapat dibagikan sebagai tautan saat
 * paparan. Nama wilayah yang tidak dikenal jatuh kembali ke wilayah berisiko tertinggi,
 * sehingga halaman tidak pernah terbuka kosong; nama yang dikenal tetapi di luar kewenangan
 * pengguna tetap terpilih dan dinyatakan "tidak ada rincian", bukan disembunyikan
 * (CLAUDE.md §15, §23).
 */
export default async function PetaPage({
  searchParams,
}: {
  searchParams: Promise<{
    wilayah?: string | string[];
    layer?: string | string[];
    bulan?: string | string[];
    tingkat?: string | string[];
  }>;
}) {
  const params = await searchParams;
  const requested = typeof params.wilayah === "string" ? params.wilayah : null;
  const layer = toMapLayer(typeof params.layer === "string" ? params.layer : null);
  const months = toHistoricalMonths(typeof params.bulan === "string" ? params.bulan : null);
  const level = toMapLevel(typeof params.tingkat === "string" ? params.tingkat : null);

  const data = await getMapData(undefined, months);
  const hasData = data.districts.some(
    (district) =>
      district.historical !== null || district.current !== null || district.predictive !== null,
  );

  if (!hasData) {
    return (
      <Panel title="Live Kamtibmas Map">
        <EmptyState label="Tidak ada penilaian risiko yang dapat ditampilkan untuk kewenangan Anda." />
      </Panel>
    );
  }

  const selected = resolveSelectedDistrict(data, requested);
  const detail = selected === null ? null : await getAreaDetail(selected);

  return (
    <RiskMap
      data={data}
      selected={selected}
      detail={detail}
      layer={layer}
      months={months}
      level={level}
    />
  );
}
