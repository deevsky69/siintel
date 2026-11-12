import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ScreenTabs } from "@/components/shell/screen-tabs";
import { ApiError } from "@/lib/api";
import { getProfile } from "@/lib/decisions";
import {
  getProduct,
  isAwaitingDecision,
  listProducts,
  type MonthlyProduct,
} from "@/lib/monthly-products";
import { getMonthlyOutlook, type MonthlyOutlook } from "@/lib/patrol-plan-api";
import { ActionForm, AnalystForm, DecideForm, DraftForm } from "./forms";

export const dynamic = "force-dynamic";

const TABS = [
  { href: "/ops/produk-bulanan", label: "Produk Bulanan" },
  { href: "/ops/peringkat", label: "Peringkat 65 Kelurahan" },
] as const;

/**
 * Dua tahap sejak 10 November 2026 (keputusan pemilik proyek 1B, catatan 177):
 * Analis menyusun draf — peringkat bulan itu dibekukan sekaligus — lalu memeriksa dan
 * mengirim; Pimpinan menetapkan; Fungsi/Polsek mencatat. Tahap KBO dan Kasat dihapus.
 */
const STEPS = [
  { key: "ANALYST", label: "Analis menyusun & memeriksa" },
  { key: "PIMPINAN", label: "Pimpinan menetapkan" },
  { key: "EXECUTE", label: "Pelaksanaan dicatat" },
] as const;
const THREAT_LABEL: Record<string, string> = {
  CURANMOR: "curanmor",
  CURAT: "curat",
  CURAS: "curas",
};

function doneAt(product: MonthlyProduct | null): number {
  if (!product) return 0;
  if (product.status === "DECIDED") return 2;
  return isAwaitingDecision(product.status) ? 1 : 0;
}

