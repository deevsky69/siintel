import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { getPendingDecisionCount, getProfile } from "@/lib/dashboard";

/**
 * Shell untuk seluruh halaman aplikasi.
 *
 * Halaman masuk berada di luar grup ini karena tidak boleh menampilkan sidebar maupun
 * identitas pengguna.
 *
 * Menu disaring menurut permission yang benar-benar dipegang pengguna. Itu **kenyamanan,
 * bukan otorisasi**: backend tetap memeriksa setiap permintaan (CLAUDE.md §15).
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const profile = await getProfile();

  // Lencana hanya bermakna bagi yang dapat memutuskan. Bagi peran lain, rekomendasi yang
  // menunggu bukan pekerjaan mereka — angka yang tidak dapat mereka selesaikan hanya
  // menjadi kecemasan tanpa jalan keluar.
  const canDecide = profile.permissions.includes("commander_decision:approve");
  const pendingDecisions = canDecide ? await countPending() : 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Topbar name={profile.full_name ?? profile.username} roleName={profile.role} />
      <div className="flex min-h-0 flex-1">
        <Sidebar permissions={profile.permissions} pendingDecisions={pendingDecisions} />
        <main className="min-w-0 flex-1 overflow-auto p-4">{children}</main>
      </div>
    </div>
  );
}

/**
 * Jumlah rekomendasi tertunda, atau 0 bila tidak dapat diambil.
 *
 * Kegagalan di sini **tidak boleh menjatuhkan seluruh shell**: lencana adalah penanda
 * tambahan, dan halaman yang gagal dimuat seluruhnya karena satu angka hiasan jauh lebih
 * merugikan daripada lencana yang tidak muncul.
 */
async function countPending(): Promise<number> {
  try {
    return await getPendingDecisionCount();
  } catch {
    return 0;
  }
}
