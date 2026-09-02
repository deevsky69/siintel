import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RunResult, ScoringConfig } from "@/lib/scoring";
import { contributionText, factorValue, weightPercent } from "./display";
import { RunPanel } from "./run-panel";
import type { RunState } from "./run-state";
import { RunSummary } from "./run-summary";
import { ScoringBasis } from "./scoring-basis";

/** Server action digantikan tiruan: yang diuji di sini formulirnya, bukan backend-nya. */
const runAssessment = vi.fn<(previous: RunState, form: FormData) => Promise<RunState>>();

vi.mock("./actions", () => ({
  runAssessment: (previous: RunState, form: FormData) => runAssessment(previous, form),
}));

beforeEach(() => {
  runAssessment.mockReset();
});

/**
 * Uji layar Mesin Penilaian Risiko.
 *
 * Yang dijaga di sini bukan rupa layarnya melainkan janjinya:
 *
 * 1. bobot tampil beserta status `DEMO`/`PROPOSED`-nya, bukan sebagai angka final;
 * 2. faktor yang tidak terukur ditulis "tidak terukur" — **tidak pernah** sebagai 0;
 * 3. faktor berbobot nol terlihat jalurnya, tetapi dinyatakan tidak menyumbang;
 * 4. profil yang tidak menghasilkan apa pun menyebut alasannya, bukan diisi contoh;
 * 5. penjelasan berlabel `RULE`, dan tidak ada satu kata pun "prediksi" pada layar ini.
 */

const config: ScoringConfig = {
  active_version: "dummy-v1",
  active_status: "DEMO",
  versions: [
    {
      version: "dummy-v1",
      status: "DEMO",
      active: true,
      profiles: [
        {
          profile: "historical",
          applies_to: ["CURANMOR", "CURAT"],
          positive_weight_total: 1,
          factors: [
            {
              factor: "historical_factor",
              weight: 0.3,
              sign: "positive",
              persisted: true,
              basis: "Kepadatan kejadian historis pada sel dan jenis ini.",
            },
            {
              factor: "recent_trend_factor",
              weight: 0.7,
              sign: "positive",
              persisted: true,
              basis: null,
            },
          ],
        },
      ],
    },
    {
      version: "proposed-2026-09-01",
      status: "PROPOSED",
      active: false,
      profiles: [
        {
          profile: "planned",
          applies_to: ["UNJUK_RASA", "KERAMAIAN"],
          positive_weight_total: 1,
          factors: [
            {
              factor: "mass_estimate_factor",
              weight: 1,
              sign: "positive",
              persisted: false,
              basis: null,
            },
            {
              factor: "readiness_factor",
              weight: -0.1,
              sign: "negative",
              persisted: false,
              basis: null,
            },
          ],
        },
      ],
    },
  ],
  thresholds: {
    version: "dummy-v1",
    status: "DEMO / PROPOSED",
    risk_classes: [
      { class: "LOW", min: 0, max: 44 },
      { class: "CRITICAL", min: 85, max: 100 },
    ],
  },
  time_windows: ["00:00-06:00", "18:00-23:59"],
  persisted_factors: ["historical_factor", "recent_trend_factor"],
  coverage: { locations: 33, assessment_dates: 84 },
  reference_time: "2025-12-31T21:00:00+07:00",
  demo_clock: true,
  config_basis: "Bobot berasal dari config/risk/risk-weights.yaml.",
  score_basis: "risk_score = round(Sum(bobot x faktor)).",
  persistence_basis: "Tabel risk_scores menyimpan lima kolom faktor.",
};