/** Produk bulanan (Modul 4 mekanisme): satu naskah per bulan, dua tahap, lalu pelaksanaan. */
export default async function ProdukBulananPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.bulan;
  const [profile, list] = await Promise.all([getProfile(), listProducts()]);
  const month =
    (Array.isArray(raw) ? raw[0] : raw) || list.data[0]?.target_month || list.suggested_month;
  const can = (p: string) => profile.permissions.includes(p);
  let product: MonthlyProduct | null = null;
  try {
    product = await getProduct(month);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) throw error;
  }
  // Lampiran: perkiraan singkat bulan sasaran (sebelumnya layar Rencana Patroli tersendiri
  // dengan persetujuannya sendiri — 2.ii). Gagal/403 → lampiran tidak tampil, naskah tetap.
  const outlook: MonthlyOutlook | null = product
    ? await getMonthlyOutlook(month).catch(() => null)
    : null;
  const done = doneAt(product);
  const awaiting = product ? isAwaitingDecision(product.status) : false;
  const analystTurn = product?.status === "DRAFT" && can("monthly_product:draft");
  const leaderTurn = awaiting && can("monthly_product:decide");
  const attachedNames = new Set(
    (product?.status === "DECIDED"
      ? product.items.filter((item) => item.selected)
      : (product?.items ?? [])
    ).map((item) => item.kelurahan),
  );
  const attachedSlots = (outlook?.threats ?? []).flatMap((threat) =>
    threat.slots
      .filter((slot) => attachedNames.has(slot.kelurahan))
      .map((slot) => ({ ...slot, threat_type: threat.threat_type })),
  );

  return (
    <div className="space-y-3">
      <ScreenTabs tabs={TABS} current="/ops/produk-bulanan" />
      <Panel
        title={`Produk Bulanan ${month}`}
        action={
          <span className="panel-action">
            {[list.suggested_month, ...list.data.map((row) => row.target_month)]
              .filter((value, index, all) => all.indexOf(value) === index)
              .map((value) => (
                <Link
                  key={value}
                  href={`/ops/produk-bulanan?bulan=${value}`}
                  className={`mr-2 ${value === month ? "text-accent" : ""}`}
                >
                  {value}
                </Link>
              ))}
          </span>
        }
      >
        <ol className="mb-3 flex flex-wrap gap-2 text-xs">
          {STEPS.map((step, index) => (
            <li
              key={step.key}
              className={`rounded-full border px-2.5 py-0.5 ${
                index < done
                  ? "border-risk-low/60 bg-risk-low/10 text-risk-low"
                  : index === done && product
                    ? "border-accent/60 bg-accent/10 text-accent"
                    : "border-base-800 text-ink-faint"
              }`}
            >
              {index + 1}. {step.label}
            </li>
          ))}
        </ol>

        {!product ? (
          can("monthly_product:draft") ? (
            <div className="space-y-2">
              <p className="text-xs text-ink-muted">
                Menyusun draf sekaligus membekukan peringkat {month}; yang dibekukan itulah yang
                dievaluasi setelah bulan berakhir.
              </p>
              <DraftForm month={month} />
            </div>
          ) : (
            <EmptyState label="Produk bulan ini belum disusun Analis." />
          )
        ) : (
          <>
            <p className="mb-3 text-xs text-ink-muted">
              {product.facts.method} · batas data {product.facts.data_cutoff} ·{" "}
              {product.facts.total_basis} kejadian dasar · {product.facts.pending_count} menunggu
              konfirmasi kelurahan
              {product.priority_count !== null
                ? ` · ${product.priority_count} kelurahan prioritas`
                : ""}
              {awaiting && !leaderTurn ? " · menunggu penetapan Pimpinan" : ""}
            </p>

            {analystTurn ? <AnalystForm month={month} items={product.items} /> : null}
            {leaderTurn ? <DecideForm month={month} items={product.items} /> : null}

            {!analystTurn && !leaderTurn ? (
              <ul className="divide-y divide-base-800">
                {product.items.map((item) => (
                  <li
                    key={item.kelurahan}
                    className={`py-2 text-xs ${item.analyst_status === "REJECTED" ? "opacity-50" : ""}`}
                  >
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="tabular-nums text-ink-muted">{item.rank}</span>
                      <span className="font-semibold text-ink">{item.kelurahan}</span>
                      <span className="text-ink-faint">{item.kecamatan}</span>
                      <span className="text-ink-faint">
                        {item.predicted_count.toFixed(1)}/bulan
                      </span>
                      {item.analyst_status ? (
                        <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs">
                          {item.analyst_status}
                        </span>
                      ) : null}
                      {item.selected ? (
                        <span className="rounded bg-risk-low/15 px-1.5 py-0.5 text-2xs font-semibold text-risk-low">
                          PRIORITAS
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-ink-muted">
                      {item.decided_action ?? item.analyst_text ?? item.proposal_text}
                    </p>
                    {item.analyst_reason ? (
                      <p className="text-2xs text-ink-faint">
                        Alasan analis: {item.analyst_reason}
                      </p>
                    ) : null}
                    {item.actions.length > 0 ? (
                      <ul className="mt-1 text-2xs text-ink-faint">
                        {item.actions.map((a) => (
                          <li key={`${a.acted_at}-${a.place}`}>
                            {a.acted_at.slice(0, 16).replace("T", " ")} · {a.unit} · {a.place} ·{" "}
                            {a.action}
                            {a.result ? ` · ${a.result}` : ""}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {product.status === "DECIDED" &&
                    item.selected &&
                    can("monthly_product:execute") ? (
                      <ActionForm month={month} kelurahan={item.kelurahan} />
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}

            {product.stages.length > 0 ? (
              <ul className="mt-3 text-2xs text-ink-faint">
                {product.stages.map((s) => (
                  <li key={`${s.stage}-${s.acted_at}`}>
                    {s.stage} · {s.outcome} · {s.acted_at.slice(0, 16).replace("T", " ")}
                    {s.reason ? ` · ${s.reason}` : ""}
                    {s.note ? ` · ${s.note}` : ""}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        )}
      </Panel>

      {product && outlook ? (
        <Panel
          title={`Lampiran: perkiraan jam rawan ${outlook.target_label}`}
          action={
            <a
              href={`/api/perkiraan?bulan=${month}`}
              className="panel-action text-accent"
              title="Unduh perkiraan lengkap (.docx)"
            >
              Unduh .docx
            </a>
          }
        >
          <p className="mb-2 text-2xs leading-relaxed text-ink-faint">
            Blok jam per kelurahan {product.status === "DECIDED" ? "prioritas" : "dalam draf"} dari
            kejadian bulan yang sama tahun-tahun sebelumnya
            {outlook.basis_labels.length ? ` (${outlook.basis_labels.join(", ")})` : ""}. Ikut
            penetapan Pimpinan di atas; tidak ada persetujuan tersendiri. {outlook.status}.
          </p>
          {attachedSlots.length === 0 ? (
            <EmptyState label="Tidak ada blok jam yang menonjol untuk kelurahan ini." />
          ) : (
            <ul className="divide-y divide-base-800 text-xs">
              {attachedSlots.map((slot) => (
                <li
                  key={`${slot.threat_type}-${slot.kelurahan}-${slot.block_start}`}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5"
                >
                  <span className="font-semibold text-ink">{slot.kelurahan}</span>
                  <span className="text-ink-muted">
                    {THREAT_LABEL[slot.threat_type] ?? slot.threat_type}
                  </span>
                  <span className="font-mono text-ink-muted">{slot.block_label}</span>
                  <span className="text-ink-faint">
                    {slot.incidents} kejadian · {slot.function}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      ) : null}
    </div>
  );
}
