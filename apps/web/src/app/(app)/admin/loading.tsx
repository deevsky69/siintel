import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat layar administrasi (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Administrasi">
      <LoadingState label="Memuat pengguna dan peran…" />
    </Panel>
  );
}
