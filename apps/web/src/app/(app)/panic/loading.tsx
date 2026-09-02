import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Laporan Mendesak">
      <LoadingState label="Memuat laporan mendesak…" />
    </Panel>
  );
}
