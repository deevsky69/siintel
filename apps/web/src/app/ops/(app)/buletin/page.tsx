import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import { getAdvisoryPreview, getBulletins } from "@/lib/babin";
import { getProfile } from "@/lib/decisions";
import { ApproveButton, GenerateForm } from "./bulletin-forms";

export const dynamic = "force-dynamic";

const LABEL = { DRAFT: "Draf", APPROVED: "Disetujui, menunggu bot", SENT: "Terkirim" } as const;

/**
 * Persetujuan warga — satu antrean (10 November 2026, keputusan pemilik proyek 2.iii).
 *
 * Buletin mingguan kelurahan menunggu persetujuan Pimpinan dalam satu daftar lintas minggu,
 * lalu riwayat per minggu. Administrator tetap menyusun draf di sini. Imbauan bulanan ke grup
 * WhatsApp warga **tidak lagi menunggu persetujuan** (keputusan 10 November 2026 mencabut 3A):
 * di sini hanya pratinjau teks dan jumlah grup yang sudah menerimanya.
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
    getAdvisoryPreview().catch(() => null),
  ]);
  const canManage = profile.permissions.includes("bulletin:manage");
  const canApprove = profile.permissions.includes("bulletin:approve");
  const week = one("minggu") || history.weeks[0] || "";
  const sent = (week ? history.data.filter((row) => row.week_start === week) : history.data).filter(
    (row) => row.status !== "DRAFT",
  );
  const waiting = drafts.data.length;

  return (
    <div className="space-y-3">
      <StatusNotice status="PROPOSED" tone="caution">
        Buletin mingguan hanya terkirim setelah disetujui Pimpinan. Imbauan bulanan ke grup warga
        dikirim bot secara otomatis setiap awal bulan (keputusan 10 November 2026).
      </StatusNotice>

      <Panel
        title="Menunggu persetujuan"
        action={
          <span className="panel-action">
            {waiting === 0 ? "tidak ada" : `${waiting} menunggu`}
          </span>
        }
      >
        {waiting === 0 ? (
          <EmptyState label="Tidak ada buletin yang menunggu persetujuan." />
        ) : (
          <ul className="divide-y divide-base-800">
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

      {advisory ? (
        <Panel
          title={`Imbauan bulanan ke grup warga · ${advisory.month}`}
          action={
            <span className="panel-action">
              otomatis · {advisory.groups_sent}/{advisory.groups_registered} grup sudah menerima
            </span>
          }
        >
          <p className="text-2xs leading-relaxed text-ink-faint">
            Dikirim bot setiap awal bulan ke grup yang terdaftar lewat /daftar; warga dapat
            memintanya kapan saja dengan /info. Tidak ada persetujuan: isinya imbauan kehati-hatian
            dari pola bulan yang sama tahun-tahun sebelumnya, tanpa skor maupun taktik kepolisian.
          </p>
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
        </Panel>
      ) : null}

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
