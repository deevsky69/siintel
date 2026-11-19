import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ScreenTabs } from "@/components/shell/screen-tabs";
import { getProfile } from "@/lib/decisions";
import {
  getDataQuality,
  getImpactQueue,
  getMatchQueue,
  getStandardQueue,
} from "@/lib/standardization";
import { AreaForm, DuplicateForm, ImpactForm, MatchForm } from "./forms";

export const dynamic = "force-dynamic";

const TABS = [
  { href: "/ops/laporan-petugas", label: "Daftar kejadian" },
  { href: "/ops/input?formulir=kejadian", label: "+ Catat kejadian", permission: "crime:write" },
  { href: "/ops/pembakuan", label: "Mutu Data", permission: "crime:triage" },
] as const;

/**
 * Mutu Data (Modul 1; naskah Taskap 4.1 dan Tabel 22, 18 November 2026): kelengkapan isian,
 * isian yang ditandai untuk diperiksa, pencocokan laporan warga dengan kejadian resmi,
 * kelurahan tertunda, dan dugaan laporan ganda. Sistem menandai dan mengusulkan; petugas
 * yang memutuskan, dengan alasan.
 */
export default async function PembakuanPage() {
  const profile = await getProfile();
  if (!profile.permissions.includes("crime:triage")) {
    return <EmptyState label="Mutu data hanya untuk Administrator." />;
  }
  // Tiga permintaan berjalan bersamaan; ringkasan mutu dan antrean pencocokan boleh gagal
  // tanpa menjatuhkan antrean pembakuan yang sudah ada.
  const [queue, quality, matches, impact] = await Promise.all([
    getStandardQueue(),
    getDataQuality().catch(() => null),
    getMatchQueue().catch(() => null),
    getImpactQueue().catch(() => null),
  ]);
  const pct = (value: number | null) => (value === null ? "—" : `${value.toFixed(2)}%`);
  return (
    <div className="space-y-3">
      <ScreenTabs tabs={TABS} current="/ops/pembakuan" permissions={profile.permissions} />
      {quality ? (
        <Panel
          title="Kelengkapan dan hitungan"
          action={<span className="panel-action">{quality.incidents} laporan 3C</span>}
        >
          <div className="grid gap-4 lg:grid-cols-3">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Isian</th>
                  <th className="text-right">Terisi</th>
                  <th className="text-right">%</th>
                </tr>
              </thead>
              <tbody>
                {quality.completeness.map((row) => (
                  <tr key={row.field}>
                    <td>{row.label}</td>
                    <td className="text-right tabular-nums">{row.filled}</td>
                    <td className="text-right tabular-nums">{pct(row.pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ditandai untuk diperiksa</th>
                  <th className="text-right">Jumlah</th>
                </tr>
              </thead>
              <tbody>
                {quality.flags.map((row) => (
                  <tr key={row.kind}>
                    <td>{row.label}</td>
                    <td className="text-right tabular-nums">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hitungan kejadian</th>
                  <th className="text-right">Jumlah</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Kejadian resmi</td>
                  <td className="text-right tabular-nums">{quality.counting.official}</td>
                </tr>
                <tr>
                  <td>Laporan warga tertaut (terhitung sekali)</td>
                  <td className="text-right tabular-nums">{quality.counting.linked_reports}</td>
                </tr>
                <tr>
                  <td>Kejadian tambahan terverifikasi</td>
                  <td className="text-right tabular-nums">
                    {quality.counting.additional_verified}
                  </td>
                </tr>
                <tr>
                  <td>Menunggu pencocokan</td>
                  <td className="text-right tabular-nums">{quality.counting.awaiting_match}</td>
                </tr>
                <tr>
                  <td>Menunggu pemeriksaan</td>
                  <td className="text-right tabular-nums">
                    {quality.counting.awaiting_verification}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-2xs text-ink-faint">{quality.basis}</p>
        </Panel>
      ) : null}
      {matches ? (
        <Panel
          title="Laporan warga dan kejadian resmi"
          action={<span className="panel-action">{matches.total} menunggu</span>}
        >
          {matches.data.length === 0 ? (
            <EmptyState label="Tidak ada laporan warga terverifikasi yang menunggu pencocokan." />
          ) : (
            <ul className="divide-y divide-base-800">
              {matches.data.map((row) => (
                <li key={row.code} className="space-y-1.5 py-2 text-xs">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-mono text-ink-muted">{row.code}</span>
                    <span className="font-semibold text-ink">{row.category}</span>
                    <span className="text-ink-faint">{row.reported_at.slice(0, 10)}</span>
                    <span className="text-ink-muted">{row.kelurahan ?? row.kecamatan ?? "—"}</span>
                    <span className="text-ink-faint">
                      {row.candidates.length} usulan padanan (±{matches.window_days} hari)
                    </span>
                  </div>
                  {row.description ? <p className="text-ink-muted">{row.description}</p> : null}
                  <MatchForm code={row.code} candidates={row.candidates} />
                </li>
              ))}
            </ul>
          )}
        </Panel>
      ) : null}
      {impact ? (
        <Panel
          title="Dampak belum terverifikasi"
          action={
            <span className="panel-action">
              {impact.verified}/{impact.reports} terverifikasi · {impact.from} – {impact.to}
            </span>
          }
        >
          {impact.data.length === 0 ? (
            <EmptyState label="Seluruh laporan tiga bulan terakhir sudah terverifikasi dampaknya." />
          ) : (
            <ul className="divide-y divide-base-800">
              {impact.data.map((row) => (
                <li key={row.code} className="space-y-1.5 py-2 text-xs">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-mono text-ink-muted">{row.code}</span>
                    <span className="font-semibold text-ink">{row.incident_type}</span>
                    <span className="text-ink-faint">{row.incident_date}</span>
                    <span className="text-ink-muted">{row.kelurahan ?? row.kecamatan}</span>
                    <span className="text-ink-faint">{row.target_type ?? "—"}</span>
                  </div>
                  <ImpactForm code={row.code} />
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-2xs text-ink-faint">
            Dampak adalah unsur D pada IKW. Selama laporan tiga bulan terakhir di sebuah kelurahan
            belum terverifikasi dampaknya, IKW kelurahan itu berstatus sementara atau ditahan.
          </p>
        </Panel>
      ) : null}
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
