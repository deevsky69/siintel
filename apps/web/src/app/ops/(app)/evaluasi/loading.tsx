import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Evaluation Center (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Evaluation Center">
      <LoadingState label="Memuat hasil evaluasi…" />
    </Panel>
  );
}
