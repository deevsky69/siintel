import type { PatternDistribution, ThreatTypeCount } from "@/lib/patterns";

/**
 * Pembantu tampilan Crime Pattern DNA — murni, tanpa pemanggilan API.
 *
 * Dipisahkan dari `lib/patterns.ts` dengan sengaja: modul itu memanggil `lib/api.ts`, yang
 * membaca cookie sesi dan hanya hidup di server. Semua yang ada di sini adalah pemilihan
 * dan pemformatan tampilan, sehingga dapat diuji langsung tanpa jaringan maupun sesi.
 *
 * Tidak ada satu pun fungsi di sini yang menghitung ulang angka. Jumlah, persentase, dan
 * peringkat datang jadi dari backend; yang dilakukan di sini hanya memilih jenis yang
 * ditampilkan, menyusun tautan, dan merapikan nama untuk dibaca manusia.
 */

/** Nama jenis gangguan untuk pembaca. Nomenklatur kedinasan tidak diterjemahkan. */
const THREAT_LABELS: Record<string, string> = {
  CURANMOR: "Curanmor",
  CURAT: "Curat",
  CURAS: "Curas",
  TAWURAN: "Tawuran",
  KEJAHATAN_JALANAN: "Kejahatan Jalanan",
};

/**
 * Nama jenis gangguan.
 *
 * Jenis yang belum punya nama tampilan dirapikan apa adanya, bukan disembunyikan:
 * taksonomi kejadian belum final (U-16), jadi nilai baru harus tetap dapat dipilih.
 */
export function threatLabel(threatType: string): string {
  return THREAT_LABELS[threatType] ?? humanize(threatType);
}

/**
 * Merapikan nilai taksonomi menjadi teks yang enak dibaca.
 *
 * `modus` dan `target_type` disimpan sebagai teks bergaris bawah (`kelalaian_pengguna`)
 * dan belum memiliki daftar label resmi di `config/taxonomy/mappings.yaml`. Yang dilakukan
 * di sini murni kosmetik — mengganti garis bawah dengan spasi dan mengawali dengan huruf
 * besar. **Tidak ada nilai yang diterjemahkan atau digabungkan**, karena menggabungkan dua
 * nilai berbeda menjadi satu nama akan mengubah angkanya tanpa terlihat.
 *
 * Nilai yang sudah tertulis rapi (nama kecamatan, kategori TKP seperti "Pusat Aktivitas")
 * dibiarkan apa adanya — merapikannya justru akan merusak kapitalisasinya.
 */
export function humanize(value: string): string {
  const needsTidying = value.includes("_") || value === value.toLocaleLowerCase("id-ID");
  if (!needsTidying) return value;

  const spaced = value.replaceAll("_", " ").toLocaleLowerCase("id-ID");
  return spaced.charAt(0).toLocaleUpperCase("id-ID") + spaced.slice(1);
}

/**
 * Jenis gangguan yang harus ditampilkan.
 *
 * Nama yang dikenal dipakai apa adanya; nama yang tidak dikenal (tautan usang, salah
 * ketik, atau jenis di luar cakupan wilayah pengguna) jatuh kembali ke jenis dengan
 * kejadian terbanyak, supaya paparan tidak pernah terbuka dengan layar kosong. Backend
 * menolak jenis tak dikenal dengan 400, jadi pemilihan harus terjadi sebelum permintaan
 * kedua dikirim — bukan sesudahnya.
 */
export function resolveThreatType(
  available: ThreatTypeCount[],
  requested: string | null,
): string | null {
  if (available.length === 0) return null;

  const wanted = requested?.trim().toUpperCase() ?? null;
  const known = available.find((row) => row.threat_type === wanted);
  // Daftar dari backend sudah urut terbanyak lebih dulu.
  return known?.threat_type ?? available[0].threat_type;
}

/** Tautan ke satu keadaan layar pola, supaya dapat disalin dan dibagikan saat paparan. */
export function patternHref(threatType: string): string {
  return `/pola?jenis=${encodeURIComponent(threatType)}`;
}

/**
 * Jumlah kejadian golongan terbesar dalam satu distribusi.
 *
 * Panjang batang diskalakan terhadap angka ini, bukan terhadap 100%. Alasannya: sebaran
 * 24 jam hampir tidak pernah melewati 12% per jam, sehingga batang berskala persen akan
 * rata-rata pendek dan tidak terbaca. Konsekuensinya batang terpanjang **bukan** berarti
 * 100% — karena itu setiap panel menyatakan skalanya, dan setiap batang tetap
 * mencantumkan jumlah dan persentasenya sendiri.
 */
export function peakOf(distribution: PatternDistribution): number {
  return distribution.buckets.reduce((peak, bucket) => Math.max(peak, bucket.incidents), 0);
}

/** Panjang batang dalam persen terhadap golongan terbesar; 0 bila distribusinya kosong. */
export function barWidth(incidents: number, peak: number): number {
  return peak === 0 ? 0 : Math.round((incidents / peak) * 100);
}

/**
 * "62% dari 464 kejadian" — persentase tidak pernah ditulis tanpa penyebutnya.
 *
 * Angka desimal memakai koma sesuai kaidah Bahasa Indonesia.
 */
export function shareText(sharePercent: number, denominator: number): string {
  const percent = sharePercent.toFixed(1).replace(".", ",");
  return `${percent}% dari ${denominator} kejadian`;
}

/** Tanggal ringkas untuk tabel pengulangan. */
export function formatDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}
