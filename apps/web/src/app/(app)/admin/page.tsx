import { RoadmapPage } from "@/components/roadmap";

export default function AdministrasiPage() {
  return (
    <RoadmapPage
      title="Administrasi"
      purpose="Pengelolaan pengguna, peran, dan kewenangan dari layar, serta penelusuran audit trail. Seluruh mekanismenya sudah berjalan di backend — yang belum ada hanyalah antarmukanya; penetapan password bahkan sengaja hanya lewat perintah di server."
      tasks={[
        { code: "TASK 140-142", detail: "Layar pengguna, peran, dan penelusuran audit" },
        {
          code: "TASK 143",
          detail: "Endpoint pengelolaan pengguna (`user:manage`, `role:manage`)",
        },
      ]}
      ready={[
        { label: "6 peran dengan 43 permission dan 146 pemberian kewenangan, ditegakkan di query" },
        { label: "Audit trail append-only yang juga mencatat penolakan otorisasi" },
        {
          label:
            "Penetapan password lewat `pnpm user:password` — tidak pernah lewat kode atau seed",
        },
        {
          label: "Cakupan wilayah terbukti: Polsek melihat 13 dari 84 rekomendasi",
          href: "/rekomendasi",
        },
      ]}
    />
  );
}
