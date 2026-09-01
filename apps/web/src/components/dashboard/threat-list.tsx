import { Panel } from "@/components/panel";
import { RISK_BG, RISK_LABELS, RISK_TEXT, riskClassOf } from "@/lib/risk";

type Row = { label: string; score: number };

/** Daftar berperingkat dengan batang risiko — dipakai Top Threat dan Risk Index. */
export function ScoreList({
  title,
  rows,
  emptyLabel,
}: {
  title: string;
  rows: Row[];
  emptyLabel: string;
}) {
  if (rows.length === 0) {
    return (
      <Panel title={title}>
        <p className="text-sm text-ink-muted">{emptyLabel}</p>
      </Panel>
    );
  }

  return (
    <Panel title={title}>
      <ul className="space-y-2.5">
        {rows.map((row) => {
          const risk = riskClassOf(row.score);
          return (
            <li key={row.label} className="flex items-center gap-3">
              <span className="w-32 shrink-0 truncate text-xs text-ink" title={row.label}>
                {row.label}
              </span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
                <span
                  className={`block h-full rounded-full ${RISK_BG[risk]}`}
                  style={{ width: `${Math.min(100, Math.max(0, row.score))}%` }}
                />
              </span>
              <span className={`w-8 text-right font-mono text-xs font-semibold ${RISK_TEXT[risk]}`}>
                {row.score}
              </span>
              <span className="w-12 text-right text-[10px] uppercase text-ink-muted">
                {RISK_LABELS[risk]}
              </span>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
