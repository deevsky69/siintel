import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar operasi (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Antrean & Tindakan Operasional">
      <LoadingState label="Memuat tindakan operasional…" />
    </Panel>
  );
}
