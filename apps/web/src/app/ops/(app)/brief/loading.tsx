import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat Executive Brief (CLAUDE.md §23). */
export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl">
      <Panel title="Executive Brief">
        <LoadingState label="Menyusun ringkasan situasi…" />
      </Panel>
    </div>
  );
}
