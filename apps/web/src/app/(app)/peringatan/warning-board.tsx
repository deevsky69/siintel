import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import { RISK_TEXT, type RiskClass } from "@/lib/risk";
import {
  allowsTransition,
  formatWib,
  type PredictionDetail,
  SEVERITY_LABELS,
  STATUS_HINTS,
  STATUS_LABELS,
  severityRiskClass,
  WARNING_ACTIONS,
  type WarningAction,
  type WarningDetail,
  type WarningStatus,
} from "@/lib/warnings";
import { ExplainabilityPanel } from "./explainability";
import { FollowUpForm } from "./follow-up-form";

/**
 * Kelas badge ditulis utuh, bukan dirangkai dari potongan, supaya Tailwind benar-benar
 * membangkitkan kelasnya saat memindai berkas ini.
 */
const SEVERITY_BADGE: Record<RiskClass, string> = {
  LOW: "bg-risk-low/15 text-risk-low",
  MODERATE: "bg-risk-moderate/15 text-risk-moderate",
  HIGH: "bg-risk-high/15 text-risk-high",
  CRITICAL: "bg-risk-critical/15 text-risk-critical",
};

export type WarningGroup = {
  status: WarningStatus;
  rows: WarningDetail[];
  /** Jumlah seluruh baris berstatus ini di backend, bukan hanya yang termuat di halaman. */
  total: number;
};

