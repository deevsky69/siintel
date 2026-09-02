import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat jejak audit (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Jejak Audit">
      <LoadingState label="Memuat jejak audit…" />
    </Panel>
  );
}
