import Link from "next/link";
import { TrackForm, VehicleForm } from "./forms";

export const metadata = { title: "Lacak Laporan — SIGAP WARGA" };

/**
 * Lacak laporan dan cek kendaraan (tahap 2, 2 November 2026).
 *
 * Dua hal yang sering ditanyakan warga ke Polsek, dijawab tanpa harus datang: sampai mana
 * laporan saya (nomor LP + PIN), dan apakah kendaraan yang akan saya beli pernah dilaporkan
 * hilang (plat atau nomor rangka). Keduanya hanya menjawab yang menjadi hak penanya.
 */
export default async function LacakPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const tab = params.tab === "kendaraan" ? "kendaraan" : "laporan";
  return (
    <div className="mx-auto w-full max-w-lg space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-accent-soft">
          SIGAP WARGA
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink">Lacak laporan dan cek kendaraan</h1>
      </div>
      <div className="grid grid-cols-2 gap-2 rounded-full bg-base-850 p-1" role="tablist">
        <Link
          href="/lacak"
          role="tab"
          aria-selected={tab === "laporan"}
          className={`rounded-full py-2 text-center text-sm font-semibold ${tab === "laporan" ? "bg-base-900 text-ink shadow-sm" : "text-ink-muted"}`}
        >
          Lacak laporan
        </Link>
        <Link
          href="/lacak?tab=kendaraan"
          role="tab"
          aria-selected={tab === "kendaraan"}
          className={`rounded-full py-2 text-center text-sm font-semibold ${tab === "kendaraan" ? "bg-base-900 text-ink shadow-sm" : "text-ink-muted"}`}
        >
          Cek kendaraan
        </Link>
      </div>
      <section className="warga-card p-5">
        {tab === "laporan" ? (
          <>
            <p className="mb-4 text-sm text-ink-muted">
              Masukkan nomor LP dan PIN yang diberikan petugas saat melapor. Hasilnya menampilkan
              tahap penanganan perkara Anda.
            </p>
            <TrackForm />
          </>
        ) : (
          <>
            <p className="mb-4 text-sm text-ink-muted">
              Sebelum membeli kendaraan bekas, periksa apakah plat atau nomor rangkanya tercatat
              dalam laporan kehilangan. Jawabannya hanya tercatat atau tidak.
            </p>
            <VehicleForm />
          </>
        )}
      </section>
    </div>
  );
}
