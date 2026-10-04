import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Rencana Patroli (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Rencana Patroli">
      <LoadingState label="Menyusun usulan dari pola tahun dasar…" />
    </Panel>
  );
}
