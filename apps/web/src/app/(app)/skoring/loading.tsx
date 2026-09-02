import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar penilaian risiko (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Mesin Penilaian Risiko">
      <LoadingState label="Memuat bobot dan ambang…" />
    </Panel>
  );
}