const result: RunResult = {
  assessment_date: "2025-12-18",
  dry_run: true,
  written: 0,
  existing_rows: 0,
  reference_time: "2025-12-31T21:00:00+07:00",
  demo_clock: true,
  weights_version: "dummy-v1",
  weights_status: "DEMO",
  threshold_version: "dummy-v1",
  threshold_status: "DEMO / PROPOSED",
  evidence: { incidents: 1200, date_from: "2023-01-01", date_to: "2025-12-31" },
  profiles: [
    {
      profile: "historical",
      weights_version: "dummy-v1",
      threat_types: ["CURANMOR"],
      weights: { historical_factor: 0.3 },
      combinations: 8,
      scored: 6,
      unscored: 2,
      risk_class_distribution: { CRITICAL: 1, LOW: 5 },
      by_threat_type: [{ threat_type: "CURANMOR", cells: 6, highest: 98, average: 40 }],
      unscored_reasons: [
        { reason: "faktor berbobot tidak dapat dihitung — recent_trend_factor", combinations: 2 },
      ],
      sample: [
        {
          grid_id: "JKS-001",
          kecamatan: "Kebayoran Baru",
          kelurahan: "Senayan",
          polsek: "Polsek Kebayoran Baru",
          location_type: "Parkiran",
          threat_type: "CURANMOR",
          time_window: "18:00-23:59",
          risk_score: 98,
          risk_class: "CRITICAL",
          unscored_reason: null,
          factors: [
            {
              factor: "historical_factor",
              value: 100,
              weight: 0.3,
              contribution: 30,
              source: "RULE",
              reason: null,
              basis: null,
            },
            {
              factor: "community_factor",
              value: 14,
              weight: null,
              contribution: 0,
              source: "RULE",
              reason: null,
              basis: null,
            },
            {
              factor: "intelligence_factor",
              value: null,
              weight: 0,
              contribution: 0,
              source: "RULE",
              reason: "tidak ada laporan intelijen terverifikasi pada cakupan ini",
              basis: null,
            },
          ],
        },
      ],
      not_computed_reason: null,
      unscored_basis: "Kombinasi yang salah satu faktor berbobotnya tidak terukur tidak dinilai.",
    },
    {
      profile: "planned",
      weights_version: "dummy-v1",
      threat_types: [],
      weights: {},
      combinations: 0,
      scored: 0,
      unscored: 0,
      risk_class_distribution: {},
      by_threat_type: [],
      unscored_reasons: [],
      sample: [],
      not_computed_reason: "versi bobot aktif tidak memiliki profil 'planned'.",
      unscored_basis: "…",
    },
  ],
  score_basis: "risk_score = round(Sum(bobot x faktor)).",
  dry_run_basis: "Tidak ada satu baris risk_scores pun yang ditulis.",
  persistence_basis: "Tabel risk_scores menyimpan lima kolom faktor.",
};

describe("dasar perhitungan", () => {
  it("menyebut status bobot, bukan menyajikannya sebagai angka final", () => {
    render(<ScoringBasis config={config} />);

    expect(screen.getAllByText("DEMO").length).toBeGreaterThan(0);
    expect(screen.getByText("PROPOSED")).toBeDefined();
    expect(screen.getByText(/belum ditetapkan pemilik proyek/)).toBeDefined();
  });

  it("menampilkan kedua profil beserta bobot dan jenis ancamannya", () => {
    render(<ScoringBasis config={config} />);

    // Nama profil muncul dua kali per profil: pada judul dan pada caption tabel bobot.
    expect(screen.getAllByText(/Profil A — Pola Historis/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Profil B — Gangguan Terencana/).length).toBeGreaterThan(0);
    expect(screen.getByText("CURANMOR")).toBeDefined();
    expect(screen.getByText("UNJUK_RASA")).toBeDefined();
    expect(screen.getByText("30%")).toBeDefined();
    expect(screen.getByText("-10%")).toBeDefined();
  });

  it("menyatakan faktor bertanda negatif sebagai pengurang skor", () => {
    render(<ScoringBasis config={config} />);

    expect(screen.getByText("mengurangi skor")).toBeDefined();
  });

  it("menampilkan kelas risiko dari konfigurasi ambang", () => {
    render(<ScoringBasis config={config} />);

    expect(screen.getByText("LOW")).toBeDefined();
    expect(screen.getByText("85–100")).toBeDefined();
    expect(screen.getByText("DEMO / PROPOSED")).toBeDefined();
  });
});

