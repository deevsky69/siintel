import { Panel } from "@/components/panel";
import type { OutlookRow } from "@/lib/dashboard";
import { RISK_BG, RISK_TEXT, riskClassOf } from "@/lib/risk";

const HORIZON_LABEL: Record<string, string> = {
  "6H": "+6 JAM",
  "12H": "+12 JAM",
  "24H": "+24 JAM",
  "3D": "+3 HARI",
  "7D": "+7 HARI",
};

export function OutlookPanel({ rows }: { rows: OutlookRow[] }) {
  return (
    <Panel title="Prediction Outlook">
      <div className="grid grid-cols-5 gap-2">
        {rows.map((row) => {
          const risk = row.risk_score === null ? null : riskClassOf(row.risk_score);
          return (
            <div key={row.horizon} className="text-center">
              <div className="stat-label mb-1.5">{HORIZON_LABEL[row.horizon] ?? row.horizon}</div>
              <div
                className={`flex h-14 items-center justify-center rounded border border-base-800 ${
                  risk ? `${RISK_BG[risk]}/15` : "bg-base-950/40"
                }`}
              >
                <span
                  className={`font-heading text-xl font-bold ${risk ? RISK_TEXT[risk] : "text-ink-muted"}`}
                >
                  {row.risk_score ?? "—"}
                </span>
              </div>
              <div className="mt-1.5 truncate text-2xs text-ink-muted" title={row.kecamatan ?? ""}>
                {row.kecamatan ?? "tidak ada"}
              </div>
              <div className="truncate text-2xs uppercase tracking-wider text-ink-muted">
                {row.threat_type ?? ""}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
