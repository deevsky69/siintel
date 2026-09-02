import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Panel } from "@/components/panel";
import { NAV_ITEMS } from "@/components/shell/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { RISK_LABELS, riskClassOf } from "@/lib/risk";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

/**
 * Seluruh permission yang disebut menu mana pun, **baca maupun tindakan**.
 *
 * `actions` wajib ikut: tanpanya seluruh menu menjadi "hanya dapat dibaca" dan pindah ke
 * kelompok Lainnya yang tertutup — keadaan yang tidak dimaksudkan test ini.
 */
const ALL_PERMISSIONS = [
  ...new Set(NAV_ITEMS.flatMap((item) => [...item.permissions, ...item.actions])),
];

describe("shell aplikasi", () => {
  it("membuat setiap menu tetap dapat dicapai — sebagian di balik Lainnya", () => {
    // "Lainnya" memindahkan menu keluar dari jalur harian, bukan menghapusnya. Yang
    // diperiksa di sini justru itu: tidak ada satu pun layar yang menjadi tidak
    // terjangkau dari sidebar.
    render(<Sidebar permissions={ALL_PERMISSIONS} />);
    fireEvent.click(screen.getByRole("button", { name: /lainnya/i }));

    for (const item of NAV_ITEMS) {
      expect(
        screen.getByRole("link", { name: new RegExp(item.label, "i") }),
        item.href,
      ).toBeDefined();
    }
  });

  it("menutup Lainnya secara bawaan supaya sidebar tetap pendek", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    expect(screen.queryByRole("link", { name: /pola/i })).toBeNull();
    expect(screen.getByRole("button", { name: /lainnya/i }).getAttribute("aria-expanded")).toBe(
      "false",
    );
  });

  it("menandai menu yang sedang aktif untuk pembaca layar", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    const active = screen.getByRole("link", { name: /beranda/i });
    expect(active.getAttribute("aria-current")).toBe("page");
  });

  it("menyembunyikan menu yang tidak dapat dipakai peran itu sama sekali", () => {
    // Kewenangan Pimpinan yang sebenarnya, disalin dari config/rbac/permissions.yaml.
    // Ia tidak memegang satu pun izin tulis maupun pengelolaan pengguna.
    const pimpinan = [
      "analytics:read",
      "audit:read",
      "citizen_report:read",
      "commander_decision:approve",
      "commander_decision:read",
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

    expect(screen.queryByRole("link", { name: /input data/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /admin/i })).toBeNull();
    expect(screen.getByRole("link", { name: /keputusan/i })).toBeDefined();
    expect(screen.getByRole("link", { name: /audit/i })).toBeDefined();
  });

  it("tidak menampilkan menu apa pun ketika kewenangan tidak diketahui", () => {
    // Kegagalan memuat profil tidak boleh berubah menjadi sidebar yang menjanjikan lebih
    // banyak daripada yang dapat dibuka.
    render(<Sidebar permissions={[]} />);

    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });

  it("menampilkan lencana jumlah keputusan yang menunggu", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} pendingDecisions={19} />);

    expect(screen.getByText("19")).toBeDefined();
    expect(screen.getByText("19 rekomendasi menunggu keputusan Anda")).toBeDefined();
  });

  it("tidak menggambar lencana ketika tidak ada yang menunggu", () => {
    render(<Sidebar permissions={ALL_PERMISSIONS} pendingDecisions={0} />);

    expect(screen.queryByText(/menunggu keputusan Anda/)).toBeNull();
  });

  it("meletakkan kelompok Putuskan lebih dulu daripada kelompok lain", () => {
    // Bagi Pimpinan, Keputusan adalah satu-satunya menu berisi sesuatu yang hanya dapat
    // diselesaikan olehnya. Sebelumnya ia berada di urutan kesembilan.
    render(<Sidebar permissions={ALL_PERMISSIONS} />);

    const links = screen.getAllByRole("link");
    expect(links[0].getAttribute("href")).toBe("/rekomendasi");
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
