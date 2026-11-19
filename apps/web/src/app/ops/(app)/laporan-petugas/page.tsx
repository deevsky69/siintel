import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ReportFilters } from "@/components/reports/report-filters";
import { StatusForm } from "@/components/reports/status-form";
import { ScreenTabs } from "@/components/shell/screen-tabs";
import { getProfile } from "@/lib/dashboard";
import { getEntryOptions } from "@/lib/data-entry";
import { getCrimes, jamKejadian } from "@/lib/reports";
import { changeCrimeStatus } from "./actions";

export const dynamic = "force-dynamic";

const TABS = [
  { href: "/ops/laporan-petugas", label: "Daftar kejadian" },
  { href: "/ops/input?formulir=kejadian", label: "+ Catat kejadian", permission: "crime:write" },
  { href: "/ops/pembakuan", label: "Pembakuan", permission: "crime:triage" },
] as const;

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

  const profile = await getProfile();
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
      <ScreenTabs tabs={TABS} current="/ops/laporan-petugas" permissions={profile.permissions} />
      <ReportFilters
        action="/ops/laporan-petugas"
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
          <span className="text-2xs text-ink-faint">
            {page.pagination.total_items} kejadian dalam cakupan Anda
          </span>
        }
        bodyClassName="p-0 [&>p]:px-3 [&>p]:pb-3"
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
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kode</th>
                  <th>Waktu</th>
                  <th>Jenis</th>
                  <th>Wilayah</th>
                  <th>Modus</th>
                  <th>Status</th>
                  <th className="act">Ubah status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.code}>
                    <td className="font-mono text-ink-muted">{row.code}</td>
                    <td className="whitespace-nowrap">
                      {row.incident_date}{" "}
                      <span className="font-mono text-2xs text-ink-faint">{jamKejadian(row)}</span>
                    </td>
                    <td>{row.incident_type}</td>
                    <td className="text-ink-muted">
                      {row.kecamatan}
                      {row.kelurahan ? (
                        <span className="block text-2xs text-ink-faint">{row.kelurahan}</span>
                      ) : null}
                    </td>
                    <td className="text-ink-muted">{row.modus ?? "—"}</td>
                    <td className="text-ink-muted">
                      {row.status ? (statusLabels[row.status] ?? row.status) : "—"}
                    </td>
                    <td className="act">
                      {Object.keys(statusLabels).length > 0 ? (
                        <StatusForm
                          code={row.code}
                          current={row.status}
                          options={statusLabels}
                          action={changeCrimeStatus}
                        />
                      ) : (
                        <span className="text-2xs text-ink-faint">Perlu kewenangan menulis</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-2xs leading-relaxed text-ink-faint">
          Status boleh mundur dan melompat (belum ada SOP urutan wajib); setiap perpindahan tercatat
          di jejak audit. Baris di sini dicatat petugas; identitas korban, pelaku, dan saksi tidak
          disimpan.
        </p>
      </Panel>
    </div>
  );
}
