import { Basis } from "@/components/basis";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import {
  longDate,
  type PatrolPlan,
  PLAN_DECISION_LABELS,
  type PlanDecisionRow,
  type PlanEvaluation,
  percentText,
  slotKeyOf,
  type ThreatEvaluation,
  type ThreatPlan,
} from "@/lib/patrol-plan";
import { PlanDecisionForm } from "./plan-decision-form";

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded border border-base-800 bg-base-850 px-3 py-2.5">
      <div className="stat-label">{label}</div>
      <div className="mt-1 font-heading text-2xl font-bold leading-none text-accent">{value}</div>
      <div className="mt-1.5 text-2xs leading-relaxed text-ink-muted">{hint}</div>
    </div>
  );
}

/**
 * Rencana patroli tahun sasaran — bagian tampilan, dipisahkan dari pengambilan data.
 *
 * Dua bagian: USULAN (dari pola tahun dasar) dan PENCOCOKAN (dengan kejadian nyata tahun
 * sasaran). Setiap slot membawa angkanya sendiri, dan setiap persen kemiripan dibaca
 * bersama definisinya — karena "mirip 73%" tanpa definisi tidak dapat dipertanggung-
 * jawabkan di depan penguji.
 */
export function PatrolPlanView({
  plan,
  evaluation,
  canDecide = false,
}: {
  plan: PatrolPlan;
  evaluation: PlanEvaluation | null;
  /** Pemegang `commander_decision:approve`; penolakan sesungguhnya tetap di backend. */
  canDecide?: boolean;
}) {
  const resultOf = new Map(
    (evaluation?.per_threat ?? []).map((row) => [row.threat_type, row] as const),
  );
  const totalSlots = plan.threats.reduce((sum, threat) => sum + threat.slots.length, 0);

  return (
    <div className="space-y-3">
      <StatusNotice status={plan.status} tone="caution">
        Usulan, bukan perintah. Aturan penyusunannya (versi <code>{plan.version}</code>) dan ukuran
        kemiripannya belum ditetapkan pemilik proyek.
      </StatusNotice>
      <Basis className="mt-0" label="Cara usulan disusun">
        {plan.plan_basis}
      </Basis>

      <Panel
        title={`Rencana Patroli ${plan.target_year}`}
        action={
          <span className="panel-action">
            pola {longDate(plan.basis_from)} – {longDate(plan.basis_to)}
            {plan.scope ? ` · ${plan.scope}` : ""}
          </span>
        }
      >
        {totalSlots === 0 ? (
          <EmptyState label="Tidak ada slot yang memenuhi batas minimum kejadian pada tahun dasar." />
        ) : (
          <div className="space-y-4">
            <p className="text-xs leading-relaxed text-ink-muted">
              Dari pola kejadian tahun dasar, untuk tiap jenis diusulkan paling banyak{" "}
              {plan.rules.max_slots_per_threat} slot (kelurahan × blok 3 jam) dengan
              sekurang-kurangnya {plan.rules.minimum_incidents} kejadian. Patroli pada slot itu
              menjangkau kejadian yang polanya berulang; slot di bawah batas minimum tidak diusulkan
              karena satu-dua kejadian setahun bukan pola.
            </p>
            <DecisionBanner decision={plan.decision ?? null} inForce={plan.in_force?.slots} />
            {canDecide ? (
              <PlanDecisionForm plan={plan} resultOf={resultOf} />
            ) : (
              plan.threats.map((threat) => (
                <ThreatSlots
                  key={threat.threat_type}
                  threat={threat}
                  result={resultOf.get(threat.threat_type)}
                />
              ))
            )}
          </div>
        )}
      </Panel>

      {evaluation ? <EvaluationPanel evaluation={evaluation} /> : null}
    </div>
  );
}

