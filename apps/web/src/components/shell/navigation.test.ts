import { describe, expect, it } from "vitest";
import { groupOf, NAV_GROUPS, NAV_ITEMS, visibleNavGroups, visibleNavItems } from "./navigation";

/** Kewenangan Pimpinan yang sebenarnya, disalin dari config/rbac/permissions.yaml. */
const PIMPINAN = [
  "analytics:read",
  "audit:read",
  "citizen_report:read",
  "commander_decision:approve",
  "commander_decision:read",
  "config:read",
  "crime:read",
  "dashboard:read",
  "evaluation:read",
  "evaluation:run",
  "intelligence:read",
  "map:read",
  "operation:read",
  "prediction:read",
  "recommendation:read",
  "risk_score:read",
  "warning:read",
];

const ALL = [...new Set(NAV_ITEMS.flatMap((item) => item.permissions))];

describe("susunan menu", () => {
  it("memakai lima kelompok sesuai permintaan pemilik proyek", () => {
    // 6 November 2026: mengikuti siklus bulanan "Mekanisme dan Fungsi SIGAP".
    expect(NAV_GROUPS.map((group) => group.id)).toEqual([
      "pemantauan",
      "bulanan",
      "laporan",
      "warga",
      "sistem",
    ]);
  });

  it("memberi setiap submenu setidaknya satu permission", () => {
    // Submenu tanpa permission lolos penyaringan untuk semua orang, termasuk yang tidak
    // dapat membukanya — persis keadaan yang ingin diperbaiki penyaringan ini.
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

  it("tidak memuat rute ganda", () => {
    // Rute yang muncul di dua kelompok membuat penanda "sedang aktif" menyala di dua
    // tempat sekaligus, dan pengguna kehilangan jejak posisinya.
    const routes = NAV_ITEMS.map((item) => item.href);

    expect(new Set(routes).size).toBe(routes.length);
  });

  it("mempertahankan seluruh layar siklus bulanan di dalam menu", () => {
    // Rantai tertutup versi bulanan (Mekanisme dan Fungsi SIGAP): peringkat → produk →
    // evaluasi. Tanpa evaluasi tidak ada yang menunjukkan peringkatnya pernah diuji.
    const routes = NAV_ITEMS.map((item) => item.href);

    for (const href of [
      "/ops/peringkat",
      "/ops/produk-bulanan",
      "/ops/evaluasi-bulanan",
      "/ops/pembakuan",
    ]) {
      expect(routes, `${href} hilang dari menu`).toContain(href);
    }
    // Layar harian keluar dari menu (rutenya tetap ada).
    for (const href of ["/ops/prediksi", "/ops/peringatan", "/ops/skoring", "/ops/rekomendasi"]) {
      expect(routes, `${href} masih di menu`).not.toContain(href);
    }
  });
});

describe("penyaringan menu menurut kewenangan", () => {
  it("menyembunyikan Input Data dari peran tanpa satu pun izin tulis", () => {
    const readerOnly = ["dashboard:read", "crime:read", "citizen_report:read"];

    expect(visibleNavItems(readerOnly).map((item) => item.href)).not.toContain("/ops/input");
  });

  it("menampilkan Input Data begitu satu izin tulis dipegang", () => {
    expect(visibleNavItems(["crime:write"]).map((item) => item.href)).toContain("/ops/input");
  });

  it("membuang kelompok yang tidak menyisakan satu pun submenu", () => {
    // Judul kelompok yang membuka daftar kosong hanya menjanjikan sesuatu yang tidak ada.
    const groups = visibleNavGroups(["dashboard:read"]);

    expect(groups.map((group) => group.id)).toEqual(["pemantauan"]);
    expect(groups[0].items.map((item) => item.href)).toEqual(["/ops"]);
  });

  it("menjawab menu kosong untuk kewenangan kosong", () => {
    expect(visibleNavGroups([])).toHaveLength(0);
    expect(visibleNavItems([])).toHaveLength(0);
  });

  it("menyembunyikan Manajemen Pengguna dan Input Data dari Pimpinan", () => {
    // Pimpinan tidak memegang satu pun izin tulis maupun pengelolaan pengguna.
    const routes = visibleNavItems(PIMPINAN).map((item) => item.href);

    expect(routes).not.toContain("/ops/admin");
    expect(routes).not.toContain("/ops/input");
    expect(routes).toContain("/ops/audit");
    expect(routes).toContain("/ops/pengaturan");
  });
});

describe("kelompok yang sedang aktif", () => {
  it("mengenali kelompok dari rutenya", () => {
    expect(groupOf("/ops")).toBe("pemantauan");
    expect(groupOf("/ops/peta")).toBe("pemantauan");
    expect(groupOf("/ops/masyarakat")).toBe("laporan");
    expect(groupOf("/ops/analitik")).toBe("pemantauan");
    expect(groupOf("/ops/produk-bulanan")).toBe("bulanan");
    expect(groupOf("/ops/babin")).toBe("warga");
    expect(groupOf("/ops/audit")).toBe("sistem");
  });

  it("mengenali rute turunan sebagai bagian submenunya", () => {
    // `/ops/wilayah/Tebet` harus tetap membuka kelompok Wilayah.
    expect(groupOf("/ops/wilayah/Tebet")).toBe("pemantauan");
    expect(groupOf("/ops/peta?wilayah=Tebet")).toBe("pemantauan");
  });

  it("mencocokkan Beranda persis, bukan sebagai awalan", () => {
    // `/` adalah awalan dari setiap rute; dicocokkan sebagai awalan, seluruh halaman akan
    // menandai Beranda sebagai halaman yang sedang dibuka.
    expect(groupOf("/ops/audit")).not.toBe(groupOf("/ops") === "sistem" ? "sistem" : "x");
    expect(groupOf("/ops/audit")).toBe("sistem");
  });

  it("menjawab null untuk rute di luar menu", () => {
    expect(groupOf("/tidak-ada")).toBeNull();
  });
});

describe("kelengkapan", () => {
  it("menampilkan seluruh submenu bagi pemegang seluruh kewenangan", () => {
    expect(visibleNavItems(ALL)).toHaveLength(NAV_ITEMS.length);
  });
});
