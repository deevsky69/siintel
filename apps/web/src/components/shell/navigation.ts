/*
 * 8 Oktober 2026, keputusan pemilik proyek: menu "Imbauan Publik" dan "Dokumen Intelijen"
 * dihapus dari navigasi. Halamannya (/imbauan, /intelijen) dan API-nya tidak dihapus —
 * imbauan yang beredar tetap dibaca aplikasi warga, dan dokumen intelijen tetap masuk
 * lewat formulir Input. Yang hilang hanya jalan masuknya dari menu.
 *
 * 10 November 2026 (2.ii): "Rencana Patroli" keluar dari menu; perkiraan bulan depannya
 * lampiran pada Produk Bulanan dan ikut penetapan Pimpinan.
 *
 * 12 November 2026, keputusan pemilik proyek (A, catatan 179): menu diringkas dari 20 ke
 * 12 submenu. Yang keluar dari menu tetap dapat dicapai sebagai TAB di layar induknya:
 *   Wilayah Rawan → (isinya = Peringkat)      Pola Gangguan → tab di Analitik
 *   Peringkat → tab di Produk Bulanan          Input Data, Pembakuan → tab di Laporan Petugas
 *   Pengaturan Sistem → hanya alamat (/ops/pengaturan), membaca bobot skor harian
 */
/**
 * Menu utama — kelompok dan submenu.
 *
 * Susunannya ditetapkan pemilik proyek, 2 September 2026: lima kelompok yang masing-masing
 * membuka submenu, menggantikan deret enam belas ikon setara yang sebelumnya memaksa mata
 * membaca seluruhnya untuk menemukan satu. Sejak 6 November 2026 kelompoknya mengikuti
 * **siklus bulanan**:
 *
 * ```text
 * Wilayah     →  keadaan wilayah: beranda, peta, analitik
 * Bulan Ini   →  produk bulanan (dengan peringkat dan lampiran), evaluasi cakupan
 * Data        →  apa yang masuk: laporan petugas, laporan masyarakat, perkara, darurat
 * Warga       →  Babinkamtibmas, buletin & imbauan, survey
 * Sistem      →  pengguna, audit
 * ```
 *
 * **Menyembunyikan menu bukan otorisasi.** Backend memeriksa setiap permintaan, dan
 * membuka alamat yang tersembunyi tetap dijawab sebagaimana mestinya (CLAUDE.md §15).
 */

export type NavItem = {
  href: string;
  label: string;
  /** Nama ikon pada `components/shell/icons.tsx`. */
  icon: string;
  /**
   * Submenu tampil bila pengguna memegang **salah satu** permission ini.
   *
   * Berisi permission yang membuat layarnya bermakna — bukan seluruh yang mungkin dipakai
   * di dalamnya.
   */
  permissions: readonly string[];
  /** Keterangan satu baris, ditampilkan sebagai `title` pada tautannya. */
  hint?: string;
};

export type NavGroup = {
  id: string;
  label: string;
  icon: string;
  items: readonly NavItem[];
};

