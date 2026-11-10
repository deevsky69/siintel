import { MapHero } from "@/components/leadership/map-hero";
import { toMapLevel } from "@/components/map/area";
import { type BoardInput, MonthlyBoard } from "@/components/monthly/board";
import { ApiError } from "@/lib/api";
import { getBulletins } from "@/lib/babin";
import { getProfile, getSummary } from "@/lib/dashboard";
import {
  getAreaDetail,
  getKelurahanOverlay,
  getMapData,
  resolveSelectedDistrict,
} from "@/lib/map-data";
import { getProduct, listProducts, type MonthlyProduct } from "@/lib/monthly-products";
import { getCitizenReports, getCrimes } from "@/lib/reports";

export const dynamic = "force-dynamic";

/**
 * Beranda (TASK 070, 150, 162; disusun ulang 10 November 2026).
 *
 * Seluruh angka berasal dari API, yang membacanya dari database. Tidak ada nilai yang
 * ditanam di kode — itu syarat klaim "working prototype, bukan mockup".
 *
 * ## Susunannya sejak 10 November 2026 (keputusan pemilik proyek 2.i)
 *
 * ```text
 * Bulan ini   papan siklus bulanan: posisi naskah, siapa yang dinanti, pelaksanaan,
 *             evaluasi, persetujuan warga — kartu yang menunggu PEMBACA ditandai
 * Peta        isi utama, dengan rincian yang terbuka saat wilayah diklik
 * ```
 *
 * Ringkasan harian (sorotan, yang menonjol, peringatan dini, prediksi, rekomendasi) tidak
 * lagi di sini: rantai hariannya sudah keluar dari menu sejak 6 November 2026 dan hanya
 * menyisakan tiga cara berbeda sistem "mengusulkan dan pimpinan memutuskan". Layarnya tetap
 * ada di alamat lama (/ops/peringatan, /ops/prediksi, /ops/rekomendasi, /ops/brief).
 *
 * Wilayah terpilih hidup di `?wilayah=`, bukan di dalam komponen: rinciannya diambil di
 * server, tautannya dapat dibagikan saat paparan, dan tombol mundur peramban bekerja.
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{
    wilayah?: string | string[];
    tingkat?: string | string[];
    kelurahan?: string | string[];
  }>;
}) {
  const params = await searchParams;
  const requested = typeof params.wilayah === "string" ? params.wilayah : null;
  // Beranda membuka pada wilayah hukum Polda Metro Jaya. Meminta wilayah tertentu berarti
  // pembaca sudah menyelam ke kecamatan, jadi tingkatnya ikut turun tanpa perlu disebut.
  const level =
    typeof params.tingkat === "string"
      ? toMapLevel(params.tingkat)
      : requested !== null
        ? "kecamatan"
        : "polda";
  // Kelurahan terpilih hanya berarti saat peta memang diperbesar ke satu kecamatan.
  const selectedKelurahan =
    level === "kelurahan" && typeof params.kelurahan === "string" ? params.kelurahan : null;

  const [profile, summary, map, products] = await Promise.all([
    getProfile(),
    getSummary(),
    getMapData(),
    // Tanpa monthly_product:read papan tetap tampil kosong-jujur, bukan menjatuhkan beranda.
    listProducts().catch(() => null),
  ]);
  const can = (p: string) => profile.permissions.includes(p);

  // Bulan yang dipapankan: produk terbaru bila ada, selain itu bulan yang disarankan API.
  const month = products?.data[0]?.target_month ?? products?.suggested_month ?? null;
  const summaryRow = products?.data.find((row) => row.target_month === month) ?? null;
  const [product, drafts] = await Promise.all([
    summaryRow && month
      ? getProduct(month).catch((error: unknown): MonthlyProduct | null => {
          if (error instanceof ApiError && error.status === 404) return null;
          throw error;
        })
      : Promise.resolve<MonthlyProduct | null>(null),
    can("bulletin:approve") || can("bulletin:manage")
      ? getBulletins("", "DRAFT")
          .then((list) => list.data.length)
          .catch(() => 0)
      : Promise.resolve(0),
  ]);

  const board: BoardInput | null = month
    ? {
        month,
        summary: summaryRow,
        product,
        permissions: profile.permissions,
        citizen: { draftBulletins: drafts },
      }
    : null;

  // Tanpa `?wilayah=`, panel rincian dibiarkan kosong beserta ajakan mengklik — bukan
  // diisi wilayah pilihan sistem.
  const selected = requested === null ? null : resolveSelectedDistrict(map, requested);

  // Ketiganya diambil bersamaan; kegagalan salah satu tidak menjatuhkan dua lainnya.
  // `null` berarti kanal itu di luar kewenangan pembaca — dinyatakan apa adanya di panel.
  const [detail, crimes, reports, overlay] = selected
    ? await Promise.all([
        getAreaDetail(selected, selectedKelurahan),
        getCrimes({ kecamatan: selected, page_size: selectedKelurahan ? 40 : 4 })
          .then((page) =>
            (selectedKelurahan
              ? page.data.filter((row) => row.kelurahan === selectedKelurahan)
              : page.data
            ).slice(0, 4),
          )
          .catch(() => null),
        getCitizenReports({ page_size: 60 })
          .then((page) =>
            page.data
              .filter(
                (row) =>
                  row.kecamatan === selected &&
                  (selectedKelurahan === null || row.kelurahan === selectedKelurahan),
              )
              .slice(0, 4),
          )
          .catch(() => null),
        level === "kelurahan" ? getKelurahanOverlay(selected).catch(() => null) : null,
      ])
    : [null, null, null, null];

  return (
    <div className="space-y-3">
      {summary.demo_clock ? (
        // Dinyatakan terbuka: angka dihitung terhadap waktu acuan dataset, bukan waktu
        // sebenarnya. Menyembunyikannya akan menyesatkan pembaca layar.
        <div className="rounded border border-accent/25 bg-accent/5 px-3 py-2 text-xs text-accent-soft">
          Mode demo — waktu acuan{" "}
          <span className="font-mono">
            {new Date(summary.reference_time).toLocaleString("id-ID", {
              timeZone: "Asia/Jakarta",
            })}{" "}
            WIB
          </span>
          {summary.display_data_until
            ? ` — layar memuat kejadian sampai ${new Date(`${summary.display_data_until}T00:00:00+07:00`).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" })}; kejadian sesudahnya hanya dipakai pencocokan.`
            : ", sesuai posisi data kejadian terakhir."}
        </div>
      ) : null}

      {board ? <MonthlyBoard input={board} /> : null}

      <MapHero
        data={map}
        selected={selected}
        kelurahan={selectedKelurahan}
        overlay={overlay}
        detail={detail}
        crimes={crimes}
        reports={reports}
        level={level}
      />
    </div>
  );
}
