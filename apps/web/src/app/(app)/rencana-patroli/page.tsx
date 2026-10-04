import { ApiError } from "@/lib/api";
import { getProfile } from "@/lib/decisions";
import { getPatrolPlan, getPatrolPlanEvaluation } from "@/lib/patrol-plan-api";
import { PatrolPlanView } from "./plan-view";

export const dynamic = "force-dynamic";

/**
 * Rencana Patroli tahun sasaran (permintaan pemilik proyek 4 Oktober 2026).
 *
 * Usulan diambil dari `/patrol-plan`; pencocokan dari `/patrol-plan/evaluation` dan hanya
 * ditampilkan bila pengguna memegang `evaluation:read` — 403 dijawab dengan menyembunyikan
 * panel pencocokan, bukan menggagalkan seluruh halaman.
 */
export default async function PatrolPlanPage() {
  const [plan, evaluation, profile] = await Promise.all([
    getPatrolPlan(),
    getPatrolPlanEvaluation().catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 403) return null;
      throw error;
    }),
    getProfile(),
  ]);

  return (
    <PatrolPlanView
      plan={plan}
      evaluation={evaluation}
      canDecide={profile.permissions.includes("commander_decision:approve")}
    />
  );
}
