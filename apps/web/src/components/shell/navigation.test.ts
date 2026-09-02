import { describe, expect, it } from "vitest";
import { groupedNavItems, NAV_GROUPS, NAV_ITEMS, visibleNavItems } from "./navigation";

/**
 * Penyaringan menu diuji sebagai fungsi murni, terpisah dari komponennya.
 *
 * Yang dijaga bukan susunan visualnya, melainkan satu aturan: **menu tampil hanya bila
 * penggunanya memegang setidaknya satu permission yang membuat layarnya bermakna.**
 */
describe("penyaringan menu menurut kewenangan", () => {
  it("menyembunyikan Input Data dari peran tanpa satu pun izin tulis", () => {
    const readerOnly = ["dashboard:read", "crime:read", "citizen_report:read"];

    expect(visibleNavItems(readerOnly).map((item) => item.href)).not.toContain("/input");
  });

  it("menampilkan Input Data begitu satu izin tulis dipegang", () => {
    expect(visibleNavItems(["crime:write"]).map((item) => item.href)).toContain("/input");
    expect(visibleNavItems(["citizen_report:write"]).map((item) => item.href)).toContain("/input");
  });

  it("menjawab daftar kosong untuk kewenangan kosong", () => {
    expect(visibleNavItems([])).toHaveLength(0);
    expect(groupedNavItems([])).toHaveLength(0);
  });

  it("membuang kelompok yang tidak menyisakan satu pun menu", () => {
    const sections = groupedNavItems(["dashboard:read"]);

    expect(sections.map((section) => section.group)).toEqual(["pantau"]);
    expect(sections[0].items.map((item) => item.href)).toEqual(["/", "/brief"]);
  });

  it("mengurutkan kelompok sesuai NAV_GROUPS, dengan Putuskan lebih dulu", () => {
    const all = [...new Set(NAV_ITEMS.flatMap((item) => item.permissions))];
    const sections = groupedNavItems(all);

    expect(sections.map((section) => section.group)).toEqual(NAV_GROUPS.map((group) => group.id));
    expect(sections[0].group).toBe("putuskan");
  });

  it("memberi setiap menu setidaknya satu permission", () => {
    // Menu tanpa permission akan lolos penyaringan untuk semua orang, termasuk pengguna
    // yang tidak dapat membukanya — persis keadaan yang ingin diperbaiki.
    for (const item of NAV_ITEMS) {
      expect(item.permissions.length, `${item.href} tidak menyebut permission`).toBeGreaterThan(0);
    }
  });

  it("memakai nama permission berbentuk resource:action", () => {
    for (const item of NAV_ITEMS) {
      for (const name of item.permissions) {
        expect(name, `${item.href}: ${name}`).toMatch(/^[a-z_]+:[a-z_]+$/);
      }
    }
  });
});
