import Link from "next/link";
import { Panel } from "@/components/panel";
import { getSopCalendar, type SopCalendar } from "@/lib/sop";
import { SopCheckForm } from "./check-form";
import { MODUL, MUATAN, PENGGUNA_PRODUK, RINGKASAN_SOP, SUMBER_DATA, VALIDASI } from "./content";

/**
 * SOP dan Modul Aplikasi SIGAP — muatan dan desain program menurut naskah Taskap revisi
 * (`docs/TASKAP - IRKHAMUL KHAKIM - 202608003058 REVISI.docx`): Gambar 4.3 (Desain Program),
 * Tabel 4.17 (Muatan SOP dan Modul Aplikasi SIGAP), dan Lampiran I (Ringkasan SOP).
 *
 * Halaman ini **statis dengan sengaja**. Isinya kutipan naskah, bukan angka dari basis data:
 * yang dijaga adalah kesamaan kata demi kata dengan naskah, sehingga penguji yang membandingkan
 * layar dengan Tabel 4.17 menemukan teks yang sama. Bila naskah berubah, ubah berkas ini —
 * dan hanya berkas ini — bersama `sop.test.tsx` yang mengunci isinya.
 *
 * Tautan pada tiap modul menunjuk layar yang menjalankannya, supaya "modul" di naskah dapat
 * ditunjuk di aplikasi.
 */

const Panah = () => (
  <span aria-hidden="true" className="hidden self-center font-bold text-accent lg:block">
    →
  </span>
);

const kotakSumber =
  "rounded border border-risk-critical/40 bg-risk-critical/10 px-3 py-2 text-center text-xs font-semibold text-ink";
const kotakModul = "flex flex-1 flex-col rounded bg-accent-deep px-3 py-3 text-center text-white";
const kotakSop =
  "rounded border border-risk-critical/50 bg-risk-critical/15 px-2 py-1.5 text-center text-2xs font-semibold text-ink";

export const dynamic = "force-dynamic";

const waktu = (iso: string) =>
  new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));

/**
 * Kalender SOP (catatan 192): butir berkala SOP yang dicatat pejabat berwenang, butir yang
 * diketahui sistem, dan rekap triwulan mutu draf serta waktu kerja. Gagal memuat tidak
 * menjatuhkan halaman — muatan dan desain SOP di bawahnya tetap tampil.
 */
function KalenderSop({ calendar }: { calendar: SopCalendar }) {
  const q = calendar.quarter;
  return (
    <Panel
      title={`Kalender SOP · ${calendar.period}`}
      action={
        <span className="text-2xs uppercase tracking-wider text-ink-faint">
          {calendar.done} dari {calendar.total} butir
        </span>
      }
      bodyClassName="flex flex-col gap-3"
    >
      <ul className="divide-y divide-base-800">
        {calendar.items.map((item) => (
          <li key={item.key} className="flex flex-col gap-1 py-2.5 text-xs">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <span
                className={`rounded border px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wider ${
                  item.done
                    ? "border-risk-low/50 bg-risk-low/10 text-risk-low"
                    : "border-base-700 text-ink-faint"
                }`}
              >
                {item.done ? "sudah" : "belum"}
              </span>
              <span className="font-semibold text-ink">{item.section}</span>
              <span className="text-2xs text-ink-faint">
                {item.source === "SYSTEM" ? "dari sistem" : `dicatat ${item.who}`}
              </span>
            </div>
            <p className="leading-relaxed text-ink-muted">{item.rule}</p>
            <p className="text-2xs leading-relaxed text-ink-faint">
              {item.fact}
              {item.done_at
                ? ` Dicatat ${item.done_by ?? "—"}, ${waktu(item.done_at)}${item.note ? ` — ${item.note}` : ""}.`
                : ""}
            </p>
            {item.can_record ? <SopCheckForm period={calendar.period} item={item.key} /> : null}
          </li>
        ))}
      </ul>
      <div className="rounded border border-base-800 bg-base-850 p-3">
        <h3 className="stat-label mb-2">Rekap {q.label}</h3>
        <dl className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="text-2xs text-ink-faint">Produk bulanan dicatat</dt>
            <dd className="mt-0.5 text-ink">
              {q.recorded} dari {q.products} produk ({q.months.join(", ")})
            </dd>
          </div>
          <div>
            <dt className="text-2xs text-ink-faint">Median skor mutu draf SIGAP</dt>
            <dd className="mt-0.5 text-ink">
              {q.median_quality_sigap === null
                ? "belum ada catatan"
                : `${q.median_quality_sigap} dari ${q.quality_max}`}
            </dd>
          </div>
          <div>
            <dt className="text-2xs text-ink-faint">Median skor cara kerja biasa</dt>
            <dd className="mt-0.5 text-ink">
              {q.median_quality_manual === null
                ? "belum ada catatan"
                : `${q.median_quality_manual} dari ${q.quality_max}`}
            </dd>
          </div>
          <div>
            <dt className="text-2xs text-ink-faint">Median data siap olah → validasi</dt>
            <dd className="mt-0.5 text-ink">
              {q.median_minutes_ready_to_validated === null
                ? "belum ada catatan"
                : `${q.median_minutes_ready_to_validated} menit`}
            </dd>
          </div>
        </dl>
      </div>
      <p className="text-2xs leading-relaxed text-ink-faint">{calendar.basis}</p>
    </Panel>
  );
}

