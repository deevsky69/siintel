import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getProfile } from "@/lib/dashboard";
import { getBacktest, getMonthlyEvaluation } from "@/lib/monthly-evaluation";
import { listProducts } from "@/lib/monthly-products";
import { getRankingOptions } from "@/lib/rankings";
import { WorkLogForm } from "./work-form";

export const dynamic = "force-dynamic";

/** Evaluasi bulanan (Modul 5 mekanisme): cakupan, pembanding, mutu usulan, pelaksanaan. */
export default async function EvaluasiBulananPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.bulan;
  const [options, products, profile] = await Promise.all([
    getRankingOptions(),
    listProducts(),
    getProfile(),
  ]);
  const canRecord = profile.permissions.includes("monthly_product:review");
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
  // Dua desimal dengan koma, seperti tabel naskah (29,97%; 3,05; 3,25×).
  const koma = (value: number, digits = 2) => value.toFixed(digits).replace(".", ",");
  const pct = (value: number | null) => (value === null ? "—" : `${koma(value)}%`);
  const num = (value: number | null) => (value === null ? "—" : koma(value));
  const kali = (value: number | null) => (value === null ? "—" : `${koma(value)}×`);
  const menit = (value: number | null) => (value === null ? "belum tercatat" : `${value} menit`);
  const waktu = (iso: string | null) =>
    iso === null
      ? "belum ada"
      : new Intl.DateTimeFormat("id-ID", {
          timeZone: "Asia/Jakarta",
          dateStyle: "medium",
          timeStyle: "short",
        }).format(new Date(iso));

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
                <th className="py-1 pr-2 text-right">Porsi luas</th>
                <th className="py-1 pr-2 text-right">PAI</th>
                <th className="py-1 pr-2 text-right">Kelipatan acak</th>
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
                    {pct(row.area_pct)}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                    {num(row.pai)}
                  </td>
                  <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                    {kali(row.vs_random)}
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
            {result.random_coverage_pct !== null
              ? ` Pembanding acak: ${result.top_n} dari ${result.kelurahan_total} kelurahan dipilih acak rata-rata mencakup ${pct(result.random_coverage_pct)} kejadian.`
              : ""}{" "}
            PAI kosong berarti ada kelurahan pilihan yang luas BPS-nya belum tercantum, atau angka
            dibatasi ke satu Polsek.
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
      {result.work ? (
        <Panel title="Mutu draf dan waktu kerja">
          <dl className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 xl:grid-cols-4">
            <div>
              <dt className="stat-label">Skor mutu draf SIGAP</dt>
              <dd className="mt-1 text-ink">
                {result.work.quality_sigap_total === null
                  ? "belum dinilai"
                  : `${result.work.quality_sigap_total} dari ${result.work.quality_max}`}
              </dd>
            </div>
            <div>
              <dt className="stat-label">Skor cara kerja biasa</dt>
              <dd className="mt-1 text-ink">
                {result.work.quality_manual_total === null
                  ? "belum dinilai"
                  : `${result.work.quality_manual_total} dari ${result.work.quality_max}`}
              </dd>
            </div>
            <div>
              <dt className="stat-label">Data siap olah → validasi selesai</dt>
              <dd className="mt-1 text-ink">{menit(result.work.minutes_ready_to_validated)}</dd>
            </div>
            <div>
              <dt className="stat-label">Data diterima → siap olah</dt>
              <dd className="mt-1 text-ink">{menit(result.work.minutes_receive_to_ready)}</dd>
            </div>
          </dl>
          <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
            Draf siap {waktu(result.work.draft_ready_at)} · validasi selesai{" "}
            {waktu(result.work.validated_at)} — keduanya dari catatan sistem. Rubrik:{" "}
            {result.work.rubric.map((item) => item.label.toLowerCase()).join(", ")}; skor tiap unsur
            0 belum memenuhi, 1 perlu revisi, 2 memenuhi.
          </p>
          {canRecord ? (
            <div className="mt-3 border-t border-base-800 pt-3">
              <WorkLogForm month={month} work={result.work} />
            </div>
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
                      <th className="py-1 pr-2 text-right">Porsi luas</th>
                      <th className="py-1 pr-2 text-right">PAI</th>
                      <th className="py-1 pr-2 text-right">Kelipatan acak</th>
                      <th className="py-1 pr-2 text-right">Model unggul–kalah–seri</th>
                      <th className="py-1 pr-2 text-right">PAI model unggul</th>
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
                            {pct(row.area_pct)}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {num(row.pai)}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {kali(row.vs_random)}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {test ? `${test.wins}–${test.losses}–${test.ties}` : ""}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {test && test.pai_wins !== null
                              ? `${test.pai_wins} dari ${period.months} bulan`
                              : ""}
                          </td>
                          <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                            {test ? (test.p_value === null ? "—" : koma(test.p_value, 3)) : ""}
                          </td>
                        </tr>
                      );
                    })}
                    <tr>
                      <td className="py-1.5 pr-2 font-semibold text-ink">
                        Acak {period.random.top_n} dari {period.random.kelurahan_total}
                      </td>
                      <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                        {koma(period.random.expected_covered, 1)} / {period.methods[0]?.total ?? 0}
                      </td>
                      <td className="py-1.5 pr-2 text-right tabular-nums font-semibold text-ink">
                        {pct(period.random.coverage_pct)}
                      </td>
                      <td className="py-1.5 pr-2 text-right text-ink-muted">–</td>
                      <td className="py-1.5 pr-2 text-right text-ink-muted">–</td>
                      <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">1,00×</td>
                      <td colSpan={3} />
                    </tr>
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
              <thead className="text-left text-2xs uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="py-1 pr-2">Metode</th>
                  <th className="py-1 pr-2 text-right">Tercakup</th>
                  <th className="py-1 pr-2 text-right">Cakupan</th>
                  <th className="py-1 pr-2 text-right">Porsi luas</th>
                  <th className="py-1 pr-2 text-right">PAI</th>
                  <th className="py-1 pr-2 text-right">Kelipatan acak</th>
                </tr>
              </thead>
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
                    <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                      {pct(row.area_pct)}
                    </td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                      {num(row.pai)}
                    </td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-ink-muted">
                      {kali(row.vs_random)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <p className="mt-3 rounded border border-base-800 bg-base-850 p-2 text-2xs leading-relaxed text-ink-muted">
            <span className="font-semibold text-ink">Ambang pemakaian model.</span> Rata-rata
            cakupan AI dalam {backtest.criterion.months} siklus berturut-turut melampaui metode
            historis terbaik sekurang-kurangnya {koma(backtest.criterion.min_margin_pct, 0)} poin
            persen dengan PAI sekurang-kurangnya {koma(backtest.criterion.min_pai, 1)}; apabila
            belum tercapai, peringkat historis terbaik dipakai sebagai dasar prioritas sementara
            model diperbaiki. ({backtest.criterion.source}.) Penilaian untuk bulan sasaran tertentu
            tampil pada halaman Peringkat.
          </p>
          {backtest.area_source ? (
            <p className="mt-2 text-2xs text-ink-faint">
              Luas kelurahan: {backtest.area_source}; luas wilayah hukum{" "}
              {backtest.area_total_km2 === null ? "—" : koma(backtest.area_total_km2)} km². PAI
              kosong berarti ada kelurahan pilihan yang luasnya belum tercantum.
            </p>
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
