/**
 * Terjemahan nama faktor dominan pada `dominant_factors`.
 *
 * Hanya penamaan untuk layar. Nilai dan asal (`source`) tidak pernah diubah di sini —
 * penjelasan harus tetap mencerminkan mekanisme yang benar-benar dipakai (CLAUDE.md §27).
 * Faktor yang belum dikenal ditampilkan apa adanya, bukan disembunyikan.
 */
const FACTOR_LABELS: Record<string, string> = {
  historical_incident_density: "Kepadatan kejadian historis",
  recent_incident_trend: "Tren kejadian terkini",
  time_window_pattern: "Pola jendela waktu",
  spatial_concentration: "Konsentrasi spasial",
};

export function factorLabel(factor: string): string {
  return FACTOR_LABELS[factor] ?? factor.replace(/_/g, " ");
}

/** Penjelasan asal faktor — dipakai sebagai keterangan di bawah daftar WHY. */
export const SOURCE_NOTE =
  "RULE = kontribusi aturan berbobot. MODEL = kontribusi fitur model terlatih. " +
  "Asal penjelasan ditampilkan apa adanya agar hasil aturan tidak terbaca sebagai temuan model.";
