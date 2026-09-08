import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { DECISION_LABELS, FUNCTION_LABELS, PRIORITY_LABELS } from "@/lib/decisions";
import {
  ACTION_STATUS_HINTS,
  ACTION_STATUS_LABELS,
  effectiveOrder,
  FINAL_STATUSES,
  type OperationRow,
  type PendingDecisionRow,
  type PoliceUnitRow,
} from "@/lib/operations";
import { formatWib } from "@/lib/warnings";
import { AssignmentForm } from "./assignment-form";
import { ResultForm } from "./result-form";

/**
 * Layar Operasi — lengan umpan balik rantai tertutup (TASK 131).
 *
 * Rantai `prediksi → peringatan → rekomendasi → keputusan → tindakan → hasil → evaluasi`
 * sebelumnya berhenti terlihat setelah keputusan: datanya ada, tetapi tidak ada satu pun
 * layar yang menunjukkan apakah keputusan itu benar-benar dijalankan.
 *
 * Karena itu panel pertama layar ini bukan daftar tindakan, melainkan **antrean kerja** —
 * keputusan yang sudah diambil pejabat tetapi belum ditindaklanjuti siapa pun. Keadaan
 * "sudah diputus, tidak pernah dijalankan" harus terlihat, bukan tenggelam
 * (CLAUDE.md §9, §13, success criteria #06 Taskap).
 */

/** Kelas ditulis utuh agar Tailwind membangkitkannya saat memindai berkas ini. */
const STATUS_BADGE: Record<string, string> = {
  PLANNED: "bg-risk-moderate/15 text-risk-moderate",
  ACTIVE: "bg-accent/15 text-accent",
  COMPLETED: "bg-risk-low/15 text-risk-low",
  CANCELLED: "bg-risk-critical/15 text-risk-critical",
};

/** Keputusan yang boleh melahirkan tindakan hanya dua; keduanya diberi warna sendiri. */
const DECISION_BADGE: Record<string, string> = {
  APPROVED: "bg-risk-low/15 text-risk-low",
  MODIFIED: "bg-accent/15 text-accent",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge shrink-0 ${STATUS_BADGE[status] ?? "bg-base-800 text-ink-muted"}`}>
      {ACTION_STATUS_LABELS[status] ?? status}
    </span>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span className={`badge shrink-0 ${DECISION_BADGE[decision] ?? "bg-base-800 text-ink-muted"}`}>
      {DECISION_LABELS[decision] ?? decision}
    </span>
  );
}

function functionLabel(value: string): string {
  return FUNCTION_LABELS[value] ?? value;
}

function area(row: { kecamatan: string | null; polsek: string | null }): string {
  return [row.kecamatan, row.polsek].filter(Boolean).join(" · ") || "Wilayah tidak tercatat";
}

function href(code: string): string {
  return `/operasi?dipilih=${encodeURIComponent(code)}`;
}

function Card({
  code,
  selected,
  badge,
  heading,
  meta,
  summary,
}: {
  code: string;
  selected: boolean;
  badge: React.ReactNode;
  heading: string;
  meta: string;
  summary: string;
}) {
  return (
    <li>
      <Link
        href={href(code)}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-850 hover:border-base-600"
        }`}
      >
        <div className="flex items-start gap-3">
          {badge}
          <span className="flex-1 font-heading text-sm font-semibold text-ink">{heading}</span>
          <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">{code}</span>
        </div>
        <p className="mt-1 text-xs text-ink-muted">{meta}</p>
        <p className="mt-1 line-clamp-2 text-xs text-ink-muted">{summary}</p>
      </Link>
    </li>
  );
}

function Group({
  title,
  note,
  children,
  count,
  emptyLabel,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
  count: number;
  emptyLabel: string;
}) {
  return (
    <div>
      <h3 className="stat-label">
        {title} <span className="text-ink-muted">({count})</span>
      </h3>
      {note ? <p className="mt-1 text-2xs text-ink-muted">{note}</p> : null}
      {count === 0 ? (
        <EmptyState label={emptyLabel} />
      ) : (
        <ul className="mt-2 space-y-2">{children}</ul>
      )}
    </div>
  );
}

/**
 * Perintah yang berlaku disandingkan dengan usulan asli sistem.
 *
 * Bentuknya sama dengan layar `/rekomendasi` dengan sengaja: keduanya harus terbaca
 * sebagai satu jejak yang sama, bukan dua cerita berbeda tentang satu keputusan.
 */
