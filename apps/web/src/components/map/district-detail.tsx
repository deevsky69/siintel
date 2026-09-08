import type {
  AreaDetail,
  AreaPrediction,
  AreaWarning,
  MapDistrict,
  PredictiveArea,
} from "@/lib/map-data";
import { RISK_BG, RISK_LABELS, RISK_TEXT } from "@/lib/risk";
import { SEVERITY_LABELS, severityRiskClass } from "@/lib/warnings";
import { toRiskClass } from "./area";
import { factorLabel, SOURCE_NOTE } from "./factors";

/**
 * Panel rincian satu kecamatan — isi `GET /map/area/{kecamatan}`.
 *
 * Panel menjawab pertanyaan "wilayah ini potensi ancamannya apa saja": jenis ancaman dan
 * kelasnya, jendela waktu paling rawan, riwayat kejadian yang menjadi dasarnya, peringatan
 * yang masih menunggu tindakan, dan prediksi terdekat beserta WHY-nya.
 *
 * Tiga aturan yang mengikat bentuk panel ini:
 *
 * - **Kelas risiko tidak pernah dihitung di layar.** Kelas selalu diambil dari respons;
 *   nilai yang tidak dikenal ditampilkan tanpa kelas, bukan diberi kelas cadangan (§12).
 * - **Prediksi tidak diberi kelas.** API tidak mengirim `risk_class` untuk prediksi karena
 *   ambangnya masih DEMO / PROPOSED (U-01), jadi skor prediksi tampil sebagai angka.
 * - **`dominant_factors` selalu tampil lengkap dengan asalnya** (`RULE`/`MODEL`).
 *   Menyembunyikan asal akan menyajikan hasil aturan seolah temuan model (§27).
 */

const HORIZON_LABEL: Record<string, string> = {
  "6H": "+6 jam",
  "12H": "+12 jam",
  "24H": "+24 jam",
  "3D": "+3 hari",
  "7D": "+7 hari",
};

const STATUS_LABEL: Record<string, string> = {
  PUBLISHED: "Dipublikasikan",
  VALIDATED: "Tervalidasi",
  DRAFT: "Draf",
};

export function horizonLabel(horizon: string): string {
  return HORIZON_LABEL[horizon] ?? horizon;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="stat-label mb-2">{children}</h3>;
}

/** Keterangan asal angka dari backend — diteruskan apa adanya, tidak diringkas ulang. */
function Basis({ children }: { children: React.ReactNode }) {
  return <p className="mt-2 text-2xs leading-relaxed text-ink-faint">{children}</p>;
}

/**
 * Baris skor dengan batang risiko.
 *
 * `riskClass` datang dari backend. Bila kosong atau tidak dikenal, batang digambar netral
 * dan kolom kelas menyatakan "tanpa kelas" — bukan kelas turunan dari skor.
 */