export default async function SopPage() {
  const calendar = await getSopCalendar().catch(() => null);
  return (
    <div className="space-y-3">
      {calendar ? <KalenderSop calendar={calendar} /> : null}
      <Panel
        title="Desain Program — SOP dan Aplikasi SIGAP"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">Gambar 4.3</span>
        }
        bodyClassName="flex flex-col gap-4"
      >
        <p className="rounded bg-accent-deep px-3 py-2 text-center font-heading text-sm font-bold uppercase tracking-wide text-white">
          SOP dan Aplikasi SIGAP: Siklus Bulanan Deteksi Dini Kejahatan 3C
        </p>

        <section aria-labelledby="sop-sumber">
          <h3 id="sop-sumber" className="stat-label mb-2">
            Sumber data
          </h3>
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {SUMBER_DATA.map((sumber) => (
              <li key={sumber} className={kotakSumber}>
                {sumber}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="sop-modul">
          <h3 id="sop-modul" className="stat-label mb-2">
            Lima modul dan bagian SOP yang mengaturnya
          </h3>
          <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
            {MODUL.map((modul, index) => (
              <li key={modul.no} className="flex flex-1 gap-2">
                <div className="flex flex-1 flex-col gap-2">
                  <div className={kotakModul}>
                    <span className="font-heading text-xs font-bold uppercase tracking-wider">
                      {modul.no}
                    </span>
                    <span className="mt-1 text-xs font-semibold">{modul.nama}</span>
                  </div>
                  <div className={kotakSop}>{modul.sop}</div>
                  <p className="text-center text-2xs text-ink-muted">
                    {modul.layar.map((layar, i) => (
                      <span key={layar.href + layar.label}>
                        {i > 0 ? " · " : ""}
                        <Link href={layar.href} className="text-accent hover:underline">
                          {layar.label}
                        </Link>
                      </span>
                    ))}
                  </p>
                </div>
                {index < MODUL.length - 1 ? <Panah /> : null}
              </li>
            ))}
          </ol>
          <p className="mt-2 text-center text-2xs font-semibold text-ink-muted">
            ↺ umpan balik awal bulan berikutnya (Modul 5 kembali ke Modul 1)
          </p>
        </section>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <section aria-labelledby="sop-validasi">
            <h3 id="sop-validasi" className="stat-label mb-2">
              Validasi berjenjang (Modul 4)
            </h3>
            <ol className="flex flex-wrap items-center gap-1.5">
              {VALIDASI.map((tahap, index) => (
                <li key={tahap} className="flex items-center gap-1.5">
                  <span
                    className={`rounded px-2.5 py-1.5 text-center text-2xs font-semibold ${
                      index === VALIDASI.length - 1
                        ? "bg-accent-deep text-white"
                        : "border border-base-700 bg-base-850 text-ink"
                    }`}
                  >
                    {tahap}
                  </span>
                  {index < VALIDASI.length - 1 ? (
                    <span aria-hidden="true" className="font-bold text-accent">
                      →
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          </section>
          <section aria-labelledby="sop-pengguna">
            <h3 id="sop-pengguna" className="stat-label mb-2">
              Pengguna produk
            </h3>
            <ul className="flex flex-wrap gap-1.5">
              {PENGGUNA_PRODUK.map((pengguna) => (
                <li key={pengguna} className={kotakSumber}>
                  {pengguna}
                </li>
              ))}
            </ul>
            <p className="mt-2 rounded border border-risk-critical/40 px-2.5 py-1.5 text-center text-2xs font-semibold text-ink">
              Tindak lanjut dicatat dan dikirim kembali ke Modul 5
            </p>
          </section>
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <div className="rounded border border-base-700 bg-base-850 px-3 py-2 text-center">
            <p className="font-heading text-xs font-bold uppercase tracking-wide text-ink">
              Dasbor Internal SIGAP
            </p>
            <p className="mt-1 text-2xs leading-relaxed text-ink-muted">
              Peta kelurahan, profil rentang jam, peringkat prediksi, status validasi, dan riwayat
              keputusan
            </p>
          </div>
          <div className="rounded border border-base-700 bg-base-850 px-3 py-2 text-center">
            <p className="font-heading text-xs font-bold uppercase tracking-wide text-ink">
              SIGAP Bersama (Masyarakat)
            </p>
            <p className="mt-1 text-2xs leading-relaxed text-ink-muted">
              Imbauan per kelurahan, status laporan milik pelapor, dan kanal informasi warga yang
              dikelola Humas dan Satbinmas
            </p>
          </div>
        </div>

        <p className="rounded border border-risk-critical/50 bg-risk-critical/15 px-3 py-2 text-center text-xs font-semibold text-ink">
          KEAMANAN INFORMASI: hak akses menurut peran • data dianonimkan • catatan akses diperiksa
          bulanan • pencadangan terjadwal
        </p>
        <div className="rounded bg-accent-deep px-3 py-2 text-center text-white">
          <p className="font-heading text-xs font-bold uppercase tracking-wide">Hasil</p>
          <p className="mt-1 text-2xs leading-relaxed">
            Peringatan dini yang menyebut kelurahan, jenis kejahatan, dan rentang jam rawan,
            tervalidasi berjenjang, ditindaklanjuti fungsi pelaksana, dan diukur ketepatannya setiap
            bulan
          </p>
        </div>
      </Panel>

      <Panel
        title="Muatan SOP dan Modul Aplikasi SIGAP"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">Tabel 4.17</span>
        }
      >
        <div className="table-scroll">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <thead>
              <tr className="border-b border-base-800">
                <th className="stat-label py-2 font-medium">Bagian SOP</th>
                <th className="stat-label py-2 font-medium">Modul Aplikasi</th>
                <th className="stat-label py-2 font-medium">Isi Pokok</th>
                <th className="stat-label py-2 text-center font-medium">Kelemahan yang Dijawab</th>
              </tr>
            </thead>
            <tbody>
              {MUATAN.map((baris) => (
                <tr key={baris.bagian} className="border-b border-base-800/60 align-top">
                  <td className="py-2 font-semibold text-ink">{baris.bagian}</td>
                  <td className="py-2 text-ink">{baris.modul}</td>
                  <td className="py-2 text-ink-muted">{baris.isi}</td>
                  <td className="py-2 text-center font-mono text-ink">{baris.kelemahan}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title="Ringkasan SOP Deteksi Dini Kejahatan 3C Berbasis Data"
        action={
          <span className="text-2xs uppercase tracking-wider text-ink-faint">Lampiran I</span>
        }
      >
        <div className="table-scroll">
          <table className="w-full min-w-[36rem] text-left text-xs">
            <thead>
              <tr className="border-b border-base-800">
                <th className="stat-label py-2 font-medium">No</th>
                <th className="stat-label py-2 font-medium">Bagian</th>
                <th className="stat-label py-2 font-medium">Ketentuan Pokok</th>
              </tr>
            </thead>
            <tbody>
              {RINGKASAN_SOP.map(([bagian, ketentuan], index) => (
                <tr key={bagian} className="border-b border-base-800/60 align-top">
                  <td className="py-2 font-mono text-ink-muted">{index + 1}</td>
                  <td className="py-2 font-semibold text-ink">{bagian}</td>
                  <td className="py-2 leading-relaxed text-ink-muted">{ketentuan}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
          Sumber: naskah Taskap, Bab IV (Gambar 4.3 dan Tabel 4.17) serta Lampiran I. SOP berstatus
          rancangan yang diajukan kepada Kapolres; halaman ini menampilkan muatannya, bukan
          pengesahannya.
        </p>
      </Panel>
    </div>
  );
}
