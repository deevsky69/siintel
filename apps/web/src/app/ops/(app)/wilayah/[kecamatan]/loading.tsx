import { LoadingState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan memuat profil kecamatan — batasnya sendiri, supaya berpindah dari daftar wilayah
 * ke rinciannya tetap memberi tanda (CLAUDE.md §23). */
export default function Loading() {
  return (
    <Panel title="Profil Wilayah">
      <LoadingState label="Memuat profil wilayah…" />
    </Panel>
  );
}