function OrderTrail({
  row,
}: {
  row: { decision: string; original_recommendation: string; modified_text: string | null };
}) {
  const order = effectiveOrder(row);

  return (
    <>
      <div className="mt-4">
        <div className="stat-label">Perintah yang Berlaku</div>
        <p className="mt-1 text-sm leading-relaxed text-ink">{order.text}</p>
        <p className="mt-1 text-2xs text-ink-muted">
          {order.adjusted
            ? "Pejabat menyesuaikan usulan sistem; yang dijalankan di lapangan adalah teks di atas."
            : "Usulan sistem disetujui apa adanya oleh pejabat berwenang."}
        </p>
      </div>

      {order.adjusted ? (
        <div className="mt-3">
          <div className="stat-label">Usulan Asli Sistem</div>
          <p className="mt-1 text-sm leading-relaxed text-ink-muted">
            {row.original_recommendation}
          </p>
          <p className="mt-1 text-2xs text-ink-muted">
            Tidak ditimpa — disimpan berdampingan agar jejak usulan dan keputusan tetap dapat
            ditelusuri.
          </p>
        </div>
      ) : null}
    </>
  );
}

function QueueDetail({
  row,
  units,
  unitScopeBasis,
  canWrite,
}: {
  row: PendingDecisionRow;
  units: PoliceUnitRow[];
  unitScopeBasis: string | null;
  canWrite: boolean;
}) {
  return (
    <Panel title="Rincian Penugasan">
      <div className="flex flex-wrap items-center gap-3">
        <DecisionBadge decision={row.decision} />
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {row.decision_code}
        </span>
        <span className="text-xs text-ink-muted">
          Fungsi {functionLabel(row.recommended_function)}
          {row.priority ? ` · Prioritas ${PRIORITY_LABELS[row.priority] ?? row.priority}` : ""}
          {` · ${area(row)}`}
        </span>
      </div>

      <p className="mt-2 text-xs text-ink-muted">
        Diputus {formatWib(row.decision_at)} atas rekomendasi{" "}
        <Link
          href={`/rekomendasi?dipilih=${encodeURIComponent(row.recommendation_code)}`}
          className="font-mono text-accent hover:underline"
        >
          {row.recommendation_code}
        </Link>
        .
      </p>

      <p className="mt-3 rounded border border-risk-moderate/40 bg-risk-moderate/10 px-3 py-2 text-xs text-risk-moderate">
        Keputusan ini belum ditindaklanjuti. Belum ada satuan yang ditugaskan, sehingga belum ada
        hasil nyata yang dapat dievaluasi.
      </p>

      <OrderTrail row={row} />

      {canWrite ? (
        <AssignmentForm
          decisionCode={row.decision_code}
          units={units}
          scopeBasis={unitScopeBasis}
        />
      ) : (
        <p className="mt-4 border-t border-base-800 pt-4 text-xs text-ink-muted">
          Keputusan ini menunggu penugasan oleh Command Center. Peran Anda tidak memiliki kewenangan
          mencatat penugasan.
        </p>
      )}
    </Panel>
  );
}

