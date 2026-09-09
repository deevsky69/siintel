import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Kanal Imbauan (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Kanal Imbauan">
      <LoadingState label="Memuat imbauan yang beredar…" />
    </Panel>
  );
}
