import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  DECISION_LABELS,
  type DecisionRow,
  FUNCTION_LABELS,
  PENDING,
  PRIORITY_LABELS,
  type RecommendationRow,
} from "@/lib/decisions";
import { formatWib } from "@/lib/warnings";
import { DecisionForm } from "./decision-form";

/**
 * Layar Rekomendasi & Keputusan Pimpinan (TASK 121, 130).
 *
 * Inti layar ini bukan daftarnya, melainkan **jejaknya**: usulan sistem dan keputusan
 * pejabat ditampilkan berdampingan, sehingga terlihat bahwa yang dijalankan di lapangan
 * adalah keputusan manusia — bukan keluaran model yang diteruskan begitu saja
 * (CLAUDE.md §13, success criteria #05 Taskap).
 */

/** Kelas ditulis utuh agar Tailwind membangkitkannya saat memindai berkas ini. */
const STATUS_BADGE: Record<string, string> = {
  PENDING_REVIEW: "bg-risk-moderate/15 text-risk-moderate",
  APPROVED: "bg-risk-low/15 text-risk-low",
  MODIFIED: "bg-accent/15 text-accent",
  REJECTED: "bg-risk-critical/15 text-risk-critical",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge shrink-0 ${STATUS_BADGE[status] ?? "bg-base-800 text-ink-muted"}`}>
      {DECISION_LABELS[status] ?? status}
    </span>
  );
}

function RecommendationCard({ row, selected }: { row: RecommendationRow; selected: boolean }) {
  return (
    <li>
      <Link
        href={`/rekomendasi?dipilih=${encodeURIComponent(row.code)}`}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-950/40 hover:border-base-600"
        }`}
      >
        <div className="flex items-start gap-3">
          <StatusBadge status={row.status} />
          <span className="flex-1 font-heading text-sm font-semibold text-ink">
            {FUNCTION_LABELS[row.recommended_function] ?? row.recommended_function}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
            {row.code}
          </span>
        </div>
        <p className="mt-1.5 line-clamp-2 text-xs text-ink-muted">{row.recommendation_text}</p>
      </Link>
    </li>
  );
}

function Group({
  title,
  rows,
  selected,
  emptyLabel,
}: {
  title: string;
  rows: RecommendationRow[];
  selected: string | null;
  emptyLabel: string;
}) {
  return (
    <div>
      <h3 className="stat-label">
        {title} <span className="text-ink-muted">({rows.length})</span>
      </h3>
      {rows.length === 0 ? (
        <EmptyState label={emptyLabel} />
      ) : (
        <ul className="mt-2 space-y-2">
          {rows.map((row) => (
            <RecommendationCard key={row.code} row={row} selected={row.code === selected} />
          ))}
        </ul>
      )}
    </div>
  );
}

function DecisionRecord({ decision }: { decision: DecisionRow }) {
  return (
    <div className="mt-4 border-t border-base-800 pt-4">
      <div className="flex items-center gap-3">
        <StatusBadge status={decision.decision} />
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
          {decision.code}
        </span>
        <span className="text-[11px] text-ink-muted">{formatWib(decision.decided_at)}</span>
      </div>

      {decision.modified_text ? (
        <div className="mt-3">
          <div className="stat-label">Rekomendasi Setelah Disesuaikan Pejabat</div>
          <p className="mt-1 text-sm leading-relaxed text-ink">{decision.modified_text}</p>
        </div>
      ) : null}

      <div className="mt-3">
        <div className="stat-label">Pertimbangan</div>
        <p className="mt-1 text-sm leading-relaxed text-ink-muted">
          {decision.reason ?? "Tidak dicantumkan."}
        </p>
      </div>
    </div>
  );
}

function Detail({
  row,
  decision,
  canDecide,
}: {
  row: RecommendationRow;
  decision: DecisionRow | null;
  canDecide: boolean;
}) {
  return (
    <Panel title="Usulan Sistem & Keputusan">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={row.status} />
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
          {row.code}
        </span>
        <span className="text-[11px] text-ink-muted">
          Fungsi {FUNCTION_LABELS[row.recommended_function] ?? row.recommended_function}
          {row.priority ? ` · Prioritas ${PRIORITY_LABELS[row.priority] ?? row.priority}` : ""}
        </span>
      </div>

      <div className="mt-4">
        <div className="stat-label">Usulan Sistem</div>
        <p className="mt-1 text-sm leading-relaxed text-ink">{row.recommendation_text}</p>
        <p className="mt-2 text-[10px] text-ink-muted">
          Bersumber dari prediksi{" "}
          <Link
            href={`/peringatan${row.warning_code ? `?dipilih=${encodeURIComponent(row.warning_code)}` : ""}`}
            className="font-mono text-accent hover:underline"
          >
            {row.prediction_code}
          </Link>
          {row.warning_code ? ` melalui peringatan ${row.warning_code}` : ""}. Usulan adalah{" "}
          <strong className="text-ink">opsi, bukan perintah</strong>.
        </p>
      </div>

      {decision ? <DecisionRecord decision={decision} /> : null}

      {row.status === PENDING && canDecide ? <DecisionForm code={row.code} /> : null}

      {row.status === PENDING && !canDecide ? (
        <p className="mt-4 border-t border-base-800 pt-4 text-xs text-ink-muted">
          Rekomendasi ini menunggu keputusan pejabat berwenang. Peran Anda tidak memiliki kewenangan
          memutuskan.
        </p>
      ) : null}
    </Panel>
  );
}

export function RecommendationBoard({
  pending,
  decided,
  selected,
  decision,
  canDecide,
}: {
  pending: RecommendationRow[];
  decided: RecommendationRow[];
  selected: RecommendationRow | null;
  decision: DecisionRow | null;
  canDecide: boolean;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Panel title="Rekomendasi Tindakan" bodyClassName="space-y-5 overflow-y-auto">
        <Group
          title="Menunggu Keputusan"
          rows={pending}
          selected={selected?.code ?? null}
          emptyLabel="Tidak ada rekomendasi yang menunggu keputusan."
        />
        <Group
          title="Sudah Diputus"
          rows={decided}
          selected={selected?.code ?? null}
          emptyLabel="Belum ada keputusan tercatat."
        />
      </Panel>

      {selected ? (
        <Detail row={selected} decision={decision} canDecide={canDecide} />
      ) : (
        <Panel title="Usulan Sistem & Keputusan">
          <EmptyState label="Pilih satu rekomendasi untuk melihat usulan dan keputusannya." />
        </Panel>
      )}
    </div>
  );
}
