import { ReportFilters } from "@/components/reports/report-filters";
import { getCitizenReports, getCommunitySummary, REPORT_STATUSES } from "@/lib/community";
import { getEntryOptions } from "@/lib/data-entry";
import { CommunityView } from "./community-view";

export const dynamic = "force-dynamic";

/**
 * Community Signal Dashboard (TASK 024, 163) — fitur MVP #12, keluaran §8 no. 6.
 *
 * Seluruh penyaring disimpan di alamat (`?status=`, `?kategori=`, `?cari=`, `?dari=`,
 * `?sampai=`), bukan keadaan di peramban, agar halaman tetap komponen server dan hasil
 * saringannya dapat dibagikan sebagai tautan saat paparan.
 *
 * Ringkasan diambil lebih dulu karena daftar kategori berasal dari **datanya sendiri**,
 * bukan dari daftar yang ditulis di kode. Nilai penyaring yang tidak dikenal dibuang di
 * sini supaya antarmuka tidak pernah menggemakan kembali isian sembarang dari URL;
 * penyaringan yang sesungguhnya tetap ditegakkan backend (CLAUDE.md §21).
 */
export default async function CommunityPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (key: string) => {
    const value = params[key];
    return typeof value === "string" ? value.trim() : "";
  };

  const requestedStatus = one("status").toUpperCase();
  const requestedCategory = one("kategori");
  const search = one("cari");
  const dateFrom = one("dari");
  const dateTo = one("sampai");

  const summary = await getCommunitySummary();

  const status = REPORT_STATUSES.find((value) => value === requestedStatus) ?? null;
  const category = requestedCategory in summary.per_category ? requestedCategory : null;

  const [reports, options] = await Promise.all([
    // Diambil lebih banyak daripada yang ditampilkan karena pencarian teks dan rentang
    // tanggal disaring di sini: `GET /citizen-reports` belum melayani keduanya.
    getCitizenReports({ status, category, pageSize: 200 }),
    getEntryOptions().catch(() => null),
  ]);

  const statusLabels: Record<string, string> = Object.fromEntries(
    (options?.citizen_report_status ?? []).map((option) => [option.value, option.label]),
  );

  // Penyaringan di sini hanya **mempersempit** apa yang sudah disaring backend menurut
  // cakupan wilayah — tidak pernah memperluasnya. Baris yang tidak boleh dilihat pengguna
  // tidak pernah sampai ke sini sejak awal.
  const needle = search.toLowerCase();
  const rows = reports.data
    .filter((row) => (dateFrom ? row.reported_at.slice(0, 10) >= dateFrom : true))
    .filter((row) => (dateTo ? row.reported_at.slice(0, 10) <= dateTo : true))
    .filter((row) =>
      needle === ""
        ? true
        : [row.code, row.category, row.description, row.kecamatan, row.location_text]
            .filter((value): value is string => typeof value === "string")
            .some((value) => value.toLowerCase().includes(needle)),
    );

  const filtered = Boolean(status || category || search || dateFrom || dateTo);

  return (
    <div className="space-y-3">
      <ReportFilters
        action="/masyarakat"
        search={search}
        searchLabel="Cari"
        searchHint="Kode, kategori, isi laporan, wilayah…"
        dateFrom={dateFrom}
        dateTo={dateTo}
        dateLabel="Tanggal lapor"
        resultCount={rows.length}
        filtered={filtered}
        selects={[
          {
            name: "status",
            label: "Tahapan penanganan",
            options: statusLabels,
            current: status ?? "",
            anyLabel: "Semua tahapan",
          },
          {
            name: "kategori",
            label: "Kategori",
            options: Object.fromEntries(Object.keys(summary.per_category).map((k) => [k, k])),
            current: category ?? "",
            anyLabel: "Semua kategori",
          },
        ]}
      />

      <CommunityView
        summary={summary}
        reports={{ ...reports, data: rows }}
        filters={{ status, category }}
        statusLabels={statusLabels}
      />
    </div>
  );
}
