import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import { getAdvisoryApproval, getBulletins } from "@/lib/babin";
import { getProfile } from "@/lib/decisions";
import { AdvisoryApproveForm, ApproveButton, GenerateForm } from "./bulletin-forms";

export const dynamic = "force-dynamic";

const LABEL = { DRAFT: "Draf", APPROVED: "Disetujui, menunggu bot", SENT: "Terkirim" } as const;

/**
 * Persetujuan warga — SATU antrean (10 November 2026, keputusan pemilik proyek 2.iii).
 *
 * Imbauan bulanan ke grup warga dan buletin mingguan kelurahan sama-sama penerbitan informasi
 * kepada warga yang menunggu persetujuan Pimpinan; sebelumnya keduanya panel terpisah.
 * Kini: satu daftar "menunggu persetujuan" (imbauan bulan berjalan + seluruh buletin draf,
 * lintas minggu), lalu riwayat per minggu. Administrator tetap menyusun draf di sini.
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
  const [history, drafts, advisory] = await Promise.all([
    getBulletins(one("minggu"), ""),
    getBulletins("", "DRAFT"),
    getAdvisoryApproval().catch(() => null),
  ]);
  const canManage = profile.permissions.includes("bulletin:manage");
  const canApprove = profile.permissions.includes("bulletin:approve");
  const week = one("minggu") || history.weeks[0] || "";
  const sent = (week ? history.data.filter((row) => row.week_start === week) : history.data).filter(
    (row) => row.status !== "DRAFT",
  );
  const advisoryPending = advisory !== null && !advisory.approved;
  const waiting = (advisoryPending ? 1 : 0) + drafts.data.length;

  return (
    <div className="space-y-3">
      <StatusNotice status="PROPOSED" tone="caution">
        Penerbitan informasi kepada warga: imbauan bulanan dan buletin mingguan hanya terkirim
        setelah disetujui Pimpinan. Satu antrean untuk keduanya.
      </StatusNotice>

      <Panel
        title="Menunggu persetujuan"
        action={
          <span className="panel-action">
            {waiting === 0 ? "tidak ada" : `${waiting} menunggu`}
            {advisory ? ` · ${advisory.groups_registered} grup warga terdaftar` : ""}
          </span>
        }
      >
        {waiting === 0 ? (
          <EmptyState label="Tidak ada imbauan maupun buletin yang menunggu persetujuan." />
        ) : (
          <ul className="divide-y divide-base-800">
            {advisoryPending && advisory ? (
              <li className="py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                  <span className="rounded bg-accent/10 px-1.5 py-0.5 text-2xs font-semibold text-accent">
                    IMBAUAN BULANAN
                  </span>
                  <span className="font-heading font-semibold text-ink">{advisory.month}</span>
                  <span className="text-ink-faint">
                    ke {advisory.groups_registered} grup warga terdaftar
                  </span>
                  {canApprove ? <AdvisoryApproveForm month={advisory.month} /> : null}
                </div>
                {advisory.sample ? (
                  <details className="mt-1">
                    <summary className="cursor-pointer text-2xs text-accent">
                      Contoh teks ({advisory.sample.kelurahan})
                    </summary>
                    <pre className="mt-1 whitespace-pre-wrap rounded bg-base-850 p-3 font-sans text-xs leading-relaxed text-ink">
                      {advisory.sample.text}
                    </pre>
                  </details>
                ) : null}
              </li>
            ) : null}
            {drafts.data.map((row) => (
              <li key={row.id} className="py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                  <span className="rounded bg-base-800 px-1.5 py-0.5 text-2xs font-semibold text-ink-muted">
                    BULETIN {row.week_start}
                  </span>
                  <span className="font-heading font-semibold text-ink">{row.kelurahan}</span>
                  <span className="text-ink-faint">{row.kecamatan}</span>
                  <span className="text-ink-faint">{row.figures.total ?? 0} kejadian</span>
                  {canApprove ? <ApproveButton id={row.id} /> : null}
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

      {canManage ? (
        <Panel title="Susun Buletin">
          <GenerateForm suggested={history.suggested_week} />
          <p className="mt-2 text-2xs leading-relaxed text-ink-faint">{history.basis}</p>
        </Panel>
      ) : null}

      <Panel
        title={`Riwayat buletin minggu ${week || "—"}`}
        action={
          <span className="panel-action">
            {history.weeks.map((value) => (
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
        {sent.length === 0 ? (
          <EmptyState label="Belum ada buletin yang disetujui atau terkirim pada minggu ini." />
        ) : (
          <ul className="divide-y divide-base-800">
            {sent.map((row) => (
              <li key={row.id} className="py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                  <span className="font-heading font-semibold text-ink">{row.kelurahan}</span>
                  <span className="text-ink-faint">{row.kecamatan}</span>
                  <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs text-ink-muted">
                    {LABEL[row.status]}
                  </span>
                  <span className="text-ink-faint">{row.figures.total ?? 0} kejadian</span>
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