function ScoreRow({
  label,
  score,
  riskClass,
  note,
}: {
  label: string;
  score: number;
  riskClass: string | null;
  note?: string;
}) {
  const risk = toRiskClass(riskClass);
  return (
    <li className="flex items-center gap-2.5">
      <span className="w-28 shrink-0 truncate text-xs text-ink" title={label}>
        {label}
      </span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
        <span
          className={`block h-full rounded-full ${risk ? RISK_BG[risk] : "bg-accent"}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </span>
      {note ? <span className="shrink-0 text-2xs text-ink-faint">{note}</span> : null}
      <span
        className={`w-7 text-right font-mono text-xs font-semibold ${risk ? RISK_TEXT[risk] : "text-ink"}`}
      >
        {score}
      </span>
      <span className="w-11 text-right text-2xs uppercase text-ink-muted">
        {risk ? RISK_LABELS[risk] : "tanpa kelas"}
      </span>
    </li>
  );
}

/** Batang perbandingan tanpa warna risiko — dipakai untuk cacah kejadian historis. */
function CountRow({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <li className="flex items-center gap-2.5">
      <span className="w-28 shrink-0 truncate text-xs text-ink" title={label}>
        {label}
      </span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
        <span
          className="block h-full rounded-full bg-accent-deep"
          style={{ width: `${max > 0 ? Math.round((value / max) * 100) : 0}%` }}
        />
      </span>
      <span className="w-10 text-right font-mono text-xs font-semibold text-ink">{value}</span>
    </li>
  );
}

/** Ringkasan layer prediktif untuk wilayah ini — sengaja tanpa kelas risiko. */
function PredictiveSummary({ area, horizon }: { area: PredictiveArea; horizon: string }) {
  return (
    <div className="rounded border border-accent/25 bg-accent/5 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-heading text-sm font-semibold text-ink">{area.threat_type}</p>
          <p className="truncate text-xs text-ink-muted">
            {area.time_window ?? "jendela tidak tercatat"} · {area.cell_count} sel ·{" "}
            {area.prediction_code}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <span className="font-heading text-xl font-bold leading-none text-accent">
            {area.risk_score}
          </span>
          <span className="ml-1 text-2xs text-ink-faint">/100</span>
          <p className="text-2xs uppercase text-ink-faint">tanpa kelas</p>
        </div>
      </div>
      <p className="mt-1.5 font-mono text-2xs text-ink-faint">
        Horizon {horizonLabel(horizon)} · confidence{" "}
        {area.confidence === null ? "tidak ada" : `${area.confidence}%`} ·{" "}
        {area.model_version ?? "versi model tidak tercatat"}
      </p>
    </div>
  );
}

function WarningCard({ warning }: { warning: AreaWarning }) {
  const risk = severityRiskClass(warning.severity);

  return (
    <li className="rounded border border-base-800 bg-base-850 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="flex items-center gap-2">
            <span className={`badge bg-base-800 ${RISK_TEXT[risk]}`}>
              {SEVERITY_LABELS[warning.severity] ?? warning.severity}
            </span>
            <span className="truncate font-heading text-sm font-semibold text-ink">
              {warning.threat_type}
            </span>
          </p>
          <p className="mt-1 truncate text-xs text-ink-muted">
            {warning.time_window ?? "jendela tidak tercatat"}
            {warning.grid_id ? ` · ${warning.grid_id}` : ""}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <span className={`font-heading text-lg font-bold leading-none ${RISK_TEXT[risk]}`}>
            {warning.risk_score}
          </span>
          <span className="ml-1 text-2xs text-ink-faint">/100</span>
          <p className="text-2xs text-ink-faint">
            {warning.confidence === null ? "confidence —" : `confidence ${warning.confidence}%`}
          </p>
        </div>
      </div>
      <p className="mt-1.5 font-mono text-2xs text-ink-faint">
        {warning.code} · dari {warning.prediction_code} · ambang{" "}
        {warning.threshold_version ?? "tidak tercatat"}
      </p>
    </li>
  );
}

function PredictionCard({ prediction }: { prediction: AreaPrediction }) {
  return (
    <li className="rounded border border-base-800 bg-base-850 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          {/* WHAT */}
          <p className="truncate font-heading text-sm font-semibold text-ink">
            {prediction.threat_type}
          </p>
          {/* WHERE */}
          <p className="truncate text-xs text-ink-muted">
            {prediction.kelurahan ? `${prediction.kelurahan} · ` : ""}
            {prediction.grid_id}
          </p>
        </div>
        <div className="shrink-0 text-right">
          {/* RISK — tanpa kelas: API tidak mengirim kelas untuk prediksi (U-01). */}
          <span className="font-heading text-xl font-bold leading-none text-accent">
            {prediction.risk_score}
          </span>
          <span className="ml-1 text-2xs text-ink-faint">/100</span>
          <p className="text-2xs uppercase text-ink-faint">tanpa kelas</p>
        </div>
      </div>

      <dl className="mt-2 grid grid-cols-4 gap-2 text-xs">
        <div>
          {/* WHEN */}
          <dt className="text-ink-faint">Jendela</dt>
          <dd className="font-mono text-ink">{prediction.time_window ?? "tidak ada"}</dd>
        </div>
        <div>
          <dt className="text-ink-faint">Horizon</dt>
          <dd className="font-mono text-ink">{horizonLabel(prediction.forecast_horizon)}</dd>
        </div>
        <div>
          {/* CONFIDENCE */}
          <dt className="text-ink-faint">Confidence</dt>
          <dd className="font-mono text-ink">
            {prediction.confidence === null ? "tidak ada" : `${prediction.confidence}%`}
          </dd>
        </div>
        <div>
          <dt className="text-ink-faint">Status</dt>
          <dd className="text-ink">{STATUS_LABEL[prediction.status] ?? prediction.status}</dd>
        </div>
      </dl>

      {/* WHY */}
      <div className="mt-2.5 border-t border-base-800 pt-2">
        <p className="stat-label mb-1.5">Why</p>
        {prediction.dominant_factors.length === 0 ? (
          <p className="text-xs text-ink-muted">Tidak ada faktor dominan yang tercatat.</p>
        ) : (
          <ul className="space-y-1.5">
            {prediction.dominant_factors.map((factor) => (
              <li key={factor.factor} className="flex items-center gap-2">
                <span className="badge bg-base-800 text-accent-soft">{factor.source}</span>
                <span className="min-w-0 flex-1 truncate text-xs text-ink">
                  {factorLabel(factor.factor)}
                </span>
                <span className="h-1 w-14 shrink-0 overflow-hidden rounded-full bg-base-800">
                  <span
                    className="block h-full rounded-full bg-accent"
                    style={{ width: `${Math.min(100, Math.max(0, factor.contribution * 100))}%` }}
                  />
                </span>
                <span className="w-9 shrink-0 text-right font-mono text-xs text-ink-muted">
                  {Math.round(factor.contribution * 100)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="mt-2 font-mono text-2xs text-ink-faint">
        {prediction.code} · {formatDate(prediction.prediction_date)} ·{" "}
        {prediction.model_version ?? "versi model tidak tercatat"}
      </p>
    </li>
  );
}

/**
 * Panel ini berganti isi setiap kali wilayah lain dipilih pada peta, sehingga diberi
 * nama sendiri: pengguna papan ketik/pembaca layar dapat melompat langsung ke sini
 * tanpa harus menelusuri seluruh peta. Namanya sengaja berbeda dari judul panel
 * pembungkusnya agar keduanya tidak tertukar.
 */
const REGION = { role: "region", "aria-label": "Rincian wilayah terpilih" } as const;

export function DistrictDetail({
  district,
  detail,
  horizon,
}: {
  /** Baris wilayah pada kedua layer peta; `null` bila belum ada yang dipilih. */
  district: MapDistrict | null;
  /** Isi `/map/area/{kecamatan}`; `null` bila API menjawab 404 (tidak ada / di luar cakupan). */
  detail: AreaDetail | null;
  horizon: string;
}) {
  if (district === null) {
    return (
      <div {...REGION}>
        <p className="text-sm text-ink-muted">
          Pilih salah satu kecamatan pada peta untuk melihat potensi ancamannya.
        </p>
      </div>
    );
  }

  if (detail === null) {
    // Backend menjawab 404 untuk kecamatan yang tidak ada **dan** untuk kecamatan di luar
    // kewenangan pengguna. Antarmuka tidak menebak mana yang berlaku (CLAUDE.md §15, §24).
    return (
      <div className="space-y-2" {...REGION}>
        <h2 className="font-heading text-base font-bold text-ink">{district.kecamatan}</h2>
        <p className="text-sm text-ink-muted">
          Tidak ada rincian wilayah ini yang dapat ditampilkan untuk kewenangan Anda.
        </p>
      </div>
    );
  }

  const headline = district.current;
  const headlineRisk = toRiskClass(headline?.risk_class ?? null);
  const history = detail.history;
  const maxIncidents = history.by_threat_type.reduce(
    (best, row) => Math.max(best, row.incidents),
    0,
  );

  return (
    <div className="space-y-4" {...REGION}>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate font-heading text-base font-bold text-ink">{detail.kecamatan}</h2>
          <p className="text-xs text-ink-muted">
            {detail.polsek ?? "Polsek tidak tercatat"} · {detail.grid_count} grid
          </p>
          <p className="text-xs text-ink-muted">
            {detail.assessment_date
              ? `Penilaian ${formatDate(detail.assessment_date)}`
              : "Belum ada tanggal penilaian"}
          </p>
        </div>
        <div className="shrink-0 text-right">
          {headline === null ? (
            <span className="text-sm text-ink-muted">tidak ada data</span>
          ) : (
            <>
              <span
                className={`font-heading text-3xl font-bold leading-none ${
                  headlineRisk ? RISK_TEXT[headlineRisk] : "text-ink"
                }`}
              >
                {headline.risk_score}
              </span>
              <span className="ml-1 text-xs text-ink-faint">/100</span>
              <p
                className={`text-xs font-semibold uppercase ${
                  headlineRisk ? RISK_TEXT[headlineRisk] : "text-ink-muted"
                }`}
              >
                {headlineRisk ? RISK_LABELS[headlineRisk] : "tanpa kelas"}
              </p>
              <p className="text-2xs text-ink-faint">rata-rata {headline.average_risk_score}</p>
            </>
          )}
        </div>
      </header>

      <section>
        <SectionTitle>Potensi Ancaman</SectionTitle>
        {detail.threats.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada penilaian risiko untuk wilayah ini pada tanggal penilaian terakhir.
          </p>
        ) : (
          <>
            <ul className="space-y-2">
              {detail.threats.map((threat) => (
                <ScoreRow
                  key={threat.threat_type}
                  label={threat.threat_type}
                  score={threat.risk_score}
                  riskClass={threat.risk_class}
                  note={threat.time_window ?? undefined}
                />
              ))}
            </ul>
            <Basis>{detail.aggregation_basis}</Basis>
          </>
        )}
      </section>

      <section>
        <SectionTitle>Jendela Waktu Paling Rawan</SectionTitle>
        {detail.time_windows.length === 0 ? (
          <p className="text-sm text-ink-muted">Tidak ada data jendela waktu untuk wilayah ini.</p>
        ) : (
          <>
            <p className="mb-2 font-heading text-lg font-bold text-ink">
              {detail.critical_time_window ?? "tidak tercatat"}
            </p>
            <ul className="space-y-2">
              {detail.time_windows.map((window) => (
                <ScoreRow
                  key={window.time_window ?? "tanpa-jendela"}
                  label={window.time_window ?? "tanpa jendela"}
                  score={window.risk_score}
                  riskClass={window.risk_class}
                />
              ))}
            </ul>
            <Basis>{detail.time_window_basis}</Basis>
          </>
        )}
      </section>

      <section>
        <SectionTitle>Riwayat Kejadian</SectionTitle>
        {history.total_incidents === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada kejadian tercatat untuk wilayah ini pada data yang dapat Anda akses.
          </p>
        ) : (
          <>
            <p className="mb-2 text-sm text-ink">
              <span className="font-heading text-2xl font-bold">{history.total_incidents}</span>{" "}
              kejadian ·{" "}
              <span className="font-mono text-xs text-ink-muted">
                {formatDate(history.date_from)} – {formatDate(history.date_to)}
              </span>
            </p>
            <ul className="space-y-2">
              {history.by_threat_type.map((row) => (
                <CountRow
                  key={row.threat_type}
                  label={row.threat_type}
                  value={row.incidents}
                  max={maxIncidents}
                />
              ))}
            </ul>
          </>
        )}
      </section>

      <section>
        <SectionTitle>Peringatan Aktif</SectionTitle>
        {detail.active_warnings.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada peringatan aktif yang menunggu tindakan di wilayah ini.
          </p>
        ) : (
          <ul className="space-y-2">
            {detail.active_warnings.map((warning) => (
              <WarningCard key={warning.code} warning={warning} />
            ))}
          </ul>
        )}
        <Basis>{detail.active_warnings_basis}</Basis>
      </section>

      <section>
        <SectionTitle>Prediksi {horizonLabel(horizon)}</SectionTitle>
        {district.predictive === null ? (
          <p className="text-sm text-ink-muted">
            Tidak ada prediksi terpublikasi untuk wilayah ini pada horizon {horizonLabel(horizon)}.
          </p>
        ) : (
          <PredictiveSummary area={district.predictive} horizon={horizon} />
        )}
      </section>

      <section>
        <SectionTitle>Prediksi Teratas Wilayah Ini</SectionTitle>
        {detail.top_predictions.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada prediksi terpublikasi untuk wilayah ini.
          </p>
        ) : (
          <>
            <ul className="space-y-2">
              {detail.top_predictions.map((prediction) => (
                <PredictionCard key={prediction.code} prediction={prediction} />
              ))}
            </ul>
            <Basis>{SOURCE_NOTE}</Basis>
          </>
        )}
      </section>
    </div>
  );
}
