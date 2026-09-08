import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import type { MapLevel } from "@/components/map/area";
import { RiskLegend } from "@/components/map/legend";
import { MapCanvas } from "@/components/map/map-canvas";
import { Panel } from "@/components/panel";
import type { AreaDetail, MapData } from "@/lib/map-data";
import type { CitizenRow, CrimeRow } from "@/lib/reports";
import { RISK_LABELS, RISK_TEXT, riskClassOf } from "@/lib/risk";
import { HOME_AREA } from "@/lib/wilayah";

/**
 * Peta sebagai isi utama beranda, beserta panel rincian yang terisi saat wilayah diklik.
 *
 * ## Hover dan klik memikul beban yang berbeda
 *
 * Susunannya mengikuti cara aplikasi pemantauan lain membagi keduanya — Grafana Geomap,
 * ArcGIS Dashboards, Datadog, ESRI Operations Dashboard:
 *
 * | | Isinya | Ukuran |
 * |---|---|---|
 * | **Hover** | identitas, angka utama, status, satu pembanding | 3–5 baris, tanpa tautan |
 * | **Klik** | ancaman berperingkat, jam rawan, riwayat, peringatan aktif, prediksi | panel penuh |
 *
 * Hover menjawab satu pertanyaan saja: **apakah ini perlu saya buka?** Menaruh lebih
 * banyak di sana membuat kotak yang menutupi peta yang sedang dibaca, dan tooltip yang
 * mengikuti kursor tidak dapat memuat apa pun yang harus diklik — ia hilang begitu kursor
 * bergeser ke arahnya.
 *
 * ## Wilayah terpilih hidup di alamat, bukan di komponen
 *
 * Klik mengubah `?wilayah=` pada beranda, bukan menyimpan keadaan di peramban. Dengan
 * begitu rinciannya diambil di server, tampilan yang sedang dibicarakan dapat dibagikan
 * sebagai tautan saat paparan, dan tombol mundur peramban bekerja seperti yang diharapkan.
 */
export function MapHero({
  data,
  selected,
  detail,
  crimes,
  reports,
  level,
}: {
  data: MapData;
  selected: string | null;
  detail: AreaDetail | null;
  /**
   * Beranda membuka pada tingkat wilayah hukum Polda Metro Jaya, bukan langsung pada
   * kecamatan. Alasannya bukan hiasan: pimpinan membaca posisi satuannya **di antara**
   * satuan lain, dan peta yang langsung menampilkan sembilan poligon tanpa konteks tidak
   * pernah menjawab pertanyaan itu.
   */
  level: MapLevel;
  /** Kejadian terbaru di wilayah terpilih; `null` bila di luar kewenangan pembaca. */
  crimes: CrimeRow[] | null;
  /** Laporan masyarakat terbaru di wilayah terpilih; `null` bila di luar kewenangan. */
  reports: CitizenRow[] | null;
}) {
  const scored = data.districts.filter((district) => district.current !== null);

  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="col-span-12 xl:col-span-8">
        <Panel
          title="Peta Kerawanan"
          bodyClassName="flex flex-col gap-3"
          action={
            <Link href="/peta" className="panel-action">
              Peta lengkap
            </Link>
          }
        >
          {scored.length === 0 ? (
            <EmptyState label="Tidak ada penilaian risiko yang dapat ditampilkan untuk kewenangan Anda." />
          ) : (
            <>
              <nav aria-label="Tingkat wilayah" className="flex flex-wrap items-center gap-1.5">
                <Link
                  href="/?tingkat=polda"
                  scroll={false}
                  aria-current={level === "polda" ? "page" : undefined}
                  className={`rounded px-1.5 py-0.5 text-xs transition-colors ${
                    level === "polda"
                      ? "font-semibold text-ink"
                      : "text-ink-muted hover:text-accent"
                  }`}
                >
                  Polda Metro Jaya
                </Link>
                <span aria-hidden="true" className="text-2xs text-ink-faint">
                  &#8250;
                </span>
                <Link
                  href="/?tingkat=kecamatan"
                  scroll={false}
                  aria-current={level === "kecamatan" ? "page" : undefined}
                  className={`rounded px-1.5 py-0.5 text-xs transition-colors ${
                    level === "kecamatan"
                      ? "font-semibold text-ink"
                      : "text-ink-muted hover:text-accent"
                  }`}
                >
                  {HOME_AREA}
                </Link>
              </nav>

              <MapCanvas
                districts={data.districts}
                layer="current"
                selected={selected}
                className="mx-auto max-h-[54vh] w-full"
                level={level}
                // Klik tetap di beranda: rinciannya muncul di panel sebelah, bukan dengan
                // meninggalkan halaman yang baru saja dibuka pengguna.
                linkTo="home"
              />
              {level === "kecamatan" ? <RiskLegend /> : null}
              <p className="text-2xs leading-relaxed text-ink-faint">
                {level === "polda"
                  ? `Hanya ${HOME_AREA} yang diwarnai — sebelas wilayah lain di luar wilayah hukum Polres ini. Klik untuk membuka peta kecamatannya.`
                  : "Arahkan kursor untuk ringkasan, klik untuk rincian. Layer historis dan prediktif ada di peta lengkap."}
              </p>
            </>
          )}
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-4">
        <Panel title={selected ?? "Rincian Wilayah"} className="h-full">
          {selected === null ? (
            <EmptyState
              label={
                level === "polda"
                  ? `Klik ${HOME_AREA} pada peta untuk membuka kecamatannya.`
                  : "Klik salah satu kecamatan pada peta untuk melihat rinciannya."
              }
            />
          ) : detail === null ? (
            <EmptyState
              label={`Tidak ada rincian untuk ${selected}. Wilayah ini mungkin berada di luar kewenangan akun Anda.`}
            />
          ) : (
            <AreaSummary detail={detail} kecamatan={selected} crimes={crimes} reports={reports} />
          )}
        </Panel>
      </div>
    </div>
  );
}

