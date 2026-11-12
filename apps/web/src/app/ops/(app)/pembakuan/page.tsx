import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ScreenTabs } from "@/components/shell/screen-tabs";
import { getProfile } from "@/lib/decisions";
import { getStandardQueue } from "@/lib/standardization";
import { AreaForm, DuplicateForm } from "./forms";

export const dynamic = "force-dynamic";

const TABS = [
  { href: "/ops/laporan-petugas", label: "Daftar kejadian" },
  { href: "/ops/input?formulir=kejadian", label: "+ Catat kejadian", permission: "crime:write" },
  { href: "/ops/pembakuan", label: "Pembakuan", permission: "crime:triage" },
] as const;

/** Pembakuan laporan (Modul 1 mekanisme): kelurahan tertunda dan dugaan laporan ganda. */
export default async function PembakuanPage() {
  const profile = await getProfile();
  if (!profile.permissions.includes("crime:triage")) {
    return <EmptyState label="Pembakuan laporan hanya untuk Administrator." />;
  }
  const queue = await getStandardQueue();
  return (
    <div className="space-y-3">
      <ScreenTabs tabs={TABS} current="/ops/pembakuan" permissions={profile.permissions} />
      <Panel
        title="Kelurahan belum pasti"
        action={<span className="panel-action">{queue.area_pending.total} menunggu</span>}
      >
        {queue.area_pending.data.length === 0 ? (
          <EmptyState label="Semua kejadian sudah punya kelurahan." />
        ) : (
          <ul className="divide-y divide-base-800">
            {queue.area_pending.data.map((row) => (
              <li
                key={row.code}
                className="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 text-xs"
              >
                <span className="font-mono text-ink-muted">{row.code}</span>
                <span className="font-semibold text-ink">{row.incident_type}</span>
                <span className="text-ink-faint">{row.incident_date}</span>
                <span className="text-ink-muted">Kec. {row.kecamatan}</span>
                {row.street ? <span className="text-ink-faint">{row.street}</span> : null}
                <span className="ml-auto">
                  <AreaForm
                    code={row.code}
                    options={queue.kelurahan_options[row.kecamatan] ?? []}
                  />
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel
        title="Dugaan laporan ganda"
        action={<span className="panel-action">{queue.suspected_duplicates.total} menunggu</span>}
      >
        {queue.suspected_duplicates.data.length === 0 ? (
          <EmptyState label="Tidak ada dugaan ganda." />
        ) : (
          <ul className="divide-y divide-base-800">
            {queue.suspected_duplicates.data.map((row) => (
              <li
                key={row.code}
                className="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 text-xs"
              >
                <span className="font-mono text-ink-muted">{row.code}</span>
                <span className="font-semibold text-ink">{row.incident_type}</span>
                <span className="text-ink-faint">{row.incident_date}</span>
                <span className="text-ink-muted">{row.kelurahan ?? row.kecamatan}</span>
                <span className="text-ink-faint">mirip {row.duplicate_of}</span>
                <span className="ml-auto">
                  <DuplicateForm code={row.code} />
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-2xs text-ink-faint">{queue.duplicate_basis}</p>
      </Panel>
    </div>
  );
}
