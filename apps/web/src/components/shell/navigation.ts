/**
 * Menu utama.
 *
 * Dua hal yang berubah pada 2 September 2026, keduanya menjawab keluhan yang sama —
 * layar pimpinan memuat terlalu banyak hal untuk dibaca:
 *
 * 1. **Menu disaring menurut kewenangan.** Sebelumnya keenambelas menu tampil kepada semua
 *    peran. Seorang Pimpinan yang membuka `Data Entry` atau `Admin` hanya disambut kalimat
 *    "Akun Anda tidak memiliki kewenangan" — menu yang tidak pernah dapat dipakai, tetapi
 *    tetap menuntut perhatian setiap kali sidebar dibaca.
 *
 * 2. **Menu dikelompokkan menurut kata kerja**, bukan dideret rata. Enam belas ikon setara
 *    memaksa mata membaca seluruhnya untuk menemukan satu; empat kelompok pendek dapat
 *    dilompati.
 *
 * **Menyembunyikan menu bukan otorisasi.** Backend tetap memeriksa setiap permintaan, dan
 * membuka alamatnya langsung tetap dijawab sebagaimana mestinya (CLAUDE.md §15, §21).
 * Penyaringan di sini semata mengurangi apa yang harus dibaca.
 */

export type NavItem = {
  href: string;
  label: string;
  /** Nama ikon pada `components/shell/icons.tsx`. */
  icon: string;
  /**
   * Menu tampil bila pengguna memegang **salah satu** permission ini.
   *
   * Berisi permission yang membuat layarnya bermakna — bukan seluruh permission yang
   * mungkin dipakai di dalamnya. `Data Entry` misalnya menuntut salah satu izin **tulis**:
   * tanpa satu pun di antaranya, seluruh formulirnya tersembunyi dan yang tersisa hanya
   * penjelasan mengapa layar itu kosong.
   */
  permissions: readonly string[];
  group: NavGroup;
};

export type NavGroup = "pantau" | "putuskan" | "telaah" | "data" | "sistem";

export const NAV_GROUPS: ReadonlyArray<{ id: NavGroup; label: string }> = [
  { id: "putuskan", label: "Putuskan" },
  { id: "pantau", label: "Pantau" },
  { id: "telaah", label: "Telaah" },
  { id: "data", label: "Data" },
  { id: "sistem", label: "Sistem" },
] as const;

export const NAV_ITEMS: readonly NavItem[] = [
  // --- Putuskan: yang menuntut tindakan seseorang, bukan sekadar dibaca. ---------------
  //
  // Kelompok ini diletakkan **paling atas** dengan sengaja. Bagi Pimpinan, `Keputusan`
  // adalah satu-satunya menu yang memuat sesuatu yang hanya dapat diselesaikan olehnya
  // (`commander_decision:approve`); sebelumnya ia berada di urutan kesembilan, tanpa satu
  // pun penanda bahwa ada yang menunggu di dalamnya.
  {
    href: "/rekomendasi",
    label: "Keputusan",
    icon: "recommendation",
    permissions: ["recommendation:read"],
    group: "putuskan",
  },
  {
    href: "/peringatan",
    label: "Peringatan",
    icon: "warning",
    permissions: ["warning:read"],
    group: "putuskan",
  },
  {
    href: "/operasi",
    label: "Operasi",
    icon: "operation",
    permissions: ["operation:read"],
    group: "putuskan",
  },

  // --- Pantau: keadaan sekarang. --------------------------------------------------------
  {
    href: "/",
    label: "Beranda",
    icon: "dashboard",
    permissions: ["dashboard:read"],
    group: "pantau",
  },
  {
    href: "/brief",
    label: "Brief",
    icon: "brief",
    permissions: ["dashboard:read"],
    group: "pantau",
  },
  { href: "/peta", label: "Peta", icon: "map", permissions: ["map:read"], group: "pantau" },

  // --- Telaah: ditelusuri saat ada pertanyaan, bukan dibaca tiap hari. ------------------
  {
    href: "/prediksi",
    label: "Prediksi",
    icon: "prediction",
    permissions: ["prediction:read"],
    group: "telaah",
  },
  {
    href: "/skoring",
    label: "Skoring",
    icon: "scoring",
    permissions: ["risk_score:read"],
    group: "telaah",
  },
  {
    href: "/pola",
    label: "Pola",
    icon: "pattern",
    permissions: ["analytics:read"],
    group: "telaah",
  },
  {
    href: "/analitik",
    label: "Analitik",
    icon: "analytics",
    permissions: ["analytics:read"],
    group: "telaah",
  },
  {
    href: "/evaluasi",
    label: "Evaluasi",
    icon: "evaluation",
    permissions: ["evaluation:read"],
    group: "telaah",
  },

  // --- Data: pekerjaan harian petugas. --------------------------------------------------
  {
    href: "/input",
    label: "Input Data",
    icon: "entry",
    // Menuntut izin **tulis**: tanpa satu pun, seluruh formulirnya tersembunyi.
    permissions: ["crime:write", "intelligence:write", "citizen_report:write"],
    group: "data",
  },
  {
    href: "/masyarakat",
    label: "Masyarakat",
    icon: "community",
    permissions: ["citizen_report:read"],
    group: "data",
  },
  {
    href: "/intelijen",
    label: "Intelijen",
    icon: "intelligence",
    permissions: ["intelligence:read"],
    group: "data",
  },

  // --- Sistem: pemeriksaan atas sistem, bukan pekerjaan operasional. --------------------
  {
    href: "/audit",
    label: "Audit",
    icon: "audit",
    permissions: ["audit:read"],
    group: "sistem",
  },
  {
    href: "/admin",
    label: "Admin",
    icon: "admin",
    permissions: ["user:read", "user:manage", "role:manage", "config:manage"],
    group: "sistem",
  },
] as const;

/**
 * Menu yang pantas ditampilkan kepada pemegang `held`.
 *
 * Daftar kosong menghasilkan menu kosong, **bukan** seluruh menu. Kegagalan memuat profil
 * tidak boleh berubah menjadi sidebar yang menjanjikan lebih banyak daripada yang dapat
 * dibuka — dan karena penyaringan ini bukan otorisasi, tidak ada yang bocor dengan
 * bersikap ketat di sini.
 */
export function visibleNavItems(held: readonly string[]): NavItem[] {
  const owned = new Set(held);
  return NAV_ITEMS.filter((item) => item.permissions.some((name) => owned.has(name)));
}

/** Menu terlihat, dikelompokkan dan urut sesuai `NAV_GROUPS`. Kelompok kosong dibuang. */
export function groupedNavItems(
  held: readonly string[],
): Array<{ group: NavGroup; label: string; items: NavItem[] }> {
  const visible = visibleNavItems(held);
  return NAV_GROUPS.map((group) => ({
    group: group.id,
    label: group.label,
    items: visible.filter((item) => item.group === group.id),
  })).filter((section) => section.items.length > 0);
}
