/**
 * Tangga risiko dan labelnya.
 *
 * Ambang di sini **tidak boleh dianggap final**: nilainya mencerminkan
 * `config/risk/warning-thresholds.yaml` yang berstatus `DEMO / PROPOSED` (U-01).
 * Antarmuka hanya menampilkan; ambang sesungguhnya ditetapkan backend, sehingga
 * saat threshold resmi turun, tampilan ikut berubah tanpa perubahan kode di sini.
 */

export type RiskClass = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export const RISK_LABELS: Record<RiskClass, string> = {
  LOW: "Rendah",
  MODERATE: "Sedang",
  HIGH: "Tinggi",
  CRITICAL: "Kritis",
};

/** Ambang tampilan, sepadan dengan config/risk/warning-thresholds.yaml (DEMO/PROPOSED). */
const DISPLAY_BANDS: ReadonlyArray<{ max: number; risk: RiskClass }> = [
  { max: 44, risk: "LOW" },
  { max: 69, risk: "MODERATE" },
  { max: 84, risk: "HIGH" },
  { max: 100, risk: "CRITICAL" },
];

export function riskClassOf(score: number): RiskClass {
  const clamped = Math.min(100, Math.max(0, score));
  return DISPLAY_BANDS.find((band) => clamped <= band.max)?.risk ?? "CRITICAL";
}

/** Warna teks/aksen menurut kelas risiko. */
export const RISK_TEXT: Record<RiskClass, string> = {
  LOW: "text-risk-low",
  MODERATE: "text-risk-moderate",
  HIGH: "text-risk-high",
  CRITICAL: "text-risk-critical",
};

/** Warna latar batang/badge menurut kelas risiko. */
export const RISK_BG: Record<RiskClass, string> = {
  LOW: "bg-risk-low",
  MODERATE: "bg-risk-moderate",
  HIGH: "bg-risk-high",
  CRITICAL: "bg-risk-critical",
};

/** Nilai heksadesimal untuk keperluan SVG/peta yang tidak dapat memakai kelas Tailwind. */
export const RISK_HEX: Record<RiskClass, string> = {
  LOW: "#38bdf8",
  MODERATE: "#4ade80",
  HIGH: "#fb923c",
  CRITICAL: "#ef4444",
};
