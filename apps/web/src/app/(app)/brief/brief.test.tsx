import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  actionSentence,
  type DailyBrief,
  decisionSentence,
  formatBriefDate,
  situationSentence,
} from "@/lib/brief";
import { BriefDocument } from "./brief-document";

const brief: DailyBrief = {
  reference_time: "2025-12-27T09:30:00+07:00",
  demo_clock: true,
  brief_date: "2025-12-27",
  brief_time: "09.30",
  window_hours: 24,
  scope_polsek: null,
  scope_basis: "Seluruh angka mencakup seluruh wilayah yang boleh dibaca akun ini.",
  clock_basis: "Waktu acuan aplikasi dipakai sebagai 'sekarang' (keputusan SDL-16).",

  incidents_recent: 2,
  incidents_basis: "Kejadian antara 26/12/2025 09.30 dan 27/12/2025 09.30 WIB.",

  active_warnings: 35,
  warnings_by_severity: [
    { severity: "WARNING", count: 21 },
    { severity: "CRITICAL", count: 14 },
  ],
  warnings_basis: "Peringatan dini berstatus ACTIVE — kueri yang sama dengan GET /warnings.",

  assessment_date: "2025-12-31",
  top_area: {
    kecamatan: "Pasar Minggu",
    risk_score: 88,
    risk_class: "CRITICAL",
    threat_type: "CURAT",
    time_window: "18:00-23:59",
  },
  top_area_basis: "Sel risiko tertinggi pada tanggal penilaian terakhir (2025-12-31).",
  top_threats: [
    {
      threat_type: "CURAT",
      kecamatan: "Pasar Minggu",
      time_window: "18:00-23:59",
      risk_score: 88,
      risk_class: "CRITICAL",
    },
    {
      threat_type: "CURANMOR",
      kecamatan: "Cilandak",
      time_window: "18:00-23:59",
      risk_score: 86,
      risk_class: "CRITICAL",
    },
  ],
  top_threats_basis: "Jenis ancaman dengan sel risiko tertinggi pada tanggal penilaian terakhir.",

  pending_recommendations: 19,
  pending_by_function: [
    { recommended_function: "SAMAPTA", count: 10 },
    { recommended_function: "BINMAS", count: 9 },
  ],
  pending_recommendations_basis: "Rekomendasi berstatus PENDING_REVIEW.",

  pending_actions: 1,
  pending_action_items: [
    {
      decision_code: "DEC-0064",
      decision: "MODIFIED",
      decided_at: "2025-12-27T03:00:00+00:00",
      recommendation_code: "REC-0102",
      recommended_function: "SAMAPTA",
      priority: "HIGH",
      kecamatan: "Tebet",
      original_recommendation: "Kerahkan dua unit ke Tebet.",
      modified_text: "Kerahkan satu unit ke Tebet, satu unit siaga di Mapolsek.",
    },
  ],
  pending_actions_basis: "Keputusan APPROVED atau MODIFIED yang belum memiliki tindakan.",

  accuracy: {
    hits: 60,
    false_positives: 91,
    false_negatives: 90,
    precision: 0.397,
    recall: 0.4,
    evaluated_rows: 241,
    status: "PROPOSED",
  },
  accuracy_basis: "Aturan pencocokan final belum ditetapkan (U-03).",
};

/**
 * Kueri dibatasi pada satu bagian, bukan seluruh dokumen: angka yang sama memang muncul
 * pada kalimat pembuka dan pada daftar angka di bawahnya — dan pengulangan itu justru
 * yang diuji di tempat lain.
 */
function section(title: string) {
  const found = screen.getByRole("heading", { name: title }).closest("section");
  if (!found) throw new Error(`bagian "${title}" tidak ditemukan`);
  return within(found);
}

describe("kalimat template executive brief", () => {
  it("menyusun kalimat situasi dari angka yang diterima", () => {
    expect(situationSentence(brief)).toBe(
      "Dalam 24 jam terakhir sampai 27 Desember 2025 pukul 09.30 WIB, tercatat 2 kejadian, " +
        "35 peringatan dini masih berstatus aktif, dan wilayah dengan sel risiko tertinggi " +
        "adalah Pasar Minggu pada skor 88 (Kritis).",
    );
  });

  it("melewatkan bagian yang tidak boleh dibaca pengguna, bukan menyebutnya nol", () => {
    const sentence = situationSentence({
      ...brief,
      incidents_recent: null,
      active_warnings: null,
    });

    expect(sentence).not.toBeNull();
    expect(sentence).not.toMatch(/kejadian/);
    expect(sentence).toMatch(/Pasar Minggu/);
  });

  it("menyatakan keadaan kosong dengan kata, bukan angka nol", () => {
    expect(decisionSentence({ ...brief, pending_recommendations: 0 })).toBe(
      "Tidak ada rekomendasi yang menunggu keputusan.",
    );
    expect(actionSentence({ ...brief, pending_actions: 0 })).toBe(
      "Seluruh keputusan yang telah disetujui sudah ditindaklanjuti di lapangan.",
    );
  });

  it("tidak menyusun kalimat sama sekali bila tidak ada angka yang boleh dipakai", () => {
    expect(
      situationSentence({
        ...brief,
        incidents_recent: null,
        active_warnings: null,
        top_area: null,
      }),
    ).toBeNull();
    expect(decisionSentence({ ...brief, pending_recommendations: null })).toBeNull();
    expect(actionSentence({ ...brief, pending_actions: null })).toBeNull();
  });

  it("menuliskan tanggal tanpa menguraikannya sebagai waktu", () => {
    // Menguraikan lewat `new Date` akan menggeser tanggal pada server non-WIB.
    expect(formatBriefDate("2025-12-27")).toBe("27 Desember 2025");
    expect(formatBriefDate("bukan-tanggal")).toBe("bukan-tanggal");
  });
});

