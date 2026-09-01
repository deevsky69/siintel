/** Menu utama, mengikuti sidebar pada referensi visual `design/gambaran-website.png`. */
export type NavItem = {
  href: string;
  label: string;
  /** Nama ikon pada `components/shell/icons.tsx`. */
  icon: string;
};

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/peta", label: "Live Map", icon: "map" },
  { href: "/prediksi", label: "Prediction", icon: "prediction" },
  { href: "/peringatan", label: "Early Warning", icon: "warning" },
  { href: "/analitik", label: "Analytics", icon: "analytics" },
  { href: "/rekomendasi", label: "Recommendation", icon: "recommendation" },
  { href: "/evaluasi", label: "Evaluation", icon: "evaluation" },
  { href: "/intelijen", label: "Intelligence", icon: "intelligence" },
  { href: "/admin", label: "Admin", icon: "admin" },
] as const;
