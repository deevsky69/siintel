import type { RiskClass } from "@/lib/risk";
import { RISK_HEX, RISK_LABELS, riskClassOf } from "@/lib/risk";
import type { MapLayer } from "./area";
import { HISTORICAL_HEX, historicalOpacity, PREDICTIVE_HEX, predictiveOpacity } from "./area";

/**
 * Legenda peta.
 *
 * Layer risiko berjalan memakai tangga kelas: rentang angkanya **diturunkan dari
 * `riskClassOf`**, tidak ditulis ulang di sini, supaya ambang hanya hidup di satu tempat
 * (CLAUDE.md §12). Bila ambang resmi kelak menggantikan ambang DEMO / PROPOSED, legenda
 * ikut berubah tanpa penyuntingan.
 *
 * Layer prediktif **tidak punya tangga kelas**: API tidak mengirim `risk_class` untuk
 * prediksi karena ambangnya belum ditetapkan (U-01). Legendanya karena itu berupa skala
 * menerus 0–100 dengan pernyataan terbuka bahwa yang ditampilkan adalah skor mentah.
 *
 * Layer historis tidak punya tangga kelas **maupun** skala mutlak: yang digambar adalah
 * cacah kejadian, dan kepekatannya relatif terhadap wilayah terbanyak pada jendela yang
 * sedang tampil. Legendanya karena itu menyebut angka puncak yang sedang berlaku — tanpa
 * itu, pembaca akan menyangka warna yang sama berarti jumlah yang sama di jendela lain.
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

/** Titik contoh skala prediktif — hanya penanda skala, bukan ambang kelas. */
const PREDICTIVE_TICKS = [0, 25, 50, 75, 100] as const;

function CurrentRiskLegend() {
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

function PredictiveLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      <span className="stat-label">Skor Prediksi</span>
      {PREDICTIVE_TICKS.map((tick) => (
        <span key={tick} className="flex items-center gap-1.5 text-[11px] text-ink-muted">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: PREDICTIVE_HEX, opacity: predictiveOpacity(tick) }}
          />
          <span className="font-mono">{tick}</span>
        </span>
      ))}
      <span className="text-[10px] uppercase tracking-wider text-ink-faint">
        Skor mentah 0–100 · tanpa kelas risiko resmi
      </span>
    </div>
  );
}

function HistoricalLegend({ peak, total }: { peak: number; total: number }) {
  const ticks = peak > 0 ? [0, Math.round(peak / 2), peak] : [0];

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      <span className="stat-label">Cacah Kejadian</span>
      {ticks.map((tick) => (
        <span key={tick} className="flex items-center gap-1.5 text-[11px] text-ink-muted">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: HISTORICAL_HEX, opacity: historicalOpacity(tick, peak) }}
          />
          <span className="font-mono">{tick}</span>
        </span>
      ))}
      <span className="flex items-center gap-1.5 text-[11px] text-ink-muted">
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full border border-base-950"
          style={{ backgroundColor: HISTORICAL_HEX, opacity: 0.55 }}
        />
        <span>titik = lokasi, luasnya sebanding cacah</span>
      </span>
      <span className="text-[10px] uppercase tracking-wider text-ink-faint">
        Skala relatif · {total} kejadian pada jendela ini · bukan kelas risiko
      </span>
    </div>
  );
}

export function RiskLegend({
  layer = "current",
  historical,
}: {
  layer?: MapLayer;
  historical?: { peakIncidents: number; totalIncidents: number };
}) {
  if (layer === "historical") {
    return (
      <HistoricalLegend
        peak={historical?.peakIncidents ?? 0}
        total={historical?.totalIncidents ?? 0}
      />
    );
  }
  return layer === "predictive" ? <PredictiveLegend /> : <CurrentRiskLegend />;
}
