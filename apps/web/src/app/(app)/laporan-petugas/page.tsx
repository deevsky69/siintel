import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ReportFilters } from "@/components/reports/report-filters";
import { StatusForm } from "@/components/reports/status-form";
import { getEntryOptions } from "@/lib/data-entry";
import { getCrimes } from "@/lib/reports";
import { changeCrimeStatus } from "./actions";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 100;

/**
 * Laporan Petugas — kejadian yang dicatat petugas, beserta penanganannya (TASK 161–163).
 *
 * Statusnya dapat diubah **langsung dari daftar ini**. Pertanyaan yang memicunya —
 * "bagaimana cara mengganti status?" — muncul justru saat seseorang sedang menatap
 * daftarnya, dan formulir yang berada di layar lain menuntutnya mengingat kode kejadian
 * lalu berpindah dua kali.
 *
 * Penyaringnya berupa formulir GET biasa: hasil saringan tersimpan di alamat, dapat
 * dibagikan sebagai tautan, dan penyaringannya dikerjakan di **query database**. Menarik
 * seluruh baris lalu memilahnya di peramban akan menembus batas cakupan wilayah — baris
 * yang tidak boleh dilihat pengguna tidak boleh sampai ke peramban sama sekali.
 */
export default async function LaporanPetugasPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return typeof value === "string" ? value.trim() : "";
  };

  const search = one("cari");
  const dateFrom = one("dari");
  const dateTo = one("sampai");
  const incidentType = one("jenis");
  const kecamatan = one("wilayah");
  const statusFilter = one("status");

  const [page, options] = await Promise.all([
    getCrimes({
      page_size: PAGE_SIZE,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      incident_type: incidentType || undefined,
      kecamatan: kecamatan || undefined,
    }),
    getEntryOptions().catch(() => null),
  ]);

  const statusLabels: Record<string, string> = Object.fromEntries(
    (options?.crime_status ?? []).map((option) => [option.value, option.label]),
  );
  const typeLabels: Record<string, string> = Object.fromEntries(
    (options?.incident_type ?? []).map((option) => [option.value, option.label]),
  );
  const areaLabels: Record<string, string> = Object.fromEntries(
    [...new Set(page.data.map((row) => row.kecamatan))].sort().map((name) => [name, name]),
  );

  // Pencarian teks dan penyaring status dikerjakan di sini karena `GET /crimes` belum
  // melayani keduanya. Itu **bukan** kebocoran cakupan: baris yang sampai ke sini sudah
  // disaring wilayahnya oleh backend, dan yang dikerjakan di sini hanya mempersempit
  // lebih jauh — tidak pernah memperluas.
  const needle = search.toLowerCase();
  const rows = page.data
    .filter((row) => (statusFilter ? row.status === statusFilter : true))
    .filter((row) =>
      needle === ""
        ? true
        : [row.code, row.incident_type, row.kecamatan, row.kelurahan, row.modus, row.location_type]
            .filter((value): value is string => typeof value === "string")
            .some((value) => value.toLowerCase().includes(needle)),
    );

  const filtered = Boolean(
    search || dateFrom || dateTo || incidentType || kecamatan || statusFilter,
  );

  return (
    <div className="space-y-3">
      <ReportFilters
        action="/laporan-petugas"
        search={search}
        searchLabel="Cari"
        searchHint="Kode, jenis, wilayah, modus…"
        dateFrom={dateFrom}
        dateTo={dateTo}
        dateLabel="Tanggal kejadian"
        resultCount={rows.length}
        filtered={filtered}
        selects={[
          {
            name: "jenis",
            label: "Jenis kejadian",
            options: typeLabels,
            current: incidentType,
            anyLabel: "Semua jenis",
          },
          {
            name: "wilayah",
            label: "Kecamatan",
            options: areaLabels,
            current: kecamatan,
            anyLabel: "Semua kecamatan",
          },
          {
            name: "status",
            label: "Status penanganan",
            options: statusLabels,
            current: statusFilter,
            anyLabel: "Semua status",
          },
        ]}
      />

      <Panel
        title="Laporan Petugas"
        action={
          <span className="text-[10px] text-ink-faint">
            {page.pagination.total_items} kejadian dalam cakupan Anda
          </span>
        }
      >
        {rows.length === 0 ? (
          <EmptyState
            label={
              filtered
                ? "Tidak ada kejadian yang cocok dengan saringan ini."
                : "Tidak ada kejadian tercatat untuk kewenangan Anda."
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-ink-faint">
                  <th className="pb-1 font-normal">Kode</th>
                  <th className="pb-1 font-normal">Waktu</th>
                  <th className="pb-1 font-normal">Jenis</th>
                  <th className="pb-1 font-normal">Wilayah</th>
                  <th className="pb-1 font-normal">Modus</th>
                  <th className="pb-1 font-normal">Status</th>
                  <th className="pb-1 font-normal">Ubah status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
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
                    <td className="py-1.5 pr-3 text-ink-muted">{row.modus ?? "—"}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">
                      {row.status ? (statusLabels[row.status] ?? row.status) : "—"}
                    </td>
                    <td className="py-1.5">
                      {Object.keys(statusLabels).length > 0 ? (
                        <StatusForm
                          code={row.code}
                          current={row.status}
                          options={statusLabels}
                          action={changeCrimeStatus}
                        />
                      ) : (
                        <span className="text-[10px] text-ink-faint">Perlu kewenangan menulis</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">
          Alur penanganan <strong>Dilaporkan → Penyelidikan → Penyidikan → Selesai</strong> boleh
          <strong> mundur dan melompat</strong>. Itu disengaja: belum ada SOP yang menetapkan
          urutannya wajib, dan melarang mundur berarti perkara yang keliru ditutup tidak akan pernah
          dapat dibuka kembali. Setiap perpindahan tercatat di jejak audit lengkap dengan status
          sebelum dan sesudahnya.
        </p>
        <p className="mt-1.5 text-[10px] leading-relaxed text-ink-faint">
          Setiap baris di sini <strong>dicatat petugas</strong> dan karenanya sudah terverifikasi.
          Identitas korban, pelaku, dan saksi tidak disimpan pada sistem ini.
        </p>
      </Panel>
    </div>
  );
}
