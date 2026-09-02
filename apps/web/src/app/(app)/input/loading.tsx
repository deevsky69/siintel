import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar pemasukan data (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Input Data">
      <LoadingState label="Memuat pilihan wilayah dan taksonomi…" />
    </Panel>
  );
}
