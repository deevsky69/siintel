import { Panel } from "@/components/panel";
import type { WarningRow } from "@/lib/dashboard";
import { RISK_TEXT, riskClassOf } from "@/lib/risk";

const SEVERITY_LABEL: Record<string, string> = {
  LOW: "Rendah",
  WATCH: "Waspada",
  WARNING: "Peringatan",
  CRITICAL: "Kritis",
};

export function EarlyWarningPanel({
  warning,
  total,
}: {
  warning: WarningRow | null;
  total: number;
}) {
  if (!warning) {
    return (
      <Panel title="Early Warning">
        <p className="text-sm text-ink-muted">Tidak ada peringatan aktif.</p>
      </Panel>
    );
  }

  const risk = riskClassOf(warning.risk_score);

  return (
    <Panel title="Early Warning" action={<span className="panel-action">{total} aktif</span>}>
      <div className="rounded border border-risk-critical/40 bg-risk-critical/5 p-3">
        <div className="mb-3 flex items-center gap-2">
          <span className={`font-heading text-sm font-bold ${RISK_TEXT[risk]}`}>
            {SEVERITY_LABEL[warning.severity] ?? warning.severity}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-ink-muted">
            {warning.code}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5">
          <div>
            <dt className="stat-label">Ancaman</dt>
            <dd className="mt-0.5 font-heading text-sm font-semibold text-ink">
              {warning.threat_type}
            </dd>
          </div>
          <div className="text-right">
            <dt className="stat-label">Risk Score</dt>
            <dd
              className={`mt-0.5 font-heading text-2xl font-bold leading-none ${RISK_TEXT[risk]}`}
            >
              {warning.risk_score}
              <span className="text-xs text-ink-muted">/100</span>
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="stat-label">Lokasi</dt>
            <dd className="mt-0.5 text-sm text-ink">
              {warning.kecamatan}
              {warning.kelurahan ? ` — ${warning.kelurahan}` : ""}
            </dd>
          </div>
          <div>
            <dt className="stat-label">Jendela Waktu</dt>
            <dd className="mt-0.5 font-mono text-sm text-ink">{warning.time_window ?? "—"}</dd>
          </div>
          <div>
            <dt className="stat-label">Confidence</dt>
            <dd className="mt-0.5 font-mono text-sm text-ink">
              {warning.confidence !== null ? `${warning.confidence}%` : "—"}
            </dd>
          </div>
        </dl>
      </div>
    </Panel>
  );
}
