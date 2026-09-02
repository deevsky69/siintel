import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuditPage, AuditSummary } from "@/lib/audit";
import { readFilters } from "@/lib/audit";
import { AuditBoard } from "./audit-board";

const page: AuditPage = {
  data: [
    {
      code: "AUD-0001",
      timestamp: "2025-12-31T14:00:00+00:00",
      timestamp_wib: "2025-12-31T21:00:00+07:00",
      action: "APPROVE_RECOMMENDATION",
      resource_type: "recommendation",
      resource_id: "REC-0006",
      result: "SUCCESS",
      detail: { decision: "APPROVED" },
      username: "demo.pimpinan",
      user_code: "USER-001",
    },
    {
      code: "AUD-0002",
      timestamp: "2025-12-31T13:00:00+00:00",
      timestamp_wib: "2025-12-31T20:00:00+07:00",
      action: "SYSTEM_SEED",
      resource_type: "system",
      resource_id: null,
      result: "SUCCESS",
      detail: null,
      username: null,
      user_code: null,
    },
  ],
  pagination: { total_items: 2, page: 1, page_size: 50 },
  filter_basis: "Rentang tanggal dibaca sebagai waktu setempat (WIB).",
  scope_basis: "Jejak audit tidak dapat dibatasi per wilayah.",
  append_only_basis: "Jejak audit bersifat hanya-tambah.",
};

const summary: AuditSummary = {
  total: 206,
  per_result: { SUCCESS: 168, DENIED: 22, FAILED: 16 },
  per_action: [{ key: "LOGIN", count: 141 }],
  per_resource_type: [{ key: "user", count: 14 }],
  recent_refusals: [
    {
      code: "AUD-0100",
      timestamp_wib: "2025-12-31T20:30:00+07:00",
      action: "MANAGE_USER",
      result: "DENIED",
      resource_type: "user",
      resource_id: null,
      username: "demo.pimpinan",
      detail: { reason: "permission 'user:manage' tidak dimiliki role Pimpinan" },
    },
  ],
  earliest: "2025-12-01T00:00:00+00:00",
  latest: "2025-12-31T14:00:00+00:00",
  denied_basis: "DENIED berarti ditolak karena kewenangan; FAILED melanggar aturan bisnis.",
  scope_basis: "Jejak audit tidak dapat dibatasi per wilayah.",
  append_only_basis: "Jejak audit bersifat hanya-tambah.",
};

const panel = (title: string) => {
  const section = screen.getByRole("heading", { name: title }).closest("section");
  if (!section) throw new Error(`panel "${title}" tidak ditemukan`);
  return within(section);
};

const board = (props: Partial<Parameters<typeof AuditBoard>[0]> = {}) =>
  render(<AuditBoard page={page} summary={summary} filters={{}} {...props} />);

describe("papan jejak audit", () => {
  it("membuka penolakan lebih dulu, bukan keberhasilan", () => {
    // Audit yang menonjolkan keberhasilan tidak dapat dipakai menilai apakah pembatasan
    // kewenangan bekerja. Urutan panel di sini adalah bagian dari maknanya.
    board();

    const headings = screen.getAllByRole("heading").map((node) => node.textContent);
    expect(headings[0]).toBe("Percobaan yang Ditolak");
  });

  it("menjumlahkan penolakan dan kegagalan sebagai satu angka", () => {
    board();

    expect(panel("Percobaan yang Ditolak").getByText("38")).toBeDefined();
  });

  it("membedakan ditolak karena kewenangan dari gagal karena aturan", () => {
    board();

    expect(screen.getAllByText(/Ditolak — kewenangan/).length).toBeGreaterThan(0);
    expect(panel("Percobaan yang Ditolak").getByText(/tidak dimiliki role Pimpinan/)).toBeDefined();
  });

  it("menandai peristiwa sistem, bukan mengisinya dengan nama pengganti", () => {
    board();

    expect(panel("Seluruh Catatan").getByText(/peristiwa sistem, tanpa pengguna/)).toBeDefined();
  });

  it("menyatakan sifat hanya-tambah pada layar", () => {
    // Sifat ini yang membuat jejak audit bernilai sebagai bukti; menyembunyikannya di
    // kode saja membuat pembaca layar tidak punya cara tahu.
    board();

    expect(panel("Seluruh Catatan").getByText(/hanya-tambah/)).toBeDefined();
  });

  it("menyatakan bahwa jejak audit tidak dapat dibatasi per wilayah", () => {
    board();

    expect(panel("Seluruh Catatan").getByText(/tidak dapat dibatasi per wilayah/)).toBeDefined();
  });

  it("menyatakan keadaan kosong, bukan menampilkan nol", () => {
    board({
      page: { ...page, data: [], pagination: { ...page.pagination, total_items: 0 } },
      summary: { ...summary, recent_refusals: [] },
    });

    expect(screen.getByText(/Tidak ada percobaan yang ditolak/i)).toBeDefined();
    expect(screen.getByText(/Tidak ada catatan yang cocok/i)).toBeDefined();
  });

  it("tautan penyaring mempertahankan penyaring lain yang sedang aktif", () => {
    board({ filters: { action: "LOGIN", result: "DENIED" } });

    const link = panel("Seluruh Catatan").getByRole("link", { name: /Berhasil/ });
    expect(link.getAttribute("href")).toContain("aksi=LOGIN");
    expect(link.getAttribute("href")).toContain("hasil=SUCCESS");
  });
});

describe("membaca penyaring dari URL", () => {
  it("menerima hasil yang sah", () => {
    expect(readFilters({ hasil: "DENIED" }).result).toBe("DENIED");
  });

  it("membuang nilai asing alih-alih menggemakannya", () => {
    // Menggemakan masukan yang tak dikenal kembali ke query backend hanya memindahkan
    // penolakannya ke tempat yang lebih jauh dari penyebabnya.
    expect(readFilters({ hasil: "<script>" }).result).toBeUndefined();
  });
});