export const NAV_GROUPS: readonly NavGroup[] = [
  {
    id: "pemantauan",
    label: "Wilayah",
    icon: "map",
    items: [
      {
        href: "/ops",
        label: "Beranda",
        icon: "dashboard",
        permissions: ["dashboard:read"],
        hint: "Papan bulan ini dan peta",
      },
      {
        href: "/ops/peta",
        label: "Peta",
        icon: "map",
        permissions: ["map:read"],
        hint: "Peta historis dan kelurahan prioritas bulan ini",
      },
      {
        href: "/ops/analitik",
        label: "Analitik",
        icon: "analytics",
        permissions: ["analytics:read"],
        hint: "Tren, pola waktu, perbandingan wilayah; tab Pola Gangguan",
      },
    ],
  },
  {
    id: "bulanan",
    label: "Bulan Ini",
    icon: "recommendation",
    items: [
      {
        href: "/ops/produk-bulanan",
        label: "Produk Bulanan",
        icon: "recommendation",
        permissions: ["monthly_product:read"],
        hint: "Analis menyusun & memeriksa, Pimpinan menetapkan, Fungsi/Polsek mencatat; tab Peringkat",
      },
      {
        href: "/ops/evaluasi-bulanan",
        label: "Evaluasi",
        icon: "evaluation",
        permissions: ["evaluation:read"],
        hint: "Cakupan kejadian di kelurahan pilihan",
      },
    ],
  },
  {
    id: "laporan",
    label: "Data",
    icon: "entry",
    items: [
      {
        href: "/ops/laporan-petugas",
        label: "Laporan Petugas",
        icon: "entry",
        permissions: ["crime:read"],
        hint: "Kejadian yang dicatat petugas; tab Catat kejadian dan Pembakuan",
      },
      {
        href: "/ops/masyarakat",
        label: "Laporan Masyarakat",
        icon: "community",
        permissions: ["citizen_report:read"],
        hint: "Laporan dari kanal publik, triase di tempat",
      },
      {
        href: "/ops/perkara",
        label: "Berkas Perkara",
        icon: "feed",
        permissions: ["case_file:read"],
        hint: "Tahap perkara yang dilacak warga",
      },
      {
        href: "/ops/panic",
        label: "Panic Button",
        icon: "panic",
        permissions: ["panic:read"],
        hint: "Permintaan bantuan darurat",
      },
    ],
  },
  {
    id: "warga",
    label: "Warga",
    icon: "community",
    items: [
      {
        href: "/ops/babin",
        label: "Babinkamtibmas",
        icon: "community",
        permissions: ["babin:read"],
        hint: "Kontak Babin per kelurahan",
      },
      {
        href: "/ops/buletin",
        label: "Buletin & Imbauan",
        icon: "brief",
        permissions: ["bulletin:read"],
        hint: "Buletin mingguan menunggu persetujuan Pimpinan; imbauan bulanan otomatis",
      },
      {
        href: "/ops/survey",
        label: "Survey Rasa Aman",
        icon: "community",
        permissions: ["review:moderate"],
        hint: "Ulasan warga yang menunggu moderasi",
      },
    ],
  },
  {
    id: "sistem",
    label: "Sistem",
    icon: "admin",
    items: [
      {
        href: "/ops/admin",
        label: "Manajemen Pengguna",
        icon: "admin",
        permissions: ["user:read", "user:manage", "role:manage"],
        hint: "Akun dan peran",
      },
      {
        href: "/ops/audit",
        label: "Audit Log",
        icon: "audit",
        permissions: ["audit:read"],
        hint: "Jejak siapa melakukan apa",
      },
    ],
  },
] as const;

/** Seluruh submenu, tanpa kelompoknya — dipakai pengujian dan pencarian rute. */
export const NAV_ITEMS: readonly NavItem[] = NAV_GROUPS.flatMap((group) => group.items);

/**
 * Kelompok beserta submenu yang pantas ditampilkan kepada pemegang `held`.
 *
 * Kelompok yang tidak menyisakan satu pun submenu dibuang seluruhnya — judul kelompok
 * yang membuka daftar kosong hanya menjanjikan sesuatu yang tidak ada.
 *
 * Kewenangan kosong menghasilkan menu kosong, **bukan** seluruh menu: kegagalan memuat
 * profil tidak boleh berubah menjadi sidebar yang menjanjikan lebih banyak daripada yang
 * dapat dibuka. Tidak ada yang bocor dengan bersikap ketat, sebab ini bukan otorisasi.
 */
export function visibleNavGroups(held: readonly string[]): NavGroup[] {
  const owned = new Set(held);
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.permissions.some((name) => owned.has(name))),
  })).filter((group) => group.items.length > 0);
}

/** Submenu saja, rata — untuk pencarian rute dan pengujian. */
export function visibleNavItems(held: readonly string[]): NavItem[] {
  return visibleNavGroups(held).flatMap((group) => group.items);
}

/**
 * Kelompok yang memuat rute aktif; `null` bila rutenya tidak ada di menu.
 *
 * Beranda (`/ops`) dicocokkan persis: setiap rute lain diawali `/ops`, dan pencocokan
 * awalan akan membuat kelompok pertama selalu terbuka.
 */
/**
 * Layar yang keluar dari menu tetapi tetap milik sebuah kelompok (dicapai lewat tab atau
 * alamat): kelompoknya tetap terbuka supaya pengguna tahu posisinya.
 */
const OFF_MENU_GROUP: ReadonlyArray<readonly [string, string]> = [
  ["/ops/wilayah", "pemantauan"],
  ["/ops/pola", "pemantauan"],
  ["/ops/peringkat", "bulanan"],
  ["/ops/rencana-patroli", "bulanan"],
  ["/ops/input", "laporan"],
  ["/ops/pembakuan", "laporan"],
  ["/ops/pengaturan", "sistem"],
];

export function groupOf(pathname: string): string | null {
  const path = pathname.split("?")[0];
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (item.href === "/ops" ? path === "/ops" : path.startsWith(item.href)) {
        return group.id;
      }
    }
  }
  for (const [prefix, id] of OFF_MENU_GROUP) {
    if (path.startsWith(prefix)) return id;
  }
  return null;
}
