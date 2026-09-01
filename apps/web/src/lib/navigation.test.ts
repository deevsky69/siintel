import { describe, expect, it } from "vitest";
import { DEFAULT_PATH, safeNextPath } from "@/lib/navigation";

describe("tujuan pengalihan setelah masuk", () => {
  it("menerima lintasan relatif dalam aplikasi", () => {
    expect(safeNextPath("/peta")).toBe("/peta");
    expect(safeNextPath("/evaluasi?tahun=2025")).toBe("/evaluasi?tahun=2025");
  });

  it("menolak origin lain", () => {
    // Tautan seperti /masuk?lanjut=https://situs-palsu adalah jalur phishing yang
    // meyakinkan justru karena berawal dari domain yang sah.
    expect(safeNextPath("https://situs-palsu.example")).toBe(DEFAULT_PATH);
    expect(safeNextPath("http://situs-palsu.example")).toBe(DEFAULT_PATH);
  });

  it("menolak bentuk protokol-relatif", () => {
    expect(safeNextPath("//situs-palsu.example")).toBe(DEFAULT_PATH);
    expect(safeNextPath("/\\situs-palsu.example")).toBe(DEFAULT_PATH);
  });

  it("menolak skema selain lintasan", () => {
    expect(safeNextPath("javascript:alert(1)")).toBe(DEFAULT_PATH);
    expect(safeNextPath("data:text/html,x")).toBe(DEFAULT_PATH);
  });

  it("memakai halaman utama bila tidak ada tujuan", () => {
    expect(safeNextPath(null)).toBe(DEFAULT_PATH);
    expect(safeNextPath("")).toBe(DEFAULT_PATH);
    expect(safeNextPath("   ")).toBe(DEFAULT_PATH);
  });
});
