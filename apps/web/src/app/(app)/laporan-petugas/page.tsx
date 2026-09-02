import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { getCrimes } from "@/lib/reports";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 50;

/**
 * Laporan Petugas — kejadian yang dicatat petugas (TASK 161).
 *
 * Membaca `GET /crimes`, yang sudah membatasi cakupan wilayah di query. Berbeda dari
 * Laporan Masyarakat, setiap baris di sini **sudah terverifikasi**: ia dicatat petugas,
 * bukan dikirim orang yang tidak dikenal. Perbedaan itu disebut di layar supaya kedua
 * daftar tidak terbaca setara hanya karena bentuk tabelnya sama.
 */
export default async function LaporanPetugasPage({
  searchParams,
}: {
  searchParams: Promise<{ jenis?: string | string[]; wilayah?: string | string[] }>;
}) {
  const params = await searchParams;
  const incident_type = typeof params.jenis === "string" ? params.jenis : undefined;
  const kecamatan = typeof params.wilayah === "string" ? params.wilayah : undefined;

  const page = await getCrimes({ page_size: PAGE_SIZE, incident_type, kecamatan });

  return (
    <div className="space-y-3">
      <Panel
        title="Laporan Petugas"
        action={
          <span className="text-[10px] text-ink-faint">
            {page.pagination.total_items} kejadian tercatat
            {page.pagination.total_items > PAGE_SIZE ? ` · menampilkan ${PAGE_SIZE} terbaru` : null}
          </span>
        }
      >
        {page.data.length === 0 ? (
          <EmptyState label="Tidak ada kejadian tercatat untuk kewenangan Anda." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-ink-faint">
                  <th className="pb-1 font-normal">Kode</th>
                  <th className="pb-1 font-normal">Waktu</th>
                  <th className="pb-1 font-normal">Jenis</th>
                  <th className="pb-1 font-normal">Wilayah</th>
                  <th className="pb-1 font-normal">Lokasi</th>
                  <th className="pb-1 font-normal">Modus</th>
                  <th className="pb-1 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                {page.data.map((row) => (
                  <tr key={row.code} className="border-t border-base-800 align-top">
                    <td className="py-1.5 pr-3 font-mono text-[10px] text-ink-muted">{row.code}</td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      <span className="text-ink">{row.incident_date}</span>{" "}
                      <span className="font-mono text-[10px] text-ink-faint">
                        {row.incident_time.slice(0, 5)}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-ink">{row.incident_type}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">
                      {row.kecamatan}
                      {row.kelurahan ? (
                        <span className="block text-[10px] text-ink-faint">{row.kelurahan}</span>
                      ) : null}
                    </td>
                    <td className="py-1.5 pr-3 text-ink-muted">{row.location_type ?? "—"}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">{row.modus ?? "—"}</td>
                    <td className="py-1.5 text-ink-muted">{row.status ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">
          Setiap baris di sini <strong>dicatat petugas</strong> dan karenanya sudah terverifikasi —
          berbeda dari Laporan Masyarakat, yang sebagiannya belum diperiksa siapa pun. Keduanya
          sengaja tidak digabung menjadi satu daftar: bentuk tabel yang sama akan membuat perbedaan
          keandalannya hilang tepat di tempat ia paling penting.
        </p>
        <p className="mt-1.5 text-[10px] leading-relaxed text-ink-faint">
          Identitas korban, pelaku, dan saksi <strong>tidak disimpan</strong> pada sistem ini.
        </p>
      </Panel>
    </div>
  );
}
