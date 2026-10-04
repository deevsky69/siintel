import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PatrolPlan, PlanEvaluation } from "@/lib/patrol-plan";
import { percentText } from "@/lib/patrol-plan";
import { PatrolPlanView } from "./plan-view";

const slot = {
  rank: 1,
  threat_type: "CURANMOR",
  polsek: "Polsek Kebayoran Baru",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Cipete Utara",
  block_start: 3,
  block_label: "03.00-06.00",
  incidents: 11,
  share_percent: 4.8,
  cumulative_share_percent: 4.8,
  why: "11 kejadian CURANMOR di Kelurahan Cipete Utara (Kebayoran Baru) pada 03.00-06.00 sepanjang tahun dasar — 4.8% dari seluruh CURANMOR yang jamnya tercatat.",
};

const plan: PatrolPlan = {
  version: "rencana-patroli-v1",
  status: "PROPOSED",
  basis_from: "2025-01-01",
  basis_to: "2025-12-31",
  target_year: 2026,
  scope: null,
  rules: { basis_months: 12, max_slots_per_threat: 15, minimum_incidents: 3 },
  threats: [
    {
      threat_type: "CURANMOR",
      basis_incidents: 259,
      basis_with_hour: 227,
      basis_unknown_time: 32,
      basis_unknown_kelurahan: 5,
      slots: [slot],
      covered_share_percent: 4.8,
    },
    {
      threat_type: "CURAS",
      basis_incidents: 37,
      basis_with_hour: 24,
      basis_unknown_time: 13,
      basis_unknown_kelurahan: 0,
      slots: [],
      covered_share_percent: 0,
    },
  ],
  plan_basis: "Slot = kelurahan x blok 3 jam x jenis.",
  reference_time: "2026-01-01T00:00:00+07:00",
  demo_clock: true,
};

const evaluation: PlanEvaluation = {
  version: "rencana-patroli-v1",
  status: "PROPOSED",
  target_year: 2026,
  target_observed_from: "2026-01-01",
  target_observed_to: "2026-09-28",
  scope: null,
  overall: {
    slots: 1,
    slots_hit: 1,
    slot_hit_rate_percent: 100,
    actual_evaluable: 745,
    covered_incidents: 31,
    coverage_percent: 4.2,
    hour_similarity_percent: 84.3,
    area_similarity_percent: 74.9,
  },
  per_threat: [
    {
      threat_type: "CURANMOR",
      slots: 1,
      slots_hit: 1,
      slot_hit_rate_percent: 100,
      actual_incidents: 313,
      actual_evaluable: 237,
      actual_unknown_time: 76,
      actual_unknown_kelurahan: 0,
      covered_incidents: 14,
      coverage_percent: 5.9,
      hour_similarity_percent: 70.2,
      area_similarity_percent: 46.2,
      hour_profile: [
        { block_start: 0, block_label: "00.00-03.00", basis_incidents: 20, actual_incidents: 18 },
      ],
      slot_results: [{ ...slot, actual_incidents: 3, hit: true }],
    },
  ],
  similarity_basis: "Kemiripan pola jam = jumlah atas delapan blok dari min(porsi, porsi).",
  partial_year_basis: "Tahun sasaran dibandingkan sejauh datanya ada.",
  reference_time: "2026-01-01T00:00:00+07:00",
  demo_clock: true,
};

describe("rencana patroli", () => {
  it("menampilkan slot usulan beserta angkanya dan menandai usulan sebagai PROPOSED", () => {
    render(<PatrolPlanView plan={plan} evaluation={null} />);

    expect(screen.getByText("Rencana Patroli 2026")).toBeDefined();
    expect(screen.getAllByText(/PROPOSED/).length).toBeGreaterThan(0);
    expect(screen.getByText("Cipete Utara")).toBeDefined();
    expect(screen.getByText("03.00-06.00")).toBeDefined();
    expect(screen.getByTitle(/11 kejadian CURANMOR di Kelurahan Cipete Utara/)).toBeDefined();
  });

  it("menyatakan jenis tanpa slot sebagai terlalu tersebar, bukan menyembunyikannya", () => {
    render(<PatrolPlanView plan={plan} evaluation={null} />);

    expect(screen.getByText(/terlalu tersebar/)).toBeDefined();
    expect(screen.getByText(/13 tanpa jam/)).toBeDefined();
  });

  it("menampilkan empat angka kemiripan beserta definisinya", () => {
    render(<PatrolPlanView plan={plan} evaluation={evaluation} />);

    expect(screen.getByText("84,3%")).toBeDefined();
    expect(screen.getByText("74,9%")).toBeDefined();
    expect(screen.getAllByText("100%").length).toBeGreaterThan(0);
    expect(screen.getByText("4,2%")).toBeDefined();
    expect(screen.getByText(/Kemiripan pola jam = jumlah/)).toBeDefined();
    expect(screen.getByText(/Tahun sasaran dibandingkan sejauh datanya ada/)).toBeDefined();
  });

  it("menandai angka yang tidak dapat dihitung, bukan menulis nol", () => {
    expect(percentText(null)).toBe("—");
    expect(percentText(12.34)).toBe("12,3%");
  });
});
