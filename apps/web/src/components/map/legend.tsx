import type { RiskClass } from "@/lib/risk";
import { RISK_HEX, RISK_LABELS, riskClassOf } from "@/lib/risk";

/**
 * Legenda RISK LEVEL.
 *
 * Rentang angka **diturunkan dari `riskClassOf`**, tidak ditulis ulang di sini: ambang
 * hanya boleh hidup di satu tempat (CLAUDE.md §12). Bila ambang resmi kelak menggantikan
 * ambang DEMO/PROPOSED, legenda ikut berubah tanpa penyuntingan.
 */
export type RiskBand = { risk: RiskClass; min: number; max: number };

export function riskBands(): RiskBand[] {
  const bands: RiskBand[] = [];
  for (let score = 0; score <= 100; score += 1) {
    const risk = riskClassOf(score);
    const last = bands.at(-1);
    if (last && last.risk === risk) last.max = score;
    else bands.push({ risk, min: score, max: score });
  }
  return bands;
}

export function RiskLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      <span className="stat-label">Risk Level</span>
      {riskBands().map((band) => (
        <span key={band.risk} className="flex items-center gap-1.5 text-[11px] text-ink-muted">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: RISK_HEX[band.risk] }}
          />
          <span className="font-mono">
            {band.min}–{band.max}
          </span>
          <span className="uppercase">{RISK_LABELS[band.risk]}</span>
        </span>
      ))}
      <span className="text-[10px] uppercase tracking-wider text-ink-faint">
        Ambang DEMO / PROPOSED
      </span>
    </div>
  );
}