function WarningCard({ warning, selected }: { warning: WarningDetail; selected: boolean }) {
  const risk = severityRiskClass(warning.severity);

  return (
    <li>
      <Link
        href={`/peringatan?dipilih=${encodeURIComponent(warning.code)}`}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-850 hover:border-base-600"
        }`}
      >
        <div className="flex items-start gap-3">
          <span className={`badge shrink-0 ${SEVERITY_BADGE[risk]}`}>
            {SEVERITY_LABELS[warning.severity] ?? warning.severity}
          </span>
          <span className="flex-1 font-heading text-sm font-semibold text-ink">
            {warning.threat_type}
          </span>
          <span className="font-mono text-2xs uppercase tracking-wider text-ink-muted">
            {warning.code}
          </span>
        </div>

        <div className="mt-2 flex items-end gap-3">
          <div className="min-w-0 flex-1">
            <div className="stat-label">Lokasi</div>
            <div className="truncate text-xs text-ink">
              {warning.kecamatan}
              {warning.kelurahan ? ` — ${warning.kelurahan}` : ""}
              {warning.grid_id ? (
                <span className="ml-1 font-mono text-2xs text-ink-muted">{warning.grid_id}</span>
              ) : null}
            </div>
          </div>
          <div className="text-right">
            <div className="stat-label">Risk</div>
            <div className={`font-heading text-xl font-bold leading-none ${RISK_TEXT[risk]}`}>
              {warning.risk_score}
              <span className="text-2xs text-ink-muted">/100</span>
            </div>
          </div>
          <div className="text-right">
            <div className="stat-label">Confidence</div>
            <div className="font-mono text-xs text-ink">
              {warning.confidence !== null ? `${warning.confidence}%` : "—"}
            </div>
          </div>
        </div>

        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 border-t border-base-800 pt-2">
          <div>
            <span className="stat-label">Jendela Waktu</span>
            <span className="ml-1 font-mono text-xs text-ink">{warning.time_window ?? "—"}</span>
          </div>
          <div className="text-right">
            <span className="stat-label">Ambang</span>
            <span className="ml-1 font-mono text-xs text-ink">
              {warning.threshold_version ?? "tidak ada"}
            </span>
          </div>
          <div className="col-span-2 text-2xs text-ink-muted">
            {formatWib(warning.window_start)} → {formatWib(warning.window_end)}
          </div>
        </div>
      </Link>
    </li>
  );
}

function GroupPanel({ group, selectedCode }: { group: WarningGroup; selectedCode: string | null }) {
  return (
    <Panel
      title={`Peringatan ${STATUS_LABELS[group.status] ?? group.status}`}
      action={
        <span className="panel-action">
          {group.total > 0 ? `${group.total} peringatan` : "tidak ada"}
        </span>
      }
    >
      <p className="mb-2 text-2xs text-ink-muted">{STATUS_HINTS[group.status]}</p>
      {group.rows.length === 0 ? (
        // Keadaan kosong dinyatakan dengan kata, bukan angka nol.
        <EmptyState
          label={`Tidak ada peringatan berstatus ${STATUS_LABELS[group.status] ?? group.status}.`}
        />
      ) : (
        <>
          <ul className="space-y-2">
            {group.rows.map((warning) => (
              <WarningCard
                key={warning.code}
                warning={warning}
                selected={warning.code === selectedCode}
              />
            ))}
          </ul>
          {group.total > group.rows.length ? (
            <p className="mt-2 text-2xs text-ink-muted">
              Menampilkan {group.rows.length} dari {group.total} peringatan.
            </p>
          ) : null}
        </>
      )}
    </Panel>
  );
}

/**
 * Tindak lanjut peringatan.
 *
 * Tombol hanya ditawarkan bila dua syarat terpenuhi sekaligus: transisinya masih sah
 * menurut status peringatan, dan pengguna memiliki kewenangannya. Keduanya sekadar
 * kenyamanan — backend tetap yang menolak, dengan 409 untuk transisi tidak sah dan 403
 * untuk kewenangan yang tidak dimiliki (CLAUDE.md §21). Yang dihindari di sini adalah
 * menawarkan tombol yang sudah pasti ditolak.
 */
function FollowUpPanel({
  warning,
  canAcknowledge,
  canResolve,
}: {
  warning: WarningDetail | null;
  canAcknowledge: boolean;
  canResolve: boolean;
}) {
  if (!warning) {
    return (
      <Panel title="Tindak Lanjut">
        <EmptyState label="Tidak ada peringatan yang dipilih." />
      </Panel>
    );
  }

  const permitted: Record<WarningAction, boolean> = {
    acknowledge: canAcknowledge,
    resolve: canResolve,
  };

  // Yang masih mungkin menurut status, terlepas dari kewenangan — dipakai untuk
  // membedakan "peringatan sudah selesai" dari "Anda tidak berwenang".
  const possible = WARNING_ACTIONS.filter((action) => allowsTransition(warning.status, action));
  const offers = possible.filter((action) => permitted[action]);

  return (
    <Panel title="Tindak Lanjut">
      <p className="mb-3 text-2xs leading-relaxed text-ink-muted">
        Peringatan terpilih <span className="font-mono text-ink">{warning.code}</span> berstatus{" "}
        <span className="text-ink">{STATUS_LABELS[warning.status] ?? warning.status}</span>.
      </p>

      {offers.length > 0 ? (
        <FollowUpForm code={warning.code} offers={offers} />
      ) : possible.length === 0 ? (
        <p className="text-xs leading-relaxed text-ink-muted">
          Peringatan ini sudah berstatus akhir, sehingga tidak ada tindak lanjut yang tersisa.
        </p>
      ) : (
        // Kewenangan disembunyikan, bukan dinonaktifkan diam-diam: pengguna diberi tahu
        // alasannya agar tahu kepada siapa tindak lanjut ini harus dimintakan.
        <p className="text-xs leading-relaxed text-ink-muted">
          Akun Anda tidak memiliki kewenangan menindaklanjuti peringatan. Tombolnya tidak
          ditampilkan, dan seandainya permintaan tetap dikirim, backend yang menolaknya.
        </p>
      )}

      {/* CLAUDE.md §13: peringatan bukan perintah operasional. */}
      <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
        Peringatan dini bukan perintah. Tindakan operasional hanya lahir setelah keputusan pejabat
        berwenang.
      </p>
    </Panel>
  );
}

/**
 * Warning Center (TASK 111) — bagian tampilan.
 *
 * Dipisahkan dari pengambilan data supaya dapat diuji tanpa backend.
 */
export function WarningBoard({
  groups,
  selected,
  sourcePrediction,
  canAcknowledge,
  canResolve,
}: {
  groups: WarningGroup[];
  selected: WarningDetail | null;
  sourcePrediction: PredictionDetail | null;
  /** Kewenangan dari `/auth/me`; hanya menentukan tombol mana yang tampak. */
  canAcknowledge: boolean;
  canResolve: boolean;
}) {
  const thresholds = [
    ...new Set(
      groups
        .flatMap((group) => group.rows)
        .map((warning) => warning.threshold_version)
        .filter((version): version is string => Boolean(version)),
    ),
  ];

  return (
    <div className="space-y-3">
      {/* CLAUDE.md §11: ambang belum final, dan itu dinyatakan di layar. */}
      <StatusNotice status="DEMO / PROPOSED">
        Ambang yang memicu peringatan pada layar ini berasal dari konfigurasi versi{" "}
        <span className="font-mono">
          {thresholds.length > 0 ? thresholds.join(", ") : "tidak ada"}
        </span>
        . Ambang tersebut belum ditetapkan secara resmi, sehingga tingkat peringatan di sini belum
        boleh dibaca sebagai keputusan final.
      </StatusNotice>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 flex flex-col gap-3 xl:col-span-7">
          {groups.map((group) => (
            <GroupPanel key={group.status} group={group} selectedCode={selected?.code ?? null} />
          ))}
        </div>

        <div className="col-span-12 flex flex-col gap-3 xl:col-span-5">
          <ExplainabilityPanel warning={selected} prediction={sourcePrediction} />
          <FollowUpPanel
            warning={selected}
            canAcknowledge={canAcknowledge}
            canResolve={canResolve}
          />
        </div>
      </div>
    </div>
  );
}
