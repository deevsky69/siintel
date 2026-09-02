import { Panel } from "@/components/panel";
import type { LeadershipBoard } from "@/lib/leadership";

/**
 * Isu menonjol sepekan terakhir, dibandingkan terhadap pekan sebelumnya.
 *
 * Perubahan disajikan sebagai **selisih kejadian**, bukan persentase — dari basis satu
 * kejadian menjadi tiga, "naik 200%" terbaca jauh lebih dramatis daripada kenyataannya, dan
 * layar pimpinan adalah tempat terakhir yang pantas melebih-lebihkan.
 */
export function ProminentIssues({ issues }: { issues: LeadershipBoard["prominent_issues"] }) {
  const peak = issues.issues.reduce((best, row) => Math.max(best, row.incidents), 0);

  return (
    <Panel
      title="Isu Menonjol Sepekan"
      action={
        <span className="text-[10px] text-ink-faint">
          {issues.window_from} s.d. {issues.window_to}
        </span>
      }
    >
      {issues.issues.length === 0 ? (
        <p className="text-xs text-ink-muted">
          Tidak ada kejadian tercatat pada pekan ini untuk kewenangan Anda.
        </p>
      ) : (
        <ul className="space-y-2">
          {issues.issues.map((row) => (
            <li key={row.threat_type}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs text-ink">{row.threat_type}</span>
                <span className="flex items-baseline gap-2 font-mono text-xs">
                  <span className="text-ink">{row.incidents}</span>
                  <span
                    className={
                      row.change > 0
                        ? "text-risk-critical"
                        : row.change < 0
                          ? "text-risk-moderate"
                          : "text-ink-faint"
                    }
                  >
                    {row.change > 0 ? `+${row.change}` : row.change}
                  </span>
                </span>
              </div>
              <div className="mt-1 h-1 rounded bg-base-800">
                <div
                  className="h-1 rounded bg-accent/70"
                  style={{ width: `${peak === 0 ? 0 : (row.incidents / peak) * 100}%` }}
                />
              </div>
              <p className="mt-0.5 text-[10px] text-ink-faint">
                Pekan sebelumnya {row.previous_incidents} kejadian
              </p>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">{issues.basis}</p>
    </Panel>
  );
}
