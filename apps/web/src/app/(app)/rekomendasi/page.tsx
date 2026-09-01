import {
  getDecisions,
  getProfile,
  getRecommendations,
  indexDecisions,
  splitByDecision,
} from "@/lib/decisions";
import { RecommendationBoard } from "./recommendation-board";

export const dynamic = "force-dynamic";

/**
 * Rekomendasi & Keputusan Pimpinan (TASK 121, 130).
 *
 * Rantai `prediksi → peringatan → rekomendasi → keputusan → tindakan` berhenti di layar
 * ini bila tidak ada pejabat yang memutuskan. Itu bukan hambatan yang perlu dipangkas,
 * melainkan hal yang justru harus terlihat saat paparan (CLAUDE.md §13, §14).
 */
export default async function RecommendationPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const requested = typeof params.dipilih === "string" ? params.dipilih : null;

  const [recommendations, decisions, profile] = await Promise.all([
    getRecommendations(),
    getDecisions(),
    getProfile(),
  ]);

  const { pending, decided } = splitByDecision(recommendations.data);

  // Yang menunggu keputusan dibuka lebih dulu: itulah yang menuntut tindakan pejabat.
  const selected =
    recommendations.data.find((row) => row.code === requested) ?? pending[0] ?? decided[0] ?? null;

  return (
    <RecommendationBoard
      pending={pending}
      decided={decided}
      selected={selected}
      decision={selected ? (indexDecisions(decisions.data).get(selected.code) ?? null) : null}
      // Menyembunyikan tombol hanyalah kenyamanan; backend tetap yang menolak.
      canDecide={profile.permissions.includes("commander_decision:approve")}
    />
  );
}
