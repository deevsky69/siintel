import { Panel } from "@/components/panel";
import type { UnitCount } from "@/lib/dashboard";

const STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Aktif",
  STANDBY: "Siaga",
  INACTIVE: "Tidak Aktif",
};

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: "bg-risk-moderate",
  STANDBY: "bg-risk-low",
  INACTIVE: "bg-base-600",
};

export function PatrolStatus({ units, operations }: { units: UnitCount[]; operations: number }) {
  const total = units.reduce((sum, row) => sum + row.count, 0);

  return (
    <Panel title="Patrol Status">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="font-heading text-3xl font-bold leading-none text-ink">{total}</span>
        <span className="stat-label">unit terdaftar</span>
      </div>

      <ul className="space-y-2">
        {units.map((row) => (
          <li key={row.status} className="flex items-center gap-2.5">
            <span className={`h-2 w-2 rounded-full ${STATUS_COLOR[row.status] ?? "bg-base-600"}`} />
            <span className="flex-1 text-xs text-ink">
              {STATUS_LABEL[row.status] ?? row.status}
            </span>
            <span className="font-mono text-xs text-ink-muted">
              {row.count} ({total ? Math.round((row.count / total) * 100) : 0}%)
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-3 border-t border-base-800 pt-3">
        <div className="stat-label">Penugasan berjalan</div>
        <div className="mt-1 font-heading text-lg font-bold text-ink">{operations}</div>
      </div>
    </Panel>
  );
}
