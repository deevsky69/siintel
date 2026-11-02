import { getProfile } from "@/lib/decisions";
import { getScoringConfig } from "@/lib/scoring";
import { RunPanel } from "./run-panel";
import { ScoringBasis } from "./scoring-basis";

export const dynamic = "force-dynamic";

/**
 * Mesin Penilaian Risiko.
 *
 * Layar ini menampilkan **dasar** perhitungan lebih dulu — versi bobot beserta statusnya,
 * kedua profil penilaian, bobot tiap faktor, dan jenis ancaman yang dicakupnya — baru
 * kemudian tombol menjalankannya. Urutan itu disengaja: skor yang tampil tanpa asalnya
 * tidak dapat diperdebatkan siapa pun, dan seluruh bobot di sini masih berstatus
 * DEMO / PROPOSED (U-02, CLAUDE.md §11).
 *
 * Yang dihasilkan adalah penilaian atas **keadaan berjalan**, bukan prediksi.
 */
export default async function ScoringPage() {
  const [config, profile] = await Promise.all([getScoringConfig(), getProfile()]);

  return (
    <div className="space-y-3">
      <ScoringBasis config={config} />
      <RunPanel
        // Menyembunyikan tombol hanyalah kenyamanan; backend tetap yang menolak.
        canRun={profile.permissions.includes("risk_score:run")}
        referenceDate={config.reference_time.slice(0, 10)}
      />
    </div>
  );
}
