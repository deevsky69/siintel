import { EarlyWarningPanel } from "@/components/dashboard/early-warning";
import { OutlookPanel } from "@/components/dashboard/outlook";
import { PatrolStatus } from "@/components/dashboard/patrol-status";
import { RecommendationPanel } from "@/components/dashboard/recommendations";
import { SituationOverview } from "@/components/dashboard/situation-overview";
import { ScoreList } from "@/components/dashboard/threat-list";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  getActiveWarnings,
  getOutlook,
  getRecommendations,
  getSummary,
  getTrends,
} from "@/lib/dashboard";

export const dynamic = "force-dynamic";

/**
 * Executive Dashboard (TASK 070).
 *
 * Seluruh angka pada halaman ini berasal dari API, yang membacanya dari database.
 * Tidak ada nilai yang ditanam di kode — itu syarat klaim "working prototype,
 * bukan mockup" pada success criteria Taskap.
 */
export default async function DashboardPage() {
  const [summary, trends, outlook, warnings] = await Promise.all([
    getSummary(),
    getTrends(),
    getOutlook(),
    getActiveWarnings(),
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
          <Panel title="Live Kamtibmas Map" className="h-full" bodyClassName="p-0">
            <EmptyState label="Peta wilayah dibangun pada TASK 080–084" />
          </Panel>
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
