import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ApiError } from "@/lib/api";
import { getProfile } from "@/lib/decisions";
import { getProduct, listProducts, type MonthlyProduct } from "@/lib/monthly-products";
import { ActionForm, AnalystForm, DecideForm, DraftForm, OutcomeForm } from "./forms";

export const dynamic = "force-dynamic";

const STEPS = [
  { key: "ANALYST", label: "Analis" },
  { key: "KBO", label: "KBO" },
  { key: "KASAT", label: "Kasat Intelkam" },
  { key: "PIMPINAN", label: "Pimpinan" },
] as const;
const DONE_AT: Record<MonthlyProduct["status"], number> = {
  DRAFT: 0,
  ANALYST_REVIEWED: 1,
  KBO_CHECKED: 2,
  VALIDATED: 3,
  DECIDED: 4,
};

/** Produk bulanan (Modul 4 mekanisme): satu naskah per bulan, empat tahap, lalu pelaksanaan. */
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
  const done = product ? DONE_AT[product.status] : 0;

  return (
    <div className="space-y-3">
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
            <DraftForm month={month} />
          ) : (
            <EmptyState label="Produk bulan ini belum disusun." />
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
            </p>

            {product.status === "DRAFT" && can("monthly_product:draft") ? (
              <AnalystForm month={month} items={product.items} />
            ) : null}
            {product.status === "ANALYST_REVIEWED" && can("monthly_product:review") ? (
              <OutcomeForm month={month} stage="kbo" label="Mutu analisis baik" />
            ) : null}
            {product.status === "KBO_CHECKED" && can("monthly_product:validate") ? (
              <OutcomeForm month={month} stage="kasat" label="Validasi, teruskan ke Pimpinan" />
            ) : null}
            {product.status === "VALIDATED" && can("monthly_product:decide") ? (
              <DecideForm month={month} items={product.items} />
            ) : null}

            {!(product.status === "DRAFT" && can("monthly_product:draft")) &&
            !(product.status === "VALIDATED" && can("monthly_product:decide")) ? (
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
    </div>
  );
}
