import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { toHistoricalMonths, toMapLayer, toMapLevel } from "@/components/map/area";
import { RiskMap } from "@/components/map/risk-map";
import { Panel } from "@/components/panel";
import {
  getAreaDetail,
  getKelurahanOverlay,
  getMapData,
  resolveSelectedDistrict,
} from "@/lib/map-data";
import { getPriorityKelurahan } from "@/lib/monthly-products";

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
    kelurahan?: string | string[];
  }>;
}) {
  const params = await searchParams;
  const requested = typeof params.wilayah === "string" ? params.wilayah : null;
  const layer = toMapLayer(typeof params.layer === "string" ? params.layer : null);
  const months = toHistoricalMonths(typeof params.bulan === "string" ? params.bulan : null);
  const level = toMapLevel(typeof params.tingkat === "string" ? params.tingkat : null);
  const selectedKelurahan =
    level === "kelurahan" && typeof params.kelurahan === "string" ? params.kelurahan : null;

  const [data, priority] = await Promise.all([
    getMapData(undefined, months),
    // Kelurahan prioritas bulan ini (produk bulanan terakhir yang ditetapkan Pimpinan);
    // kegagalan memuatnya tidak menjatuhkan peta.
    getPriorityKelurahan().catch(() => null),
  ]);
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
  const [detail, overlay] = await Promise.all([
    selected === null ? null : getAreaDetail(selected, selectedKelurahan),
    // Lapisan kelurahan hanya diminta saat peta memang diperbesar ke satu kecamatan.
    level === "kelurahan" && selected !== null
      ? getKelurahanOverlay(selected, undefined, months)
      : null,
  ]);

  return (
    <div className="space-y-3">
      {priority && priority.items.length > 0 ? (
        <Panel
          title={`Kelurahan prioritas ${priority.month}`}
          action={
            <Link href={`/ops/produk-bulanan?bulan=${priority.month}`} className="panel-action">
              Produk bulanan →
            </Link>
          }
        >
          <ul className="flex flex-wrap gap-2 text-xs">
            {priority.items.map((item) => (
              <li key={item.kelurahan}>
                <Link
                  href={`/ops/peta?wilayah=${encodeURIComponent(item.kecamatan)}&tingkat=kelurahan&kelurahan=${encodeURIComponent(item.kelurahan)}`}
                  className="inline-flex items-center gap-1.5 rounded border border-[#C1801E]/60 bg-[#C1801E]/10 px-2 py-1 text-ink"
                >
                  <span className="h-2 w-2 bg-[#C1801E]" aria-hidden="true" />
                  {item.kelurahan}
                  <span className="text-ink-faint">· {item.kecamatan}</span>
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-2xs text-ink-faint">
            Ditetapkan Pimpinan pada produk bulanan; digarisi emas pada peta tingkat kelurahan.
          </p>
        </Panel>
      ) : null}
      <RiskMap
        data={data}
        selected={selected}
        detail={detail}
        layer={layer}
        months={months}
        level={level}
        overlay={overlay}
        selectedKelurahan={selectedKelurahan}
        priority={priority?.items.map((item) => item.kelurahan) ?? []}
      />
    </div>
  );
}
