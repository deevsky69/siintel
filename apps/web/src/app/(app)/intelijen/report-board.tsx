import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  IMPACT_CLASSES,
  IMPACT_LABELS,
  INTELLIGENCE_STATUS_CLASSES,
  INTELLIGENCE_STATUS_HINTS,
  INTELLIGENCE_STATUS_LABELS,
  type IntelligenceFacet,
  type IntelligencePage,
  type IntelligenceRow,
  RELIABILITY_HINTS,
} from "@/lib/intel";
import {
  areaOf,
  formatDate,
  type IntelligenceSelection,
  intelligenceHref,
  labelOf,
  pageRangeText,
  scoreText,
  toggled,
} from "./display";

/**
 * Layar Laporan Intelijen — daftar di kiri, rincian di kanan.
 *
 * Komponen ini **murni presentasi**: seluruh isinya datang dari
 * `GET /intelligence-reports`. Tidak ada laporan yang dinilai, diberi peringkat, atau
 * ditandai penting di sini.
 *
 * Dua hal yang mengikat tampilan layar ini:
 *
 * 1. **Tiga angka penilaian bukan keluaran mesin.** `reliability`, `confidence`, dan
 *    `urgency` dicatat oleh penyusun laporan. Layar menyatakannya di atas daftar, bukan di
 *    catatan kaki, karena "confidence" pada layar lain (prediksi) memang berasal dari
 *    mesin dan keduanya mudah tertukar (CLAUDE.md §27).
 * 2. **Jumlah pada penyaring memakai penyebut yang berbeda dari daftar.** Angka di chip
 *    dihitung atas seluruh cakupan, bukan atas hasil penyaringan yang sedang tampil —
 *    dinyatakan lewat `filter_basis`, bukan dibiarkan ditebak.
 */

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
      className={
        active
          ? "flex items-center gap-2 rounded border border-accent/60 bg-accent/10 px-2.5 py-1 text-xs text-accent"
          : "flex items-center gap-2 rounded border border-base-800 px-2.5 py-1 text-xs text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
      }
    >
      <span className="truncate">{label}</span>
      <span className="font-mono text-ink-faint">{count}</span>
    </Link>
  );
}

function FilterRow({
  legend,
  facets,
  current,
  hrefFor,
  labels,
}: {
  legend: string;
  facets: IntelligenceFacet[];
  current: string | null;
  hrefFor: (value: string) => string;
  labels?: Record<string, string>;
}) {
  if (facets.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="stat-label w-16 shrink-0">{legend}</span>
      {facets.map((facet) => (
        <FilterChip
          key={facet.value}
          href={hrefFor(facet.value)}
          active={current === facet.value}
          label={labels ? labelOf(labels, facet.value) : facet.value}
          count={facet.reports}
          title={INTELLIGENCE_STATUS_HINTS[facet.value] ?? RELIABILITY_HINTS[facet.value]}
        />
      ))}
    </div>
  );
}

