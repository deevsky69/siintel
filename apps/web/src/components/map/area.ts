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
export type MapLayer = "current" | "predictive";

export const MAP_LAYERS: ReadonlyArray<{ id: MapLayer; label: string }> = [
  { id: "current", label: "Risiko Berjalan" },
  { id: "predictive", label: "Prediktif" },
] as const;

export function toMapLayer(value: string | null | undefined): MapLayer {
  return value === "predictive" ? "predictive" : "current";
}

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
export function mapHref(kecamatan: string | null, layer: MapLayer = "current"): string {
  const params = new URLSearchParams();
  if (kecamatan !== null) params.set("wilayah", kecamatan);
  if (layer !== "current") params.set("layer", layer);
  const query = params.toString();
  return query === "" ? "/peta" : `/peta?${query}`;
}

/** Warna tunggal layer prediktif: aksen sian, bukan salah satu warna kelas risiko. */
export const PREDICTIVE_HEX = "#22d3ee";

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
