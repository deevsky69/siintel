import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Warning Center (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Warning Center">
      <LoadingState label="Memuat peringatan dini…" />
    </Panel>
  );
}
