import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Community Signal Dashboard (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Sinyal Masyarakat">
      <LoadingState label="Memuat laporan masyarakat…" />
    </Panel>
  );
}