describe("hasil penilaian", () => {
  it("menegaskan uji coba tidak menulis apa pun", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText(/Uji coba/)).toBeDefined();
    expect(screen.getByText(/tidak ada satu baris risk_scores pun yang ditulis/i)).toBeDefined();
  });

  it("memisahkan yang dinilai dari yang tidak dapat dinilai, beserta alasannya", () => {
    render(<RunSummary result={result} />);

    // Kedua profil memuat hitungan yang sama bentuknya, jadi yang diperiksa profil A.
    const historical = screen.getByText(/Profil A — Pola Historis/).closest("section");
    expect(historical).not.toBeNull();
    const block = within(historical as HTMLElement);
    expect(block.getByText("Tidak Dinilai").nextElementSibling?.textContent).toBe("2");
    expect(block.getByText(/recent_trend_factor/)).toBeDefined();
  });

  it("tidak pernah menulis faktor yang tak terukur sebagai nol", () => {
    render(<RunSummary result={result} />);

    const card = screen.getByText("JKS-001").closest("li");
    expect(card).not.toBeNull();
    const rows = within(card as HTMLElement);
    expect(rows.getByText("tidak terukur")).toBeDefined();
    expect(
      rows.getByText(/tidak ada laporan intelijen terverifikasi pada cakupan ini/),
    ).toBeDefined();
  });

  it("memperlihatkan jalur faktor tanpa bobot tetapi menyatakan ia tidak menyumbang", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText(/Laporan masyarakat terverifikasi/)).toBeDefined();
    expect(screen.getByText(/tidak berbobot pada versi aktif/)).toBeDefined();
    expect(screen.getByText(/berbobot nol — tidak menyumbang/)).toBeDefined();
  });

  it("menandai setiap penjelasan sebagai RULE, bukan temuan model", () => {
    render(<RunSummary result={result} />);

    expect(screen.getAllByText("RULE")).toHaveLength(3);
  });

  it("menyebut alasan profil terencana tidak menghasilkan apa pun", () => {
    render(<RunSummary result={result} />);

    expect(screen.getByText(/tidak memiliki profil 'planned'/)).toBeDefined();
  });

  it("tidak menyebut hasilnya sebagai prediksi", () => {
    const { container } = render(<RunSummary result={result} />);

    expect(container.textContent?.toLowerCase()).not.toContain("prediksi");
  });
});

describe("pembentukan teks", () => {
  it("membedakan tidak terukur dari nol", () => {
    expect(factorValue(null)).toBe("tidak terukur");
    expect(factorValue(0)).toBe("0");
  });

  it("menyatakan bobot dalam persen, termasuk yang bertanda negatif", () => {
    expect(weightPercent(0.3)).toBe("30%");
    expect(weightPercent(-0.1)).toBe("-10%");
  });

  it("membedakan tidak berbobot dari berbobot nol", () => {
    expect(contributionText(0, null)).toContain("tidak berbobot");
    expect(contributionText(0, 0)).toContain("tidak menyumbang");
    expect(contributionText(30, 0.3)).toContain("30 poin");
  });
});

describe("tombol penjalanan", () => {
  it("menyembunyikan tombol dari peran tanpa kewenangan, dan menyebut sebabnya", () => {
    render(<RunPanel canRun={false} referenceDate="2025-12-31" />);

    expect(screen.queryByRole("button", { name: /uji coba/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /tulis penilaian/i })).toBeNull();
    expect(screen.getByText(/tidak memiliki kewenangan/)).toBeDefined();
  });

  it("menutup tombol tulis sampai ada hasil uji coba", async () => {
    runAssessment.mockResolvedValue({ error: null, result: null });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    const write = screen.getByRole("button", { name: /tulis penilaian/i });
    expect(write.hasAttribute("disabled")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));
    await waitFor(() => expect(runAssessment).toHaveBeenCalledTimes(1));
    // Uji coba dikirim sebagai mode "uji"; hanya "tulis" yang menulis.
    expect(runAssessment.mock.calls[0][1].get("mode")).toBe("uji");
  });

  it("membuka tombol tulis setelah uji coba tanggal yang sama ditampilkan", async () => {
    runAssessment.mockResolvedValue({ error: null, result });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /tulis penilaian/i }).hasAttribute("disabled"),
      ).toBe(false),
    );
    // Hasil uji coba tampil lebih dulu — sebelum ada satu baris pun yang ditulis.
    expect(screen.getByText(/Uji coba/)).toBeDefined();
  });

  it("menampilkan penolakan backend apa adanya", async () => {
    runAssessment.mockResolvedValue({
      error: "Tanggal penilaian 2025-12-31 sudah memiliki 133 baris risk_scores.",
      result: null,
    });
    render(<RunPanel canRun referenceDate="2025-12-31" />);

    fireEvent.click(screen.getByRole("button", { name: /uji coba/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("133 baris"));
  });
});
