import { Panel } from "@/components/panel";
import type { DashboardSummary } from "@/lib/dashboard";
import { RISK_TEXT, riskClassOf } from "@/lib/risk";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded border border-base-800 bg-base-850 px-3 py-2.5">
      <div className="stat-label">{label}</div>
      <div className="mt-1 font-heading text-xl font-bold leading-none text-ink">{value}</div>
      {hint ? <div className="mt-1 text-2xs text-ink-muted">{hint}</div> : null}
    </div>
  );
}

export function SituationOverview({ summary }: { summary: DashboardSummary }) {
  // Indeks keamanan naik ketika risiko turun, sehingga kelasnya dibaca dari sisi risiko.
  const risk = riskClassOf(100 - summary.security_index);

  return (
    <Panel
      title="Situation Overview"
      action={
        summary.assessment_date ? (
          <span className="text-2xs text-ink-muted">Penilaian {summary.assessment_date}</span>
        ) : null
      }
    >
      <div className="mb-4 flex items-end gap-4">
        <div>
          <div className="stat-label">Security Index</div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className={`font-heading text-5xl font-bold leading-none ${RISK_TEXT[risk]}`}>
              {summary.security_index}
            </span>
            <span className="text-sm text-ink-muted">/100</span>
          </div>
        </div>
        <p className="flex-1 text-2xs leading-relaxed text-ink-muted">
          {summary.security_index_basis}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="Kejadian 24 Jam" value={summary.incidents_24h} />
        <Stat label="Prediksi 24 Jam" value={summary.predictions_24h} />
        <Stat label="High Risk Area" value={summary.high_risk_areas} />
        <Stat label="Warning Aktif" value={summary.active_warnings} />
        <Stat label="Operasi Berjalan" value={summary.active_operations} />
        <Stat
          label="Jam Kritis"
          value={summary.critical_time_window ?? "—"}
          hint="Jendela risiko tertinggi"
        />
      </div>
    </Panel>
  );
}
