import Link from "next/link";
import { changeReportStatus } from "@/app/ops/(app)/masyarakat/actions";
import { Basis } from "@/components/basis";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { Attachments } from "@/components/reports/attachments";
import { ReportDetail } from "@/components/reports/report-detail";
import { StatusForm } from "@/components/reports/status-form";
import { StatusNotice } from "@/components/warnings/status-notice";
import {
  areaOf,
  type CitizenReportPage,
  type CitizenReportRow,
  type CommunitySummary,
  formatMoment,
  labelOf,
  REPORT_STATUS_CLASSES,
  REPORT_STATUS_HINTS,
  REPORT_STATUS_LABELS,
  REPORT_STATUSES,
} from "@/lib/community";

/** Penyaring yang sedang berlaku; keduanya berasal dari URL, bukan state klien. */
export type CommunityFilters = { status: string | null; category: string | null };

/** Menyusun tautan penyaring: memilih nilai yang sama berarti melepas penyaringnya. */
function filterHref(current: CommunityFilters, change: Partial<CommunityFilters>): string {
  const next = { ...current, ...change };
  const query = new URLSearchParams();
  if (next.status) query.set("status", next.status);
  if (next.category) query.set("kategori", next.category);
  const suffix = query.toString();
  return suffix ? `/ops/masyarakat?${suffix}` : "/ops/masyarakat";
}

/** Ubin angka yang sekaligus penyaring: tautan, supaya keadaannya tersimpan di URL. */
function StatTile({
  href,
  active,
  label,
  value,
  title,
}: {
  href: string;
  active: boolean;
  label: string;
  value: number;
  title?: string;
}) {
  return (
    <Link
      href={href}
      title={title}
      aria-current={active ? "true" : undefined}
      className={`flex min-w-[7.5rem] flex-col rounded border px-3 py-2 transition ${
        active
          ? "border-accent/60 bg-accent/10"
          : "border-base-800 bg-base-850/60 hover:border-accent/40"
      }`}
    >
      <span className="stat-label">{label}</span>
      <span className="mt-1 font-heading text-xl font-bold leading-none text-ink">{value}</span>
    </Link>
  );
}

function Chip({
  href,
  active,
  label,
  count,
}: {
  href: string;
  active: boolean;
  label: string;
  count: number;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "true" : undefined}
      className={`badge normal-case tracking-normal ${
        active ? "bg-accent/15 text-accent" : "bg-base-850 text-ink-muted hover:text-accent-soft"
      }`}
    >
      {label} <span className="font-mono">{count}</span>
    </Link>
  );
}

