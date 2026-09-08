import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getCitizenReports } from "@/lib/reports";

export const dynamic = "force-dynamic";

/** Status yang berarti laporan masih menunggu tindakan seseorang. */
const WAITING = new Set(["RECEIVED", "VERIFIED", "FORWARDED"]);

/** Ambang tampilan untuk "mendesak". Bukan ambang resmi — lihat catatan di layar. */
const URGENT_FROM = 70;

/**
 * Panic Button — antrean permintaan bantuan mendesak (TASK 161).
 *
 * ## Yang perlu diketahui sebelum membaca kode ini
 *
 * **Kanal panic button yang sebenarnya belum ada.** Tombol darurat sekali-tekan menuntut
 * dua hal yang belum dimiliki sistem ini: aplikasi di tangan warga yang dapat mengirim
 * lokasi seketika (LAPOR PRESISI, PHASE 17), dan **komitmen respons** — siapa yang
 * menerima, dalam berapa lama, dan apa yang terjadi bila tidak ada yang menjawab.
 *
 * Yang kedua bukan pekerjaan teknis. Tombol darurat yang menjanjikan bantuan tanpa ada
 * yang berkewajiban datang lebih berbahaya daripada tidak ada tombol sama sekali: ia
 * membuat orang berhenti mencari pertolongan lain.
 *
 * Karena itu layar ini **tidak berpura-pura** menjadi kanal itu. Ia menampilkan hal
 * terdekat yang benar-benar ada — laporan masyarakat berurgensi tinggi yang belum
 * tertangani — dan menyatakan perbedaannya di bagian paling atas, bukan di catatan kaki.
 */
export default async function PanicPage() {
  const page = await getCitizenReports({ page_size: 100 });

  const waiting = page.data
    .filter((row) => WAITING.has(row.status))
    .filter((row) => (row.urgency_score ?? 0) >= URGENT_FROM)
    .sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));

  return (
    <div className="space-y-3">
      {/* Ditempatkan paling atas, bukan sebagai catatan kaki: pembaca yang mengira layar
          ini adalah kanal darurat sungguhan akan mengandalkannya. */}
      <div className="rounded border border-risk-critical/40 bg-risk-critical/10 px-3.5 py-3">
        <p className="stat-label text-risk-critical">Kanal darurat belum tersambung</p>
        <p className="mt-1.5 text-xs leading-relaxed text-ink">
          Tombol darurat sekali-tekan <strong>belum ada</strong>. Ia menuntut aplikasi di tangan
          warga yang dapat mengirim lokasi seketika, dan — yang lebih menentukan —{" "}
          <strong>komitmen respons</strong>: siapa yang menerima, dalam berapa lama, dan apa yang
          terjadi bila tidak ada yang menjawab.
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
          Yang kedua bukan pekerjaan teknis, dan tidak boleh diputuskan dari sisi ini. Tombol
          darurat yang menjanjikan bantuan tanpa ada yang berkewajiban datang lebih berbahaya
          daripada tidak ada tombol sama sekali — ia membuat orang berhenti mencari pertolongan
          lain. Untuk keadaan darurat, jalur yang berlaku tetap <strong>110</strong>.
        </p>
      </div>

      <Panel
        title="Laporan Mendesak yang Belum Tertangani"
        action={
          <span className="text-2xs text-ink-faint">
            urgensi ≥ {URGENT_FROM} · dari {page.data.length} laporan terbaru
          </span>
        }
      >
        {waiting.length === 0 ? (
          <EmptyState label="Tidak ada laporan berurgensi tinggi yang masih menunggu tindakan." />
        ) : (
          <ul className="space-y-2">
            {waiting.map((row) => (
              <li
                key={row.code}
                className="border-t border-base-800 pt-2 first:border-t-0 first:pt-0"
              >
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-sm font-bold text-risk-critical">
                    {row.urgency_score}
                  </span>
                  <span className="text-xs text-ink">{row.category}</span>
                  <span className="rounded border border-base-700 px-1.5 py-0.5 text-2xs text-ink-muted">
                    {row.status}
                  </span>
                  <span className="ml-auto font-mono text-2xs text-ink-faint">{row.code}</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                  {row.description ?? "Tanpa keterangan."}
                </p>
                <p className="mt-0.5 text-2xs text-ink-faint">
                  {row.reported_at.slice(0, 16).replace("T", " ")} ·{" "}
                  {row.kecamatan ?? "tanpa lokasi"}
                  {row.location_text ? ` · ${row.location_text}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
          Ambang urgensi {URGENT_FROM} adalah <strong>ambang tampilan</strong>, bukan ambang resmi —
          dan skor urgensinya sendiri berstatus DEMO, bukan hasil penilaian model. Daftar ini
          menyaring laporan yang sudah masuk; ia <strong>bukan</strong> antrean panggilan darurat.
        </p>
        <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
          Seluruh laporan masyarakat, termasuk yang tidak mendesak, ada di{" "}
          <Link href="/masyarakat" className="underline hover:text-ink-muted">
            Laporan Masyarakat
          </Link>
          .
        </p>
      </Panel>
    </div>
  );
}
