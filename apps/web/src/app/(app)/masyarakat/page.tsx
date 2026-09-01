import { getCitizenReports, getCommunitySummary, REPORT_STATUSES } from "@/lib/community";
import { CommunityView } from "./community-view";

export const dynamic = "force-dynamic";

/**
 * Community Signal Dashboard (TASK 024) — fitur MVP #12, keluaran §8 no. 6.
 *
 * Pilihan penyaring disimpan di URL (`?status=`, `?kategori=`), bukan state klien, agar
 * halaman tetap server component dan tautannya dapat dibagikan saat paparan — pola yang
 * sama dipakai layar Operasi dan Warning Center.
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
  const requestedStatus = typeof params.status === "string" ? params.status.toUpperCase() : null;
  const requestedCategory = typeof params.kategori === "string" ? params.kategori : null;

  const summary = await getCommunitySummary();

  const status = REPORT_STATUSES.find((value) => value === requestedStatus) ?? null;
  const category =
    requestedCategory && requestedCategory in summary.per_category ? requestedCategory : null;

  const reports = await getCitizenReports({ status, category });

  return <CommunityView summary={summary} reports={reports} filters={{ status, category }} />;
}
