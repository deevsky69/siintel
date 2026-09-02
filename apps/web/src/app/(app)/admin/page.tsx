import { Panel } from "@/components/panel";
import {
  getRoles,
  getSessionProfile,
  getUsers,
  type RoleCatalogue,
  type UserDirectory,
} from "@/lib/administration";
import { ApiError } from "@/lib/api";
import { AdminBoard } from "./admin-board";

export const dynamic = "force-dynamic";

/**
 * Administrasi — pengguna, peran, dan kewenangan (TASK 143).
 *
 * Satu-satunya menu yang seluruh mekanismenya sudah berjalan di backend sejak TASK 015
 * dan TASK 052, tetapi belum pernah punya antarmuka. Yang ditambahkan di sini hanyalah
 * pintu masuknya — bukan kewenangan baru.
 *
 * Keadaan "tidak berwenang" ditangani di sini, bukan dilempar ke `error.tsx`: peran
 * selain Administrator memang tidak memegang `user:read`, dan itu keadaan yang benar,
 * bukan kegagalan yang perlu dicoba ulang (CLAUDE.md §23).
 */
export default async function AdministrationPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const requested = typeof params.dipilih === "string" ? params.dipilih : null;

  const profile = await getSessionProfile();

  let directory: UserDirectory;
  let catalogue: RoleCatalogue;
  try {
    [directory, catalogue] = await Promise.all([getUsers(), getRoles()]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      return <Unauthorized role={profile.role} />;
    }
    throw error;
  }

  const selected = directory.data.find((user) => user.code === requested) ?? null;

  return (
    <AdminBoard
      directory={directory}
      catalogue={catalogue}
      selected={selected}
      // Menyembunyikan formulir hanyalah kenyamanan; backend tetap yang menolak.
      canManage={profile.permissions.includes("user:manage")}
      currentUserCode={profile.code}
    />
  );
}

/** Keadaan tidak berwenang — dinyatakan, bukan disamarkan sebagai daftar kosong. */
function Unauthorized({ role }: { role: string }) {
  return (
    <div className="mx-auto max-w-2xl">
      <Panel title="Administrasi">
        <div className="rounded border border-risk-moderate/40 bg-risk-moderate/5 px-4 py-3">
          <div className="stat-label text-risk-moderate">Tidak berwenang</div>
          <p className="mt-1 text-sm leading-relaxed text-ink">
            Peran {role} tidak memegang <code>user:read</code>, sehingga daftar pengguna dan peran
            tidak dapat ditampilkan. Permintaan ditolak backend dan percobaannya tercatat pada audit
            trail.
          </p>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-ink-muted">
          Pengelolaan pengguna dipegang peran Administrator. Pemisahan ini disengaja: kewenangan
          yang memberikan kewenangan tidak diberikan kepada peran yang memutuskan tindakan
          operasional.
        </p>
      </Panel>
    </div>
  );
}
