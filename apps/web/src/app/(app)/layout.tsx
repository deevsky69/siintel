import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { getProfile } from "@/lib/dashboard";

/**
 * Shell untuk seluruh halaman aplikasi.
 *
 * Halaman masuk berada di luar grup ini karena tidak boleh menampilkan sidebar maupun
 * identitas pengguna.
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const profile = await getProfile();

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Topbar name={profile.full_name ?? profile.username} roleName={profile.role} />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-auto p-4">{children}</main>
      </div>
    </div>
  );
}
