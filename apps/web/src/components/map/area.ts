import type { RiskClass } from "@/lib/risk";
import { RISK_LABELS } from "@/lib/risk";

/**
 * Pembantu tampilan peta — murni, tanpa pemanggilan API.
 *
 * Dipisahkan dari `lib/map-data.ts` dengan sengaja: modul itu memanggil `lib/api.ts`, yang
 * membaca cookie sesi dan karenanya hanya boleh hidup di server. Bidang gambar peta adalah
 * komponen klien (ia menyimpan wilayah yang sedang disorot), jadi apa pun yang ikut ke
 * peramban harus bebas dari jalur itu.
 */

/** Layer peta pada CLAUDE.md §24 yang digambar di bidang yang sama. */
export type MapLayer = "historical" | "current" | "predictive";

/**
 * Urutannya mengikuti arah waktu — sudah terjadi, sedang berjalan, diperkirakan — supaya
 * peta terbaca sebagai satu garis waktu dan bukan tiga tampilan yang kebetulan bertetangga.
 */
export const MAP_LAYERS: ReadonlyArray<{ id: MapLayer; label: string }> = [
  { id: "historical", label: "Historis" },
  { id: "current", label: "Risiko Berjalan" },
  { id: "predictive", label: "Prediktif" },
] as const;

export function toMapLayer(value: string | null | undefined): MapLayer {
  if (value === "predictive") return "predictive";
  if (value === "historical") return "historical";
  return "current";
}

/** Panjang jendela historis yang dilayani `GET /map/historical`. */
export const HISTORICAL_MONTHS = [1, 3, 12, 36] as const;

export type HistoricalMonths = (typeof HISTORICAL_MONTHS)[number];

export const DEFAULT_HISTORICAL_MONTHS: HistoricalMonths = 12;

/**
 * Panjang jendela dari alamat.
 *
 * Nilai yang tidak dilayani API **dibuang**, bukan diteruskan: meneruskannya hanya
 * memindahkan penolakan 400 ke tengah halaman, padahal jawaban yang benar untuk tautan
 * usang adalah jendela bawaan.
 */
export function toHistoricalMonths(value: string | null | undefined): HistoricalMonths {
  const parsed = Number(value);
  return HISTORICAL_MONTHS.find((month) => month === parsed) ?? DEFAULT_HISTORICAL_MONTHS;
}

export const HISTORICAL_MONTH_LABELS: Record<HistoricalMonths, string> = {
  1: "1 bulan",
  3: "3 bulan",
  12: "12 bulan",
  36: "Seluruh data",
};

/**
 * Kelas risiko dari respons API.
 *
 * Nilai yang tidak dikenal antarmuka dijawab `null`, **bukan** diturunkan dari skor:
 * menurunkan kelas sendiri berarti menaruh ambang kedua di layar, sementara ambang
 * hanya boleh hidup di satu tempat (CLAUDE.md §12). Wilayah tanpa kelas yang dikenal
 * digambar sebagai "tanpa kelas", bukan diberi kelas karangan.
 */
export function toRiskClass(value: string | null | undefined): RiskClass | null {
  return value != null && value in RISK_LABELS ? (value as RiskClass) : null;
}

/**
 * Tautan ke satu keadaan peta.
 *
 * Wilayah terpilih **dan** layer keduanya hidup di alamat, sehingga keadaan peta yang
 * sedang dibicarakan dapat disalin dan dibagikan saat paparan. Layer bawaan tidak ditulis
 * ke alamat supaya tautan yang paling sering dibagikan tetap pendek.
 */
export function mapHref(
  kecamatan: string | null,
  layer: MapLayer = "current",
  months: HistoricalMonths = DEFAULT_HISTORICAL_MONTHS,
): string {
  const params = new URLSearchParams();
  if (kecamatan !== null) params.set("wilayah", kecamatan);
  if (layer !== "current") params.set("layer", layer);
  // Jendela hanya ditulis bila layer historis sedang tampil **dan** bukan jendela bawaan:
  // parameter yang tidak berpengaruh pada layer lain hanya memanjangkan tautan paparan.
  if (layer === "historical" && months !== DEFAULT_HISTORICAL_MONTHS) {
    params.set("bulan", String(months));
  }
  const query = params.toString();
  return query === "" ? "/peta" : `/peta?${query}`;
}

/** Warna tunggal layer prediktif: aksen sian, bukan salah satu warna kelas risiko. */
export const PREDICTIVE_HEX = "#22d3ee";

/**
 * Warna layer historis: kuning-jingga, sengaja jauh dari sian prediktif **dan** dari
 * tangga merah kelas risiko. Cacah kejadian bukan risiko, dan tidak boleh terbaca begitu
 * hanya karena warnanya mirip.
 */
export const HISTORICAL_HEX = "#f59e0b";

const HISTORICAL_OPACITY = { min: 0.12, max: 0.82 } as const;

/**
 * Kepekatan wilayah pada layer historis, relatif terhadap wilayah dengan kejadian
 * terbanyak pada jendela yang sedang tampil.
 *
 * Skalanya **relatif, bukan mutlak** — dan itu keputusan yang perlu disadari pembacanya:
 * wilayah paling pekat adalah yang terbanyak *pada jendela ini*, bukan wilayah yang
 * melewati ambang mana pun. Tidak ada ambang yang boleh dipakai di sini, karena cacah
 * kejadian tidak punya kelas (lihat `aggregation_basis` dari API).
 *
 * `peak` nol atau negatif menghasilkan kepekatan terendah untuk semua wilayah, bukan
 * pembagian dengan nol.
 */
export function historicalOpacity(incidents: number, peak: number): number {
  if (peak <= 0 || incidents <= 0) return HISTORICAL_OPACITY.min;
  const ratio = Math.min(1, incidents / peak);
  return HISTORICAL_OPACITY.min + ratio * (HISTORICAL_OPACITY.max - HISTORICAL_OPACITY.min);
}

/** Jari-jari titik lokasi, mengikuti akar cacah supaya luas lingkaran sebanding cacahnya. */
export function pointRadius(incidents: number, peak: number): number {
  if (peak <= 0) return MIN_POINT_RADIUS;
  const ratio = Math.sqrt(Math.max(1, incidents)) / Math.sqrt(Math.max(1, peak));
  return MIN_POINT_RADIUS + ratio * (MAX_POINT_RADIUS - MIN_POINT_RADIUS);
}

const MIN_POINT_RADIUS = 7;
const MAX_POINT_RADIUS = 26;

/** Kepekatan terendah dan tertinggi layer prediktif, supaya skor kecil tetap terbaca. */
const PREDICTIVE_OPACITY = { min: 0.18, max: 0.88 } as const;

/**
 * Kepekatan warna layer prediktif menurut skor.
 *
 * Skala menerus dipakai dengan sengaja: prediksi tidak punya kelas risiko (U-01), jadi
 * warnanya tidak boleh terbaca sebagai empat tingkat yang seolah sudah ditetapkan.
 */
export function predictiveOpacity(score: number): number {
  const ratio = Math.min(100, Math.max(0, score)) / 100;
  return PREDICTIVE_OPACITY.min + ratio * (PREDICTIVE_OPACITY.max - PREDICTIVE_OPACITY.min);
}
