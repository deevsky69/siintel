import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getBacktest, getMonthlyEvaluation } from "@/lib/monthly-evaluation";
import { listProducts } from "@/lib/monthly-products";
import { getRankingOptions } from "@/lib/rankings";

export const dynamic = "force-dynamic";

/** Evaluasi bulanan (Modul 5 mekanisme): cakupan, pembanding, mutu usulan, pelaksanaan. */
export default async function EvaluasiBulananPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.bulan;
  const [options, products] = await Promise.all([getRankingOptions(), listProducts()]);
  const months = [
    ...new Set([
      ...options.frozen.map((f) => f.target_month),
      ...products.data.map((p) => p.target_month),
    ]),
  ]
    .sort()
    .reverse();
  const month = (Array.isArray(raw) ? raw[0] : raw) || months[0] || options.suggested_month;
  const rawScope = params.cakupan;
  const scope = (Array.isArray(rawScope) ? rawScope[0] : rawScope) || options.default_scope;
  // Jumlah kelurahan uji: naskah Lampiran 8 K membandingkan 4, 6, dan 8.
  const rawN = params.n;
  const wantedN = Number((Array.isArray(rawN) ? rawN[0] : rawN) ?? "");
  const topN = [4, 6, 8].includes(wantedN) ? wantedN : undefined;
  // Uji historis berdiri sendiri: bila gagal, evaluasi bulan tetap tampil.
  const [result, backtest] = await Promise.all([
    getMonthlyEvaluation(month),
    getBacktest(scope, topN).catch(() => null),
  ]);
  const pct = (value: number | null) => (value === null ? "—" : `${value.toFixed(1)}%`);
  const num = (value: number | null) => (value === null ? "—" : value.toFixed(2));

  return (
    <div className="space-y-3">
      <Panel
        title={`Evaluasi ${month}`}
        action={
          <span className="panel-action">
            {months.map((value) => (
              <Link
                key={value}
                href={`/ops/evaluasi-bulanan?bulan=${value}`}
                className={`mr-2 ${value === month ? "text-accent" : ""}`}
              >
                {value}
              </Link>
            ))}
          </span>
        }
      >
        {result.methods.length === 0 ? (
          <EmptyState label="Belum ada peringkat yang dibekukan untuk bulan ini." />
        ) : (
          <table className="w-full text-xs">
            <thead className="text-left text-2xs uppercase tracking-wide text-ink-faint">
              <tr>
                <th className="py-1 pr-2">Metode</th>
                <th className="py-1 pr-2">Cakupan data</th>
                <th className="py-1 pr-2 text-right">Tercakup</th>
                <th className="py-1 pr-2 text-right">Cakupan</th>
                <th className="py-1 pr-2 text-right">PAI</th>
                <th className="py-1 pr-2">Kelurahan ({result.top_n})</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-base-800">
              {result.methods.map((row) => (
                <tr key={`${row.method}-${row.scope}`} className={row.frozen ? "bg-accent/5" : ""}>
                  <td className="py-1.5 pr-2 font-semibold text-ink">
                    {row.method_label}
                    {row.frozen ? (
                      <span className="ml-1 rounded bg-risk-low/15 px-1 text-2xs text-risk-low">
                        beku
                      </span>
                    ) : null}
                  </td>
                  <td className="py-1.5 pr-2 text-ink-muted">
                    {row.scope === "VEHICLE" ? "Kendaraan" : "Semua 3C"}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                    {row.covered} / {row.mappable_total}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums font-semibold text-ink">
                    {pct(row.coverage_pct)}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                    {num(row.pai)}
                  </td>
                  <td className="py-1.5 pr-2 text-ink-faint">{row.selected.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {result.methods[0] ? (
          <p className="mt-2 text-2xs text-ink-faint">
            {result.methods[0].unmappable} kejadian bulan ini belum dapat dipetakan ke kelurahan.
          </p>
        ) : null}
      </Panel>

      {result.decision ? (
        <Panel
          title="Keputusan Pimpinan"
          action={<span className="panel-action">{pct(result.decision.coverage_pct)}</span>}
        >
          <ul className="divide-y divide-base-800 text-xs">
            {result.decision.items.map((item) => (
              <li key={item.kelurahan} className="flex flex-wrap items-center gap-x-3 py-1.5">
                <span className="font-semibold text-ink">{item.kelurahan}</span>
                <span className="text-ink-faint">{item.kecamatan}</span>
                <span className="tabular-nums text-ink-muted">{item.actual} kejadian</span>
                <span className="tabular-nums text-ink-muted">{item.actions} kegiatan</span>
                <span className="text-ink-faint">{item.decided_action}</span>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      {result.quality ? (
        <Panel title="Mutu usulan">
          <p className="text-xs text-ink-muted">
            Diterima {result.quality.analyst.ACCEPTED ?? 0} · Direvisi{" "}
            {result.quality.analyst.REVISED ?? 0} · Ditolak {result.quality.analyst.REJECTED ?? 0}
            {result.quality.returned.length > 0
              ? ` · Dikembalikan ${result.quality.returned.length}×`
              : ""}
          </p>
          {result.quality.reasons.length > 0 ? (
            <ul className="mt-2 text-2xs text-ink-faint">
              {result.quality.reasons.map((row) => (
                <li key={row.kelurahan}>
                  {row.kelurahan} · {row.status} · {row.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </Panel>
      ) : null}
      <p className="text-2xs text-ink-faint">{result.basis}</p>

      {backtest ? (
        <Panel
          title="Uji historis model"
          action={
            <span className="panel-action">
              {options.scopes.map((item) => (
                <Link
                  key={item}
                  href={`/ops/evaluasi-bulanan?bulan=${month}&cakupan=${item}&n=${backtest.top_n}`}
                  className={`mr-2 ${item === backtest.scope ? "text-accent" : ""}`}
                >
                  {item === "VEHICLE" ? "Kendaraan" : "Semua 3C"}
                </Link>
              ))}
              <span className="mr-2 text-ink-faint">·</span>
              {[4, 6, 8].map((count) => (
                <Link
                  key={count}
                  href={`/ops/evaluasi-bulanan?bulan=${month}&cakupan=${backtest.scope}&n=${count}`}
                  className={`mr-2 ${count === backtest.top_n ? "text-accent" : ""}`}
                >
                  {count} kelurahan
                </Link>
              ))}
            </span>
          }
        >
          {!backtest.model.available ? (
            <p className="mb-2 text-xs text-ink-muted">
              Model belum tersedia: {backtest.model.reason}
            </p>
          ) : null}
          {backtest.periods.length === 0 ? (
            <EmptyState label="Belum ada bulan uji di luar masa latih model." />
          ) : (
            <div className="space-y-4">
              {backtest.periods.map((period) => (
                <table key={period.label} className="w-full text-xs">
                  <caption className="pb-1 text-left text-2xs uppercase tracking-wide text-ink-faint">
                    {period.label} · {period.span} · {period.months} bulan · {backtest.top_n}{" "}
                    kelurahan
                  </caption>
                  <thead className="text-left text-2xs uppercase tracking-wide text-ink-faint">
                    <tr>
                      <th className="py-1 pr-2">Metode</th>
                      <th className="py-1 pr-2 text-right">Tercakup</th>
                      <th className="py-1 pr-2 text-right">Cakupan</th>
                      <th className="py-1 pr-2 text-right">PAI</th>
                      <th className="py-1 pr-2 text-right">Model unggul–kalah–seri</th>
                      <th className="py-1 pr-2 text-right">Uji tanda (p)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-base-800">
                    {period.methods.map((row) => {
                      const test = period.sign_tests.find((item) => item.against === row.method);
                      return (
                        <tr key={row.method} className={row.kind === "model" ? "bg-accent/5" : ""}>
                          <td className="py-1.5 pr-2 font-semibold text-ink">
                            {row.method_label}
                            {row.kind === "annual" ? ` ${backtest.annual_year}` : ""}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                            {row.covered} / {row.total}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums font-semibold text-ink">
                            {pct(row.coverage_pct)}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {num(row.pai)}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {test ? `${test.wins}–${test.losses}–${test.ties}` : ""}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {test ? (test.p_value === null ? "—" : test.p_value.toFixed(3)) : ""}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ))}
            </div>
          )}
          {backtest.fixed.methods.length > 0 ? (
            <table className="mt-4 w-full text-xs">
              <caption className="pb-1 text-left text-2xs uppercase tracking-wide text-ink-faint">
                Skenario tetap · {backtest.fixed.span} · informasi berhenti pada akhir masa latih
              </caption>
              <tbody className="divide-y divide-base-800">
                {backtest.fixed.methods.map((row) => (
                  <tr key={row.method}>
                    <td className="py-1.5 pr-2 font-semibold text-ink">{row.method_label}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                      {row.covered} / {row.total}
                    </td>
                    <td className="py-1.5 pr-2 text-right tabular-nums font-semibold text-ink">
                      {pct(row.coverage_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <p className="mt-3 text-2xs text-ink-faint">
            {backtest.model.model_version
              ? `${backtest.model.model_version} · dilatih sampai ${backtest.model.train_until} · `
              : ""}
            {backtest.basis}
          </p>
        </Panel>
      ) : null}
    </div>
  );
}
