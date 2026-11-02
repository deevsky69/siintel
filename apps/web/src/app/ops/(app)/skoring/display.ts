/**
 * Label dan pembentukan teks layar penilaian risiko.
 *
 * Dipisahkan dari `@/lib/scoring` dengan sengaja: modul itu menarik `@/lib/api` yang
 * memuat `next/headers`, dan komponen `"use client"` tidak boleh mengimpornya. Berkas ini
 * murni — tanpa akses jaringan, tanpa sesi — sehingga aman dipakai kedua sisi sekaligus
 * dapat diuji tanpa backend.
 */

export const PROFILE_LABELS: Record<string, string> = {
  historical: "Profil A — Pola Historis",
  planned: "Profil B — Gangguan Terencana",
};

export const PROFILE_HINTS: Record<string, string> = {
  historical:
    "Untuk gangguan yang berulang dan meninggalkan jejak statistik. Riwayat kejadian adalah petunjuk terkuatnya.",
  planned:
    "Untuk kegiatan yang direncanakan dan diketahui sebelum terjadi. Yang dinilai perkiraan dampaknya, bukan kemungkinan terjadinya.",
};

/** Nama faktor dalam Bahasa Indonesia. Nama teknisnya tetap ditampilkan berdampingan. */
export const FACTOR_LABELS: Record<string, string> = {
  historical_factor: "Kepadatan kejadian historis",
  recent_trend_factor: "Kecenderungan 30 hari terakhir",
  temporal_factor: "Kesesuaian jendela waktu",
  spatial_factor: "Konsentrasi & pengulangan",
  context_factor: "Kategori TKP di sekitar",
  intelligence_factor: "Laporan intelijen terverifikasi",
  community_factor: "Laporan masyarakat terverifikasi",
  mass_estimate_factor: "Perkiraan jumlah massa",
  location_sensitivity_factor: "Kedekatan objek vital",
  history_of_disorder_factor: "Riwayat kericuhan serupa",
  source_reliability_factor: "Keandalan sumber informasi",
  readiness_factor: "Kesiapan personel",
};

export function profileLabel(profile: string): string {
  return PROFILE_LABELS[profile] ?? profile;
}

export function factorLabel(factor: string): string {
  return FACTOR_LABELS[factor] ?? factor;
}

/** Bobot sebagai persen, mis. 0,3 → "30%". Bobot negatif tetap bertanda minus. */
export function weightPercent(weight: number): string {
  return `${(weight * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

/**
 * Nilai faktor untuk tampilan.
 *
 * `null` **tidak pernah** ditulis sebagai 0: nol berarti diukur dan hasilnya nol,
 * sedangkan tidak terukur berarti tidak ada dasar untuk mengukurnya sama sekali.
 */
export function factorValue(value: number | null): string {
  return value === null ? "tidak terukur" : String(value);
}

/** Sumbangan satu faktor terhadap skor, dalam satuan poin skor. */
export function contributionText(contribution: number, weight: number | null): string {
  if (weight === null) return "tidak berbobot pada versi aktif";
  if (weight === 0) return "berbobot nol — tidak menyumbang";
  return `${contribution.toLocaleString("id-ID", { maximumFractionDigits: 2 })} poin`;
}
