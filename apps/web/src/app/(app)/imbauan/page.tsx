import { getProfile } from "@/lib/decisions";
import { getAlertCandidates, getPublicAlerts } from "@/lib/public-alerts";
import { AlertBoard } from "./alert-board";

export const dynamic = "force-dynamic";

/** Kewenangan menerbitkan — ditetapkan pemilik proyek 9 September 2026 pada Pimpinan. */
const PUBLISH_PERMISSION = "public_alert:publish";

/**
 * Kanal Imbauan (TASK 111).
 *
 * Lengan terakhir rantai CLAUDE.md §9. Sebelum 9 September 2026 rantai itu berhenti di
 * dalam organisasi: `public_alerts` punya tabel dan 25 baris, tetapi tidak ada satu
 * endpoint pun dan tidak ada satu layar pun — peringatan dini tidak pernah sampai kepada
 * orang yang paling berkepentingan.
 *
 * Daftar calon hanya diambil untuk pengguna yang benar-benar dapat menerbitkan.
 * Endpoint-nya sendiri dibatasi `public_alert:publish`, jadi memintanya tanpa kewenangan
 * akan dijawab 403 dan membuat seluruh halaman gagal — padahal pembaca tanpa kewenangan
 * tetap berhak melihat imbauan yang beredar.
 */
export default async function KanalImbauanPage() {
  const profile = await getProfile();
  const canPublish = profile.permissions.includes(PUBLISH_PERMISSION);

  const [alerts, candidates] = await Promise.all([
    getPublicAlerts(),
    canPublish ? getAlertCandidates() : Promise.resolve(null),
  ]);

  return (
    <AlertBoard
      alerts={alerts.data}
      candidates={candidates?.data ?? []}
      canPublish={canPublish}
      gateBasis={alerts.severity_gate_basis}
      listBasis={alerts.basis}
      draftBasis={candidates?.draft_basis ?? ""}
    />
  );
}
