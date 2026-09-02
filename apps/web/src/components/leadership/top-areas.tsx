import Link from "next/link";
import { Panel } from "@/components/panel";
import type { LeadershipBoard } from "@/lib/leadership";
import { REPORT_LEVEL_TONE, toneOf } from "@/lib/leadership";

/**
 * Daftar wilayah menurut **jumlah laporan** (permintaan pemilik proyek: sepuluh teratas).
 *
 * Yang paling mudah keliru dari daftar ini: ia terlihat seperti peringkat kerawanan, tetapi
 * yang diperingkat adalah **volume laporan**. Wilayah dengan laporan terbanyak belum tentu
 * wilayah paling rawan — jumlah laporan tidak ditimbang dan tidak dinormalkan terhadap luas
 * maupun jumlah penduduk, dan wilayah dengan pelaporan yang lebih aktif akan selalu naik.
 *
 * Karena itu tingkatnya (Kritis/Sedang/Rendah) dinyatakan sebagai peringkat volume, bukan
 * kelas risiko, dan panel ini menampilkan kelas risiko wilayah **secara terpisah** di kartu
 * Status Wilayah supaya keduanya tidak tertukar.
 */
export function TopReportAreas({ top }: { top: LeadershipBoard["top_report_areas"] }) {
  return (
    <Panel
      title="Top Area Menurut Jumlah Laporan"
      action={
        <span className="text-[10px] text-ink-faint">
          {top.days} hari · {top.window_from} s.d. {top.window_to}
        </span>
      }
    >
      {top.areas.length === 0 ? (
        <p className="text-xs text-ink-muted">
          Tidak ada laporan pada jendela ini untuk kewenangan Anda.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-ink-faint">
                <th className="pb-1 font-normal">#</th>
                <th className="pb-1 font-normal">Kecamatan</th>
                <th className="pb-1 text-right font-normal">Kejadian</th>
                <th className="pb-1 text-right font-normal">Intelijen</th>
                <th className="pb-1 text-right font-normal">Masyarakat</th>
                <th className="pb-1 text-right font-normal">Total</th>
                <th className="pb-1 text-right font-normal">Tingkat</th>
              </tr>
            </thead>
            <tbody>
              {top.areas.map((area, index) => (
                <tr key={area.kecamatan} className="border-t border-base-800">
                  <td className="py-1.5 font-mono text-[10px] text-ink-faint">{index + 1}</td>
                  <td className="py-1.5">
                    <Link
                      href={`/peta?wilayah=${encodeURIComponent(area.kecamatan)}&layer=historical`}
                      className="text-ink hover:text-accent"
                    >
                      {area.kecamatan}
                    </Link>
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink-muted">
                    {area.crime_incidents}
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink-muted">
                    {area.intelligence_reports}
                  </td>
                  <td className="py-1.5 text-right font-mono text-ink-muted">
                    {area.citizen_reports}
                  </td>
                  <td className="py-1.5 text-right font-mono font-semibold text-ink">
                    {area.reports}
                  </td>
                  <td className="py-1.5 text-right">
                    <span
                      className={`rounded border px-1.5 py-0.5 text-[10px] ${toneOf(
                        REPORT_LEVEL_TONE,
                        area.level,
                      )}`}
                    >
                      {area.level_label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {top.unattributed_reports > 0 ? (
        <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">
          {top.unattributed_reports} laporan masyarakat pada jendela ini tidak memiliki lokasi yang
          cocok dengan master lokasi, sehingga tidak terhitung pada baris mana pun di atas.
        </p>
      ) : null}

      <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">{top.basis}</p>
    </Panel>
  );
}