function DecisionBanner({
  decision,
  inForce,
}: {
  decision: PlanDecisionRow | null;
  inForce: number | undefined;
}) {
  if (decision === null) {
    return (
      <p className="rounded border border-base-800 bg-base-850 px-3 py-2 text-xs text-ink-muted">
        <span className="text-ink">Belum diputus.</span> Sampai Pimpinan memutuskan, usulan ini
        belum menjadi rencana yang berlaku.
      </p>
    );
  }
  return (
    <p className="rounded border border-accent/30 bg-accent/5 px-3 py-2 text-xs text-ink-muted">
      <span className="font-heading font-semibold text-accent">
        {PLAN_DECISION_LABELS[decision.decision]}
      </span>{" "}
      oleh <span className="text-ink">{decision.decided_by}</span> pada{" "}
      {new Date(decision.decided_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })} WIB (
      {decision.code}) — {inForce ?? decision.slots_in_force} dari {decision.proposed_slots} slot
      usulan berlaku.
      {decision.reason ? <> Pertimbangan: {decision.reason}</> : null}
    </p>
  );
}

export function ThreatSlots({
  threat,
  result,
  selectable = false,
}: {
  threat: ThreatPlan;
  result?: ThreatEvaluation;
  /** Menampilkan kotak centang "dipertahankan" per slot (formulir keputusan MODIFIED). */
  selectable?: boolean;
}) {
  const actualOf = new Map(
    (result?.slot_results ?? []).map(
      (row) => [`${row.kelurahan}|${row.block_start}`, row] as const,
    ),
  );
  return (
    <section aria-label={`Usulan ${threat.threat_type}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-heading text-sm font-semibold text-ink">{threat.threat_type}</h3>
        <span className="text-2xs text-ink-faint">
          {threat.basis_incidents} kejadian tahun dasar · {threat.basis_with_hour} berjam tercatat
          {threat.basis_unknown_time > 0 ? ` · ${threat.basis_unknown_time} tanpa jam` : ""}
          {threat.basis_unknown_kelurahan > 0
            ? ` · ${threat.basis_unknown_kelurahan} tanpa kelurahan`
            : ""}
        </span>
      </div>
      {threat.slots.length === 0 ? (
        <p className="mt-1 text-xs text-ink-muted">
          Tidak ada slot yang mencapai batas minimum: kejadian jenis ini terlalu tersebar untuk
          membentuk pola kelurahan × jam.
        </p>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-base-800">
                {selectable ? <th className="stat-label pb-1.5">Patroli</th> : null}
                <th className="stat-label pb-1.5">#</th>
                <th className="stat-label pb-1.5">Kelurahan</th>
                <th className="stat-label pb-1.5">Kecamatan</th>
                <th className="stat-label pb-1.5">Blok jam</th>
                <th className="stat-label pb-1.5 text-right">Kejadian tahun dasar</th>
                <th className="stat-label pb-1.5 text-right">Porsi</th>
                {result ? <th className="stat-label pb-1.5 text-right">Nyata</th> : null}
              </tr>
            </thead>
            <tbody>
              {threat.slots.map((slot) => {
                const actual = actualOf.get(`${slot.kelurahan}|${slot.block_start}`);
                return (
                  <tr
                    key={`${slot.kelurahan}-${slot.block_start}`}
                    className="border-b border-base-800/60 last:border-0"
                    title={slot.why}
                  >
                    {selectable ? (
                      <td className="py-1.5">
                        <input
                          type="checkbox"
                          name="kept"
                          value={slotKeyOf(slot)}
                          defaultChecked
                          aria-label={`Pertahankan ${slot.kelurahan} ${slot.block_label}`}
                        />
                      </td>
                    ) : null}
                    <td className="py-1.5 font-mono text-ink-muted">{slot.rank}</td>
                    <td className="py-1.5 text-ink">{slot.kelurahan}</td>
                    <td className="py-1.5 text-ink-muted">{slot.kecamatan}</td>
                    <td className="py-1.5 font-mono text-ink">{slot.block_label}</td>
                    <td className="py-1.5 text-right font-mono text-ink">{slot.incidents}</td>
                    <td className="py-1.5 text-right font-mono text-ink-muted">
                      {percentText(slot.share_percent)}
                    </td>
                    {result ? (
                      <td className="py-1.5 text-right font-mono">
                        {actual ? (
                          <span className={actual.hit ? "text-accent" : "text-ink-faint"}>
                            {actual.actual_incidents}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-1.5 text-2xs text-ink-faint">
            Ke-{threat.slots.length} slot ini bersama-sama memuat{" "}
            {percentText(threat.covered_share_percent)} kejadian {threat.threat_type} tahun dasar
            yang jamnya tercatat.
          </p>
        </div>
      )}
    </section>
  );
}

function EvaluationPanel({ evaluation }: { evaluation: PlanEvaluation }) {
  const { overall } = evaluation;
  return (
    <Panel
      title={`Pencocokan dengan Kejadian Nyata ${evaluation.target_year}`}
      action={
        <span className="panel-action">
          data {longDate(evaluation.target_observed_from)} –{" "}
          {longDate(evaluation.target_observed_to)}
        </span>
      }
    >
      <div className="space-y-3">
        <StatusNotice status={evaluation.status} tone="caution">
          Ukuran kemiripan berstatus usulan sampai ditetapkan pemilik proyek.
        </StatusNotice>
        <Basis className="mt-0" label="Cara kemiripan dihitung">
          {evaluation.similarity_basis} {evaluation.partial_year_basis}
        </Basis>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <Metric
            label="Kemiripan pola jam"
            value={percentText(overall.hour_similarity_percent)}
            hint="Sebaran blok jam tahun dasar dibandingkan tahun sasaran"
          />
          <Metric
            label="Kemiripan pola wilayah"
            value={percentText(overall.area_similarity_percent)}
            hint="Sebaran kelurahan tahun dasar dibandingkan tahun sasaran"
          />
          <Metric
            label="Ketepatan slot"
            value={percentText(overall.slot_hit_rate_percent)}
            hint={`${overall.slots_hit} dari ${overall.slots} slot usulan mengalami kejadian jenis itu`}
          />
          <Metric
            label="Cakupan kejadian"
            value={percentText(overall.coverage_percent)}
            hint={`${overall.covered_incidents} dari ${overall.actual_evaluable} kejadian berjam-berkelurahan jatuh di slot usulan`}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-base-800">
                <th className="stat-label pb-1.5">Jenis</th>
                <th className="stat-label pb-1.5 text-right">Pola jam</th>
                <th className="stat-label pb-1.5 text-right">Pola wilayah</th>
                <th className="stat-label pb-1.5 text-right">Ketepatan slot</th>
                <th className="stat-label pb-1.5 text-right">Cakupan</th>
                <th className="stat-label pb-1.5 text-right">Kejadian nyata</th>
                <th className="stat-label pb-1.5 text-right">Tanpa jam</th>
              </tr>
            </thead>
            <tbody>
              {evaluation.per_threat.map((row) => (
                <tr key={row.threat_type} className="border-b border-base-800/60 last:border-0">
                  <td className="py-1.5 font-heading font-semibold text-ink">{row.threat_type}</td>
                  <td className="py-1.5 text-right font-mono text-ink">
                    {percentText(row.hour_similarity_percent)}
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink">
                    {percentText(row.area_similarity_percent)}
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink">
                    {percentText(row.slot_hit_rate_percent)}
                    <span className="text-ink-faint">
                      {" "}
                      ({row.slots_hit}/{row.slots})
                    </span>
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink">
                    {percentText(row.coverage_percent)}
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink">{row.actual_incidents}</td>
                  <td className="py-1.5 text-right font-mono text-ink-muted">
                    {row.actual_unknown_time}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details>
          <summary className="cursor-pointer text-2xs uppercase tracking-wider text-ink-muted hover:text-accent">
            Sebaran blok jam: tahun dasar vs tahun sasaran, per jenis
          </summary>
          <div className="mt-2 grid gap-3 md:grid-cols-3">
            {evaluation.per_threat.map((row) => (
              <div key={row.threat_type}>
                <div className="stat-label mb-1">{row.threat_type}</div>
                <ul className="space-y-0.5">
                  {row.hour_profile.map((block) => (
                    <li
                      key={block.block_start}
                      className="flex justify-between gap-2 text-2xs text-ink-muted"
                    >
                      <span className="font-mono">{block.block_label}</span>
                      <span className="font-mono text-ink">
                        {block.basis_incidents} → {block.actual_incidents}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </details>
      </div>
    </Panel>
  );
}
