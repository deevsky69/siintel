// Profil pengguna berasal dari `/auth/me`; pemuatnya sudah ada di `lib/decisions.ts`
// dan tidak digandakan di sini agar hanya ada satu bentuk `Profile`.
import { getOutlook } from "@/lib/dashboard";
import { getProfile } from "@/lib/decisions";
import { getPredictions } from "@/lib/prediction-center";
import { ACTION_PERMISSIONS, HORIZONS, STATUSES } from "./display";
import { type Filter, PredictionBoard } from "./prediction-board";
import { RunPanel } from "./run-panel";

export const dynamic = "force-dynamic";

/**
 * AI Prediction Center (MVP #7).
 *
 * Seluruh isi halaman berasal dari `/predictions` dan `/predictions/run`. Tidak ada angka,
 * ambang, maupun penjelasan yang ditanam di kode — kelas risiko dibaca dari
 * `config/risk/warning-thresholds.yaml` oleh backend, dan faktor penjelas datang apa adanya
 * dari respons API.
 *
 * Yang harus disadari pembaca layar ini, dan dinyatakan terbuka di dalamnya: **tidak ada
 * model terlatih**. Prediksi dihasilkan dari proyeksi persistensi berbasis aturan atas
 * penilaian risiko yang sudah ada, sehingga `model_version` menyebut versi aturan dan
 * setiap faktor berlabel `RULE` (CLAUDE.md §25, §27).
 *
 * Prediksi yang sedang dibuka ditentukan lewat parameter `dipilih` pada URL, dan
 * penyaringnya lewat `horizon` serta `status` — sehingga pilihan dapat dibagikan sebagai
 * tautan saat paparan tanpa memerlukan penyimpanan keadaan di peramban.
 */
export default async function PredictionCenterPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const read = (key: string) => (typeof params[key] === "string" ? params[key] : null);

  // Nilai penyaring yang tidak dikenal diabaikan, bukan diteruskan ke backend: URL yang
  // diketik tangan tidak boleh membuat layar menampilkan galat.
  const horizonParam = read("horizon");
  const statusParam = read("status");
  const filter: Filter = {
    horizon: HORIZONS.some((item) => item === horizonParam) ? horizonParam : null,
    status: STATUSES.some((item) => item === statusParam) ? statusParam : null,
  };

  const [predictions, outlook, profile] = await Promise.all([
    getPredictions({ horizon: filter.horizon ?? undefined, status: filter.status ?? undefined }),
    // Dipakai hanya untuk waktu acuan aplikasi: dataset berhenti Desember 2025 dan jam
    // dinding tidak dipakai (SDL-16). Endpoint ini memakai permission yang sama dengan
    // daftar prediksi, sehingga tidak menambah syarat kewenangan bagi layar ini.
    getOutlook(),
    getProfile(),
  ]);

  const requested = read("dipilih");
  // Bila tautan menunjuk prediksi di luar halaman yang dimuat, layar kembali ke prediksi
  // berisiko tertinggi — bukan menampilkan layar kosong.
  const selected =
    predictions.data.find((row) => row.code === requested) ?? predictions.data[0] ?? null;

  return (
    <div className="space-y-3">
      <PredictionBoard
        rows={predictions.data}
        total={predictions.pagination.total_items}
        selected={selected}
        filter={filter}
        // Menyembunyikan tombol hanyalah kenyamanan; backend tetap yang menolak.
        canPublish={profile.permissions.includes(ACTION_PERMISSIONS.publish)}
      />
      <RunPanel
        canRun={profile.permissions.includes(ACTION_PERMISSIONS.run)}
        referenceDate={outlook.reference_time.slice(0, 10)}
      />
    </div>
  );
}
