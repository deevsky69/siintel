import { RoadmapPage } from "@/components/roadmap";

export default function PredictionPage() {
  return (
    <RoadmapPage
      title="Prediction Engine"
      purpose="Menjalankan dan memantau siklus prediksi: memilih horizon, menjalankan model, meninjau hasil sebelum dipublikasikan, dan membandingkannya dengan siklus sebelumnya. Saat ini prediksi sudah ada di database dan dapat dilihat pada peta serta Warning Center, tetapi menjalankannya masih lewat proses seed — belum dari layar."
      tasks={[
        {
          code: "TASK 100-104",
          detail:
            "Model machine learning sungguhan: rekayasa fitur, pelatihan, validasi silang, dan penyimpanan versi model",
        },
        {
          code: "TASK 039",
          detail:
            "Endpoint menjalankan prediksi (`prediction:run`) dan mempublikasikannya (`prediction:publish`)",
        },
        { code: "TASK 105", detail: "Layar peninjauan hasil sebelum publikasi" },
      ]}
      ready={[
        { label: "180 prediksi dengan faktor dominan dan sumbernya (RULE/MODEL)", href: "/peta" },
        { label: "Peringatan dini yang lahir dari prediksi", href: "/peringatan" },
        { label: "Metrik precision dan recall untuk menilai mutu prediksi", href: "/evaluasi" },
        { label: "Permission `prediction:run` dan `prediction:publish` sudah ada di katalog RBAC" },
      ]}
    />
  );
}
