import type { ReactNode } from "react";
import {
  actionSentence,
  type DailyBrief,
  decisionSentence,
  effectiveInstruction,
  formatBriefDate,
  riskLabel,
  situationSentence,
  threatSentence,
} from "@/lib/brief";
import { formatPercent, formatRatio } from "@/lib/evaluation";
import { RISK_TEXT, type RiskClass } from "@/lib/risk";
import { formatWib, SEVERITY_LABELS } from "@/lib/warnings";

/**
 * Gaya cetak.
 *
 * Pimpinan mencetak brief ini, sehingga halaman harus tetap utuh di atas kertas. Yang
 * dilakukan: menonaktifkan shell aplikasi (topbar, sidebar, dan pembungkus `h-screen`
 * yang memotong isi menjadi satu layar), lalu menjadikan seluruh dokumen hitam di atas
 * putih.
 *
 * Ditempatkan di dalam komponen halaman, bukan di `globals.css`, karena hanya berlaku
 * untuk layar ini — dan karena elemennya ikut hilang ketika pengguna berpindah halaman.
 *
 * Warna kelas risiko sengaja dibuang saat mencetak. Tidak ada keterangan yang hilang:
 * kelas risiko **selalu** ditulis sebagai kata ("Kritis", "Tinggi"), bukan hanya sebagai
 * warna — hal yang sama juga menolong pembaca yang tidak dapat membedakan warna.
 */
const PRINT_CSS = `
@media print {
  @page { margin: 16mm; }
  html, body { height: auto !important; overflow: visible !important; }
  body {
    background: #fff !important;
    background-image: none !important;
    color: #111 !important;
  }
  body > div { display: block !important; height: auto !important; overflow: visible !important; }
  body > div > header { display: none !important; }
  body > div > div { display: block !important; }
  body > div > div > nav { display: none !important; }
  body > div > div > main { overflow: visible !important; padding: 0 !important; }
  .brief-doc {
    max-width: none !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
  }
  .brief-doc, .brief-doc * {
    color: #111 !important;
    background: transparent !important;
    box-shadow: none !important;
    border-color: #b8bfc9 !important;
  }
  .brief-doc section { break-inside: avoid; page-break-inside: avoid; }
  .brief-hide-print { display: none !important; }
}
`;

/** Satu bagian brief: judul bernomor, kalimat pembuka, isi, lalu dasar perhitungannya. */
function Section({
  number,
  title,
  lead,
  children,
  bases,
}: {
  number: number;
  title: string;
  lead: string | null;
  children?: ReactNode;
  /** Teks `*_basis` dari API. Angka tidak pernah tampil tanpa asal-usulnya. */
  bases: string[];
}) {
  return (
    <section className="border-t border-base-800 pt-5">
      <h2 className="font-heading text-sm font-bold uppercase tracking-[0.14em] text-accent">
        {number}. {title}
      </h2>
      {lead ? <p className="mt-2 text-base leading-relaxed text-ink">{lead}</p> : null}
      {children ? <div className="mt-3">{children}</div> : null}
      <div className="mt-3 space-y-1">
        {bases.map((basis) => (
          <p key={basis} className="text-2xs leading-relaxed text-ink-faint">
            Dasar: {basis}
          </p>
        ))}
      </div>
    </section>
  );
}

/** Baris angka: label di kiri, nilai di kanan. Angka pada kalimat selalu diulang di sini. */
function Figure({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 border-b border-base-800/60 py-1.5 last:border-0">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="text-right">
        <span className="font-heading text-base font-semibold text-ink">{value}</span>
        {note ? <span className="ml-2 text-xs text-ink-muted">{note}</span> : null}
      </dd>
    </div>
  );
}

/** Keterangan bagian yang tidak dapat diisi — dinyatakan dengan kata, bukan angka nol. */
function Unavailable({ reason }: { reason: string }) {
  return <p className="text-sm italic leading-relaxed text-ink-muted">{reason}</p>;
}

function RiskWord({ riskClass }: { riskClass: string }) {
  return (
    <span className={RISK_TEXT[riskClass as RiskClass] ?? "text-ink"}>{riskLabel(riskClass)}</span>
  );
}

/**
 * Executive Brief harian (modul MVP #14) — bagian tampilan.
 *
 * Dipisahkan dari pengambilan data supaya dapat diuji tanpa backend.
 *
 * Ini **dokumen**, bukan dasbor kedua: satu kolom, dibaca dari atas ke bawah, dan dapat
 * dibacakan apa adanya. Kalimat pembuka tiap bagian disusun template pada `@/lib/brief`
 * — tidak ada model bahasa di sistem ini — dan setiap angka di dalam kalimat itu diulang
 * sebagai angka pada daftar di bawahnya, sehingga kekeliruan penyusunan kalimat terlihat
 * (CLAUDE.md §27).
 */