/**
 * Ringkasan wilayah pada panel klik.
 *
 * Sengaja **lebih pendek** daripada panel rincian di `/peta`: beranda menjawab "apa yang
 * menonjol", bukan "ceritakan semuanya". Yang dipilih adalah lima hal yang menentukan
 * apakah wilayah ini perlu ditindak hari ini — sisanya satu klik lagi.
 */
function AreaSummary({
  detail,
  kecamatan,
  crimes,
  reports,
}: {
  detail: AreaDetail;
  kecamatan: string;
  crimes: CrimeRow[] | null;
  reports: CitizenRow[] | null;
}) {
  const top = detail.threats[0];
  const risk = top ? riskClassOf(top.risk_score) : null;

  return (
    <div className="flex h-full flex-col">
      {top ? (
        <div className="flex items-baseline gap-2">
          <span
            className={`font-heading text-3xl font-bold leading-none ${risk ? RISK_TEXT[risk] : "text-ink"}`}
          >
            {top.risk_score}
          </span>
          <span className="text-xs text-ink-muted">/100</span>
          <span className="ml-auto text-xs text-ink-muted">{risk ? RISK_LABELS[risk] : ""}</span>
        </div>
      ) : null}

      <dl className="mt-3 space-y-1.5">
        <Fact label="Ancaman utama" value={top?.threat_type ?? "—"} />
        <Fact label="Jam rawan" value={detail.critical_time_window ?? "—"} />
        <Fact
          label="Peringatan aktif"
          value={String(detail.active_warnings.length)}
          alarm={detail.active_warnings.length > 0}
        />
        <Fact label="Kejadian tercatat" value={String(detail.history.total_incidents)} />
        <Fact label="Sel dinilai" value={String(detail.grid_count)} />
      </dl>

      {detail.threats.length > 1 ? (
        <div className="mt-3">
          <p className="stat-label">Ancaman lain</p>
          <ul className="mt-1 space-y-0.5">
            {detail.threats.slice(1, 4).map((threat) => (
              <li key={threat.threat_type} className="flex items-baseline gap-2 text-xs">
                <span className="text-ink-muted">{threat.threat_type}</span>
                <span className="ml-auto font-mono text-ink">{threat.risk_score}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Kejadian dan laporan ditampilkan TERPISAH, bukan disatukan menurut waktu.
          Keduanya berbeda keandalan — kejadian sudah dicatat petugas, laporan masyarakat
          sebagiannya belum diperiksa siapa pun — dan satu daftar berurut waktu membuat
          perbedaan itu hilang tepat di tempat keputusan diambil. */}
      <RecentList
        title="Kejadian terbaru"
        empty="Tidak ada kejadian tercatat."
        denied="Di luar kewenangan akun Anda."
        rows={crimes?.map((row) => ({
          key: row.code,
          headline: row.incident_type,
          meta: `${row.incident_date} ${row.incident_time.slice(0, 5)}`,
          tail: row.status ?? null,
        }))}
      />

      <RecentList
        title="Laporan masyarakat"
        empty="Tidak ada laporan warga."
        denied="Di luar kewenangan akun Anda."
        rows={reports?.map((row) => ({
          key: row.code,
          headline: row.category,
          meta: row.reported_at.slice(0, 10),
          tail: row.status,
        }))}
      />

      <div className="mt-auto flex flex-wrap gap-2 pt-3">
        <Link
          href={`/wilayah/${encodeURIComponent(kecamatan)}`}
          className="rounded border border-accent/40 bg-accent/10 px-2.5 py-1 text-2xs uppercase tracking-wider text-accent transition-colors hover:bg-accent/20"
        >
          Rincian lengkap
        </Link>
        <Link
          href={`/peta?wilayah=${encodeURIComponent(kecamatan)}`}
          className="rounded border border-base-700 px-2.5 py-1 text-2xs uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
        >
          Buka di peta
        </Link>
      </div>
    </div>
  );
}

/**
 * Daftar ringkas isi wilayah — paling banyak empat baris.
 *
 * Dibatasi dengan sengaja: panel ini melengkapi peta, bukan menggantikan layar daftar.
 * Empat baris cukup menjawab "apa yang terjadi di sini akhir-akhir ini"; selebihnya ada
 * di tautan "Rincian lengkap" tepat di bawahnya.
 *
 * `rows` bernilai `undefined` berarti kanal itu **di luar kewenangan pembaca** — dinyatakan
 * apa adanya, bukan ditampilkan sebagai daftar kosong. Keduanya terlihat sama di layar
 * padahal artinya berbeda jauh.
 */
function RecentList({
  title,
  rows,
  empty,
  denied,
}: {
  title: string;
  rows: { key: string; headline: string; meta: string; tail: string | null }[] | undefined;
  empty: string;
  denied: string;
}) {
  return (
    <div className="mt-3">
      <p className="stat-label">{title}</p>
      {rows === undefined ? (
        <p className="mt-1 text-2xs text-ink-faint">{denied}</p>
      ) : rows.length === 0 ? (
        <p className="mt-1 text-2xs text-ink-faint">{empty}</p>
      ) : (
        <ul className="mt-1 space-y-1">
          {rows.slice(0, 4).map((row) => (
            <li key={row.key} className="text-xs leading-tight">
              <div className="flex items-baseline gap-2">
                <span className="text-ink">{row.headline}</span>
                {row.tail ? (
                  <span className="ml-auto shrink-0 text-2xs uppercase tracking-wider text-ink-faint">
                    {row.tail}
                  </span>
                ) : null}
              </div>
              <div className="text-2xs text-ink-faint">{row.meta}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Fact({ label, value, alarm }: { label: string; value: string; alarm?: boolean }) {
  return (
    <div className="flex items-baseline gap-3 border-t border-base-800 pt-1.5 first:border-t-0 first:pt-0">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd
        className={`ml-auto font-mono text-xs ${alarm ? "font-bold text-risk-critical" : "text-ink"}`}
      >
        {value}
      </dd>
    </div>
  );
}
