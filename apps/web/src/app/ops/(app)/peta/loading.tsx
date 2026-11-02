import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

export default function PetaLoading() {
  return (
    <Panel title="Live Kamtibmas Map">
      <LoadingState label="Memuat peta risiko wilayah…" />
    </Panel>
  );
}
