import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AREA_STATUS_TONE, toneOf } from "@/lib/leadership";
import { board } from "./fixtures";
import { ProminentIssues } from "./issues";
import { PolicyRecommendations } from "./policy";
import { AreaStatusCard, AttentionCard, PriorityAreasCard, ReportsCard } from "./summary-cards";
import { TopReportAreas } from "./top-areas";

/**
 * Yang diuji di sini adalah hal-hal yang membuat layar ini **menyesatkan** bila rusak,
 * bukan sekadar tampil berbeda:
 *
 * - total laporan yang menyembunyikan rinciannya;
 * - pemetaan status yang tampil seolah sudah resmi;
 * - daftar volume laporan yang terbaca sebagai peringkat kerawanan;
 * - rekomendasi yang terbaca sebagai keluaran AI.
 */

describe("kartu laporan masuk", () => {
  it("menampilkan rincian ketiga jenis laporan, bukan hanya totalnya", () => {
    render(<ReportsCard reports={board.reports_24h} />);

    expect(screen.getByText("7")).toBeDefined();
    expect(screen.getByText("Kejadian kriminal")).toBeDefined();
    expect(screen.getByText("Laporan intelijen")).toBeDefined();
    expect(screen.getByText("Laporan masyarakat")).toBeDefined();
  });

  it("menyebut laporan tanpa lokasi alih-alih membiarkannya hilang tanpa keterangan", () => {
    render(<ReportsCard reports={board.reports_24h} />);

    expect(screen.getByText(/2 laporan masyarakat di antaranya tanpa lokasi/)).toBeDefined();
  });

  it("menyatakan bahwa laporan intelijen dicacah per hari, bukan per 24 jam", () => {
    render(<ReportsCard reports={board.reports_24h} />);

    expect(screen.getByText(/dicacah per hari \(2025-12-31\)/)).toBeDefined();
  });
});

describe("kartu status wilayah", () => {
  it("menyatakan pemetaannya belum disetujui", () => {
    render(<AreaStatusCard areaStatus={board.area_status} />);

    expect(screen.getAllByText("PROPOSED").length).toBeGreaterThan(0);
    expect(screen.getByText(/belum disetujui/)).toBeDefined();
  });

  it("menyebut berapa wilayah pada status yang paling banyak", () => {
    render(<AreaStatusCard areaStatus={board.area_status} />);

    expect(screen.getByText(/dari 3 kecamatan berstatus Siaga/)).toBeDefined();
    // Jumlah pada lencana status Siaga, dibaca dari lencananya sendiri agar angka "2"
    // di kalimat ringkasan tidak ikut tercocokkan.
    const badge = screen.getByText("Siaga", { selector: "span.rounded" });
    expect(badge.textContent).toContain("2");
  });

  it("menyatakan bahwa status mengikuti sel tertinggi, sama seperti peta", () => {
    render(<AreaStatusCard areaStatus={board.area_status} />);

    expect(screen.getByText(/sel dengan skor tertinggi/)).toBeDefined();
  });
});

describe("kartu perlu perhatian", () => {
  it("memisahkan peringatan dari keputusan yang hanya dapat diambil pimpinan", () => {
    render(<AttentionCard items={board.needs_attention.items} />);

    expect(
      screen.getByText(/1 peringatan belum diterima · 1 menunggu keputusan Anda/),
    ).toBeDefined();
  });

  it("menautkan tiap butir ke layar yang menanganinya", () => {
    render(<AttentionCard items={board.needs_attention.items} />);

    expect(screen.getByRole("link", { name: /Peringatan CRITICAL/ }).getAttribute("href")).toBe(
      "/peringatan?kode=WRN-0001",
    );
  });

  it("menyatakan keadaan kosong sebagai tidak ada yang menunggu, bukan panel rusak", () => {
    render(<AttentionCard items={[]} />);

    expect(screen.getByText(/Tidak ada peringatan aktif/)).toBeDefined();
  });
});

describe("kartu wilayah prioritas", () => {
  it("menampilkan sel tertinggi dan rata-rata berdampingan", () => {
    render(<PriorityAreasCard areas={board.priority_areas} />);

    expect(screen.getByText("88")).toBeDefined();
    expect(screen.getByText("/58")).toBeDefined();
    expect(screen.getByText(/Keduanya menjawab pertanyaan yang berbeda/)).toBeDefined();
  });
});

describe("daftar top area menurut jumlah laporan", () => {
  it("mempertahankan urutan yang dikirim API", () => {
    render(<TopReportAreas top={board.top_report_areas} />);

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("cell")[1].textContent)).toEqual([
      "Cilandak",
      "Pancoran",
    ]);
  });

  it("menyatakan tingkatnya bukan kelas risiko", () => {
    render(<TopReportAreas top={board.top_report_areas} />);

    expect(screen.getByText(/bukan kelas risiko/)).toBeDefined();
    expect(screen.getByText("Kritis")).toBeDefined();
    expect(screen.getByText("Sedang")).toBeDefined();
  });

  it("menyebut laporan yang tidak dapat dibebankan ke wilayah mana pun", () => {
    render(<TopReportAreas top={board.top_report_areas} />);

    expect(
      screen.getByText(/3 laporan masyarakat pada jendela ini tidak memiliki lokasi/),
    ).toBeDefined();
  });
});

describe("isu menonjol", () => {
  it("menyajikan perubahan sebagai selisih bertanda, bukan persen", () => {
    render(<ProminentIssues issues={board.prominent_issues} />);

    expect(screen.getByText("+4")).toBeDefined();
    expect(screen.getByText("0")).toBeDefined();
    expect(screen.queryByText(/%/)).toBeNull();
  });

  it("menampilkan pembanding pekan sebelumnya", () => {
    render(<ProminentIssues issues={board.prominent_issues} />);

    // Kedua isu contoh sama-sama berbasis 1 kejadian pekan sebelumnya.
    expect(screen.getAllByText("Pekan sebelumnya 1 kejadian")).toHaveLength(2);
  });
});

describe("rekomendasi kebijakan", () => {
  it("menandai sumbernya sebagai aturan, bukan keluaran model", () => {
    render(<PolicyRecommendations policy={board.policy} />);

    expect(screen.getByText("RULE")).toBeDefined();
    expect(screen.getByText("Diturunkan aturan")).toBeDefined();
    expect(screen.queryByText(/\bAI\b/)).toBeNull();
  });

  it("menyertakan dasar tiap butir", () => {
    render(<PolicyRecommendations policy={board.policy} />);

    expect(screen.getByText("Pasar Minggu berstatus Siaga dengan skor 88.")).toBeDefined();
  });

  it("membiarkan panel kosong alih-alih mengisinya dengan saran umum", () => {
    render(<PolicyRecommendations policy={{ ...board.policy, recommendations: [] }} />);

    expect(screen.getByText(/sengaja dibiarkan kosong/)).toBeDefined();
  });
});

describe("warna status", () => {
  it("menjawab warna netral untuk status yang tidak dikenal, bukan warna teraman", () => {
    // Kelas risiko baru yang belum dipetakan akan tiba di sini sebagai `null`. Menjatuhkannya
    // ke warna "Aman" membuat wilayah yang tidak diketahui tampak aman, dan tidak ada yang
    // akan menyadarinya.
    const unknown = toneOf(AREA_STATUS_TONE, null);

    expect(unknown).not.toBe(AREA_STATUS_TONE.AMAN);
    expect(unknown).toContain("text-ink-muted");
  });
});
