import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar keputusan (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Rekomendasi & Keputusan Pimpinan">
      <LoadingState label="Memuat rekomendasi…" />
    </Panel>
  );
}
