import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import {
  DECISION_LABELS,
  type DecisionRow,
  FUNCTION_LABELS,
  headlineOf,
  PENDING,
  PRIORITY_LABELS,
  type RecommendationRow,
} from "@/lib/decisions";
import { RISK_LABELS, RISK_TEXT, riskClassOf } from "@/lib/risk";
import { formatWib } from "@/lib/warnings";
import { DecisionForm } from "./decision-form";

/**
 * Layar Rekomendasi & Keputusan Pimpinan (TASK 121, 130; disusun ulang 7 Oktober 2026).
 *
 * Inti layar ini bukan daftarnya, melainkan **jejaknya**: usulan sistem dan keputusan
 * pejabat ditampilkan berdampingan, sehingga terlihat bahwa yang dijalankan di lapangan
 * adalah keputusan manusia — bukan keluaran model yang diteruskan begitu saja
 * (CLAUDE.md §13, success criteria #05 Taskap).
 *
 * ## Disusun untuk dibaca Pimpinan dalam sepuluh detik
 *
 * Permintaan pemilik proyek 7 Oktober 2026: lebih ringkas dan mudah dibaca. Urutan
 * bacanya kini **apa → di mana → kapan → seberapa besar → apa yang diusulkan → putuskan**:
 * kartu daftar memuat satu baris apa/di mana/kapan, panel rincian membuka dengan empat
 * angka besar sebelum kalimat usulan, dan tiga tombol keputusan berada tepat di bawahnya.
 * Rincian teknis (kode prediksi, kode peringatan, waktu dibuat) dipindahkan ke baris
 * kecil paling bawah — tetap ada untuk ketertelusuran, tidak lagi menghalangi.
 */

/** Kelas ditulis utuh agar Tailwind membangkitkannya saat memindai berkas ini. */
const STATUS_BADGE: Record<string, string> = {
  PENDING_REVIEW: "bg-risk-moderate/15 text-risk-moderate",
  APPROVED: "bg-risk-low/15 text-risk-low",
  MODIFIED: "bg-accent/15 text-accent",
  REJECTED: "bg-risk-critical/15 text-risk-critical",
};

const PRIORITY_TONE: Record<string, string> = {
  HIGH: "text-risk-critical",
  MEDIUM: "text-risk-moderate",
  LOW: "text-ink-muted",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge shrink-0 ${STATUS_BADGE[status] ?? "bg-base-800 text-ink-muted"}`}>
      {DECISION_LABELS[status] ?? status}
    </span>
  );
}

function RecommendationCard({ row, selected }: { row: RecommendationRow; selected: boolean }) {
  const headline = headlineOf(row);
  const risk = row.risk_score != null ? riskClassOf(row.risk_score) : null;
  return (
    <li>
      <Link
        href={`/rekomendasi?dipilih=${encodeURIComponent(row.code)}`}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-850 hover:border-base-600"
        }`}
      >
        <div className="flex items-center gap-2">
          {row.risk_score != null ? (
            <span
              className={`w-9 shrink-0 text-right font-heading text-lg font-bold leading-none ${risk ? RISK_TEXT[risk] : "text-ink"}`}
            >
              {row.risk_score}
            </span>
          ) : null}
          <div className="min-w-0 flex-1">
            <p className="truncate font-heading text-sm font-semibold text-ink">
              {headline || FUNCTION_LABELS[row.recommended_function] || row.recommended_function}
            </p>
            <p className="mt-0.5 truncate text-2xs text-ink-muted">
              {FUNCTION_LABELS[row.recommended_function] ?? row.recommended_function}
              {row.priority ? (
                <>
                  {" · "}
                  <span className={PRIORITY_TONE[row.priority] ?? ""}>
                    prioritas {PRIORITY_LABELS[row.priority] ?? row.priority}
                  </span>
                </>
              ) : null}
              {" · "}
              {row.recommendation_text}
            </p>
          </div>
          <StatusBadge status={row.status} />
        </div>
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

/** Satu angka besar berlabel: apa / di mana / kapan / risiko. */
function Key({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded border border-base-800 bg-base-900/60 px-3 py-2">
      <div className="stat-label">{label}</div>
      <div className={`mt-0.5 truncate font-heading text-base font-semibold ${tone ?? "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}

function DecisionRecord({ decision }: { decision: DecisionRow }) {
  return (
    <div className="mt-4 border-t border-base-800 pt-4">
      <div className="flex items-center gap-3">
        <StatusBadge status={decision.decision} />
        <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
          {decision.code}
        </span>
        <span className="text-xs text-ink-muted">{formatWib(decision.decided_at)}</span>
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
  const risk = row.risk_score != null ? riskClassOf(row.risk_score) : null;
  const where = [row.kelurahan, row.kecamatan].filter(Boolean).join(", ");
  return (
    <Panel title="Usulan Sistem & Keputusan">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={row.status} />
        <span className="text-xs text-ink-muted">
          Untuk{" "}
          <strong className="text-ink">
            {FUNCTION_LABELS[row.recommended_function] ?? row.recommended_function}
          </strong>
          {row.priority ? (
            <>
              {" · prioritas "}
              <strong className={PRIORITY_TONE[row.priority] ?? "text-ink"}>
                {PRIORITY_LABELS[row.priority] ?? row.priority}
              </strong>
            </>
          ) : null}
        </span>
      </div>

      {/* Empat kunci sebelum kalimat: Pimpinan memutuskan dari sini, bukan dari paragraf. */}
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Key label="Apa" value={row.threat_type ?? "—"} />
        <Key label="Di mana" value={where || "—"} />
        <Key label="Kapan" value={row.time_window ?? "—"} />
        <Key
          label="Risiko"
          value={
            row.risk_score != null
              ? `${row.risk_score}/100${risk ? ` · ${RISK_LABELS[risk]}` : ""}`
              : "—"
          }
          tone={risk ? RISK_TEXT[risk] : undefined}
        />
      </div>

      <div className="mt-4">
        <div className="stat-label">Usulan Sistem</div>
        <p className="mt-1 text-base leading-relaxed text-ink">{row.recommendation_text}</p>
        <p className="mt-1.5 text-2xs text-ink-muted">
          Usulan adalah <strong className="text-ink">opsi, bukan perintah</strong>; yang dijalankan
          adalah keputusan pejabat di bawah ini.
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

      {/* Ketertelusuran, di paling bawah dan kecil: tetap ada, tidak lagi menghalangi. */}
      <p className="mt-4 border-t border-base-800 pt-3 font-mono text-2xs text-ink-faint">
        {row.code} · dari prediksi{" "}
        <Link
          href={`/peringatan${row.warning_code ? `?dipilih=${encodeURIComponent(row.warning_code)}` : ""}`}
          className="text-accent hover:underline"
        >
          {row.prediction_code}
        </Link>
        {row.warning_code ? ` melalui peringatan ${row.warning_code}` : ""} · dibuat{" "}
        {formatWib(row.created_at)}
      </p>
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
