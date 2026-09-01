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
    render(<Topbar />);

    expect(screen.getByText("PREDIKSI PRESISI")).toBeDefined();
    expect(screen.getByText(/polres metro jakarta selatan/i)).toBeDefined();
  });

  it("menyatakan terbuka bahwa pengguna belum masuk", () => {
    // Identitas palsu yang tampak nyata akan menyesatkan saat paparan.
    render(<Topbar />);

    expect(screen.getByText(/belum masuk/i)).toBeDefined();
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
