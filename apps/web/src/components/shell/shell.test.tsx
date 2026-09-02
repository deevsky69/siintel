import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Panel } from "@/components/panel";
import { NAV_ITEMS } from "@/components/shell/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { RISK_LABELS, riskClassOf } from "@/lib/risk";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

/** Seluruh permission yang disebut submenu mana pun. */
const ALL_PERMISSIONS = [...new Set(NAV_ITEMS.flatMap((item) => item.permissions))];

describe("shell aplikasi", () => {
  it("menampilkan kelima kelompok menu", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    for (const label of ["Pemantauan", "Laporan", "Analisis", "Operasi", "Sistem"]) {
      expect(screen.getByRole("button", { name: new RegExp(label, "i") })).toBeDefined();
    }
  });

  it("membuka hanya kelompok yang sedang aktif", () => {
    // Membuka seluruhnya mengembalikan persoalan yang hendak diselesaikan susunan ini:
    // dua puluh baris setara yang harus dibaca semuanya untuk menemukan satu.
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    // usePathname dipalsukan ke "/", yang berada di kelompok Pemantauan.
    expect(screen.getByRole("link", { name: /beranda/i })).toBeDefined();
    expect(screen.queryByRole("link", { name: /audit log/i })).toBeNull();
  });

  it("membuka kelompok lain ketika judulnya ditekan", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    fireEvent.click(screen.getByRole("button", { name: /sistem/i }));

    expect(screen.getByRole("link", { name: /audit log/i })).toBeDefined();
    // Kelompok yang aktif tetap terbuka: menutupnya menghilangkan penanda posisi.
    expect(screen.getByRole("link", { name: /beranda/i })).toBeDefined();
  });

  it("membuat setiap submenu dapat dicapai setelah kelompoknya dibuka", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    for (const group of ["Laporan", "Analisis", "Operasi", "Sistem"]) {
      fireEvent.click(screen.getByRole("button", { name: new RegExp(group, "i") }));
    }

    for (const item of NAV_ITEMS) {
      expect(
        screen.getByRole("link", { name: new RegExp(item.label, "i") }),
        item.href,
      ).toBeDefined();
    }
  });

  it("menandai submenu yang sedang aktif untuk pembaca layar", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    expect(screen.getByRole("link", { name: /beranda/i }).getAttribute("aria-current")).toBe(
      "page",
    );
  });

  it("menyembunyikan submenu yang tidak dapat dipakai peran itu sama sekali", () => {
    const pimpinan = [
      "analytics:read",
      "audit:read",
      "citizen_report:read",
      "commander_decision:approve",
      "config:read",
      "crime:read",
      "dashboard:read",
      "evaluation:read",
      "intelligence:read",
      "map:read",
      "operation:read",
      "prediction:read",
      "recommendation:read",
      "risk_score:read",
      "warning:read",
    ];

    render(<Sidebar permissions={pimpinan} />);
    fireEvent.click(screen.getByRole("button", { name: /laporan/i }));
    fireEvent.click(screen.getByRole("button", { name: /sistem/i }));

    expect(screen.queryByRole("link", { name: /input data/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /manajemen pengguna/i })).toBeNull();
    expect(screen.getByRole("link", { name: /audit log/i })).toBeDefined();
  });

  it("tidak menampilkan menu apa pun ketika kewenangan tidak diketahui", () => {
    // Kegagalan memuat profil tidak boleh berubah menjadi sidebar yang menjanjikan lebih
    // banyak daripada yang dapat dibuka.
    render(<Sidebar permissions={[]} />);

    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("menampilkan lencana keputusan yang menunggu pada submenunya", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} pendingDecisions={19} />);
    fireEvent.click(screen.getByRole("button", { name: /operasi/i }));

    expect(screen.getByText("19 rekomendasi menunggu keputusan Anda")).toBeDefined();
  });

  it("memindahkan lencana ke judul kelompok saat submenunya tertutup", () => {
    // Keputusan yang menunggu harus tetap terlihat tanpa membuka apa pun.
    render(<Sidebar permissions={ALL_PERMISSIONS} pendingDecisions={19} />);

    const operasi = screen.getByRole("button", { name: /operasi/i });
    expect(operasi.getAttribute("aria-expanded")).toBe("false");
    expect(operasi.textContent).toContain("19");
  });

  it("tidak menggambar lencana ketika tidak ada yang menunggu", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} pendingDecisions={0} />);

    expect(screen.queryByText(/menunggu keputusan Anda/)).toBeNull();
  });

  it("menampilkan identitas sistem dan satuan wilayah", () => {
    render(<Topbar name="demo.pimpinan" roleName="Pimpinan" />);

    expect(screen.getByText("PREDIKSI PRESISI")).toBeDefined();
    expect(screen.getByText(/polres metro jakarta selatan/i)).toBeDefined();
  });

  it("menampilkan pengguna yang sedang masuk beserta perannya", () => {
    // Identitas berasal dari /auth/me, bukan nilai yang ditanam di kode.
    render(<Topbar name="demo.pimpinan" roleName="Pimpinan" />);

    expect(screen.getByText("demo.pimpinan")).toBeDefined();
    expect(screen.getByText("Pimpinan")).toBeDefined();
  });

  it("menautkan modul penggunaan dari bilah atas", () => {
    // Modul adalah halaman berdiri sendiri di `public/`, bukan rute aplikasi; tautannya
    // mudah hilang saat topbar disunting, dan hilangnya tidak menggagalkan apa pun.
    render(<Topbar name="demo.pimpinan" roleName="Pimpinan" />);

    const link = screen.getByRole("link", { name: /modul/i });
    expect(link.getAttribute("href")).toBe("/modul.html");
  });

  it("menyediakan jalan keluar dari sesi", () => {
    render(<Topbar name="demo.pimpinan" roleName="Pimpinan" />);

    expect(screen.getByRole("button", { name: /keluar/i })).toBeDefined();
  });

  it("panel memakai judul sebagai heading", () => {
    render(<Panel title="Situation Overview">isi</Panel>);

    expect(screen.getByRole("heading", { name: "Situation Overview" })).toBeDefined();
  });
});

describe("tangga risiko", () => {
  it("memetakan skor ke kelas sesuai ambang tampilan", () => {
    expect(riskClassOf(27)).toBe("LOW");
    expect(riskClassOf(45)).toBe("MODERATE");
    expect(riskClassOf(76)).toBe("HIGH");
    expect(riskClassOf(87)).toBe("CRITICAL");
  });

  it("menjaga skor di luar rentang tetap masuk akal", () => {
    expect(riskClassOf(-10)).toBe("LOW");
    expect(riskClassOf(999)).toBe("CRITICAL");
  });

  it("menyediakan label Bahasa Indonesia untuk setiap kelas", () => {
    expect(RISK_LABELS.CRITICAL).toBe("Kritis");
    expect(Object.keys(RISK_LABELS)).toHaveLength(4);
  });
});
