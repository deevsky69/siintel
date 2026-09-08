import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  AUDIT_RESULTS,
  type AuditFilters,
  type AuditPage,
  type AuditRow,
  type AuditSummary,
  RESULT_BADGE,
  RESULT_LABELS,
} from "@/lib/audit";
import { formatWib } from "@/lib/warnings";

/**
 * Papan jejak audit — komponen presentasi murni.
 *
 * Susunannya disengaja: **penolakan lebih dulu**, baru daftar lengkap. Yang pertama
 * dicari saat memeriksa audit adalah percobaan yang ditolak, bukan pekerjaan yang
 * berhasil — dan audit yang hanya menonjolkan keberhasilan tidak dapat dipakai menilai
 * apakah pembatasan kewenangan benar-benar bekerja.
 */

function Badge({ result }: { result: string }) {
  return (
    <span className={`badge shrink-0 ${RESULT_BADGE[result] ?? "bg-base-800 text-ink-muted"}`}>
      {RESULT_LABELS[result] ?? result}
    </span>
  );
}

/** Tautan penyaring yang mempertahankan penyaring lain yang sedang aktif. */
function filterHref(filters: AuditFilters, key: string, value: string | undefined): string {
  const params = new URLSearchParams();
  const current: Record<string, string | undefined> = {
    aksi: filters.action,
    hasil: filters.result,
    jenis: filters.resource_type,
    dari: filters.date_from,
    sampai: filters.date_to,
  };
  current[key] = value;
  for (const [name, item] of Object.entries(current)) {
    if (item) params.set(name, item);
  }
  const text = params.toString();
  return text ? `/audit?${text}` : "/audit";
}

function Detail({ detail }: { detail: Record<string, unknown> | null }) {
  if (!detail || Object.keys(detail).length === 0) return null;
  return (
    <dl className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
      {Object.entries(detail).map(([key, value]) => (
        <div key={key} className="flex gap-1.5">
          <dt className="font-mono text-2xs uppercase tracking-wider text-ink-faint">{key}</dt>
          <dd className="font-mono text-2xs text-ink-muted">
            {typeof value === "object" ? JSON.stringify(value) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function Entry({ row }: { row: AuditRow }) {
  return (
    <li className="border-b border-base-800/60 py-2.5 last:border-b-0">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Badge result={row.result} />
        <span className="font-heading text-sm font-semibold text-ink">{row.action}</span>
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {row.resource_type}
          {row.resource_id ? ` · ${row.resource_id}` : ""}
        </span>
        <span className="ml-auto font-mono text-2xs text-ink-faint">
          {formatWib(row.timestamp_wib)}
        </span>
      </div>
      <div className="mt-1 text-xs text-ink-muted">
        {row.username ?? (
          // Peristiwa sistem ditandai apa adanya, bukan diisi nama pengganti.
          <span className="italic text-ink-faint">peristiwa sistem, tanpa pengguna</span>
        )}
      </div>
      <Detail detail={row.detail} />
    </li>
  );
}

function Counts({ title, rows }: { title: string; rows: { key: string; count: number }[] }) {
  const highest = Math.max(1, ...rows.map((row) => row.count));
  return (
    <div>
      <h3 className="stat-label">{title}</h3>
      {rows.length === 0 ? (
        <EmptyState label="Belum ada catatan." />
      ) : (
        <ul className="mt-2 space-y-1.5">
          {rows.map((row) => (
            <li key={row.key} className="flex items-center gap-2">
              <span className="w-44 shrink-0 truncate font-mono text-xs text-ink">{row.key}</span>
              <span
                className="h-2 rounded-sm bg-accent/40"
                style={{ width: `${Math.round((100 * row.count) / highest)}%` }}
              />
              <span className="ml-auto font-mono text-xs tabular-nums text-ink-muted">
                {row.count}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AuditBoard({
  page,
  summary,
  filters,
}: {
  page: AuditPage;
  summary: AuditSummary;
  filters: AuditFilters;
}) {
  const refusals = (summary.per_result.DENIED ?? 0) + (summary.per_result.FAILED ?? 0);

  return (
    <div className="space-y-4">
      <Panel title="Percobaan yang Ditolak">
        <p className="mb-3 max-w-[70ch] text-xs leading-relaxed text-ink-muted">
          {summary.denied_basis}
        </p>

        <div className="mb-4 flex flex-wrap gap-4">
          <div>
            <div className="stat-label">Ditolak &amp; gagal</div>
            <div className="font-heading text-2xl font-bold text-risk-critical">{refusals}</div>
          </div>
          <div>
            <div className="stat-label">Berhasil</div>
            <div className="font-heading text-2xl font-bold text-ink">
              {summary.per_result.SUCCESS ?? 0}
            </div>
          </div>
          <div>
            <div className="stat-label">Seluruh catatan</div>
            <div className="font-heading text-2xl font-bold text-ink">{summary.total}</div>
          </div>
        </div>

        {summary.recent_refusals.length === 0 ? (
          <EmptyState label="Tidak ada percobaan yang ditolak pada rentang ini." />
        ) : (
          <ul>
            {summary.recent_refusals.map((row) => (
              <Entry
                key={`${row.code ?? row.timestamp_wib}-${row.action}`}
                row={{ ...row, timestamp: row.timestamp_wib, user_code: null }}
              />
            ))}
          </ul>
        )}
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Aksi Terbanyak">
          <Counts title="" rows={summary.per_action} />
        </Panel>
        <Panel title="Jenis Sumber Daya">
          <Counts title="" rows={summary.per_resource_type} />
        </Panel>
      </div>

      <Panel title="Seluruh Catatan">
        <nav aria-label="Saring menurut hasil" className="mb-3 flex flex-wrap gap-2">
          <Link
            href={filterHref(filters, "hasil", undefined)}
            aria-current={filters.result ? undefined : "true"}
            className={`rounded border px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
              filters.result
                ? "border-base-800 text-ink-muted hover:text-ink"
                : "border-accent/60 bg-accent/10 text-accent"
            }`}
          >
            Semua
          </Link>
          {AUDIT_RESULTS.map((value) => (
            <Link
              key={value}
              href={filterHref(filters, "hasil", value)}
              aria-current={filters.result === value ? "true" : undefined}
              className={`rounded border px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
                filters.result === value
                  ? "border-accent/60 bg-accent/10 text-accent"
                  : "border-base-800 text-ink-muted hover:text-ink"
              }`}
            >
              {RESULT_LABELS[value]}
            </Link>
          ))}
        </nav>

        {page.data.length === 0 ? (
          <EmptyState label="Tidak ada catatan yang cocok dengan penyaring ini." />
        ) : (
          <>
            <p className="mb-2 text-xs text-ink-faint">
              Menampilkan {page.data.length} dari {page.pagination.total_items} catatan, terbaru
              lebih dulu.
            </p>
            <ul>
              {page.data.map((row) => (
                <Entry key={row.code ?? `${row.timestamp}-${row.action}`} row={row} />
              ))}
            </ul>
          </>
        )}

        <p className="mt-4 border-t border-base-800 pt-3 text-xs leading-relaxed text-ink-faint">
          {page.append_only_basis} {page.scope_basis} {page.filter_basis}
        </p>
      </Panel>
    </div>
  );
}
