import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { RiskLegend } from "@/components/map/legend";
import { MapCanvas } from "@/components/map/map-canvas";
import { Panel } from "@/components/panel";
import type { AreaDetail, MapData } from "@/lib/map-data";
import { RISK_LABELS, RISK_TEXT, riskClassOf } from "@/lib/risk";

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
}: {
  data: MapData;
  selected: string | null;
  detail: AreaDetail | null;
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
              <MapCanvas
                districts={data.districts}
                layer="current"
                selected={selected}
                className="mx-auto max-h-[54vh] w-full"
                // Klik tetap di beranda: rinciannya muncul di panel sebelah, bukan dengan
                // meninggalkan halaman yang baru saja dibuka pengguna.
                linkTo="home"
              />
              <RiskLegend />
              <p className="text-[10px] leading-relaxed text-ink-faint">
                Arahkan kursor untuk ringkasan, klik untuk rincian. Layer historis dan prediktif ada
                di peta lengkap.
              </p>
            </>
          )}
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-4">
        <Panel title={selected ?? "Rincian Wilayah"} className="h-full">
          {selected === null ? (
            <EmptyState label="Klik salah satu kecamatan pada peta untuk melihat rinciannya." />
          ) : detail === null ? (
            <EmptyState
              label={`Tidak ada rincian untuk ${selected}. Wilayah ini mungkin berada di luar kewenangan akun Anda.`}
            />
          ) : (
            <AreaSummary detail={detail} kecamatan={selected} />
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
function AreaSummary({ detail, kecamatan }: { detail: AreaDetail; kecamatan: string }) {
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
          <span className="ml-auto text-[11px] text-ink-muted">
            {risk ? RISK_LABELS[risk] : ""}
          </span>
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
              <li key={threat.threat_type} className="flex items-baseline gap-2 text-[11px]">
                <span className="text-ink-muted">{threat.threat_type}</span>
                <span className="ml-auto font-mono text-ink">{threat.risk_score}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-2 pt-3">
        <Link
          href={`/wilayah/${encodeURIComponent(kecamatan)}`}
          className="rounded border border-accent/40 bg-accent/10 px-2.5 py-1 text-[10px] uppercase tracking-wider text-accent transition-colors hover:bg-accent/20"
        >
          Rincian lengkap
        </Link>
        <Link
          href={`/peta?wilayah=${encodeURIComponent(kecamatan)}`}
          className="rounded border border-base-700 px-2.5 py-1 text-[10px] uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
        >
          Buka di peta
        </Link>
      </div>
    </div>
  );
}

function Fact({ label, value, alarm }: { label: string; value: string; alarm?: boolean }) {
  return (
    <div className="flex items-baseline gap-3 border-t border-base-800 pt-1.5 first:border-t-0 first:pt-0">
      <dt className="text-[11px] text-ink-muted">{label}</dt>
      <dd
        className={`ml-auto font-mono text-xs ${alarm ? "font-bold text-risk-critical" : "text-ink"}`}
      >
        {value}
      </dd>
    </div>
  );
}
