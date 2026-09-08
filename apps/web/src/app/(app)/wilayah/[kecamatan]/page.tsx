import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { DistrictDetail } from "@/components/map/district-detail";
import { Panel } from "@/components/panel";
import { getAreaDetail, MAP_HORIZON } from "@/lib/map-data";
import { getCrimes } from "@/lib/reports";

export const dynamic = "force-dynamic";

const RECENT_LIMIT = 15;

/**
 * Rincian satu kecamatan (TASK 161).
 *
 * Memakai kembali `DistrictDetail` — komponen yang sama dengan panel kanan pada peta.
 * Menyalinnya menjadi tampilan kedua akan membuat dua layar menjawab "apa ancaman di
 * Tebet" secara terpisah, dan keduanya dapat menyimpang tanpa ada yang menunjukkannya.
 *
 * Backend menjawab **404** baik untuk kecamatan yang tidak ada maupun untuk kecamatan di
 * luar kewenangan pengguna — dengan sengaja, agar keberadaan data di wilayah lain tidak
 * bocor. Halaman ini menghormatinya: keduanya tampil sama, tanpa menebak yang mana.
 */
export default async function WilayahDetailPage({
  params,
}: {
  params: Promise<{ kecamatan: string }>;
}) {
  const { kecamatan: raw } = await params;
  const kecamatan = decodeURIComponent(raw);

  const [detail, crimes] = await Promise.all([
    getAreaDetail(kecamatan),
    getCrimes({ kecamatan, page_size: RECENT_LIMIT }).catch(() => null),
  ]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Link href="/wilayah" className="text-xs text-ink-muted hover:text-accent">
          ← Wilayah Rawan
        </Link>
        <h1 className="font-heading text-lg font-bold text-ink">{kecamatan}</h1>
        <Link
          href={`/peta?wilayah=${encodeURIComponent(kecamatan)}`}
          className="ml-auto rounded border border-base-700 px-2.5 py-1 text-2xs uppercase tracking-wider text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
        >
          Lihat di peta
        </Link>
      </div>

      {detail === null ? (
        <Panel title="Rincian Wilayah">
          <EmptyState
            label={`Tidak ada rincian yang dapat ditampilkan untuk ${kecamatan}. Wilayah ini mungkin tidak dikenal, atau berada di luar kewenangan akun Anda.`}
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 xl:col-span-5">
            <Panel title="Potensi Ancaman Wilayah" className="h-full">
              <DistrictDetail
                district={{
                  kecamatan,
                  historical: null,
                  current: null,
                  predictive: null,
                }}
                detail={detail}
                horizon={MAP_HORIZON}
              />
            </Panel>
          </div>

          <div className="col-span-12 xl:col-span-7">
            <Panel
              title="Kejadian Terbaru di Wilayah Ini"
              action={
                <Link
                  href={`/laporan-petugas?wilayah=${encodeURIComponent(kecamatan)}`}
                  className="text-2xs text-ink-faint hover:text-accent"
                >
                  seluruhnya →
                </Link>
              }
              className="h-full"
            >
              {crimes === null ? (
                <EmptyState label="Daftar kejadian berada di luar kewenangan akun Anda." />
              ) : crimes.data.length === 0 ? (
                <EmptyState label="Tidak ada kejadian tercatat di wilayah ini." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-2xs uppercase tracking-wider text-ink-faint">
                        <th className="pb-1 font-normal">Waktu</th>
                        <th className="pb-1 font-normal">Jenis</th>
                        <th className="pb-1 font-normal">Kelurahan</th>
                        <th className="pb-1 font-normal">Modus</th>
                      </tr>
                    </thead>
                    <tbody>
                      {crimes.data.map((row) => (
                        <tr key={row.code} className="border-t border-base-800">
                          <td className="py-1.5 pr-3 whitespace-nowrap text-ink-muted">
                            {row.incident_date}{" "}
                            <span className="font-mono text-2xs text-ink-faint">
                              {row.incident_time.slice(0, 5)}
                            </span>
                          </td>
                          <td className="py-1.5 pr-3 text-ink">{row.incident_type}</td>
                          <td className="py-1.5 pr-3 text-ink-muted">{row.kelurahan ?? "—"}</td>
                          <td className="py-1.5 text-ink-muted">{row.modus ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}
