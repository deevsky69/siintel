import { describe, expect, it } from "vitest";
import {
  groupedNavItems,
  isPrimaryFor,
  NAV_GROUPS,
  NAV_ITEMS,
  secondaryNavItems,
  visibleNavItems,
} from "./navigation";

/** Kewenangan Pimpinan yang sebenarnya, disalin dari config/rbac/permissions.yaml. */
const PIMPINAN = [
  "analytics:read",
  "audit:read",
  "citizen_report:read",
  "commander_decision:approve",
  "commander_decision:read",
  "community_feedback:read",
  "config:read",
  "crime:read",
  "dashboard:read",
  "evaluation:read",
  "evaluation:run",
  "intelligence:read",
  "location:read",
  "map:read",
  "operation:read",
  "patrol:read",
  "police_unit:read",
  "prediction:read",
  "public_alert:read",
  "recommendation:read",
  "risk_score:read",
  "warning:read",
];

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

  it("tidak menghilangkan satu pun menu: utama dan lainnya menjumlah seluruh yang terlihat", () => {
    // "Lainnya" memindahkan menu keluar dari jalur harian, bukan menghapusnya. Bila
    // penjumlahan ini meleset, ada layar yang tidak dapat dicapai dari sidebar sama sekali.
    for (const held of [PIMPINAN, ["crime:write", "dashboard:read"], ["map:read"]]) {
      const visible = visibleNavItems(held)
        .map((item) => item.href)
        .sort();
      const split = [
        ...groupedNavItems(held).flatMap((section) => section.items),
        ...secondaryNavItems(held),
      ]
        .map((item) => item.href)
        .sort();

      expect(split).toEqual(visible);
    }
  });
});

describe("pemisahan menu utama dan lainnya", () => {
  it("menaruh tepat tujuh menu utama bagi Pimpinan", () => {
    // Aturannya diturunkan dari kewenangan, bukan dari daftar per peran yang ditulis
    // tangan: menu utama = yang dapat dikerjakan penggunanya, ditambah layar inti.
    const primary = groupedNavItems(PIMPINAN).flatMap((section) => section.items);

    expect(primary.map((item) => item.href)).toEqual([
      "/rekomendasi",
      "/peringatan",
      "/",
      "/brief",
      "/peta",
      "/evaluasi",
      "/audit",
    ]);
  });

  it("menyisihkan menu yang hanya dapat dibaca Pimpinan ke Lainnya", () => {
    const secondary = secondaryNavItems(PIMPINAN).map((item) => item.href);

    // Pimpinan memegang `prediction:read` tetapi tidak `prediction:run` maupun
    // `prediction:publish`; layar itu hanya dapat ditonton olehnya.
    expect(secondary).toContain("/prediksi");
    expect(secondary).toContain("/skoring");
    expect(secondary).toContain("/masyarakat");
    expect(secondary).not.toContain("/rekomendasi");
  });

  it("menjadikan menu utama begitu satu izin tindakannya dipegang", () => {
    const reader = ["prediction:read"];
    const runner = ["prediction:read", "prediction:run"];
    const item = NAV_ITEMS.find((row) => row.href === "/prediksi");
    if (!item) throw new Error("menu /prediksi tidak ditemukan");

    expect(isPrimaryFor(item, reader)).toBe(false);
    expect(isPrimaryFor(item, runner)).toBe(true);
  });

  it("mempertahankan layar inti sebagai menu utama walau tidak ada yang dapat dikerjakan", () => {
    // Beranda, Brief, Peta, Peringatan, dan Audit adalah konteks untuk mengambil
    // keputusan. Menyembunyikannya berarti menuntut keputusan tanpa konteks.
    for (const href of ["/", "/brief", "/peta", "/peringatan", "/audit"]) {
      const item = NAV_ITEMS.find((row) => row.href === href);
      if (!item) throw new Error(`menu ${href} tidak ditemukan`);
      expect(isPrimaryFor(item, []), href).toBe(true);
    }
  });

  it("menjadikan Keputusan menu utama bagi setiap peran yang dapat membacanya", () => {
    // Keputusan pemilik proyek, 2 September 2026. Aturan "utama = yang dapat dikerjakan"
    // sempat menaruhnya di Lainnya bagi Fungsi dan Polsek karena keduanya hanya membaca —
    // benar menurut aturan, salah menurut kenyataan: rekomendasi DIALAMATKAN kepada fungsi
    // tertentu, dan yang dialamati membacanya setiap hari.
    const fungsi = ["dashboard:read", "map:read", "recommendation:read", "crime:write"];
    const polsek = [...fungsi, "citizen_report:read", "citizen_report:write"];

    for (const held of [fungsi, polsek]) {
      const primary = groupedNavItems(held).flatMap((section) => section.items);

      expect(primary.map((item) => item.href)).toContain("/rekomendasi");
      expect(secondaryNavItems(held).map((item) => item.href)).not.toContain("/rekomendasi");
    }
  });

  it("menempatkan Keputusan paling atas bagi peran mana pun yang melihatnya", () => {
    const fungsi = ["dashboard:read", "map:read", "recommendation:read", "crime:write"];
    const primary = groupedNavItems(fungsi).flatMap((section) => section.items);

    expect(primary[0]?.href).toBe("/rekomendasi");
  });

  it("mengurutkan kelompok sesuai NAV_GROUPS, dengan Putuskan lebih dulu", () => {
    // `actions` ikut dibawa: tanpanya seluruh menu menjadi hanya-baca dan pindah ke
    // kelompok Lainnya, sehingga urutan kelompok tidak teruji sama sekali.
    const all = [...new Set(NAV_ITEMS.flatMap((item) => [...item.permissions, ...item.actions]))];
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
