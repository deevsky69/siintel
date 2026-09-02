import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar analitik kejahatan (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Crime Analytics">
      <LoadingState label="Menghitung tren, jam rawan, dan perbandingan wilayah…" />
    </Panel>
  );
}
