import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { tooltipRows } from "@/components/map/map-canvas";
import type { MapDistrict } from "@/lib/map-data";
import { board } from "./fixtures";
import { Highlights, Notables } from "./highlights";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

/**
 * Yang diuji di sini adalah **kepadatan informasi**, bukan tata letak.
 *
 * Keluhan yang memicu perubahan ini bukan "kurang bagus" melainkan "terlalu banyak
 * informasi sehingga bingung membacanya". Test yang hanya memeriksa keberadaan elemen
 * akan tetap hijau ketika kartunya perlahan tumbuh kembali menjadi laporan kecil — dan
 * pertumbuhan itu terjadi sedikit demi sedikit, tidak pernah dalam satu perubahan yang
 * kelihatan.
 */

const CARDS = ["Laporan Masuk", "Status Wilayah", "Perlu Perhatian", "Wilayah Prioritas"];

describe("sorotan beranda", () => {
  it("menampilkan tepat empat kartu", () => {
    render(<Highlights board={board} />);

    for (const title of CARDS) {
      expect(screen.getByText(title)).toBeDefined();
    }
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(4);
  });

  it("memberi setiap kartu satu angka besar, bukan beberapa", () => {
    // Kartu dengan tiga angka berhenti menjadi sorotan dan berubah menjadi laporan kecil.
    const { container } = render(<Highlights board={board} />);

    for (const card of container.querySelectorAll("section.panel")) {
      expect(card.querySelectorAll(".text-3xl")).toHaveLength(1);
    }
  });

  it("menjaga keterangan tiap kartu tetap pendek", () => {
    // Ambangnya longgar dengan sengaja — yang dijaga bukan gaya menulis, melainkan agar
    // kartu tidak kembali memuat dua paragraf seperti sebelumnya.
    const { container } = render(<Highlights board={board} />);

    for (const card of container.querySelectorAll("section.panel")) {
      const note = card.querySelector("p.text-\\[11px\\]");
      expect((note?.textContent ?? "").length).toBeLessThan(200);
    }
  });

  it("menautkan setiap kartu ke layar yang menjelaskannya", () => {
    // Rinciannya tidak dihapus dari aplikasi — ia pindah, dan kartu ini jalannya ke sana.
    const { container } = render(<Highlights board={board} />);

    for (const card of container.querySelectorAll("section.panel")) {
      expect(within(card as HTMLElement).getByRole("link")).toBeDefined();
    }
  });

  it("menyatakan pemetaan status belum disetujui", () => {
    render(<Highlights board={board} />);

    expect(screen.getByText(/belum disetujui/i)).toBeDefined();
  });
});

describe("yang menonjol", () => {
  it("menyorot kenaikan terbesar, bukan angka terbesar", () => {
    render(<Notables board={board} />);

    // CURANMOR naik +4; CURAS tidak bergerak.
    expect(screen.getByText("+4")).toBeDefined();
    expect(screen.getByText(/CURANMOR/)).toBeDefined();
  });

  it("mengaku kosong ketika tidak ada yang bergerak", () => {
    const flat = {
      ...board,
      prominent_issues: {
        ...board.prominent_issues,
        issues: [{ threat_type: "CURAS", incidents: 1, previous_incidents: 1, change: 0 }],
      },
    };

    render(<Notables board={flat} />);

    expect(screen.getByText(/Tidak ada jenis gangguan yang naik/)).toBeDefined();
  });

  it("menyatakan volume laporan bukan kerawanan", () => {
    render(<Notables board={board} />);

    expect(screen.getByText(/Volume laporan, bukan kerawanan/)).toBeDefined();
  });

  it("menandai rekomendasi sebagai turunan aturan, bukan keluaran model", () => {
    render(<Notables board={board} />);

    expect(screen.getByText(/bukan keluaran model/)).toBeDefined();
  });
});

describe("isi tooltip peta", () => {
  const district: MapDistrict = {
    kecamatan: "Tebet",
    historical: null,
    predictive: null,
    current: {
      kecamatan: "Tebet",
      polsek: "Polsek Tebet",
      risk_score: 81,
      risk_class: "HIGH",
      average_risk_score: 50,
      cell_count: 16,
      grid_count: 4,
      weights_version: "dummy-v1",
      latitude: -6.23,
      longitude: 106.85,
      threats: [
        {
          threat_type: "CURANMOR",
          risk_score: 81,
          risk_class: "HIGH",
          time_window: "18:00-23:59",
          cell_count: 9,
        },
      ],
    },
  };

  it("berhenti pada lima baris — cukup untuk memutuskan apakah perlu diklik", () => {
    // Aturan yang sama dipakai Grafana Geomap, ArcGIS Dashboards, dan Datadog. Tooltip
    // yang lebih panjang menutupi peta yang sedang dibaca.
    expect(tooltipRows(district, "current").length).toBeLessThanOrEqual(5);
  });

  it("membawa identitas, angka utama, status, dan pembandingnya", () => {
    const rows = tooltipRows(district, "current");
    const labels = rows.map((row) => row.label);

    expect(labels).toContain("Skor risiko");
    expect(labels).toContain("Kelas");
    expect(labels).toContain("Ancaman utama");
    expect(labels).toContain("Jam rawan");
  });

  it("menyatakan prediksi tidak berkelas alih-alih menghilangkan barisnya", () => {
    const predictive: MapDistrict = {
      ...district,
      current: null,
      predictive: {
        kecamatan: "Tebet",
        polsek: null,
        risk_score: 74,
        confidence: 88,
        threat_type: "CURAT",
        time_window: "18:00-23:59",
        window_start: null,
        window_end: null,
        prediction_code: "PRD-1",
        model_version: "rule-v1",
        cell_count: 3,
        threats: [],
      },
    };

    const kelas = tooltipRows(predictive, "predictive").find((row) => row.label === "Kelas");

    // "tidak diberi kelas", BUKAN "belum ditetapkan": ambangnya sudah ditetapkan
    // 9 September 2026, dan pada hari yang sama pemilik proyek memutuskan prediksi tetap
    // skor mentah. Kata "belum" menyebut keadaan yang tidak lagi berlaku, dan mengundang
    // orang berikutnya "melengkapinya".
    expect(kelas?.value).toBe("tidak diberi kelas");
  });

  it("menjawab keadaan tanpa data tanpa mengarang angka", () => {
    const empty: MapDistrict = {
      kecamatan: "Cilandak",
      historical: null,
      current: null,
      predictive: null,
    };

    expect(tooltipRows(empty, "current")).toEqual([{ label: "Risiko", value: "tidak ada data" }]);
  });
});
