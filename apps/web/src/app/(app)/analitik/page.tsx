import { RoadmapPage } from "@/components/roadmap";

export default function AnalyticsPage() {
  return (
    <RoadmapPage
      title="Analytics"
      purpose="Analisis pola kejahatan lintas waktu dan wilayah: Crime Pattern DNA, keterkaitan antar jenis ancaman, pergeseran musiman, dan ekspor untuk bahan analisis. Bagian tren dasarnya sudah tampil di Executive Dashboard."
      tasks={[
        {
          code: "TASK 090-094",
          detail: "Crime Pattern DNA, analisis korelasi spasial-temporal, deteksi pergeseran pola",
        },
        {
          code: "TASK 035",
          detail: "Endpoint analitik beserta ekspor (`analytics:read`, `analytics:export`)",
        },
      ]}
      ready={[
        {
          label: "Crime Pattern DNA — where, when, how, target, repeat per jenis gangguan",
          href: "/pola",
        },
        {
          label: "2.019 sel risiko per kecamatan, jenis ancaman, dan jendela waktu",
          href: "/peta",
        },
        { label: "Tren kejadian per bulan pada dashboard", href: "/" },
        { label: "Permission `analytics:read` dan `analytics:export` sudah ada di katalog RBAC" },
      ]}
    />
  );
}
