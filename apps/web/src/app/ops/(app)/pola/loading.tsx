import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar pola kejahatan (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Crime Pattern DNA">
      <LoadingState label="Menghitung sebaran kejadian…" />
    </Panel>
  );
}
