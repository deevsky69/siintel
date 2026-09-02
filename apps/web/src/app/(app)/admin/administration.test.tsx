import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  assignmentSummary,
  groupByResource,
  missingScopeAttributes,
  type RoleCatalogue,
  type RoleRow,
  type UserDirectory,
  type UserRow,
} from "@/lib/administration";
import { AdminBoard } from "./admin-board";

/**
 * Yang diuji di sini adalah janji-janji layar administrasi, bukan tampilannya:
 *
 * - tidak ada kolom password di mana pun, dan alasannya terbaca beserta perintahnya;
 * - keterbatasan (tidak membuat, tidak menghapus, peran tidak dapat disunting)
 *   dinyatakan, bukan disembunyikan;
 * - penugasan yang tidak lengkap terlihat sebagai peringatan, bukan sebagai tanda hubung;
 * - formulir hilang bagi akun tanpa `user:manage`.
 */

// Formulir memanggil server action; di sini yang diuji papan administrasinya.
vi.mock("./assignment-form", () => ({
  AssignmentForm: ({ isSelf }: { isSelf: boolean }) => (
    <button type="button">{isSelf ? "Formulir (akun sendiri)" : "Simpan Penugasan"}</button>
  ),
}));

const pimpinanRole: RoleRow = {
  code: "ROLE-01",
  role_name: "Pimpinan",
  level: 1,
  user_count: 1,
  active_user_count: 1,
  permission_count: 3,
  scopes: { ALL: 3 },
  permissions: [
    { permission: "commander_decision:approve", scope: "ALL" },
    { permission: "commander_decision:read", scope: "ALL" },
    { permission: "evaluation:run", scope: "ALL" },
  ],
  can_approve: true,
};

const polsekRole: RoleRow = {
  code: "ROLE-05",
  role_name: "Polsek",
  level: 5,
  user_count: 1,
  active_user_count: 1,
  permission_count: 2,
  scopes: { ALL: 1, OWN_JURISDICTION: 1 },
  permissions: [
    { permission: "location:read", scope: "ALL" },
    { permission: "crime:read", scope: "OWN_JURISDICTION" },
  ],
  can_approve: false,
};

const adminRole: RoleRow = {
  code: "ROLE-06",
  role_name: "Administrator",
  level: 6,
  user_count: 3,
  active_user_count: 3,
  permission_count: 1,
  scopes: { ALL: 1 },
  permissions: [{ permission: "user:manage", scope: "ALL" }],
  can_approve: false,
};

const pimpinan: UserRow = {
  code: "USER-001",
  username: "demo.pimpinan",
  full_name: "Pejabat Demo",
  role_code: "ROLE-01",
  role: "Pimpinan",
  role_level: 1,
  polsek: null,
  function: null,
  status: "ACTIVE",
  credential_locked: false,
  must_change_password: false,
  last_login_at: "2025-12-31T14:00:00+00:00",
};

const polsek: UserRow = {
  ...pimpinan,
  code: "USER-005",
  username: "demo.polsek",
  full_name: "Petugas Polsek",
  role_code: "ROLE-05",
  role: "Polsek",
  role_level: 5,
  polsek: "Polsek Tebet",
  last_login_at: null,
};

/** Akun rusak: peran ber-cakupan tanpa atributnya. */
const broken: UserRow = { ...polsek, code: "USER-009", username: "uji.rusak", polsek: null };

const locked: UserRow = {
  ...pimpinan,
  code: "USER-010",
  username: "uji.terkunci",
  role_code: "ROLE-06",
  role: "Administrator",
  role_level: 6,
  credential_locked: true,
  must_change_password: true,
};

const directory: UserDirectory = {
  data: [pimpinan, polsek, broken, locked],
  editable_fields: ["role_code", "polsek", "function", "status"],
  credential_basis:
    "Password hanya ditetapkan lewat perintah di server: `pnpm user:password -- <username>`.",
  lifecycle_basis: "Layar ini hanya memindahkan penugasan; tidak membuat dan tidak menghapus.",
  polsek_options: ["Polsek Tebet"],
  function_options: [{ value: "RESKRIM", label: "Reskrim" }],
  status_options: [
    { value: "ACTIVE", label: "Aktif" },
    { value: "INACTIVE", label: "Nonaktif" },
  ],
};

