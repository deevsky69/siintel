import Link from "next/link";
import { changeReportStatus } from "@/app/(app)/masyarakat/actions";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { Attachments } from "@/components/reports/attachments";
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
  return suffix ? `/masyarakat?${suffix}` : "/masyarakat";
}

function MetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2.5">
      <div className="stat-label">{label}</div>
      <div className="mt-1 font-heading text-2xl font-bold leading-none text-ink">{value}</div>
      <div className="mt-1.5 text-2xs leading-relaxed text-ink-muted">{hint}</div>
    </div>
  );
}

/** Satu pilihan penyaring: tautan, bukan tombol, supaya keadaannya tersimpan di URL. */
function FilterChip({
  href,
  active,
  label,
  count,
  title,
}: {
  href: string;
  active: boolean;
  label: string;
  count: number;
  title?: string;
}) {
  return (
    <Link
      href={href}
      title={title}
      aria-current={active ? "true" : undefined}
      className={`flex items-center justify-between gap-3 rounded border px-3 py-2 text-xs transition ${
        active
          ? "border-accent/60 bg-accent/10 text-accent"
          : "border-base-800 text-ink hover:border-accent/40 hover:text-accent-soft"
      }`}
    >
      <span className="min-w-0 truncate">{label}</span>
      <span className="shrink-0 font-mono text-xs text-ink-muted">{count}</span>
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
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-base-800">
            <th className="stat-label pb-2">Kode</th>
            <th className="stat-label pb-2">Masuk</th>
            <th className="stat-label pb-2">Kategori</th>
            <th className="stat-label pb-2">Wilayah</th>
            <th className="stat-label pb-2 text-right">Urgensi</th>
            <th className="stat-label pb-2 text-right">Verifikasi</th>
            <th className="stat-label pb-2">Tahapan</th>
            <th className="stat-label pb-2">Ubah tahapan</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => (
            <tr key={report.code} className="border-b border-base-800/60 align-top last:border-0">
              <td className="py-2 pr-3 font-mono text-xs text-ink-muted">{report.code}</td>
              <td className="py-2 pr-3 text-ink">{formatMoment(report.reported_at)}</td>
              <td className="py-2 pr-3">
                <div className="text-ink">{report.category}</div>
                {report.description ? (
                  <div className="mt-0.5 max-w-md text-2xs leading-relaxed text-ink-muted">
                    {report.description}
                  </div>
                ) : null}
                <Attachments code={report.code} count={report.attachments} />
              </td>
              <td className="py-2 pr-3">
                <div className={report.kecamatan ? "text-ink" : "text-ink-faint italic"}>
                  {areaOf(report)}
                </div>
                {report.location_text ? (
                  <div className="mt-0.5 text-2xs text-ink-muted">{report.location_text}</div>
                ) : null}
                {/* Titik peranti pelapor dan titik pusat kecamatan terlihat sama sebagai
                    sepasang angka. Yang pertama menunjuk tempat kejadian; yang kedua
                    berjarak kilometer darinya. Petugas yang menriase perlu tahu yang mana. */}
                {report.coordinate_source === "REPORTER_GPS" ? (
                  <div className="mt-0.5 text-2xs text-accent">Titik dibagikan pelapor</div>
                ) : null}
              </td>
              <td className="py-2 pr-3 text-right font-mono text-ink">
                {report.urgency_score ?? "—"}
              </td>
              <td className="py-2 pr-3 text-right font-mono text-ink">
                {report.verification_score ?? "—"}
              </td>
              <td className="py-2 pr-3">
                <span className={`badge ${REPORT_STATUS_CLASSES[report.status] ?? ""}`}>
                  {labelOf(REPORT_STATUS_LABELS, report.status)}
                </span>
              </td>
              <td className="py-2">
                {/* Triase langsung di daftar. Formulir pada Input Data tetap ada — ia
                    berguna ketika beberapa laporan ditriase berurutan — tetapi pertanyaan
                    "bagaimana cara mengubah tahapan?" muncul justru saat seseorang sedang
                    menatap daftarnya. */}
                {Object.keys(statusLabels).length > 0 ? (
                  <StatusForm
                    code={report.code}
                    current={report.status}
                    options={statusLabels}
                    action={changeReportStatus}
                  />
                ) : (
                  <span className="text-2xs text-ink-faint">Perlu kewenangan menulis</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Community Signal Dashboard (TASK 024) — bagian tampilan.
 *
 * Dipisahkan dari pengambilan data supaya dapat diuji tanpa backend.
 *
 * Kalimat "belum memengaruhi risk score" diletakkan di atas seluruh angka, bukan sebagai
 * catatan kaki. Layar yang menampilkan urgensi dan verifikasi tanpa menyebutkan bahwa
 * keduanya sintetis akan membuat pembaca menyimpulkan ada mekanisme penilaian yang
 * sesungguhnya belum dibangun (spesifikasi §4, CLAUDE.md §27).
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
        Laporan masyarakat <strong>belum memengaruhi risk score</strong>. {summary.basis}
      </StatusNotice>

      <Panel
        title="Sinyal Masyarakat"
        action={<span className="panel-action">kanal tanpa akun, tanpa identitas pelapor</span>}
      >
        {summary.total_reports === 0 ? (
          <EmptyState label="Belum ada laporan masyarakat pada cakupan Anda." />
        ) : (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <MetricCard
              label="Laporan Masuk"
              value={String(summary.total_reports)}
              hint="Seluruh laporan pada cakupan wilayah akun Anda"
            />
            <MetricCard
              label="Belum Terpetakan"
              value={String(summary.unmapped_reports)}
              hint={summary.unmapped_basis}
            />
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 xl:col-span-4">
          <Panel title="Tahapan Penanganan">
            {summary.total_reports === 0 ? (
              <EmptyState label="Tidak ada laporan untuk dirinci." />
            ) : (
              <div className="space-y-1.5">
                {REPORT_STATUSES.map((status) => (
                  <FilterChip
                    key={status}
                    href={filterHref(filters, {
                      status: filters.status === status ? null : status,
                    })}
                    active={filters.status === status}
                    label={REPORT_STATUS_LABELS[status]}
                    count={summary.per_status[status] ?? 0}
                    title={REPORT_STATUS_HINTS[status]}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="col-span-12 xl:col-span-4">
          <Panel title="Kategori Laporan">
            {categories.length === 0 ? (
              <EmptyState label="Tidak ada kategori laporan." />
            ) : (
              <div className="space-y-1.5">
                {categories.map(([category, total]) => (
                  <FilterChip
                    key={category}
                    href={filterHref(filters, {
                      category: filters.category === category ? null : category,
                    })}
                    active={filters.category === category}
                    label={category}
                    count={total}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="col-span-12 xl:col-span-4">
          <Panel title="Wilayah dengan Laporan Terbanyak">
            {summary.top_areas.length === 0 ? (
              <EmptyState label="Tidak ada wilayah dengan laporan terpetakan." />
            ) : (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-base-800">
                    <th className="stat-label pb-2">Kecamatan</th>
                    <th className="stat-label pb-2">Polsek</th>
                    <th className="stat-label pb-2 text-right">Laporan</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.top_areas.map((area) => (
                    <tr key={area.kecamatan} className="border-b border-base-800/60 last:border-0">
                      <td className="py-2 font-heading font-semibold text-ink">{area.kecamatan}</td>
                      <td className="py-2 text-ink-muted">{area.polsek ?? "—"}</td>
                      <td className="py-2 text-right font-mono text-ink">{area.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
              Urutan ini menggambarkan <strong>di mana warga melapor</strong>, bukan di mana
              risikonya tertinggi. Keduanya tidak selalu sejalan: wilayah yang warganya aktif
              melapor akan tampak menonjol meskipun kejadiannya tidak lebih banyak.
            </p>
          </Panel>
        </div>
      </div>

      <Panel
        title="Daftar Laporan"
        action={
          <span className="panel-action">
            {reports.pagination.total_items > 0
              ? `${reports.data.length} dari ${reports.pagination.total_items} laporan`
              : "tidak ada laporan"}
          </span>
        }
      >
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
          {filtered ? (
            <>
              <span>Disaring:</span>
              {filters.status ? (
                <span className="badge bg-accent/15 text-accent">
                  {labelOf(REPORT_STATUS_LABELS, filters.status)}
                </span>
              ) : null}
              {filters.category ? (
                <span className="badge bg-accent/15 text-accent">{filters.category}</span>
              ) : null}
              <Link href="/masyarakat" className="text-accent hover:text-accent-soft">
                Hapus penyaringan
              </Link>
            </>
          ) : (
            <span>Menampilkan seluruh laporan pada cakupan wilayah akun Anda.</span>
          )}
        </div>

        {reports.data.length === 0 ? (
          <EmptyState
            label={
              filtered
                ? "Tidak ada laporan yang cocok dengan penyaringan ini."
                : "Belum ada laporan masyarakat pada cakupan Anda."
            }
          />
        ) : (
          <ReportTable reports={reports.data} statusLabels={statusLabels} />
        )}

        <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
          <strong>Urgensi</strong> dan <strong>verifikasi</strong> pada tabel ini adalah nilai
          sintetis berstatus {summary.status} — bukan hasil penilaian model, dan bukan dasar
          tindakan. Deteksi duplikasi dan deteksi spam yang disyaratkan spesifikasi §4 belum
          dibangun, sehingga laporan di sini belum tersaring dari kemungkinan pengulangan.
        </p>
      </Panel>
    </div>
  );
}
