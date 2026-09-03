import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CitizenReportPage, CommunitySummary } from "@/lib/community";
import { areaOf, formatMoment, labelOf, REPORT_STATUS_LABELS } from "@/lib/community";
import { CommunityView } from "./community-view";

const BASIS =
  "Laporan masyarakat BELUM memengaruhi risk score sama sekali: tidak ada jalur dari " +
  "citizen_reports ke risk_scores maupun predictions pada prototipe ini. `urgency_score` " +
  "dan `verification_score` adalah nilai sintetis berstatus DEMO, bukan hasil penilaian model.";

const UNMAPPED_BASIS =
  "Laporan yang koordinatnya belum jatuh pada sel grid mana pun. Lokasinya tidak ditebak " +
  "ke sel terdekat.";

const mapped = {
  code: "RPT-0091",
  reported_at: "2025-12-30T02:46:00Z",
  incident_time: "2025-12-29T04:14:00Z",
  category: "Tawuran dan Perkelahian Kelompok",
  description: "Dua kelompok saling lempar batu di ujung gang menjelang tengah malam.",
  location_text: "Sekitar Pulo, di jalan utama",
  urgency_score: 90,
  verification_score: 29,
  status: "RECEIVED",
  kecamatan: "Kebayoran Baru",
  kelurahan: "Pulo",
  polsek: "Polsek Kebayoran Baru",
  grid_id: "JKS-005",
};

const unmapped = {
  code: "RPT-0104",
  reported_at: "2025-11-02T10:00:00Z",
  incident_time: null,
  category: "Kerawanan Lingkungan",
  description: "Lampu penerangan jalan mati di sepanjang gang sehingga area menjadi gelap.",
  location_text: "Wilayah Tebet, dekat pasar",
  urgency_score: 31,
  verification_score: null,
  status: "CLOSED",
  kecamatan: null,
  kelurahan: null,
  polsek: null,
  grid_id: null,
};

const summary: CommunitySummary = {
  total_reports: 150,
  per_status: { RECEIVED: 17, VERIFIED: 36, FORWARDED: 50, IN_PROGRESS: 35, CLOSED: 12 },
  per_category: { "Tawuran dan Perkelahian Kelompok": 31, "Kerawanan Lingkungan": 29 },
  top_areas: [
    { kecamatan: "Kebayoran Baru", polsek: "Polsek Kebayoran Baru", total: 19 },
    { kecamatan: "Tebet", polsek: "Polsek Tebet", total: 19 },
  ],
  recent_reports: [mapped],
  unmapped_reports: 14,
  unmapped_basis: UNMAPPED_BASIS,
  feedback: { total: 60, per_type: { INFORMATION: 22, COMPLAINT: 16 }, per_status: { NEW: 13 } },
  status: "DEMO",
  basis: BASIS,
};

const reports: CitizenReportPage = {
  data: [mapped, unmapped],
  pagination: { page: 1, page_size: 25, total_items: 150, total_pages: 6 },
  status: "DEMO",
  basis: BASIS,
};

const noFilter = { status: null, category: null };

