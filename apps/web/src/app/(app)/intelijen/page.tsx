import { Panel } from "@/components/panel";
// Profil pengguna berasal dari `/auth/me`; pemuatnya sudah ada di `lib/decisions.ts`
// dan tidak digandakan di sini agar hanya ada satu bentuk `Profile`.
import { getProfile } from "@/lib/decisions";
import { getIntelligenceReports } from "@/lib/intel";
import { readSelection, selectReport } from "./display";
import { ReportBoard } from "./report-board";

export const dynamic = "force-dynamic";

/** Berapa laporan per halaman. Cukup untuk satu layar tanpa menggulir sangat panjang. */
const PAGE_SIZE = 25;

/**
 * Layar Laporan Intelijen (TASK 033).
 *
 * Seluruh isi halaman berasal dari `GET /intelligence-reports`; tidak ada angka maupun
 * penilaian yang ditanam di kode.
 *
 * Penyaring dan laporan yang sedang dibuka hidup di alamat
 * (`/intelijen?status=VERIFIED&dipilih=INT-0068`), bukan di keadaan komponen: halamannya
 * tetap server component dan tautan satu laporan dapat disalin saat paparan.
 *
 * Kewenangan diperiksa **sebelum** permintaan dikirim, dan itu bukan pengganti pemeriksaan
 * backend — backend tetap menolak dengan 403 dan mencatatnya di audit (CLAUDE.md §21).
 * Yang dihindari di sini adalah layar galat merah bagi peran Fungsi, yang per konfigurasi
 * RBAC 1 September 2026 memang tidak memegang `intelligence:read`: keadaannya perlu
 * dijelaskan sebagai kebijakan yang sedang menunggu keputusan, bukan sebagai kerusakan.
 */
function Unauthorized() {
  return (
    <Panel title="Laporan Intelijen">
      <div className="max-w-3xl text-xs leading-relaxed text-ink-muted">
        <p>
          Akun Anda tidak memiliki kewenangan <code className="text-ink">intelligence:read</code>,
          sehingga daftar laporan intelijen tidak ditampilkan. Backend menolak permintaan yang tetap
          dikirim tanpa kewenangan, dan percobaannya tercatat di audit trail.
        </p>
        <p className="mt-2">
          Ini keadaan konfigurasi yang disengaja, bukan kerusakan. Per 1 September 2026,
          <code className="text-ink"> intelligence:read</code> dicabut sementara dari peran Fungsi:
          tabel <code className="text-ink">intelligence_reports</code> tidak memiliki kolom fungsi,
          sehingga cakupan <code className="text-ink">OWN_FUNCTION</code> mustahil ditegakkan —
          sedangkan menaikkannya menjadi <code className="text-ink">ALL</code> berarti setiap
          petugas fungsi membaca seluruh laporan intelijen se-Polres. Itu pelebaran kewenangan, dan
          keputusannya milik pemilik proyek.
        </p>
        <p className="mt-2">
          Peran Pimpinan, Administrator, dan Polsek memegang kewenangan ini; peran Polsek dibatasi
          ke wilayahnya sendiri.
        </p>
      </div>
    </Panel>
  );
}

export default async function IntelligencePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const selection = readSelection(params);

  const profile = await getProfile();
  if (!profile.permissions.includes("intelligence:read")) return <Unauthorized />;

  const page = await getIntelligenceReports({
    status: selection.status,
    category: selection.category,
    page: selection.page,
    pageSize: PAGE_SIZE,
  });

  return (
    <ReportBoard
      page={page}
      selection={selection}
      selected={selectReport(page.data, selection.selected)}
    />
  );
}
