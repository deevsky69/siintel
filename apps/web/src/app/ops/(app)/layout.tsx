import { NotificationBell } from "@/components/shell/notification-bell";
import { PanicBanner } from "@/components/shell/panic-banner";
import { ShellFrame } from "@/components/shell/shell-frame";
import { Sidebar } from "@/components/shell/sidebar";
import { getProfile } from "@/lib/dashboard";
import { countAwaitingDecision } from "@/lib/monthly-products";
import { getNotifications } from "@/lib/notifications";
import { bellFeed } from "@/lib/notifications-shape";

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
  // Notifikasi tidak bergantung pada profil: dimulai bersamaan supaya tidak ada gelombang
  // tambahan (audit 15 November 2026). Lencana keputusan tetap menunggu profil karena hanya
  // bermakna bagi yang dapat memutuskan.
  const feedPromise = getNotifications().catch(() => null);
  const profile = await getProfile();

  // Lencana hanya bermakna bagi yang dapat memutuskan. Bagi peran lain, rekomendasi yang
  // menunggu bukan pekerjaan mereka — angka yang tidak dapat mereka selesaikan hanya
  // menjadi kecemasan tanpa jalan keluar.
  const canDecide = profile.permissions.includes("monthly_product:decide");
  const [pendingDecisions, feed] = await Promise.all([
    canDecide ? countAwaitingDecision().catch(() => 0) : Promise.resolve(0),
    // Kegagalan memuat antrean tidak boleh menjatuhkan seluruh shell: lonceng adalah
    // penanda tambahan, dan halaman yang gagal seluruhnya karena satu angka jauh lebih
    // merugikan daripada lonceng yang tidak muncul.
    feedPromise,
  ]);

  return (
    <ShellFrame
      name={profile.full_name ?? profile.username}
      roleName={profile.role}
      notifications={feed ? <NotificationBell feed={bellFeed(feed)} /> : null}
      sidebar={<Sidebar permissions={profile.permissions} pendingDecisions={pendingDecisions} />}
    >
      <PanicBanner feed={feed} />
      {children}
    </ShellFrame>
  );
}
