import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getProfile } from "@/lib/decisions";
import { getRanking, getRankingOptions } from "@/lib/rankings";
import { FreezeForm } from "./freeze-form";

export const dynamic = "force-dynamic";

const CATEGORY: Record<string, string> = {
  RENDAH: "bg-risk-low/15 text-risk-low",
  SEDANG: "bg-risk-moderate/15 text-risk-moderate",
  TINGGI: "bg-risk-high/15 text-risk-high",
};

/** Peringkat bulanan 65 kelurahan (Modul 2–3 mekanisme). */
export default async function PeringkatPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return (Array.isArray(value) ? value[0] : value) ?? "";
  };
  const [profile, options] = await Promise.all([getProfile(), getRankingOptions()]);
  const month = one("bulan") || options.suggested_month;
  const method = one("metode") || options.default_method;
  const scope = one("cakupan") || options.default_scope;
  const ranking = await getRanking(month, method, scope);
  const canManage = profile.permissions.includes("ranking:manage");
  const link = (next: Partial<{ bulan: string; metode: string; cakupan: string }>) => {
    const query = new URLSearchParams({ bulan: month, metode: method, cakupan: scope, ...next });
    return `/ops/peringkat?${query.toString()}`;
  };

  return (
    <div className="space-y-3">
      <Panel
        title={`Peringkat ${ranking.target_month}`}
        action={
          <span className="panel-action flex flex-wrap items-center gap-2">
            {options.methods
              .filter((item) => item.available)
              .map((item) => (
                <Link
                  key={item.value}
                  href={link({ metode: item.value })}
                  className={item.value === method ? "text-accent" : ""}
                >
                  {item.label}
                </Link>
              ))}
            <span className="text-ink-faint">·</span>
            {options.scopes.map((item) => (
              <Link
                key={item}
                href={link({ cakupan: item })}
                className={item === scope ? "text-accent" : ""}
              >
                {item === "VEHICLE" ? "Kendaraan" : "Semua 3C"}
              </Link>
            ))}
          </span>
        }
      >
        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
          <span>
            Dasar {ranking.basis_from} – {ranking.basis_to}
          </span>
          <span>Batas data {ranking.data_cutoff}</span>
          <span>{ranking.pending_count} laporan menunggu konfirmasi kelurahan</span>
          {ranking.frozen ? (
            <span className="rounded bg-risk-low/15 px-1.5 py-0.5 font-semibold text-risk-low">
              Dibekukan
            </span>
          ) : canManage ? (
            <FreezeForm month={month} method={method} scope={scope} />
          ) : (
            <span className="text-ink-faint">Belum dibekukan</span>
          )}
        </div>
        {ranking.data.length === 0 ? (
          <EmptyState label="Belum ada kelurahan." />
        ) : (
          <table className="w-full text-xs">
            <thead className="text-left text-2xs uppercase tracking-wide text-ink-faint">
              <tr>
                <th className="py-1 pr-2">#</th>
                <th className="py-1 pr-2">Kelurahan</th>
                <th className="py-1 pr-2">Kecamatan</th>
                <th className="py-1 pr-2 text-right">Perkiraan/bulan</th>
                <th className="py-1 pr-2 text-right">Dasar</th>
                <th className="py-1 pr-2 text-right">IKW</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-base-800">
              {ranking.data.map((row) => (
                <tr key={row.kelurahan} className={row.rank <= 6 ? "bg-accent/5" : ""}>
                  <td className="py-1.5 pr-2 tabular-nums text-ink-muted">{row.rank}</td>
                  <td className="py-1.5 pr-2 font-semibold text-ink">{row.kelurahan}</td>
                  <td className="py-1.5 pr-2 text-ink-muted">{row.kecamatan}</td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                    {row.predicted_count.toFixed(1)}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink-faint">
                    {row.basis.basis_total ?? 0}
                  </td>
                  <td className="py-1.5 pr-2 text-right">
                    {row.ikw !== null && row.ikw_category ? (
                      <span
                        className={`rounded px-1.5 py-0.5 tabular-nums ${CATEGORY[row.ikw_category] ?? ""}`}
                      >
                        {row.ikw.toFixed(0)}
                      </span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-2xs text-ink-faint">
          {ranking.method_label} · {ranking.model_version} · IKW {ranking.ikw_status}
        </p>
      </Panel>
    </div>
  );
}
