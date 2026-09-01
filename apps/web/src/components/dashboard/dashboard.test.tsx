import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EarlyWarningPanel } from "@/components/dashboard/early-warning";
import { OutlookPanel } from "@/components/dashboard/outlook";
import { PatrolStatus } from "@/components/dashboard/patrol-status";
import { RecommendationPanel } from "@/components/dashboard/recommendations";
import { SituationOverview } from "@/components/dashboard/situation-overview";
import { ScoreList } from "@/components/dashboard/threat-list";
import { TrendChart } from "@/components/dashboard/trend-chart";
import type { DashboardSummary, WarningRow } from "@/lib/dashboard";

const summary: DashboardSummary = {
  reference_time: "2025-12-27T02:30:00+00:00",
  demo_clock: true,
  assessment_date: "2025-12-31",
  security_index: 47,
  security_index_basis:
    "100 dikurangi rata-rata seluruh sel risiko. Indeks resmi belum ditetapkan.",
  high_risk_basis: "Ambang berstatus DEMO / PROPOSED.",
  incidents_24h: 2,
  predictions_24h: 4,
  high_risk_areas: 8,
  active_warnings: 36,
  active_operations: 26,
  critical_time_window: "18:00-23:59",
  top_threats: [{ threat_type: "CURAT", risk_score: 88 }],
  risk_by_district: [{ kecamatan: "Pasar Minggu", risk_score: 88 }],
  units: [
    { status: "ACTIVE", count: 5 },
    { status: "STANDBY", count: 1 },
  ],
};

const warning: WarningRow = {
  code: "WRN-0001",
  severity: "CRITICAL",
  threat_type: "CURANMOR",
  time_window: "18:00-23:59",
  risk_score: 87,
  confidence: 84,
  status: "ACTIVE",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Senayan",
  prediction_code: "PRD-00001",
};

describe("situation overview", () => {
  it("menampilkan angka yang diterima dari API", () => {
    render(<SituationOverview summary={summary} />);

    expect(screen.getByText("47")).toBeDefined();
    expect(screen.getByText("36")).toBeDefined();
    expect(screen.getByText("18:00-23:59")).toBeDefined();
  });

  it("menampilkan asal angka indeks keamanan", () => {
    // Indeks bukan angka resmi (U-01/U-02); menampilkannya tanpa penjelasan menyesatkan.
    render(<SituationOverview summary={summary} />);

    expect(screen.getByText(/belum ditetapkan/i)).toBeDefined();
  });
});

describe("daftar berperingkat", () => {
  it("menampilkan skor beserta kelas risikonya", () => {
    render(
      <ScoreList title="Top Threat" rows={[{ label: "CURAT", score: 88 }]} emptyLabel="kosong" />,
    );

    expect(screen.getByText("CURAT")).toBeDefined();
    expect(screen.getByText("88")).toBeDefined();
    expect(screen.getByText("Kritis")).toBeDefined();
  });

  it("menyatakan keadaan kosong, bukan menampilkan nol", () => {
    render(<ScoreList title="Top Threat" rows={[]} emptyLabel="Belum ada penilaian risiko." />);

    expect(screen.getByText("Belum ada penilaian risiko.")).toBeDefined();
  });
});

describe("panel peringatan dini", () => {
  it("menampilkan ancaman, lokasi, skor, dan confidence", () => {
    render(<EarlyWarningPanel warning={warning} total={36} />);

    expect(screen.getByText("CURANMOR")).toBeDefined();
    expect(screen.getByText(/Kebayoran Baru/)).toBeDefined();
    expect(screen.getByText("87")).toBeDefined();
    expect(screen.getByText("84%")).toBeDefined();
  });

  it("menyatakan bila tidak ada peringatan aktif", () => {
    render(<EarlyWarningPanel warning={null} total={0} />);

    expect(screen.getByText(/tidak ada peringatan aktif/i)).toBeDefined();
  });
});

describe("panel rekomendasi", () => {
  it("menegaskan rekomendasi bukan perintah", () => {
    // CLAUDE.md §13: rantai human-in-the-loop harus terbaca di layar, bukan hanya di dokumen.
    render(<RecommendationPanel rows={[]} forWarning="WRN-0001" />);

    expect(screen.getByText(/hanya lahir setelah keputusan pejabat berwenang/i)).toBeDefined();
  });

  it("menampilkan rekomendasi beserta fungsi sasarannya", () => {
    render(
      <RecommendationPanel
        rows={[
          {
            code: "REC-0001",
            recommended_function: "SAMAPTA",
            recommendation_text: "Perkuat patroli pada jam rawan.",
            priority: "HIGH",
            status: "PENDING_REVIEW",
            warning_code: "WRN-0001",
          },
        ]}
        forWarning="WRN-0001"
      />,
    );

    expect(screen.getByText("Samapta")).toBeDefined();
    expect(screen.getByText(/perkuat patroli/i)).toBeDefined();
  });
});

describe("panel pendukung", () => {
  it("outlook menampilkan seluruh horizon", () => {
    render(
      <OutlookPanel
        rows={[
          { horizon: "6H", kecamatan: "Tebet", risk_score: 76, threat_type: "CURAT" },
          { horizon: "7D", kecamatan: null, risk_score: null, threat_type: null },
        ]}
      />,
    );

    expect(screen.getByText("+6 JAM")).toBeDefined();
    expect(screen.getByText("76")).toBeDefined();
    // Horizon tanpa prediksi ditandai, bukan diisi angka karangan.
    expect(screen.getByText("tidak ada")).toBeDefined();
  });

  it("tren menyatakan keadaan kosong", () => {
    render(<TrendChart series={[]} />);

    expect(screen.getByText(/belum ada data tren/i)).toBeDefined();
  });

  it("status patroli menghitung persentase dari total unit", () => {
    render(<PatrolStatus units={summary.units} operations={26} />);

    expect(screen.getByText("6")).toBeDefined();
    expect(screen.getByText(/5 \(83%\)/)).toBeDefined();
  });
});
