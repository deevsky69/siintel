/**
 * Menu utama — kelompok dan submenu.
 *
 * Susunannya ditetapkan pemilik proyek, 2 September 2026: lima kelompok yang masing-masing
 * membuka submenu, menggantikan deret enam belas ikon setara yang sebelumnya memaksa mata
 * membaca seluruhnya untuk menemukan satu.
 *
 * Kelompoknya disusun mengikuti **alur kerja**, bukan jenis data:
 *
 * ```text
 * Pemantauan  →  apa yang sedang terjadi
 * Laporan     →  apa yang masuk
 * Analisis    →  apa artinya
 * Operasi     →  apa yang dikerjakan
 * Sistem      →  siapa melakukan apa
 * ```
 *
 * Beberapa layar yang tidak disebut dalam permintaan tetap dimasukkan ke kelompok yang
 * paling sesuai — Prediksi, Penilaian Risiko, Evaluasi, Peringatan, Rekomendasi, Brief.
 * Menghilangkannya dari menu akan memutus rantai tertutup yang menjadi inti sistem ini
 * (CLAUDE.md §9): tanpa Prediksi dan Evaluasi, tidak ada yang dapat menunjukkan bahwa
 * ramalannya pernah diuji terhadap kenyataan.
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
   * di dalamnya. `Input Data` menuntut salah satu izin **tulis**: tanpa satu pun, seluruh
   * formulirnya tersembunyi dan yang tersisa hanya penjelasan mengapa layar itu kosong.
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
    label: "Pemantauan",
    icon: "dashboard",
    items: [
      {
        href: "/",
        label: "Beranda",
        icon: "dashboard",
        permissions: ["dashboard:read"],
        hint: "Ringkasan keadaan hari ini",
      },
      {
        href: "/informasi",
        label: "Informasi Terbaru",
        icon: "feed",
        // Menggabungkan tiga jenis catatan, jadi cukup salah satunya untuk bermakna.
        permissions: ["crime:read", "citizen_report:read", "intelligence:read"],
        hint: "Laporan dan kejadian terbaru dari seluruh kanal",
      },
      {
        href: "/peta",
        label: "Peta",
        icon: "map",
        permissions: ["map:read"],
        hint: "Historis, risiko berjalan, dan prediktif",
      },
      {
        href: "/peringatan",
        label: "Peringatan Dini",
        icon: "warning",
        permissions: ["warning:read"],
        hint: "Peringatan yang menunggu tindakan",
      },
      {
        href: "/imbauan",
        label: "Imbauan Publik",
        icon: "community",
        // `public_alert:read`, bukan `:publish`: yang tidak dapat menerbitkan tetap
        // berhak melihat apa yang sedang beredar atas nama satuannya.
        permissions: ["public_alert:read"],
        hint: "Yang sudah diumumkan kepada masyarakat",
      },
    ],
  },
  {
    id: "laporan",
    label: "Laporan",
    icon: "community",
    items: [
      {
        href: "/masyarakat",
        label: "Laporan Masyarakat",
        icon: "community",
        permissions: ["citizen_report:read"],
        hint: "Laporan yang masuk lewat kanal publik",
      },
      {
        href: "/laporan-petugas",
        label: "Laporan Petugas",
        icon: "entry",
        permissions: ["crime:read"],
        hint: "Kejadian yang dicatat petugas",
      },
      {
        href: "/panic",
        label: "Panic Button",
        icon: "panic",
        permissions: ["citizen_report:read"],
        hint: "Permintaan bantuan darurat",
      },
      {
        href: "/input",
        label: "Input Data",
        icon: "write",
        permissions: ["crime:write", "intelligence:write", "citizen_report:write"],
        hint: "Mencatat kejadian, laporan intelijen, dan triase",
      },
    ],
  },
  {
    id: "analisis",
    label: "Analisis",
    icon: "analytics",
    items: [
      {
        href: "/analitik",
        label: "Analitik",
        icon: "analytics",
        permissions: ["analytics:read"],
        hint: "Tren bulanan, pola waktu, perbandingan wilayah",
      },
      {
        href: "/wilayah",
        label: "Wilayah Rawan",
        icon: "area",
        permissions: ["risk_score:read"],
        hint: "Peringkat wilayah beserta rincian datanya",
      },
      {
        href: "/pola",
        label: "Pola Gangguan",
        icon: "pattern",
        permissions: ["analytics:read"],
        hint: "Crime Pattern DNA per jenis gangguan",
      },
      {
        href: "/prediksi",
        label: "Prediksi",
        icon: "prediction",
        permissions: ["prediction:read"],
        hint: "Prediksi per horizon beserta faktor dominannya",
      },
      {
        href: "/skoring",
        label: "Penilaian Risiko",
        icon: "scoring",
        permissions: ["risk_score:read"],
        hint: "Skor risiko beserta bobot yang menghasilkannya",
      },
      {
        href: "/evaluasi",
        label: "Evaluasi",
        icon: "evaluation",
        permissions: ["evaluation:read"],
        hint: "Prediksi dibandingkan kejadian sebenarnya",
      },
    ],
  },
  {
    id: "operasi",
    label: "Operasi",
    icon: "operation",
    items: [
      {
        href: "/operasi",
        label: "Operasi & Penugasan",
        icon: "operation",
        permissions: ["operation:read"],
        hint: "Tindakan yang dijalankan dan hasilnya",
      },
      {
        href: "/rekomendasi",
        label: "Rekomendasi & Keputusan",
        icon: "recommendation",
        permissions: ["recommendation:read"],
        hint: "Usulan tindakan dan keputusan komandan",
      },
      {
        href: "/intelijen",
        label: "Dokumen Intelijen",
        icon: "intelligence",
        permissions: ["intelligence:read"],
        hint: "Laporan intelijen beserta keandalannya",
      },
      {
        href: "/brief",
        label: "Brief Pimpinan",
        icon: "brief",
        permissions: ["dashboard:read"],
        hint: "Ringkasan siap cetak sebelum apel",
      },
    ],
  },
  {
    id: "sistem",
    label: "Sistem",
    icon: "admin",
    items: [
      {
        href: "/admin",
        label: "Manajemen Pengguna",
        icon: "admin",
        permissions: ["user:read", "user:manage", "role:manage"],
        hint: "Akun, peran, dan kewenangannya",
      },
      {
        href: "/audit",
        label: "Audit Log",
        icon: "audit",
        permissions: ["audit:read"],
        hint: "Jejak siapa melakukan apa",
      },
      {
        href: "/pengaturan",
        label: "Pengaturan Sistem",
        icon: "settings",
        permissions: ["config:read", "config:manage"],
        hint: "Bobot, ambang, dan taksonomi yang sedang berlaku",
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

/** Submenu yang terlihat, tanpa kelompoknya. */
export function visibleNavItems(held: readonly string[]): NavItem[] {
  return visibleNavGroups(held).flatMap((group) => group.items);
}

/**
 * Kelompok yang memuat rute tertentu — dipakai membuka kelompok yang sedang aktif.
 *
 * Beranda (`/`) dicocokkan persis; sisanya dengan awalan, supaya rute turunan seperti
 * `/wilayah/Tebet` tetap dikenali sebagai bagian dari submenunya.
 */
export function groupOf(pathname: string): string | null {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
      if (active) return group.id;
    }
  }
  return null;
}