export function BriefDocument({ brief }: { brief: DailyBrief }) {
  const accuracy = brief.accuracy;

  return (
    <article className="brief-doc panel mx-auto max-w-3xl px-6 py-6 md:px-10 md:py-8">
      <style>{PRINT_CSS}</style>

      <div className="border-b-2 border-ink/20 pb-5">
        <p className="font-heading text-2xs font-semibold uppercase tracking-[0.22em] text-accent">
          Executive Brief — Prediksi Presisi
        </p>
        <h1 className="mt-2 font-heading text-2xl font-bold leading-tight text-ink md:text-3xl">
          Ringkasan Situasi Kamtibmas
        </h1>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-xs md:grid-cols-4">
          <div>
            <dt className="stat-label">Tanggal</dt>
            <dd className="mt-0.5 font-heading font-semibold text-ink">
              {formatBriefDate(brief.brief_date)}
            </dd>
          </div>
          <div>
            <dt className="stat-label">Pukul</dt>
            <dd className="mt-0.5 font-heading font-semibold text-ink">{brief.brief_time} WIB</dd>
          </div>
          <div>
            <dt className="stat-label">Cakupan</dt>
            <dd className="mt-0.5 font-heading font-semibold text-ink">
              {brief.scope_polsek ?? "Seluruh wilayah Polres"}
            </dd>
          </div>
          <div>
            <dt className="stat-label">Penilaian Risiko</dt>
            <dd className="mt-0.5 font-heading font-semibold text-ink">
              {brief.assessment_date ? formatBriefDate(brief.assessment_date) : "—"}
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-relaxed text-ink-muted">{brief.scope_basis}</p>
        {brief.demo_clock ? (
          <p className="mt-2 rounded border border-accent/25 bg-accent/5 px-3 py-2 text-xs leading-relaxed text-accent-soft">
            <span className="badge mr-2 bg-accent/15 text-accent">Waktu Acuan</span>
            {brief.clock_basis}
          </p>
        ) : null}
      </div>

      <div className="mt-5 space-y-5">
        <Section
          number={1}
          title="Situasi Terakhir"
          lead={situationSentence(brief)}
          bases={[brief.incidents_basis, brief.warnings_basis, brief.top_area_basis]}
        >
          <dl>
            <Figure
              label={`Kejadian tercatat (${brief.window_hours} jam terakhir)`}
              value={brief.incidents_recent ?? "—"}
            />
            <Figure label="Peringatan dini aktif" value={brief.active_warnings ?? "—"} />
            {brief.warnings_by_severity.map((row) => (
              <Figure
                key={row.severity}
                label={`— tingkat ${SEVERITY_LABELS[row.severity] ?? row.severity}`}
                value={row.count}
                note={row.severity}
              />
            ))}
            {brief.top_area ? (
              <Figure
                label={`Wilayah paling berisiko — ${brief.top_area.kecamatan}`}
                value={brief.top_area.risk_score}
                note={`${riskLabel(brief.top_area.risk_class)} · ${brief.top_area.threat_type}${
                  brief.top_area.time_window ? ` · ${brief.top_area.time_window}` : ""
                }`}
              />
            ) : null}
          </dl>
          {brief.incidents_recent === null || brief.active_warnings === null ? (
            <div className="mt-3">
              <Unavailable reason="Sebagian angka pada bagian ini tidak disertakan — lihat dasar di bawah." />
            </div>
          ) : null}
        </Section>

        <Section
          number={2}
          title="Ancaman Menonjol dan Jam Rawannya"
          lead={threatSentence(brief)}
          bases={[brief.top_threats_basis]}
        >
          {brief.top_threats.length === 0 ? (
            <Unavailable reason="Tidak ada jenis ancaman yang dapat dirangkum untuk cakupan ini." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-base-800">
                    <th className="stat-label pb-1.5">Jenis Ancaman</th>
                    <th className="stat-label pb-1.5">Wilayah</th>
                    <th className="stat-label pb-1.5">Jam Rawan</th>
                    <th className="stat-label pb-1.5 text-right">Skor</th>
                    <th className="stat-label pb-1.5 text-right">Kelas</th>
                  </tr>
                </thead>
                <tbody>
                  {brief.top_threats.map((row) => (
                    <tr key={row.threat_type} className="border-b border-base-800/60 last:border-0">
                      <td className="py-1.5 font-heading font-semibold text-ink">
                        {row.threat_type}
                      </td>
                      <td className="py-1.5 text-ink">{row.kecamatan}</td>
                      <td className="py-1.5 font-mono text-ink">{row.time_window ?? "—"}</td>
                      <td className="py-1.5 text-right font-heading font-semibold text-ink">
                        {row.risk_score}
                      </td>
                      <td className="py-1.5 text-right font-semibold">
                        <RiskWord riskClass={row.risk_class} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section
          number={3}
          title="Menunggu Keputusan Pimpinan"
          lead={decisionSentence(brief)}
          bases={[brief.pending_recommendations_basis]}
        >
          {brief.pending_recommendations === null ? (
            <Unavailable reason="Bagian ini tidak disertakan untuk akun ini." />
          ) : (
            <dl>
              <Figure
                label="Rekomendasi menunggu keputusan"
                value={brief.pending_recommendations}
              />
              {brief.pending_by_function.map((row) => (
                <Figure
                  key={row.recommended_function}
                  label={`— fungsi ${row.recommended_function}`}
                  value={row.count}
                />
              ))}
            </dl>
          )}
        </Section>

        <Section
          number={4}
          title="Menunggu Tindakan Lapangan"
          lead={actionSentence(brief)}
          bases={[brief.pending_actions_basis]}
        >
          {brief.pending_actions === null ? (
            <Unavailable reason="Bagian ini tidak disertakan untuk akun ini." />
          ) : (
            <ol className="space-y-2.5">
              {brief.pending_action_items.map((item) => (
                <li
                  key={item.decision_code}
                  className="border-l-2 border-base-700 pl-3 text-xs leading-relaxed"
                >
                  <p className="font-heading font-semibold text-ink">
                    {item.recommended_function} · {item.kecamatan}
                    {item.priority ? ` · prioritas ${item.priority}` : ""}
                  </p>
                  <p className="mt-0.5 text-ink">{effectiveInstruction(item)}</p>
                  <p className="mt-0.5 text-2xs text-ink-faint">
                    {item.decision_code} ({item.decision}) atas {item.recommendation_code} — diputus{" "}
                    {formatWib(item.decided_at)}
                    {item.modified_text ? " · isi perintah adalah hasil modifikasi pimpinan" : ""}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </Section>

        <Section
          number={5}
          title="Ketepatan Model Sejauh Ini"
          lead={
            accuracy
              ? `Dari ${accuracy.evaluated_rows} baris yang dievaluasi, ${accuracy.hits} prediksi terbukti terjadi.`
              : null
          }
          bases={[brief.accuracy_basis]}
        >
          {accuracy === null ? (
            <Unavailable reason="Bagian ini tidak disertakan untuk akun ini." />
          ) : (
            <>
              <p className="mb-3 rounded border border-risk-high/40 bg-risk-high/10 px-3 py-2 text-xs leading-relaxed text-risk-high">
                <span className="badge mr-2 bg-risk-high/20 text-risk-high">{accuracy.status}</span>
                Angka ini <strong>belum final</strong> dan tidak boleh dibacakan sebagai capaian
                resmi.
              </p>
              <dl>
                <Figure
                  label="Precision — prediksi terbit yang terbukti"
                  value={formatRatio(accuracy.precision)}
                  note={formatPercent(accuracy.precision) ?? undefined}
                />
                <Figure
                  label="Recall — kejadian nyata yang sempat diprediksi"
                  value={formatRatio(accuracy.recall)}
                  note={formatPercent(accuracy.recall) ?? undefined}
                />
                <Figure label="Terbukti" value={accuracy.hits} />
                <Figure
                  label="Positif palsu — diprediksi, tidak terjadi"
                  value={accuracy.false_positives}
                />
                <Figure
                  label="Negatif palsu — terjadi, tidak diprediksi"
                  value={accuracy.false_negatives}
                />
              </dl>
            </>
          )}
        </Section>

        <section className="border-t border-base-800 pt-5">
          <h2 className="font-heading text-sm font-bold uppercase tracking-[0.14em] text-ink-muted">
            Catatan Penyusunan
          </h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-ink-muted">
            <li>
              Seluruh angka berasal dari basis data dan dihitung ulang setiap halaman ini dibuka.
              Kalimat pembuka tiap bagian disusun dari template tetap atas angka yang sama —{" "}
              <strong>tidak ada model bahasa</strong> yang menyusun brief ini.
            </li>
            <li>
              Kelas risiko dan tingkat peringatan dibaca apa adanya dari data, tidak dihitung ulang
              dari skor. Ambangnya masih berstatus DEMO / PROPOSED dan belum ditetapkan.
            </li>
            <li>
              Rekomendasi adalah usulan, bukan perintah. Tidak ada tindakan operasional yang lahir
              tanpa keputusan pejabat yang berwenang.
            </li>
          </ul>
          <p className="brief-hide-print mt-4 text-xs text-ink-faint">
            Tekan Ctrl+P (atau Cmd+P) untuk mencetak brief ini.
          </p>
        </section>
      </div>
    </article>
  );
}
