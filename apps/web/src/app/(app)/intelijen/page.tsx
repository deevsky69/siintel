import { RoadmapPage } from "@/components/roadmap";

export default function IntelligencePage() {
  return (
    <RoadmapPage
      title="Intelligence"
      purpose="Pengelolaan laporan intelijen dan laporan masyarakat: pencatatan, penilaian keandalan sumber, penautan ke kejadian dan prediksi, serta tindak lanjutnya. Datanya sudah ada di database dan ikut menjadi masukan penilaian risiko."
      tasks={[
        {
          code: "TASK 033",
          detail: "Endpoint laporan intelijen (`intelligence:read`, `intelligence:write`)",
        },
        {
          code: "TASK 024",
          detail: "Seed laporan masyarakat, pengumuman publik, dan umpan balik komunitas",
        },
        {
          code: "TASK 170-175",
          detail: "LAPOR PRESISI — aplikasi Android untuk laporan masyarakat",
        },
      ]}
      ready={[
        { label: "120 laporan intelijen tersimpan dan tertaut ke wilayah" },
        {
          label:
            "Tabel `citizen_reports`, `public_alerts`, dan `community_feedback` sudah bermigrasi",
        },
        {
          label:
            "Permission `intelligence:read` dan `intelligence:write` sudah ada di katalog RBAC",
        },
      ]}
    />
  );
}