describe("community signal dashboard", () => {
  it("menyatakan di atas seluruh angka bahwa laporan belum memengaruhi risk score", () => {
    // Spesifikasi §4: laporan wajib melewati validasi sebelum boleh memengaruhi risiko.
    // Tidak satu pun tahapannya sudah dibangun, dan layar harus mengatakannya.
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.getAllByText("DEMO").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/belum memengaruhi risk score/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/BELUM memengaruhi risk score sama sekali/).length).toBe(1);
  });

  it("menyebut urgensi dan verifikasi sebagai nilai sintetis, bukan hasil model", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.getAllByText(/nilai\s+sintetis berstatus/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bukan hasil penilaian model/i).length).toBeGreaterThan(0);
  });

  it("tidak mengklaim ada deteksi duplikasi atau spam", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(
      screen.getByText(/Deteksi duplikasi dan deteksi spam .* belum\s+dibangun/is),
    ).toBeDefined();
  });

  it("menampilkan ringkasan per tahapan dan per kategori", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.getAllByText("150").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Diteruskan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("50").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Kerawanan Lingkungan").length).toBeGreaterThan(0);
  });

  it("menaruh pilihan penyaring di URL, bukan di state klien", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    const stage = screen.getByRole("link", { name: /Diteruskan/ });
    expect(stage.getAttribute("href")).toBe("/masyarakat?status=FORWARDED");

    const category = screen.getByRole("link", { name: /Kerawanan Lingkungan/ });
    expect(category.getAttribute("href")).toBe("/masyarakat?kategori=Kerawanan+Lingkungan");
  });

  it("menggabungkan kedua penyaring dan menyediakan cara melepasnya", () => {
    render(
      <CommunityView
        summary={summary}
        reports={reports}
        filters={{ status: "FORWARDED", category: "Kerawanan Lingkungan" }}
      />,
    );

    // Memilih nilai yang sedang aktif berarti melepas penyaring itu saja.
    const stage = screen.getByRole("link", { name: /Diteruskan/ });
    expect(stage.getAttribute("href")).toBe("/masyarakat?kategori=Kerawanan+Lingkungan");

    expect(screen.getByRole("link", { name: "Hapus penyaringan" }).getAttribute("href")).toBe(
      "/masyarakat",
    );
  });

  it("menyatakan laporan tanpa wilayah sebagai belum terpetakan, bukan menebak lokasinya", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.getByText("belum terpetakan")).toBeDefined();
    expect(screen.getByText(UNMAPPED_BASIS)).toBeDefined();
  });

  it("membedakan wilayah pelaporan dari wilayah berisiko", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.getByText(/di mana warga melapor/i)).toBeDefined();
  });

  it("menyatakan keadaan kosong dengan kata, bukan tabel tanpa isi", () => {
    render(
      <CommunityView
        summary={{
          ...summary,
          total_reports: 0,
          per_status: {},
          per_category: {},
          top_areas: [],
          recent_reports: [],
          unmapped_reports: 0,
        }}
        reports={{ ...reports, data: [], pagination: { ...reports.pagination, total_items: 0 } }}
        filters={noFilter}
      />,
    );

    expect(screen.getAllByText(/Belum ada laporan masyarakat pada cakupan Anda/).length).toBe(2);
    expect(screen.getByText("Tidak ada kategori laporan.")).toBeDefined();
    expect(screen.getByText("tidak ada laporan")).toBeDefined();
  });

  it("menjelaskan keadaan kosong yang disebabkan penyaringan secara berbeda", () => {
    render(
      <CommunityView
        summary={summary}
        reports={{ ...reports, data: [], pagination: { ...reports.pagination, total_items: 0 } }}
        filters={{ status: "CLOSED", category: null }}
      />,
    );

    expect(screen.getByText("Tidak ada laporan yang cocok dengan penyaringan ini.")).toBeDefined();
  });

  it("tidak lagi menampilkan blok umpan balik masyarakat", () => {
    // Dihapus atas permintaan pemilik proyek, 3 September 2026. Test ini bukan sisa yang
    // terlupakan: ia menjaga agar bloknya tidak kembali diam-diam saat layar ini disunting
    // berikutnya, dan menyatakan bahwa hilangnya memang disengaja.
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    expect(screen.queryByText("Umpan Balik Masyarakat")).toBeNull();
    expect(screen.queryByText("Umpan Balik")).toBeNull();
  });

  it("tidak pernah menampilkan identitas pelapor", () => {
    // Kanal masyarakat tanpa akun dan tanpa identitas (docs/14 §3, §6). Bentuk datanya
    // memang tidak memuat identitas; test ini menjaga agar layar tidak menambahkannya.
    const { container } = render(
      <CommunityView summary={summary} reports={reports} filters={noFilter} />,
    );

    const text = container.textContent ?? "";
    expect(text).not.toMatch(/pelapor\s*:/i);
    expect(text).not.toMatch(/\bNIK\b/);
    expect(text).not.toMatch(/(?:\+62|\b08)\d{6,}/);
  });

  it("merinci laporan lengkap dengan kode, urgensi, dan tahapannya", () => {
    render(<CommunityView summary={summary} reports={reports} filters={noFilter} />);

    const row = screen.getByText("RPT-0091").closest("tr");
    expect(row).not.toBeNull();
    const cells = within(row as HTMLElement);
    expect(cells.getByText("90")).toBeDefined();
    expect(cells.getByText("29")).toBeDefined();
    expect(cells.getByText("Diterima")).toBeDefined();
  });
});

describe("penyajian data masyarakat", () => {
  it("menyatakan waktu yang tidak diketahui, bukan mengisinya diam-diam", () => {
    expect(formatMoment(null)).toBe("tidak diketahui");
    expect(formatMoment("2025-12-30T02:46:00Z")).toContain("2025");
  });

  it("menyebut laporan tanpa grid sebagai belum terpetakan", () => {
    expect(areaOf(unmapped)).toBe("belum terpetakan");
    expect(areaOf(mapped)).toBe("Pulo, Kebayoran Baru");
  });

  it("menampilkan nilai yang tidak dikenal apa adanya, bukan sebagai kosong", () => {
    expect(labelOf(REPORT_STATUS_LABELS, "FORWARDED")).toBe("Diteruskan");
    expect(labelOf(REPORT_STATUS_LABELS, "STATUS_BARU")).toBe("STATUS_BARU");
  });
});
