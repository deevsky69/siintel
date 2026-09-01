import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Panel } from "@/components/panel";
import { NAV_ITEMS } from "@/components/shell/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { RISK_LABELS, riskClassOf } from "@/lib/risk";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

describe("shell aplikasi", () => {
  it("menampilkan seluruh menu utama sesuai referensi visual", () => {
    render(<Sidebar />);

    for (const item of NAV_ITEMS) {
      expect(screen.getByRole("link", { name: new RegExp(item.label, "i") })).toBeDefined();
    }
  });

  it("menandai menu yang sedang aktif untuk pembaca layar", () => {
    render(<Sidebar />);

    const active = screen.getByRole("link", { name: /dashboard/i });
    expect(active.getAttribute("aria-current")).toBe("page");
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
