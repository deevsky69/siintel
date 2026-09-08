import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { AREA_STATUS_TONE, getLeadership, REPORT_LEVEL_TONE, toneOf } from "@/lib/leadership";

export const dynamic = "force-dynamic";

/**
 * Wilayah Rawan — peringkat kecamatan, dan pintu masuk ke rinciannya (TASK 161).
 *
 * Memakai `GET /dashboard/leadership` yang sudah menghitung keduanya: status wilayah
 * menurut penilaian risiko, dan peringkat volume laporan. Keduanya sengaja ditampilkan
 * **berdampingan dalam satu tabel**, karena keduanya sering berbeda — dan justru
 * selisihnya yang bermakna.
 *
 * Wilayah dengan banyak laporan tetapi skor risiko rendah, misalnya, biasanya bukan
 * wilayah yang memburuk melainkan wilayah yang **warganya rajin melapor**. Menampilkan
 * salah satunya saja akan menyembunyikan bacaan itu.
 */
export default async function WilayahPage() {
  const board = await getLeadership();
  const byArea = new Map(board.top_report_areas.areas.map((area) => [area.kecamatan, area]));

  return (
    <div className="space-y-3">
      <Panel
        title="Wilayah Rawan"
        action={
          <span className="text-2xs text-ink-faint">
            Penilaian {board.area_status.assessment_date ?? "—"} · laporan{" "}
            {board.top_report_areas.days} hari
          </span>
        }
      >
        {board.area_status.areas.length === 0 ? (
          <EmptyState label="Belum ada penilaian risiko untuk kewenangan Anda." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-2xs uppercase tracking-wider text-ink-faint">
                  <th className="pb-1 font-normal">#</th>
                  <th className="pb-1 font-normal">Kecamatan</th>
                  <th className="pb-1 text-right font-normal">Sel Tertinggi</th>
                  <th className="pb-1 text-right font-normal">Rata-rata</th>
                  <th className="pb-1 text-right font-normal">Status</th>
                  <th className="pb-1 text-right font-normal">Laporan</th>
                  <th className="pb-1 text-right font-normal">Volume</th>
                </tr>
              </thead>
              <tbody>
                {board.area_status.areas.map((area, index) => {
                  const reports = byArea.get(area.kecamatan);
                  return (
                    <tr key={area.kecamatan} className="border-t border-base-800">
                      <td className="py-1.5 font-mono text-2xs text-ink-faint">{index + 1}</td>
                      <td className="py-1.5">
                        <Link
                          href={`/wilayah/${encodeURIComponent(area.kecamatan)}`}
                          className="text-ink hover:text-accent"
                        >
                          {area.kecamatan}
                        </Link>
                      </td>
                      <td className="py-1.5 text-right font-mono font-semibold text-ink">
                        {area.risk_score}
                      </td>
                      <td className="py-1.5 text-right font-mono text-ink-muted">
                        {area.average_risk_score}
                      </td>
                      <td className="py-1.5 text-right">
                        <span
                          className={`rounded border px-1.5 py-0.5 text-2xs ${toneOf(
                            AREA_STATUS_TONE,
                            area.status,
                          )}`}
                        >
                          {area.label}
                        </span>
                      </td>
                      <td className="py-1.5 text-right font-mono text-ink-muted">
                        {reports?.reports ?? 0}
                      </td>
                      <td className="py-1.5 text-right">
                        {reports ? (
                          <span
                            className={`rounded border px-1.5 py-0.5 text-2xs ${toneOf(
                              REPORT_LEVEL_TONE,
                              reports.level,
                            )}`}
                          >
                            {reports.level_label}
                          </span>
                        ) : (
                          <span className="text-2xs text-ink-faint">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
          <strong>
            Dua kolom terakhir bukan pengukuran yang sama dengan tiga kolom sebelumnya.
          </strong>{" "}
          Skor risiko ditimbang dari beberapa faktor; jumlah laporan tidak ditimbang sama sekali.
          Wilayah dengan banyak laporan tetapi skor rendah biasanya bukan wilayah yang memburuk,
          melainkan wilayah yang <strong>warganya rajin melapor</strong> — dan sebaliknya.
        </p>
        <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">{board.area_status.basis}</p>
      </Panel>
    </div>
  );
}
