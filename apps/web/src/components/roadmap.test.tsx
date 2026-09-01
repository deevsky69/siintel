import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RoadmapPage } from "@/components/roadmap";

describe("halaman menu yang belum dibangun", () => {
  const page = () =>
    render(
      <RoadmapPage
        title="Analytics"
        purpose="Analisis pola kejahatan lintas waktu dan wilayah."
        tasks={[{ code: "TASK 090-094", detail: "Crime Pattern DNA" }]}
        ready={[{ label: "1.200 kejadian tersimpan" }, { label: "Tren bulanan", href: "/" }]}
      />,
    );

  it("menyatakan terus terang bahwa layar ini belum dibangun", () => {
    // Menampilkan angka contoh akan membuat yang belum dikerjakan tampak sudah jadi
    // (CLAUDE.md §11, §27); 404 membuat sistem tampak rusak. Keduanya lebih buruk.
    page();

    expect(screen.getByText(/belum dibangun/i)).toBeDefined();
  });

  it("menyebut pekerjaan yang direncanakan beserta nomor task-nya", () => {
    page();

    expect(screen.getByText("TASK 090-094")).toBeDefined();
    expect(screen.getByText("Crime Pattern DNA")).toBeDefined();
  });

  it("menunjukkan apa yang sudah ada dan menopangnya", () => {
    // Tanpa ini halaman hanya berisi janji; dengan ini ia menunjuk hal yang dapat diperiksa.
    page();

    expect(screen.getByText(/1.200 kejadian tersimpan/)).toBeDefined();
    expect(screen.getByRole("link", { name: "Tren bulanan" })).toBeDefined();
  });

  it("tidak menampilkan satu pun angka hasil analisis", () => {
    page();

    expect(screen.queryByText(/precision|recall|risk score/i)).toBeNull();
  });
});
