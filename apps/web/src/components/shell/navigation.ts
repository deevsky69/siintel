/** Menu utama, mengikuti sidebar pada referensi visual `design/gambaran-website.png`. */
export type NavItem = {
  href: string;
  label: string;
  /** Nama ikon pada `components/shell/icons.tsx`. */
  icon: string;
};

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  // Executive Brief diletakkan tepat setelah Dashboard: ia ringkasan yang dibaca
  // pimpinan lebih dulu, sebelum menelusuri layar lain.
  { href: "/brief", label: "Brief", icon: "brief" },
  { href: "/peta", label: "Live Map", icon: "map" },
  { href: "/prediksi", label: "Prediction", icon: "prediction" },
  { href: "/peringatan", label: "Early Warning", icon: "warning" },
  // Penilaian risiko diletakkan sebelum Pattern DNA: ia yang menghasilkan skor
  // yang dipakai peta, peringatan, dan prediksi.
  { href: "/skoring", label: "Risk Scoring", icon: "scoring" },
  { href: "/pola", label: "Pattern DNA", icon: "pattern" },
  { href: "/analitik", label: "Analytics", icon: "analytics" },
  { href: "/rekomendasi", label: "Recommendation", icon: "recommendation" },
  // Ditempatkan setelah Recommendation dan sebelum Evaluation supaya urutan menu
  // mengikuti rantai tertutup: keputusan → tindakan → hasil nyata → evaluasi.
  { href: "/operasi", label: "Operations", icon: "operation" },
  { href: "/evaluasi", label: "Evaluation", icon: "evaluation" },
  // Pintu masuk data diletakkan sebelum Admin: ia pekerjaan harian petugas,
  // bukan pengaturan sistem.
  { href: "/input", label: "Data Entry", icon: "entry" },
  { href: "/masyarakat", label: "Community", icon: "community" },
  { href: "/intelijen", label: "Intelligence", icon: "intelligence" },
  { href: "/admin", label: "Admin", icon: "admin" },
] as const;