function ReportCard({
  report,
  selected,
  href,
}: {
  report: IntelligenceRow;
  selected: boolean;
  href: string;
}) {
  return (
    <li>
      <Link
        href={href}
        scroll={false}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-850 hover:border-base-600"
        }`}
      >
        <div className="flex items-start gap-2">
          <span
            className={`badge shrink-0 ${INTELLIGENCE_STATUS_CLASSES[report.status ?? ""] ?? ""}`}
          >
            {labelOf(INTELLIGENCE_STATUS_LABELS, report.status)}
          </span>
          <span className="flex-1 truncate font-heading text-sm font-semibold text-ink">
            {report.category}
          </span>
          <span className="shrink-0 font-mono text-2xs uppercase tracking-wider text-ink-muted">
            {report.code}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between gap-3 text-xs">
          <span className="min-w-0 truncate text-ink-muted">{areaOf(report)}</span>
          <span className="shrink-0 text-ink-faint">{formatDate(report.report_date)}</span>
        </div>
      </Link>
    </li>
  );
}

function DetailRow({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <dt className="stat-label">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{value}</dd>
      {hint ? <dd className="text-2xs leading-relaxed text-ink-faint">{hint}</dd> : null}
    </div>
  );
}

function ReportDetail({
  report,
  assessmentBasis,
}: {
  report: IntelligenceRow;
  assessmentBasis: string;
}) {
  return (
    <Panel
      title="Rincian Laporan"
      className="col-span-12 xl:col-span-5"
      action={
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {report.code}
        </span>
      }
      bodyClassName="flex flex-col gap-4"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`badge ${INTELLIGENCE_STATUS_CLASSES[report.status ?? ""] ?? ""}`}>
          {labelOf(INTELLIGENCE_STATUS_LABELS, report.status)}
        </span>
        {report.impact ? (
          <span className={`badge ${IMPACT_CLASSES[report.impact] ?? ""}`}>
            Dampak {labelOf(IMPACT_LABELS, report.impact)}
          </span>
        ) : null}
        <span className="text-2xs text-ink-faint">
          {INTELLIGENCE_STATUS_HINTS[report.status ?? ""] ?? ""}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-3">
        <DetailRow label="Kategori" value={report.category} />
        <DetailRow label="Tanggal Laporan" value={formatDate(report.report_date)} />
        <DetailRow
          label="Wilayah"
          value={areaOf(report)}
          hint={`${report.polsek ?? "Polsek tidak dicatat"} · grid ${report.grid_id} (${report.location_code})`}
        />
        <DetailRow
          label="Keandalan Sumber"
          value={report.reliability ?? "Tidak dicatat"}
          hint={RELIABILITY_HINTS[report.reliability ?? ""] ?? "Skala A/B/C sebagaimana dicatat"}
        />
        <DetailRow label="Confidence" value={scoreText(report.confidence)} />
        <DetailRow label="Urgensi" value={scoreText(report.urgency)} />
      </dl>

      {/* Ditempatkan tepat di bawah ketiga angka itu, bukan di kaki halaman. */}
      <p className="rounded border border-base-800 bg-base-850 p-2.5 text-xs leading-relaxed text-ink-muted">
        {assessmentBasis}
      </p>
    </Panel>
  );
}

export function ReportBoard({
  page,
  selection,
  selected,
}: {
  page: IntelligencePage;
  selection: IntelligenceSelection;
  selected: IntelligenceRow | null;
}) {
  const { pagination } = page;
  const previous =
    selection.page > 1 ? intelligenceHref(selection, { page: selection.page - 1 }) : null;
  const next =
    selection.page < pagination.total_pages
      ? intelligenceHref(selection, { page: selection.page + 1 })
      : null;

  return (
    <div className="grid grid-cols-12 gap-3">
      <Panel
        title="Laporan Intelijen"
        className="col-span-12"
        action={
          <span className="panel-action">
            {pageRangeText(pagination.page, pagination.page_size, pagination.total_items)}
          </span>
        }
        bodyClassName="flex flex-col gap-3"
      >
        <FilterRow
          legend="Status"
          facets={page.filters.status}
          current={selection.status}
          labels={INTELLIGENCE_STATUS_LABELS}
          hrefFor={(value) =>
            intelligenceHref(selection, { status: toggled(selection.status, value) })
          }
        />
        <FilterRow
          legend="Kategori"
          facets={page.filters.category}
          current={selection.category}
          hrefFor={(value) =>
            intelligenceHref(selection, { category: toggled(selection.category, value) })
          }
        />

        <p className="text-2xs leading-relaxed text-ink-faint">{page.filter_basis}</p>
        <p className="text-2xs leading-relaxed text-ink-faint">{page.scope_basis}</p>
      </Panel>

      <Panel
        title="Daftar"
        className="col-span-12 xl:col-span-7"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">
            {page.source.reports_in_scope} laporan dalam cakupan
          </span>
        }
        bodyClassName="flex flex-col gap-3"
      >
        {page.data.length === 0 ? (
          <EmptyState
            label={
              selection.status || selection.category
                ? "Tidak ada laporan yang cocok dengan penyaring ini. Lepaskan salah satu penyaring untuk melihat lebih banyak."
                : "Belum ada laporan intelijen yang dapat ditampilkan untuk kewenangan Anda."
            }
          />
        ) : (
          <>
            <ul className="flex flex-col gap-2">
              {page.data.map((report) => (
                <ReportCard
                  key={report.code}
                  report={report}
                  selected={selected?.code === report.code}
                  href={intelligenceHref(selection, { selected: report.code })}
                />
              ))}
            </ul>

            {pagination.total_pages > 1 ? (
              <nav
                aria-label="Halaman laporan"
                className="flex items-center justify-between border-t border-base-800 pt-2 text-xs"
              >
                {previous ? (
                  <Link href={previous} className="panel-action">
                    ← Sebelumnya
                  </Link>
                ) : (
                  <span className="text-ink-faint">← Sebelumnya</span>
                )}
                <span className="text-ink-muted">
                  Halaman {pagination.page} dari {pagination.total_pages}
                </span>
                {next ? (
                  <Link href={next} className="panel-action">
                    Berikutnya →
                  </Link>
                ) : (
                  <span className="text-ink-faint">Berikutnya →</span>
                )}
              </nav>
            ) : null}
          </>
        )}
      </Panel>

      {selected === null ? (
        <Panel title="Rincian Laporan" className="col-span-12 xl:col-span-5">
          <EmptyState label="Pilih satu laporan pada daftar untuk melihat rinciannya." />
        </Panel>
      ) : (
        <ReportDetail report={selected} assessmentBasis={page.assessment_basis} />
      )}
    </div>
  );
}
