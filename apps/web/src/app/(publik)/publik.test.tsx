import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/masuk/page";
import BerandaPublik from "./beranda/page";
import type { ReportOptions } from "./lapor/actions";
import { ReportForm } from "./lapor/report-form";

// Server action tidak dapat dijalankan di lingkungan test; yang diuji di sini bentuk
// formulirnya, bukan pengirimannya (itu diuji di sisi API).
vi.mock("./lapor/actions", () => ({ submitReport: vi.fn() }));

// Halaman masuk memuat formulir yang membaca `?lanjut=` lewat useSearchParams, dan hook
// itu menuntut app router yang tidak ada di lingkungan test. Yang diuji di sini jalan
// kembalinya, bukan formulir masuknya — jadi routernya cukup dipalsukan.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const options: ReportOptions = {
  categories: ["Kejahatan Jalanan", "Pencurian Kendaraan"],
  kecamatan: ["Cilandak", "Tebet"],
  max_description: 1000,
  coordinate_basis: "Koordinat laporan diambil dari titik pusat kecamatan.",
  intake_basis: "Laporan masuk berstatus RECEIVED dan belum diverifikasi siapa pun.",
};

describe("halaman muka publik", () => {
  it("menawarkan tepat dua pilihan: lapor dan masuk", () => {
    render(<BerandaPublik />);

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual(["/lapor", "/masuk"]);
  });

  it("tidak memuat satu pun angka kamtibmas", () => {
    // Angka kamtibmas di halaman publik adalah data intelijen. Halaman ini dibuka tanpa
    // akun, sehingga apa pun yang tampil di sini terbit tanpa keputusan publikasi.
    const { container } = render(<BerandaPublik />);
    const text = container.textContent ?? "";

    // Satu-satunya angka yang boleh muncul adalah nomor darurat.
    expect(text.match(/\d+/g) ?? []).toEqual(["110"]);
  });

  it("mengarahkan keadaan darurat ke 110", () => {
    render(<BerandaPublik />);

    expect(screen.getByText(/110/)).toBeDefined();
    expect(screen.getByText(/bukan pengganti/i)).toBeDefined();
  });
});

describe("halaman masuk", () => {
  it("menyediakan jalan kembali bagi warga yang salah tekan", () => {
    // Tombol "Masuk Petugas" bertetangga dengan "Lapor Kejadian" di halaman muka, dan
    // salah tekan itu wajar. Pengunjung yang merasa tersesat cenderung menutup tab, bukan
    // mencari tombol mundur peramban.
    render(<LoginPage />);

    const targets = screen.getAllByRole("link").map((link) => link.getAttribute("href"));

    expect(targets).toContain("/lapor");
    expect(targets).toContain("/");
  });

  it("menawarkan tujuan yang tadi dimaksudkan warga, bukan sekadar halaman muka", () => {
    render(<LoginPage />);

    expect(screen.getByRole("link", { name: /lapor kejadian/i })).toBeDefined();
    expect(screen.getByText(/Bukan petugas dan ingin melaporkan kejadian/i)).toBeDefined();
  });
});

describe("formulir laporan masyarakat", () => {
  it("tidak menyediakan satu pun kolom identitas", () => {
    // Penjaga terhadap penambahan yang tampak membantu. Basis data tidak punya tempat
    // untuk identitas; kolom di layar hanya akan menampung data yang lalu dibuang,
    // sementara pelapor mengira datanya tersimpan.
    const { container } = render(<ReportForm options={options} />);

    const names = [...container.querySelectorAll("input, textarea, select")].map((field) =>
      field.getAttribute("name"),
    );

    expect(names).toEqual([
      "category",
      "kecamatan",
      "location_text",
      "incident_time",
      "description",
    ]);
  });

  it("tidak menyediakan unggahan berkas", () => {
    // Menyimpan foto/video warga menyentuh retensi dan klasifikasi data (U-14) — keputusan
    // kebijakan yang belum diambil, bukan pekerjaan yang belum sempat.
    const { container } = render(<ReportForm options={options} />);

    expect(container.querySelector('input[type="file"]')).toBeNull();
  });

  it("tidak membiarkan pelapor menetapkan urgensi", () => {
    const { container } = render(<ReportForm options={options} />);
    const text = container.textContent ?? "";

    expect(container.querySelector('[name="urgency_score"]')).toBeNull();
    expect(text.toLowerCase()).not.toContain("mendesak");
  });

  it("hanya menawarkan kategori yang dikirim API", () => {
    render(<ReportForm options={options} />);

    const select = screen.getByRole("combobox", { name: /jenis kejadian/i });
    const values = [...select.querySelectorAll("option")]
      .map((option) => option.getAttribute("value"))
      .filter((value) => value !== "");

    expect(values).toEqual(options.categories);
  });

  it("memperingatkan agar tidak menuliskan identitas di keterangan", () => {
    // Kolom teks bebas adalah satu-satunya jalan identitas dapat masuk. Peringatannya
    // ditaruh tepat di bawah kolomnya, bukan di catatan kaki halaman.
    render(<ReportForm options={options} />);

    expect(screen.getByText(/Jangan menuliskan nama, nomor telepon, atau alamat/)).toBeDefined();
  });

  it("meneruskan keterangan asal koordinat dari API apa adanya", () => {
    render(<ReportForm options={options} />);

    expect(screen.getByText(options.coordinate_basis)).toBeDefined();
  });
});
