import { describe, expect, it } from "vitest";
import type { ProductStatus } from "@/lib/monthly-products";
import { buildCards } from "./board";

/**
 * Papan "Bulan ini" — tiga tahap sejak 17 November 2026: staf menyusun, Kasat menelaah,
 * Pimpinan menetapkan. Kartu produk hanya menandai giliran peran yang memang dinanti.
 */
const STAF = ["monthly_product:read", "monthly_product:draft"];
const KASAT = ["monthly_product:read", "monthly_product:validate"];
const PIMPINAN = ["monthly_product:read", "monthly_product:decide"];
const ADMIN = ["monthly_product:read"];

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
    expect(produk(STAF, "DRAFT").cta).toContain("Kasat Intelkam");
    expect(produk(KASAT, "DRAFT").mine).toBe(false);
    expect(produk(PIMPINAN, "DRAFT").mine).toBe(false);
  });

  it("yang sudah diperiksa staf menunggu telaah Kasat", () => {
    for (const status of ["ANALYST_REVIEWED", "KBO_CHECKED"] as const) {
      expect(produk(KASAT, status).mine).toBe(true);
      expect(produk(KASAT, status).state).toBe("Menunggu telaah Kasat Intelkam");
      expect(produk(PIMPINAN, status).mine).toBe(false);
      expect(produk(STAF, status).mine).toBe(false);
    }
  });

  it("Pimpinan baru dinanti setelah Kasat meneruskan", () => {
    expect(produk(PIMPINAN, "VALIDATED").mine).toBe(true);
    expect(produk(PIMPINAN, "VALIDATED").state).toBe("Menunggu penetapan Pimpinan");
    expect(produk(KASAT, "VALIDATED").mine).toBe(false);
  });

  it("Administrator tidak pernah mendapat giliran di rantai ini", () => {
    for (const status of [null, "DRAFT", "ANALYST_REVIEWED", "VALIDATED", "DECIDED"] as const) {
      expect(produk(ADMIN, status).mine).toBe(false);
      expect(produk(ADMIN, status).cta).toBeNull();
    }
  });
});
