import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import { getBulletins } from "@/lib/babin";
import { getProfile } from "@/lib/decisions";
import { ApproveButton, GenerateForm } from "./bulletin-forms";

export const dynamic = "force-dynamic";

const LABEL = { DRAFT: "Draf", APPROVED: "Disetujui, menunggu bot", SENT: "Terkirim" } as const;

/**
 * Buletin mingguan kelurahan (tahap 3): disusun sistem, disetujui Pimpinan, dikirim bot ke
 * grup Telegram kelurahan dan/atau WhatsApp Babin. Human-in-the-loop seperti imbauan.
 */
export default async function BuletinPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return (Array.isArray(value) ? value[0] : value) ?? "";
  };
  const profile = await getProfile();
  const list = await getBulletins(one("minggu"), one("status").toUpperCase());
  const canManage = profile.permissions.includes("bulletin:manage");
  const canApprove = profile.permissions.includes("bulletin:approve");
  const week = one("minggu") || list.weeks[0] || "";
  const rows = week ? list.data.filter((row) => row.week_start === week) : list.data;

  return (
    <div className="space-y-3">
      <StatusNotice status="PROPOSED" tone="caution">
        Buletin adalah penerbitan informasi kepada warga: hanya yang disetujui Pimpinan yang
        dikirim.
      </StatusNotice>
      {canManage ? (
        <Panel title="Susun Buletin">
          <GenerateForm suggested={list.suggested_week} />
          <p className="mt-2 text-2xs leading-relaxed text-ink-faint">{list.basis}</p>
        </Panel>
      ) : null}
      <Panel
        title={`Buletin Minggu ${week || "—"}`}
        action={
          <span className="panel-action">
            {list.weeks.map((value) => (
              <Link
                key={value}
                href={`/ops/buletin?minggu=${value}`}
                className={`mr-2 ${value === week ? "text-accent" : ""}`}
              >
                {value}
              </Link>
            ))}
          </span>
        }
      >
        {rows.length === 0 ? (
          <EmptyState label="Belum ada buletin untuk minggu ini. Susun draf terlebih dahulu." />
        ) : (
          <ul className="divide-y divide-base-800">
            {rows.map((row) => (
              <li key={row.id} className="py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                  <span className="font-heading font-semibold text-ink">{row.kelurahan}</span>
                  <span className="text-ink-faint">{row.kecamatan}</span>
                  <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs text-ink-muted">
                    {LABEL[row.status]}
                  </span>
                  <span className="text-ink-faint">{row.figures.total ?? 0} kejadian</span>
                  {row.status === "DRAFT" && canApprove ? <ApproveButton id={row.id} /> : null}
                  {row.status === "SENT" ? (
                    <span className="text-2xs text-ink-faint">
                      {Object.entries(row.delivery)
                        .map(([channel, result]) => `${channel}: ${result}`)
                        .join(" · ")}
                    </span>
                  ) : null}
                </div>
                <details className="mt-1">
                  <summary className="cursor-pointer text-2xs text-accent">Lihat isi</summary>
                  <pre className="mt-1 whitespace-pre-wrap rounded bg-base-850 p-3 font-sans text-xs leading-relaxed text-ink">
                    {row.content}
                  </pre>
                </details>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
