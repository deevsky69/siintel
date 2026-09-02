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
    expect(NAV_GROUPS.map((group) => group.id)).toEqual([
      "pemantauan",
      "laporan",
      "analisis",
      "operasi",
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

  it("mempertahankan seluruh layar rantai tertutup di dalam menu", () => {
    // Prediksi dan Evaluasi tidak disebut dalam permintaan, tetapi menghilangkannya
    // memutus rantai yang menjadi inti sistem ini: tanpa keduanya tidak ada yang dapat
    // menunjukkan bahwa ramalannya pernah diuji terhadap kenyataan (CLAUDE.md §9).
    const routes = NAV_ITEMS.map((item) => item.href);

    for (const href of ["/prediksi", "/evaluasi", "/rekomendasi", "/peringatan", "/skoring"]) {
      expect(routes, `${href} hilang dari menu`).toContain(href);
    }
  });
});

describe("penyaringan menu menurut kewenangan", () => {
  it("menyembunyikan Input Data dari peran tanpa satu pun izin tulis", () => {
    const readerOnly = ["dashboard:read", "crime:read", "citizen_report:read"];

    expect(visibleNavItems(readerOnly).map((item) => item.href)).not.toContain("/input");
  });

  it("menampilkan Input Data begitu satu izin tulis dipegang", () => {
    expect(visibleNavItems(["crime:write"]).map((item) => item.href)).toContain("/input");
  });

  it("membuang kelompok yang tidak menyisakan satu pun submenu", () => {
    // Judul kelompok yang membuka daftar kosong hanya menjanjikan sesuatu yang tidak ada.
    const groups = visibleNavGroups(["dashboard:read"]);

    expect(groups.map((group) => group.id)).toEqual(["pemantauan", "operasi"]);
    expect(groups[0].items.map((item) => item.href)).toEqual(["/"]);
  });

  it("menjawab menu kosong untuk kewenangan kosong", () => {
    expect(visibleNavGroups([])).toHaveLength(0);
    expect(visibleNavItems([])).toHaveLength(0);
  });

  it("menyembunyikan Manajemen Pengguna dan Input Data dari Pimpinan", () => {
    // Pimpinan tidak memegang satu pun izin tulis maupun pengelolaan pengguna.
    const routes = visibleNavItems(PIMPINAN).map((item) => item.href);

    expect(routes).not.toContain("/admin");
    expect(routes).not.toContain("/input");
    expect(routes).toContain("/audit");
    expect(routes).toContain("/pengaturan");
  });
});

describe("kelompok yang sedang aktif", () => {
  it("mengenali kelompok dari rutenya", () => {
    expect(groupOf("/")).toBe("pemantauan");
    expect(groupOf("/peta")).toBe("pemantauan");
    expect(groupOf("/masyarakat")).toBe("laporan");
    expect(groupOf("/analitik")).toBe("analisis");
    expect(groupOf("/operasi")).toBe("operasi");
    expect(groupOf("/audit")).toBe("sistem");
  });

  it("mengenali rute turunan sebagai bagian submenunya", () => {
    // `/wilayah/Tebet` harus tetap membuka kelompok Analisis.
    expect(groupOf("/wilayah/Tebet")).toBe("analisis");
    expect(groupOf("/peta?wilayah=Tebet")).toBe("pemantauan");
  });

  it("mencocokkan Beranda persis, bukan sebagai awalan", () => {
    // `/` adalah awalan dari setiap rute; dicocokkan sebagai awalan, seluruh halaman akan
    // menandai Beranda sebagai halaman yang sedang dibuka.
    expect(groupOf("/audit")).not.toBe(groupOf("/") === "sistem" ? "sistem" : "x");
    expect(groupOf("/audit")).toBe("sistem");
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
