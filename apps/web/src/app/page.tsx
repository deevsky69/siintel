import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/**
 * Executive Dashboard.
 *
 * Kerangka panel sesuai `design/gambaran-website.png`. Isinya masih kosong dan
 * ditandai demikian: angka baru ditampilkan setelah API domain hidup (TASK 070),
 * karena dashboard yang menampilkan angka karangan justru merusak klaim
 * "working prototype, bukan mockup".
 */
export default function DashboardPage() {
  return (
    <div className="grid h-full grid-cols-12 gap-3">
      <div className="col-span-12 flex flex-col gap-3 xl:col-span-3">
        <Panel title="Situation Overview" className="flex-1">
          <EmptyState label="Menunggu API dashboard (TASK 070)" />
        </Panel>
        <Panel title="Top Threat (24 Jam)" className="flex-1">
          <EmptyState label="Menunggu API analitik" />
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-6">
        <Panel title="Live Kamtibmas Map" className="h-full" bodyClassName="p-0">
          <EmptyState label="Peta wilayah dibangun pada TASK 080" />
        </Panel>
      </div>

      <div className="col-span-12 flex flex-col gap-3 xl:col-span-3">
        <Panel title="Early Warning" className="flex-1">
          <EmptyState label="Menunggu API peringatan (TASK 037)" />
        </Panel>
        <Panel title="AI Recommendation" className="flex-1">
          <EmptyState label="Menunggu API rekomendasi (TASK 038)" />
        </Panel>
      </div>

      <div className="col-span-12 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Panel title="Prediction Next 24 Hours">
          <EmptyState label="TASK 083" />
        </Panel>
        <Panel title="Crime Trend">
          <EmptyState label="TASK 090" />
        </Panel>
        <Panel title="Risk Index by District">
          <EmptyState label="TASK 036" />
        </Panel>
        <Panel title="Patrol Status">
          <EmptyState label="TASK 034" />
        </Panel>
      </div>
    </div>
  );
}