function ActionDetail({ row, canWrite }: { row: OperationRow; canWrite: boolean }) {
  const closed = FINAL_STATUSES.includes(row.status);

  return (
    <Panel title="Rincian Penugasan">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={row.status} />
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {row.code}
        </span>
        <span className="text-xs text-ink-muted">
          {ACTION_STATUS_HINTS[row.status] ?? "Status tidak dikenali"}
        </span>
      </div>

      <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <div>
          <dt className="stat-label">Satuan Ditugaskan</dt>
          <dd className="mt-0.5 text-sm text-ink">
            {row.unit_name}{" "}
            <span className="text-xs text-ink-muted">
              ({row.unit_code} · {functionLabel(row.unit_function)})
            </span>
          </dd>
        </div>
        <div>
          <dt className="stat-label">Wilayah Penugasan</dt>
          <dd className="mt-0.5 text-sm text-ink">
            {area(row)}
            {row.kelurahan ? (
              <span className="text-xs text-ink-muted"> · {row.kelurahan}</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="stat-label">Mulai</dt>
          <dd className="mt-0.5 text-sm text-ink">{formatWib(row.start_at)}</dd>
        </div>
        <div>
          <dt className="stat-label">Selesai</dt>
          <dd className="mt-0.5 text-sm text-ink">{formatWib(row.end_at)}</dd>
        </div>
      </dl>

      <p className="mt-3 text-xs text-ink-muted">
        Lahir dari keputusan <span className="font-mono text-ink">{row.decision_code}</span> (
        {DECISION_LABELS[row.decision] ?? row.decision}, {formatWib(row.decision_at)}) atas
        rekomendasi{" "}
        <Link
          href={`/rekomendasi?dipilih=${encodeURIComponent(row.recommendation_code)}`}
          className="font-mono text-accent hover:underline"
        >
          {row.recommendation_code}
        </Link>
        .
      </p>

      <OrderTrail row={row} />

      <div className="mt-4 border-t border-base-800 pt-4">
        <div className="stat-label">{closed ? "Hasil Nyata" : "Catatan Penugasan"}</div>
        <p className="mt-1 text-sm leading-relaxed text-ink">
          {row.result ?? (closed ? "Tidak diuraikan." : "Belum ada catatan.")}
        </p>
        {closed ? null : (
          <p className="mt-1 text-2xs text-ink-muted">
            Ini catatan rencana, bukan hasil. Hasil nyata belum tercatat, sehingga penugasan ini
            belum dapat ikut dievaluasi.
          </p>
        )}
      </div>

      {closed ? (
        <p className="mt-4 border-t border-base-800 pt-4 text-xs text-ink-muted">
          Hasil sudah tercatat dan tidak dapat diubah dari layar ini.
        </p>
      ) : canWrite ? (
        <ResultForm code={row.code} startHint={formatWib(row.start_at)} />
      ) : (
        <p className="mt-4 border-t border-base-800 pt-4 text-xs text-ink-muted">
          Hasil nyata dicatat oleh Command Center. Peran Anda tidak memiliki kewenangan mencatat
          hasil.
        </p>
      )}
    </Panel>
  );
}

export function OperationBoard({
  queue,
  awaitingResult,
  withResult,
  selectedDecision,
  selectedAction,
  units,
  unitScopeBasis,
  canWrite,
}: {
  queue: PendingDecisionRow[];
  awaitingResult: OperationRow[];
  withResult: OperationRow[];
  selectedDecision: PendingDecisionRow | null;
  selectedAction: OperationRow | null;
  units: PoliceUnitRow[];
  /** Keterangan cakupan dari `/police-units`, ditampilkan apa adanya seperti `*_basis` lain. */
  unitScopeBasis: string | null;
  canWrite: boolean;
}) {
  const selectedCode = selectedDecision?.decision_code ?? selectedAction?.code ?? null;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Panel title="Antrean & Tindakan Operasional" bodyClassName="space-y-5 overflow-y-auto">
        <Group
          title="Sudah Diputus, Belum Ditindaklanjuti"
          note="Keputusan pejabat yang belum melahirkan penugasan satu pun."
          count={queue.length}
          emptyLabel="Seluruh keputusan yang disetujui sudah ditindaklanjuti."
        >
          {queue.map((row) => (
            <Card
              key={row.decision_code}
              code={row.decision_code}
              selected={row.decision_code === selectedCode}
              badge={<DecisionBadge decision={row.decision} />}
              heading={functionLabel(row.recommended_function)}
              meta={`${area(row)} · diputus ${formatWib(row.decision_at)}`}
              summary={effectiveOrder(row).text}
            />
          ))}
        </Group>

        <Group
          title="Berjalan, Hasil Belum Tercatat"
          note="Penugasan sudah dicatat, tetapi hasil nyatanya belum masuk ke evaluasi."
          count={awaitingResult.length}
          emptyLabel="Tidak ada penugasan yang menunggu pencatatan hasil."
        >
          {awaitingResult.map((row) => (
            <Card
              key={row.code}
              code={row.code}
              selected={row.code === selectedCode}
              badge={<StatusBadge status={row.status} />}
              heading={row.unit_name}
              meta={`${area(row)} · mulai ${formatWib(row.start_at)}`}
              summary={effectiveOrder(row).text}
            />
          ))}
        </Group>

        <Group
          title="Hasil Sudah Tercatat"
          count={withResult.length}
          emptyLabel="Belum ada hasil nyata yang tercatat."
        >
          {withResult.map((row) => (
            <Card
              key={row.code}
              code={row.code}
              selected={row.code === selectedCode}
              badge={<StatusBadge status={row.status} />}
              heading={row.unit_name}
              meta={`${area(row)} · selesai ${formatWib(row.end_at)}`}
              summary={row.result ?? "Hasil tidak diuraikan."}
            />
          ))}
        </Group>
      </Panel>

      {selectedDecision ? (
        <QueueDetail
          row={selectedDecision}
          units={units}
          unitScopeBasis={unitScopeBasis}
          canWrite={canWrite}
        />
      ) : selectedAction ? (
        <ActionDetail row={selectedAction} canWrite={canWrite} />
      ) : (
        <Panel title="Rincian Penugasan">
          <EmptyState label="Pilih satu keputusan atau tindakan untuk melihat rinciannya." />
        </Panel>
      )}
    </div>
  );
}
