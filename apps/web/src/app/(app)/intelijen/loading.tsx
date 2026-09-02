import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar laporan intelijen (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Laporan Intelijen">
      <LoadingState label="Mengambil laporan intelijen…" />
    </Panel>
  );
}
