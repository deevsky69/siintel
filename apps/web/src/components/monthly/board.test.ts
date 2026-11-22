import { describe, expect, it } from "vitest";
import type { ProductStatus } from "@/lib/monthly-products";
import { buildCards } from "./board";

/**
 * Papan "Bulan ini" — lima pemeriksa sejak 21 November 2026 (naskah Taskap revisi): analis
 * menyusun, KBO memeriksa mutu, Wakasat memeriksa, Kasat menelaah, Pimpinan menetapkan. Kartu
 * produk hanya menandai giliran peran yang memang dinanti.
 */
const STAF = ["monthly_product:read", "monthly_product:draft"];
const KBO = ["monthly_product:read", "monthly_product:review"];
const WAKASAT = ["monthly_product:read", "monthly_product:examine"];
const KASAT = ["monthly_product:read", "monthly_product:validate"];
const PIMPINAN = ["monthly_product:read", "monthly_product:decide"];
const PEMBACA = ["monthly_product:read"];

function produk(permissions: string[], status: ProductStatus | null) {
  const cards = buildCards({
    permissions,
    month: "2026-01",
    summary: status ? { target_month: "2026-01", status, priority_count: null } : null,
    product: null,
    evaluation: null,
    pendingBulletins: 0,
  } as unknown as Parameters<typeof buildCards>[0]);
  const card = cards.find((item) => item.key === "produk");
  if (!card) throw new Error("kartu produk tidak ada");
  return card;
}

describe("papan bulanan — giliran tiap peran", () => {
  it("draf adalah giliran staf, bukan Kasat atau Pimpinan", () => {
    expect(produk(STAF, "DRAFT").mine).toBe(true);
    expect(produk(STAF, "DRAFT").cta).toContain("KBO");
    expect(produk(KASAT, "DRAFT").mine).toBe(false);
    expect(produk(PIMPINAN, "DRAFT").mine).toBe(false);
  });

  it("yang sudah diperiksa analis menunggu KBO, lalu Wakasat, lalu Kasat", () => {
    expect(produk(KBO, "ANALYST_REVIEWED").mine).toBe(true);
    expect(produk(KBO, "ANALYST_REVIEWED").state).toBe("Menunggu pemeriksaan mutu KBO");
    expect(produk(WAKASAT, "ANALYST_REVIEWED").mine).toBe(false);
    expect(produk(WAKASAT, "KBO_CHECKED").mine).toBe(true);
    expect(produk(WAKASAT, "KBO_CHECKED").state).toBe("Menunggu pemeriksaan Wakasat Intelkam");
    // Kasat baru dinanti setelah Wakasat meneruskan — bukan langsung sesudah KBO.
    expect(produk(KASAT, "KBO_CHECKED").mine).toBe(false);
    expect(produk(KASAT, "WAKASAT_CHECKED").mine).toBe(true);
    expect(produk(KASAT, "WAKASAT_CHECKED").state).toBe("Menunggu telaah Kasat Intelkam");
    expect(produk(WAKASAT, "WAKASAT_CHECKED").mine).toBe(false);
    for (const status of ["ANALYST_REVIEWED", "KBO_CHECKED", "WAKASAT_CHECKED"] as const) {
      expect(produk(PIMPINAN, status).mine).toBe(false);
      expect(produk(STAF, status).mine).toBe(false);
    }
  });

  it("Pimpinan baru dinanti setelah Kasat meneruskan", () => {
    expect(produk(PIMPINAN, "VALIDATED").mine).toBe(true);
    expect(produk(PIMPINAN, "VALIDATED").state).toBe("Menunggu penetapan Pimpinan");
    expect(produk(KASAT, "VALIDATED").mine).toBe(false);
  });

  it("peran yang hanya membaca tidak pernah mendapat giliran di rantai ini", () => {
    for (const status of [
      null,
      "DRAFT",
      "ANALYST_REVIEWED",
      "KBO_CHECKED",
      "WAKASAT_CHECKED",
      "VALIDATED",
      "DECIDED",
    ] as const) {
      expect(produk(PEMBACA, status).mine).toBe(false);
      expect(produk(PEMBACA, status).cta).toBeNull();
    }
  });

  it("menampilkan tiga kartu seperti Lampiran M naskah; pelaksanaan dilebur ke kartu Produk", () => {
    const semua = [...STAF, ...KBO, ...WAKASAT, ...KASAT, ...PIMPINAN, "monthly_product:execute"];
    const cards = buildCards({
      permissions: [...semua, "evaluation:read", "bulletin:approve"],
      month: "2026-01",
      summary: { target_month: "2026-01", status: "DECIDED", priority_count: 2 },
      product: {
        items: [
          { selected: true, actions: [{}, {}] },
          { selected: true, actions: [{}] },
          { selected: false, actions: [] },
        ],
      },
      evaluation: null,
      citizen: { draftBulletins: 0 },
    } as unknown as Parameters<typeof buildCards>[0]);
    expect(cards.map((card) => card.key)).toEqual(["produk", "evaluasi", "warga"]);
    expect(cards[0]?.state).toBe("Ditetapkan · 2 kelurahan prioritas · 3 kegiatan tercatat");
    expect(cards[0]?.cta).toBe("Catat kegiatan");
    expect(cards[0]?.mine).toBe(true);
  });
});
