import { getProfile } from "@/lib/decisions";
import { getOperations, getPendingDecisions, splitByProgress, unitOptions } from "@/lib/operations";
import { OperationBoard } from "./operation-board";

export const dynamic = "force-dynamic";

/**
 * Operasi — Tindakan Lapangan & Hasil Nyata (TASK 131).
 *
 * Layar ini menutup rantai CLAUDE.md §9: setelah pejabat memutuskan, harus terlihat siapa
 * yang menjalankan dan apa hasilnya. Tanpa lengan ini, evaluasi tidak punya kenyataan
 * untuk dibandingkan dengan prediksi (§26).
 *
 * Pilihan yang sedang dibuka disimpan di URL (`?dipilih=`), bukan state klien, agar
 * halaman tetap server component dan tautannya dapat dibagikan saat paparan. Kode
 * keputusan (`DEC-…`) dan kode tindakan (`ACT-…`) berbeda awalan, sehingga satu parameter
 * cukup untuk keduanya.
 */
export default async function OperationPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const requested = typeof params.dipilih === "string" ? params.dipilih : null;

  const [operations, pending, profile] = await Promise.all([
    getOperations(),
    getPendingDecisions(),
    getProfile(),
  ]);

  const queue = pending.data;
  const { awaitingResult, withResult } = splitByProgress(operations.data);

  const decision = queue.find((row) => row.decision_code === requested) ?? null;
  const action = decision ? null : (operations.data.find((row) => row.code === requested) ?? null);

  // Bila belum ada yang dipilih, antrean kerja dibuka lebih dulu: keputusan yang belum
  // dijalankan adalah yang paling menuntut tindakan. Setelahnya penugasan yang hasilnya
  // belum tercatat — lengan umpan balik yang masih menganga.
  const fallbackDecision = decision ?? (action ? null : (queue[0] ?? null));
  const fallbackAction =
    action ?? (fallbackDecision ? null : (awaitingResult[0] ?? withResult[0] ?? null));

  return (
    <OperationBoard
      queue={queue}
      awaitingResult={awaitingResult}
      withResult={withResult}
      selectedDecision={fallbackDecision}
      selectedAction={fallbackAction}
      // Satu-satunya sumber daftar satuan yang benar-benar ada: satuan yang pernah
      // ditugaskan. Endpoint data induk satuan belum tersedia — lihat `unitOptions`.
      units={unitOptions(operations.data)}
      // Menyembunyikan formulir hanyalah kenyamanan; backend tetap yang menolak
      // (CLAUDE.md §21).
      canWrite={profile.permissions.includes("operation:write")}
    />
  );
}
