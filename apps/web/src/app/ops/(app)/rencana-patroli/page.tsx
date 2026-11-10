import { ApiError } from "@/lib/api";
import { getPatrolPlan, getPatrolPlanEvaluation } from "@/lib/patrol-plan-api";
import { PatrolPlanView } from "./plan-view";

export const dynamic = "force-dynamic";

/**
 * Rencana Patroli tahun sasaran (permintaan pemilik proyek 4 Oktober 2026).
 *
 * Usulan diambil dari `/patrol-plan`; pencocokan dari `/patrol-plan/evaluation` dan hanya
 * ditampilkan bila pengguna memegang `evaluation:read` — 403 dijawab dengan menyembunyikan
 * panel pencocokan, bukan menggagalkan seluruh halaman.
 *
 * 10 November 2026 (keputusan 2.ii): layar ini keluar dari menu dan tidak lagi memuat
 * formulir persetujuan tersendiri. Perkiraan bulan depan menjadi lampiran Produk Bulanan dan
 * ikut penetapan Pimpinan di sana; yang tersisa di sini adalah bacaan dan unduhan .docx.
 */
export default async function PatrolPlanPage() {
  const [plan, evaluation] = await Promise.all([
    getPatrolPlan(),
    getPatrolPlanEvaluation().catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 403) return null;
      throw error;
    }),
  ]);

  return <PatrolPlanView plan={plan} evaluation={evaluation} canDecide={false} />;
}
