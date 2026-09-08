import { EarlyWarningPanel } from "@/components/dashboard/early-warning";
import { OutlookPanel } from "@/components/dashboard/outlook";
import { PatrolStatus } from "@/components/dashboard/patrol-status";
import { RecommendationPanel } from "@/components/dashboard/recommendations";
import { SituationOverview } from "@/components/dashboard/situation-overview";
import { ScoreList } from "@/components/dashboard/threat-list";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { Highlights, Notables } from "@/components/leadership/highlights";
import { ProminentIssues } from "@/components/leadership/issues";
import { MapHero } from "@/components/leadership/map-hero";
import { PolicyRecommendations } from "@/components/leadership/policy";
import { TopReportAreas } from "@/components/leadership/top-areas";
import { toMapLevel } from "@/components/map/area";
import {
  getActiveWarnings,
  getOutlook,
  getRecommendations,
  getSummary,
  getTrends,
} from "@/lib/dashboard";
import { getLeadership } from "@/lib/leadership";
import { getAreaDetail, getMapData, resolveSelectedDistrict } from "@/lib/map-data";
import { getCitizenReports, getCrimes } from "@/lib/reports";

export const dynamic = "force-dynamic";

/**
 * Beranda (TASK 070, 150, 162).
 *
 * Seluruh angka berasal dari API, yang membacanya dari database. Tidak ada nilai yang
 * ditanam di kode — itu syarat klaim "working prototype, bukan mockup" pada success
 * criteria Taskap.
 *
 * ## Susunannya, dan mengapa demikian
 *
 * ```text
 * Sorotan     4 kartu — satu angka, satu baris
 * Peta        isi utama, dengan rincian yang terbuka saat wilayah diklik
 * Menonjol    3 kartu — apa yang BERGERAK, bukan apa yang ada
 * Selebihnya  terlipat
 * ```
 *
 * Pemilik proyek menyampaikan beranda memuat terlalu banyak untuk dibaca sekali duduk,
 * dan meminta peta diletakkan di sini. Keduanya menuntun ke satu keputusan: **peta menjadi
 * isi utama, dan segala sesuatu di sekitarnya dipangkas sampai satu angka dan satu baris.**
 *
 * Yang dipangkas tidak dihapus. Tabel sepuluh wilayah, daftar rekomendasi kebijakan, dan
 * panel analitik pindah ke bagian terlipat di bawah — masing-masing tetap punya layarnya
 * sendiri di menu, dan setiap kartu sorotan menautkannya.
 *
 * Blok "Menonjol" menyorot apa yang **berubah**, bukan apa yang terbesar. Daftar terbesar
 * selalu terisi dan karenanya tidak pernah memberi tahu sesuatu yang baru; yang berguna
 * dibaca setiap pagi adalah apa yang bergerak sejak kemarin.
 *
 * Wilayah terpilih hidup di `?wilayah=`, bukan di dalam komponen: rinciannya diambil di
 * server, tautannya dapat dibagikan saat paparan, dan tombol mundur peramban bekerja.
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ wilayah?: string | string[]; tingkat?: string | string[] }>;
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

  const [summary, trends, outlook, warnings, map, board] = await Promise.all([
    getSummary(),
    getTrends(),
    getOutlook(),
    getActiveWarnings(),
    getMapData(),
    getLeadership(),
  ]);

  // Tanpa `?wilayah=`, panel rincian dibiarkan kosong beserta ajakan mengklik — bukan
  // diisi wilayah pilihan sistem. Rincian yang muncul sendiri tanpa diminta membuat
  // pembaca mengira ia sedang melihat wilayah yang paling penting, padahal ia hanya
  // melihat wilayah yang kebetulan terpilih lebih dulu.
  const selected = requested === null ? null : resolveSelectedDistrict(map, requested);

  // Ketiganya diambil bersamaan; kegagalan salah satu tidak menjatuhkan dua lainnya.
  // `null` berarti kanal itu di luar kewenangan pembaca — dinyatakan apa adanya di panel,
  // bukan ditampilkan sebagai daftar kosong yang artinya berbeda jauh.
  const [detail, crimes, reports] = selected
    ? await Promise.all([
        getAreaDetail(selected),
        getCrimes({ kecamatan: selected, page_size: 4 })
          .then((page) => page.data)
          .catch(() => null),
        getCitizenReports({ page_size: 60 })
          .then((page) => page.data.filter((row) => row.kecamatan === selected).slice(0, 4))
          .catch(() => null),
      ])
    : [null, null, null];

  const topWarning = warnings.data[0] ?? null;
  const recommendations = topWarning ? await getRecommendations(topWarning.code) : null;

  return (
    <div className="space-y-3">
      {summary.demo_clock ? (
        // Dinyatakan terbuka: "24 jam terakhir" dihitung terhadap waktu acuan dataset,
        // bukan waktu sebenarnya. Menyembunyikannya akan menyesatkan pembaca layar.
        <div className="rounded border border-accent/25 bg-accent/5 px-3 py-2 text-xs text-accent-soft">
          Mode demo — waktu acuan{" "}
          <span className="font-mono">
            {new Date(summary.reference_time).toLocaleString("id-ID", {
              timeZone: "Asia/Jakarta",
            })}{" "}
            WIB
          </span>
          , sesuai rentang dataset sintetis.
        </div>
      ) : null}

      <Highlights board={board} />

      <MapHero
        data={map}
        selected={selected}
        detail={detail}
        crimes={crimes}
        reports={reports}
        level={level}
      />

      <Notables board={board} />

      {/* Selebihnya dilipat, tidak dihapus.
          Tabel sepuluh wilayah, daftar rekomendasi kebijakan, dan panel analitik masih
          dipakai peran selain Pimpinan, dan masing-masing punya layarnya sendiri di menu.
          Membiarkannya terbentang di beranda membuat halaman terlalu panjang untuk dibaca
          sekali duduk — keluhan yang memang disampaikan pemilik proyek.

          `details` dipakai apa adanya: ia bekerja tanpa JavaScript dan sudah dikenali
          pembaca layar sebagai bagian yang dapat dibuka. */}
      <details className="group space-y-3">
        <summary className="flex cursor-pointer list-none items-center gap-3 py-1 text-2xs uppercase tracking-wider text-ink-faint transition-colors hover:text-ink-muted">
          <span className="transition-transform group-open:rotate-90" aria-hidden="true">
            &#9656;
          </span>
          <span>Rincian dan panel analitik</span>
          <span className="h-px flex-1 bg-base-800" />
        </summary>

        <TopReportAreas top={board.top_report_areas} />

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <ProminentIssues issues={board.prominent_issues} />
          <PolicyRecommendations policy={board.policy} />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SituationOverview summary={summary} />
          <OutlookPanel rows={outlook.outlook} />
          <TrendChart series={trends.series} />
          <PatrolStatus units={summary.units} operations={summary.active_operations} />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ScoreList
            title="Top Threat"
            rows={summary.top_threats.map((row) => ({
              label: row.threat_type,
              score: row.risk_score,
            }))}
            emptyLabel="Belum ada penilaian risiko."
          />
          <ScoreList
            title="Risk Index by District"
            rows={summary.risk_by_district.map((row) => ({
              label: row.kecamatan,
              score: row.risk_score,
            }))}
            emptyLabel="Belum ada penilaian risiko."
          />
          <EarlyWarningPanel warning={topWarning} total={warnings.pagination.total_items} />
          <RecommendationPanel
            rows={recommendations?.data ?? []}
            forWarning={topWarning?.code ?? null}
          />
        </div>
      </details>
    </div>
  );
}