describe("dokumen executive brief", () => {
  it("menyebut kapan brief berlaku dan atas cakupan mana", () => {
    render(<BriefDocument brief={brief} />);

    expect(screen.getByText("27 Desember 2025")).toBeDefined();
    expect(screen.getByText("09.30 WIB")).toBeDefined();
    expect(screen.getByText("Seluruh wilayah Polres")).toBeDefined();
    expect(screen.getByText(/keputusan SDL-16/)).toBeDefined();
  });

  it("mengulang setiap angka pada kalimat sebagai angka tersendiri", () => {
    // Inilah pagar utamanya: bila template salah menyusun kalimat, kekeliruannya
    // terlihat karena angkanya tetap tertera di sebelahnya (CLAUDE.md §27).
    render(<BriefDocument brief={brief} />);
    const situation = section("1. Situasi Terakhir");

    expect(situation.getByText(/tercatat 2 kejadian/)).toBeDefined();
    expect(situation.getByText("Kejadian tercatat (24 jam terakhir)")).toBeDefined();
    expect(situation.getByText("2")).toBeDefined();
    expect(situation.getByText("Peringatan dini aktif")).toBeDefined();
    expect(situation.getByText("35")).toBeDefined();
    expect(situation.getByText("88")).toBeDefined();
  });

  it("merinci ancaman menonjol beserta jam rawannya", () => {
    render(<BriefDocument brief={brief} />);
    const threats = section("2. Ancaman Menonjol dan Jam Rawannya");

    expect(threats.getByText("CURAT")).toBeDefined();
    expect(threats.getByText("CURANMOR")).toBeDefined();
    expect(threats.getAllByText("18:00-23:59").length).toBe(2);
    expect(threats.getAllByText("Kritis").length).toBe(2);
  });

  it("menyebut jumlah rekomendasi yang menunggu keputusan beserta fungsinya", () => {
    render(<BriefDocument brief={brief} />);
    const pending = section("3. Menunggu Keputusan Pimpinan");

    expect(pending.getByText(/19 rekomendasi menunggu keputusan/)).toBeDefined();
    expect(pending.getByText("— fungsi SAMAPTA")).toBeDefined();
    expect(pending.getByText("10")).toBeDefined();
  });

  it("menampilkan perintah yang berlaku, bukan usulan mentah sistem", () => {
    // Usulan asli tidak pernah ditimpa (U-07); yang dibacakan adalah hasil modifikasi.
    render(<BriefDocument brief={brief} />);
    const actions = section("4. Menunggu Tindakan Lapangan");

    expect(
      actions.getByText("Kerahkan satu unit ke Tebet, satu unit siaga di Mapolsek."),
    ).toBeDefined();
    expect(actions.getByText(/hasil modifikasi pimpinan/)).toBeDefined();
    expect(actions.queryByText("Kerahkan dua unit ke Tebet.")).toBeNull();
  });

  it("menandai angka ketepatan model sebagai belum final", () => {
    render(<BriefDocument brief={brief} />);
    const accuracy = section("5. Ketepatan Model Sejauh Ini");

    expect(accuracy.getByText("PROPOSED")).toBeDefined();
    expect(accuracy.getByText(/belum final/)).toBeDefined();
    expect(accuracy.getByText("0,397")).toBeDefined();
    expect(accuracy.getByText("0,400")).toBeDefined();
    expect(accuracy.getByText(/U-03/)).toBeDefined();
  });

  it("menyertakan dasar perhitungan setiap angka turunan", () => {
    render(<BriefDocument brief={brief} />);

    expect(screen.getAllByText(/^Dasar:/).length).toBeGreaterThanOrEqual(5);
    expect(screen.getByText(/kueri yang sama dengan GET \/warnings/)).toBeDefined();
  });

  it("menyatakan bahwa brief tidak disusun model bahasa", () => {
    // docs/13: tidak ada model bahasa di sistem ini. Pembaca berhak tahu asal kalimatnya.
    render(<BriefDocument brief={brief} />);

    expect(screen.getByText(/tidak ada model bahasa/i)).toBeDefined();
    expect(screen.getByText(/template tetap/i)).toBeDefined();
  });

  it("menjelaskan bagian yang tidak boleh dibaca, bukan menghilangkannya diam-diam", () => {
    render(
      <BriefDocument
        brief={{
          ...brief,
          pending_recommendations: null,
          pending_by_function: [],
          pending_recommendations_basis:
            "Tidak disertakan: akun ini tidak memiliki kewenangan `recommendation:read`.",
          accuracy: null,
          accuracy_basis: "Tidak disertakan: akun ini tidak memiliki kewenangan `evaluation:read`.",
        }}
      />,
    );

    expect(
      section("3. Menunggu Keputusan Pimpinan").getByText(
        "Bagian ini tidak disertakan untuk akun ini.",
      ),
    ).toBeDefined();
    expect(screen.getByText(/kewenangan `evaluation:read`/)).toBeDefined();
  });

  it("mencantumkan cakupan wilayah ketika akun dibatasi polsek", () => {
    render(<BriefDocument brief={{ ...brief, scope_polsek: "Polsek Tebet" }} />);

    expect(screen.getByText("Polsek Tebet")).toBeDefined();
  });
});
