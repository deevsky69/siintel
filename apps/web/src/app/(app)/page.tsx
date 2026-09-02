import { EarlyWarningPanel } from "@/components/dashboard/early-warning";
import { OutlookPanel } from "@/components/dashboard/outlook";
import { PatrolStatus } from "@/components/dashboard/patrol-status";
import { RecommendationPanel } from "@/components/dashboard/recommendations";
import { SituationOverview } from "@/components/dashboard/situation-overview";
import { ScoreList } from "@/components/dashboard/threat-list";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { ProminentIssues } from "@/components/leadership/issues";
import { PolicyRecommendations } from "@/components/leadership/policy";
import {
  AreaStatusCard,
  AttentionCard,
  PriorityAreasCard,
  ReportsCard,
} from "@/components/leadership/summary-cards";
import { TopReportAreas } from "@/components/leadership/top-areas";
import { MapPanel } from "@/components/map/map-panel";
import {
  getActiveWarnings,
  getOutlook,
  getRecommendations,
  getSummary,
  getTrends,
} from "@/lib/dashboard";
import { getLeadership } from "@/lib/leadership";
import { getMapData } from "@/lib/map-data";

export const dynamic = "force-dynamic";

/**
 * Executive Dashboard (TASK 070) dan layar Pimpinan (TASK 150).
 *
 * Seluruh angka pada halaman ini berasal dari API, yang membacanya dari database.
 * Tidak ada nilai yang ditanam di kode — itu syarat klaim "working prototype,
 * bukan mockup" pada success criteria Taskap.
 *
 * Susunannya mengikuti permintaan pemilik proyek, 2 September 2026: empat kartu ringkas,
 * lalu daftar wilayah menurut jumlah laporan, isu menonjol sepekan, dan rekomendasi
 * kebijakan. Panel teknis yang sudah ada — peta, tren, outlook, status patroli — tetap
 * berada di bawahnya, tidak dihapus: ia masih dipakai peran selain Pimpinan, dan menghapus
 * fitur yang bekerja bukan bagian dari permintaan ini.
 *
 * Seluruh blok dibatasi kewenangan di backend. Pengguna Polsek menerima layar dengan
 * susunan yang sama, berisi wilayahnya sendiri.
 */
export default async function DashboardPage() {
  const [summary, trends, outlook, warnings, map, board] = await Promise.all([
    getSummary(),
    getTrends(),
    getOutlook(),
    getActiveWarnings(),
    getMapData(),
    getLeadership(),
  ]);

  const topWarning = warnings.data[0] ?? null;
  const recommendations = topWarning ? await getRecommendations(topWarning.code) : null;

  return (
    <div className="space-y-3">
      {summary.demo_clock ? (
        // Dinyatakan terbuka: "24 jam terakhir" dihitung terhadap waktu acuan dataset,
        // bukan waktu sebenarnya. Menyembunyikannya akan menyesatkan pembaca layar.
        <div className="rounded border border-accent/25 bg-accent/5 px-3 py-2 text-[11px] text-accent-soft">
          Mode demo — seluruh perhitungan waktu mengacu pada{" "}
          <span className="font-mono">
            {new Date(summary.reference_time).toLocaleString("id-ID", {
              timeZone: "Asia/Jakarta",
            })}{" "}
            WIB
          </span>
          , sesuai rentang dataset sintetis.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <ReportsCard reports={board.reports_24h} />
        <AreaStatusCard areaStatus={board.area_status} />
        <AttentionCard items={board.needs_attention.items} />
        <PriorityAreasCard areas={board.priority_areas} />
      </div>

      <TopReportAreas top={board.top_report_areas} />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <ProminentIssues issues={board.prominent_issues} />
        <PolicyRecommendations policy={board.policy} />
      </div>

      <div className="flex items-center gap-3 pt-1">
        <span className="text-[10px] uppercase tracking-wider text-ink-faint">Panel analitik</span>
        <span className="h-px flex-1 bg-base-800" />
      </div>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 flex flex-col gap-3 xl:col-span-3">
          <SituationOverview summary={summary} />
          <ScoreList
            title="Top Threat"
            rows={summary.top_threats.map((row) => ({
              label: row.threat_type,
              score: row.risk_score,
            }))}
            emptyLabel="Belum ada penilaian risiko."
          />
        </div>

        <div className="col-span-12 xl:col-span-6">
          <MapPanel data={map} />
        </div>

        <div className="col-span-12 flex flex-col gap-3 xl:col-span-3">
          <EarlyWarningPanel warning={topWarning} total={warnings.pagination.total_items} />
          <RecommendationPanel
            rows={recommendations?.data ?? []}
            forWarning={topWarning?.code ?? null}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <OutlookPanel rows={outlook.outlook} />
        <TrendChart series={trends.series} />
        <ScoreList
          title="Risk Index by District"
          rows={summary.risk_by_district.map((row) => ({
            label: row.kecamatan,
            score: row.risk_score,
          }))}
          emptyLabel="Belum ada penilaian risiko."
        />
        <PatrolStatus units={summary.units} operations={summary.active_operations} />
      </div>
    </div>
  );
}
