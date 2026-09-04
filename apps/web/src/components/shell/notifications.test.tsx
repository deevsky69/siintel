import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { NotificationFeed } from "@/lib/notifications";
import { NotificationBell } from "./notification-bell";

/**
 * Yang dijaga di sini adalah sifat **antrean pekerjaan**, bukan tata letak lonceng.
 *
 * Lencana notifikasi punya satu cara khas untuk gagal: ia perlahan berubah menjadi umpan
 * berita yang selalu merah, lalu berhenti dilihat siapa pun. Test di bawah menjaga tiga
 * hal yang mencegahnya — angka nol yang jujur, jalan menuju pekerjaannya, dan antrean
 * kosong yang tetap terlihat.
 */

const feed: NotificationFeed = {
  reference_time: "2025-12-31T21:00:00+07:00",
  demo_clock: true,
  role: "Pimpinan",
  total: 20,
  basis: "Notifikasi di sini adalah pekerjaan yang MENUNGGU ANDA.",
  groups: [
    {
      kind: "DECISION",
      title: "Menunggu keputusan Anda",
      action: "Setujui, modifikasi, atau tolak",
      href: "/rekomendasi",
      total: 20,
      items: [
        { code: "REC-0009", headline: "Untuk SAMAPTA", detail: "Tebet · Tingkatkan patroli" },
      ],
    },
    {
      kind: "WARNING",
      title: "Peringatan belum diterima",
      action: "Terima atau selesaikan",
      href: "/peringatan",
      total: 0,
      items: [],
    },
  ],
};

describe("lonceng antrean pekerjaan", () => {
  it("menampilkan jumlah pekerjaan yang menunggu", () => {
    render(<NotificationBell feed={feed} />);

    expect(screen.getByRole("button", { name: "20 pekerjaan menunggu Anda" })).toBeDefined();
  });

  it("menyatakan keadaan kosong sebagai kosong, bukan menyembunyikan lonceng", () => {
    // Lonceng yang hilang saat kosong membuat pengguna tidak dapat membedakan "tidak ada
    // pekerjaan" dari "notifikasinya rusak".
    render(<NotificationBell feed={{ ...feed, total: 0, groups: [] }} />);

    expect(screen.getByRole("button", { name: "Tidak ada pekerjaan yang menunggu" })).toBeDefined();
  });

  it("membuka panel hanya setelah ditekan", () => {
    render(<NotificationBell feed={feed} />);

    expect(screen.queryByText("Menunggu keputusan Anda")).toBeNull();

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByText("Menunggu keputusan Anda")).toBeDefined();
  });

  it("memberi setiap antrean jalan menuju pekerjaannya", () => {
    // Notifikasi tanpa jalan menuju pekerjaannya hanya pemberitahuan.
    render(<NotificationBell feed={feed} />);
    fireEvent.click(screen.getByRole("button", { name: /pekerjaan menunggu/ }));

    expect(screen.getByRole("link", { name: /Menunggu keputusan Anda/ }).getAttribute("href")).toBe(
      "/rekomendasi",
    );
  });

  it("mempertahankan antrean yang kosong, tidak membuangnya", () => {
    // "Nol peringatan menunggu" adalah kabar baik yang pantas terbaca; menghilangkan
    // barisnya membuat pembaca tidak dapat membedakan "tidak ada" dari "tidak diperiksa".
    render(<NotificationBell feed={feed} />);
    fireEvent.click(screen.getByRole("button", { name: /pekerjaan menunggu/ }));

    expect(screen.getByText("Peringatan belum diterima")).toBeDefined();
    expect(screen.getByText("Tidak ada yang menunggu.")).toBeDefined();
  });

  it("menjelaskan bahwa angkanya tidak dapat dihilangkan tanpa mengerjakannya", () => {
    // Penanda "sudah dibaca" pada antrean tugas berubah menjadi cara melupakan tugas.
    render(<NotificationBell feed={feed} />);
    fireEvent.click(screen.getByRole("button", { name: /pekerjaan menunggu/ }));

    expect(screen.getByText(/hanya turun ketika pekerjaannya selesai/)).toBeDefined();
  });

  it("menjelaskan peran yang memang tidak punya antrean", () => {
    render(<NotificationBell feed={{ ...feed, role: "Fungsi", total: 0, groups: [] }} />);
    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByText(/Itu bukan kekeliruan/)).toBeDefined();
  });
});