const catalogue: RoleCatalogue = {
  data: [pimpinanRole, polsekRole, adminRole],
  editable: false,
  source_basis: "Sumbernya `config/rbac/permissions.yaml`, diselaraskan seed.",
};

function board(overrides: Partial<Parameters<typeof AdminBoard>[0]> = {}) {
  return (
    <AdminBoard
      directory={directory}
      catalogue={catalogue}
      selected={polsek}
      canManage
      currentUserCode="USER-010"
      {...overrides}
    />
  );
}

describe("layar administrasi", () => {
  it("tidak pernah menawarkan kolom password, dan menyebut jalur yang benar", () => {
    const { container } = render(board());

    expect(container.querySelector('input[type="password"]')).toBeNull();
    expect(screen.getAllByText(/pnpm user:password/).length).toBeGreaterThan(0);
  });

  it("menyatakan keterbatasannya, bukan menyembunyikannya", () => {
    render(board());

    expect(screen.getByText(directory.lifecycle_basis)).toBeTruthy();
    expect(screen.getByText(catalogue.source_basis)).toBeTruthy();
  });

  it("menandai akun yang kredensialnya belum ditetapkan", () => {
    render(board());

    expect(screen.getAllByText("Kredensial terkunci")).toHaveLength(1);
    expect(screen.getAllByText("Kredensial aktif")).toHaveLength(3);
  });

  it("menyoroti penugasan yang tidak lengkap", () => {
    render(board());

    // Peran Polsek tanpa wilayah — akun yang akan ditolak setiap endpoint ber-cakupan.
    expect(screen.getByText(/peran Polsek membutuhkan Polsek/)).toBeTruthy();
  });

  it("mengunci formulir peran saat pengguna membuka penugasannya sendiri", () => {
    render(board({ selected: locked, currentUserCode: locked.code }));

    expect(screen.getByRole("button", { name: "Formulir (akun sendiri)" })).toBeTruthy();
  });

  it("menghilangkan formulir bagi akun tanpa user:manage", () => {
    render(board({ canManage: false }));

    expect(screen.queryByRole("button", { name: "Simpan Penugasan" })).toBeNull();
    expect(screen.getByText(/tidak memegang/)).toBeTruthy();
  });

  it("menunjukkan peran yang berwenang menyetujui, dan jumlah pemegangnya", () => {
    render(board());

    expect(screen.getByText("Menyetujui rekomendasi")).toBeTruthy();
    const pimpinanCard = screen.getByText("Pimpinan").closest("li");
    expect(pimpinanCard).not.toBeNull();
    expect(within(pimpinanCard as HTMLElement).getByText(/1 pemegang aktif/)).toBeTruthy();
  });

  it("menampilkan keadaan kosong, bukan tabel tanpa baris", () => {
    render(board({ directory: { ...directory, data: [] }, selected: null }));

    expect(screen.getByText("Belum ada pengguna dalam cakupan akun Anda.")).toBeTruthy();
    expect(screen.getByText("Pilih seorang pengguna untuk melihat penugasannya.")).toBeTruthy();
  });
});

describe("penyajian penugasan", () => {
  it("menyatakan cakupan dalam kalimat, termasuk saat tidak dibatasi", () => {
    expect(assignmentSummary(polsek)).toBe("Wilayah Polsek Tebet");
    expect(assignmentSummary(pimpinan)).toBe("Tanpa batas wilayah atau fungsi");
  });

  it("mengenali atribut cakupan yang kurang dari scope perannya, bukan dari namanya", () => {
    expect(missingScopeAttributes(broken, polsekRole)).toEqual(["Polsek"]);
    expect(missingScopeAttributes(polsek, polsekRole)).toEqual([]);
    // Peran tanpa pemberian ber-cakupan tidak menuntut atribut apa pun.
    expect(missingScopeAttributes(pimpinan, pimpinanRole)).toEqual([]);
    // Tanpa katalog peran, layar tidak boleh menebak-nebak.
    expect(missingScopeAttributes(broken, undefined)).toEqual([]);
  });

  it("mengelompokkan kewenangan menurut resource tanpa mengubah isinya", () => {
    const grouped = groupByResource(pimpinanRole.permissions);

    expect(grouped).toEqual([
      {
        resource: "commander_decision",
        actions: [
          { action: "approve", scope: "ALL" },
          { action: "read", scope: "ALL" },
        ],
      },
      { resource: "evaluation", actions: [{ action: "run", scope: "ALL" }] },
    ]);
  });
});
