import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar rekap Polda (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Polda Metro Jaya">
      <LoadingState label="Memuat rekap per Polres…" />
    </Panel>
  );
}
