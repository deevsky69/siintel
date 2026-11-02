// Profil pengguna berasal dari `/auth/me`; pemuatnya sudah ada di `lib/decisions.ts`
// dan tidak digandakan di sini agar hanya ada satu bentuk `Profile`.
import { getProfile } from "@/lib/decisions";
import {
  ACTION_PERMISSIONS,
  getPredictions,
  getWarningsByStatus,
  indexPredictions,
  WARNING_STATUSES,
} from "@/lib/warnings";
import { WarningBoard, type WarningGroup } from "./warning-board";

export const dynamic = "force-dynamic";

/**
 * Warning Center (TASK 111).
 *
 * Seluruh isi halaman berasal dari `/warnings` dan `/predictions`. Tidak ada angka,
 * ambang, maupun penjelasan yang ditanam di kode — itu syarat klaim "working prototype,
 * bukan mockup" pada success criteria #05 Taskap.
 *
 * Peringatan yang sedang dibuka dasarnya ditentukan lewat parameter `dipilih` pada URL,
 * sehingga pilihan dapat dibagikan sebagai tautan saat paparan tanpa memerlukan
 * penyimpanan keadaan di peramban.
 */
export default async function WarningCenterPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const requested = typeof params.dipilih === "string" ? params.dipilih : null;

  const [pages, predictions, profile] = await Promise.all([
    Promise.all(WARNING_STATUSES.map((status) => getWarningsByStatus(status))),
    getPredictions(),
    getProfile(),
  ]);

  const groups: WarningGroup[] = WARNING_STATUSES.map((status, index) => ({
    status,
    rows: pages[index].data,
    total: pages[index].pagination.total_items,
  }));

  // Bila tautan menunjuk peringatan di luar halaman yang dimuat, layar kembali ke
  // peringatan aktif dengan risiko tertinggi — bukan menampilkan layar kosong.
  const loaded = groups.flatMap((group) => group.rows);
  const selected = loaded.find((warning) => warning.code === requested) ?? loaded[0] ?? null;

  const sourcePrediction = selected
    ? (indexPredictions(predictions.data).get(selected.prediction_code) ?? null)
    : null;

  return (
    <WarningBoard
      groups={groups}
      selected={selected}
      sourcePrediction={sourcePrediction}
      // Menyembunyikan tombol hanyalah kenyamanan; backend tetap yang menolak.
      // Catatan kewenangan: role Polsek memiliki `warning:acknowledge` tetapi tidak
      // `warning:resolve`, sehingga kedua kewenangan diperiksa terpisah.
      canAcknowledge={profile.permissions.includes(ACTION_PERMISSIONS.acknowledge)}
      canResolve={profile.permissions.includes(ACTION_PERMISSIONS.resolve)}
    />
  );
}