function ReportTable({
  reports,
  statusLabels,
}: {
  reports: CitizenReportRow[];
  statusLabels: Record<string, string>;
}) {
  const canWrite = Object.keys(statusLabels).length > 0;
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Kode</th>
            <th>Masuk</th>
            <th>Kategori</th>
            <th>Wilayah</th>
            <th className="num">Urgensi</th>
            <th className="num">Verifikasi</th>
            <th>Tahapan</th>
            <th className="act">Aksi</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => (
            <tr key={report.code}>
              <td className="font-mono text-ink-muted">{report.code}</td>
              <td className="whitespace-nowrap">{formatMoment(report.reported_at)}</td>
              <td>
                <span className="inline-flex flex-wrap items-center gap-1.5">
                  {report.category}
                  <Attachments code={report.code} count={report.attachments} />
                </span>
              </td>
              <td>
                <span className={report.kecamatan ? "" : "italic text-ink-faint"}>
                  {areaOf(report)}
                </span>
                {report.coordinate_source === "REPORTER_GPS" ? (
                  <span className="mt-0.5 block text-2xs text-accent">Titik dibagikan pelapor</span>
                ) : null}
              </td>
              <td className="num">{report.urgency_score ?? "—"}</td>
              <td className="num">{report.verification_score ?? "—"}</td>
              <td>
                <span className={`badge ${REPORT_STATUS_CLASSES[report.status] ?? ""}`}>
                  {labelOf(REPORT_STATUS_LABELS, report.status)}
                </span>
              </td>
              <td className="act">
                <span className="inline-flex items-center gap-1.5">
                  <ReportDetail
                    report={report}
                    statusLabel={labelOf(REPORT_STATUS_LABELS, report.status)}
                  />
                  {canWrite ? (
                    <StatusForm
                      code={report.code}
                      current={report.status}
                      options={statusLabels}
                      action={changeReportStatus}
                    />
                  ) : null}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Laporan Masyarakat — tampilan tabel (TASK 024, 163; dirapikan 4 November 2026 atas
 * permintaan pemilik proyek: matriks yang dapat dipindai, teks seperlunya).
 *
 * Yang tetap wajib tampil dan tidak dihaluskan: laporan **belum memengaruhi risk score**,
 * urgensi/verifikasi adalah isian petugas, dan deteksi duplikasi/spam belum dibangun
 * (spesifikasi §4, CLAUDE.md §27). Ketiganya kini satu baris notice dan satu catatan kaki.
 */
export function CommunityView({
  summary,
  reports,
  filters,
  statusLabels = {},
}: {
  summary: CommunitySummary;
  reports: CitizenReportPage;
  filters: CommunityFilters;
  /** Nilai status tersimpan → labelnya. Kosong berarti pengguna tidak berwenang menulis. */
  statusLabels?: Record<string, string>;
}) {
  const categories = Object.entries(summary.per_category).sort((a, b) => b[1] - a[1]);
  const filtered = filters.status !== null || filters.category !== null;

  return (
    <div className="space-y-3">
      <StatusNotice status={summary.status} tone="caution">
        Laporan masyarakat <strong>belum memengaruhi risk score</strong>.
      </StatusNotice>

      {summary.total_reports === 0 ? (
        <Panel title="Ringkasan">
          <EmptyState label="Belum ada laporan masyarakat pada cakupan Anda." />
          <p className="mt-2 text-2xs text-ink-faint">Tidak ada kategori laporan.</p>
        </Panel>
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <StatTile
              href="/ops/masyarakat"
              active={!filtered}
              label="Laporan masuk"
              value={summary.total_reports}
            />
            {REPORT_STATUSES.map((status) => (
              <StatTile
                key={status}
                href={filterHref(filters, { status: filters.status === status ? null : status })}
                active={filters.status === status}
                label={REPORT_STATUS_LABELS[status]}
                value={summary.per_status[status] ?? 0}
                title={REPORT_STATUS_HINTS[status]}
              />
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-2xs text-ink-muted">
            <span className="stat-label">Kategori</span>
            {categories.length === 0 ? (
              <span>Tidak ada kategori laporan.</span>
            ) : (
              categories.map(([category, total]) => (
                <Chip
                  key={category}
                  href={filterHref(filters, {
                    category: filters.category === category ? null : category,
                  })}
                  active={filters.category === category}
                  label={category}
                  count={total}
                />
              ))
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-ink-muted">
            <span>
              <span className="stat-label">Terbanyak</span>{" "}
              {summary.top_areas.length === 0
                ? "—"
                : summary.top_areas.map((area) => `${area.kecamatan} ${area.total}`).join(" · ")}
              <span className="text-ink-faint">
                {" "}
                (di mana warga melapor, bukan wilayah berisiko)
              </span>
            </span>
            <span>
              <span className="stat-label">Belum terpetakan</span> {summary.unmapped_reports}{" "}
              <span className="text-ink-faint" title={summary.unmapped_basis}>
                {summary.unmapped_basis}
              </span>
            </span>
          </div>
        </div>
      )}

      <Panel
        title="Daftar Laporan"
        action={
          <span className="flex items-center gap-2 text-2xs text-ink-muted">
            {filtered ? (
              <Link href="/ops/masyarakat" className="panel-action">
                Hapus penyaringan
              </Link>
            ) : null}
            <span>
              {reports.pagination.total_items > 0
                ? `${reports.data.length} dari ${reports.pagination.total_items} laporan`
                : "tidak ada laporan"}
            </span>
          </span>
        }
        bodyClassName="p-0"
      >
        {reports.data.length === 0 ? (
          <div className="p-4">
            <EmptyState
              label={
                filtered
                  ? "Tidak ada laporan yang cocok dengan penyaringan ini."
                  : "Belum ada laporan masyarakat pada cakupan Anda."
              }
            />
          </div>
        ) : (
          <ReportTable reports={reports.data} statusLabels={statusLabels} />
        )}
        <p className="border-t border-base-800 px-3 py-2 text-2xs leading-relaxed text-ink-faint">
          Urgensi dan verifikasi diisi petugas saat triase ({summary.status}); tidak ada penilaian
          otomatis. Deteksi duplikasi dan deteksi spam (spesifikasi §4) belum dibangun.
        </p>
      </Panel>

      <Basis className="mt-0">{summary.basis}</Basis>
    </div>
  );
}
