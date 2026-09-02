import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar AI Prediction Center (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="AI Prediction Center">
      <LoadingState label="Memuat prediksi…" />
    </Panel>
  );
}
