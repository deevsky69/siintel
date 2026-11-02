/**
 * Label dan pembentukan teks layar AI Prediction Center.
 *
 * Dipisahkan dari `@/lib/prediction-center` dengan sengaja: modul itu menarik `@/lib/api`
 * yang memuat `next/headers`, dan komponen `"use client"` tidak boleh mengimpornya. Berkas
 * ini murni — tanpa akses jaringan, tanpa sesi — sehingga aman dipakai kedua sisi
 * sekaligus dapat diuji tanpa backend.
 */

/** Horizon yang dikenal `predictions.forecast_horizon`. */
export const HORIZONS = ["6H", "12H", "24H", "3D", "7D"] as const;
export type Horizon = (typeof HORIZONS)[number];

/** Status prediksi. Hanya `PUBLISHED` yang boleh melahirkan peringatan dini. */
export const STATUSES = ["DRAFT", "PUBLISHED", "VALIDATED"] as const;
export type PredictionStatus = (typeof STATUSES)[number];

/**
 * Permission yang diperiksa backend untuk tiap tindakan pada layar ini.
 *
 * Salinan ini **bukan** pengaman: penolakan sesungguhnya terjadi di backend
 * (CLAUDE.md §21). Gunanya hanya agar layar tidak menawarkan tombol yang pasti ditolak.
 */
export const ACTION_PERMISSIONS = {
  run: "prediction:run",
  publish: "prediction:publish",
} as const;

/** Keterangan tiap horizon: yang dicakup satu kali penjalanan, bukan sekadar namanya. */
export const HORIZON_LABELS: Record<string, string> = {
  "6H": "6 jam",
  "12H": "12 jam",
  "24H": "24 jam",
  "3D": "3 hari",
  "7D": "7 hari",
};

export const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draf",
  PUBLISHED: "Terpublikasi",
  VALIDATED: "Tervalidasi",
};

/** Arti tiap status, supaya pembaca layar tahu akibatnya tanpa membuka dokumen. */
export const STATUS_HINTS: Record<string, string> = {
  DRAFT: "Belum dipublikasikan — tidak melahirkan peringatan dini",
  PUBLISHED: "Sudah terbit dan boleh menjadi dasar peringatan dini",
  VALIDATED: "Sudah dibandingkan dengan kejadian sebenarnya",
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
  confidence_support: "Dasar keyakinan (kejadian penopang)",
  // Faktor pada prediksi lama yang lahir dari seed, bukan dari mesin ini.
  historical_incident_density: "Kepadatan kejadian historis",
  recent_incident_trend: "Tren kejadian terkini",
  time_window_pattern: "Pola jendela waktu",
  spatial_concentration: "Konsentrasi spasial",
  patrol_coverage_gap: "Celah cakupan patroli",
  intelligence_signal: "Sinyal intelijen",
};

export function horizonLabel(horizon: string): string {
  return HORIZON_LABELS[horizon] ?? horizon;
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function factorLabel(factor: string): string {
  return FACTOR_LABELS[factor] ?? factor.replaceAll("_", " ");
}

const WIB: Intl.DateTimeFormatOptions = {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

/** Waktu WIB yang terbaca. Nilai kosong dijawab tanda pisah, bukan tanggal karangan. */
export function formatWib(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return `${parsed.toLocaleString("id-ID", WIB)} WIB`;
}

/**
 * Jawaban **WHEN**: rentang jendela yang diprediksi, bukan hanya labelnya.
 *
 * Label seperti "18:00-23:59" tidak menyebut harinya, sedangkan prediksi menunjuk hari
 * tertentu di depan. Keduanya ditampilkan bersama.
 */
export function windowText(start: string | null, end: string | null): string {
  if (!start || !end) return "—";
  return `${formatWib(start)} s.d. ${formatWib(end)}`;
}

/**
 * Nilai faktor untuk tampilan.
 *
 * `null` **tidak pernah** ditulis sebagai 0: nol berarti diukur dan hasilnya nol,
 * sedangkan tidak terukur berarti tidak ada dasar untuk mengukurnya sama sekali.
 */
export function factorValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return "tidak terukur";
  return String(value);
}

/**
 * Sumbangan satu faktor terhadap skor, dalam satuan poin skor.
 *
 * Prediksi lama (yang lahir dari seed) menyimpan `contribution` tanpa `weight`. Sumbangan
 * itu tetap ditampilkan beserta keterangan bahwa bobotnya tidak tercatat — menyembunyikan
 * angka yang benar-benar ada akan membuat penjelasan tampak lebih kosong daripada
 * kenyataannya.
 */
export function contributionText(contribution: number, weight: number | null | undefined): string {
  const poin = `${contribution.toLocaleString("id-ID", { maximumFractionDigits: 3 })} poin`;

  if (weight === null || weight === undefined) {
    return contribution === 0 ? "tidak berbobot" : `${poin} — bobot tidak tercatat`;
  }
  if (weight === 0) return "berbobot nol — tidak menyumbang";
  return poin;
}

/**
 * Keterangan umur penilaian dasar.
 *
 * Prediksi ini memproyeksikan penilaian risiko yang sudah ada; makin tua penilaiannya,
 * makin jauh dasar perkiraan dari keadaan terakhir. Angkanya dinyatakan, bukan disamarkan.
 */
export function baselineAgeText(days: number | null): string {
  if (days === null) return "tidak ada penilaian dasar";
  if (days === 0) return "penilaian pada hari yang sama";
  return `${days} hari sebelum jendela yang diprediksi`;
}
