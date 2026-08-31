import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("halaman utama", () => {
  it("menampilkan nama sistem", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: "PREDIKSI PRESISI" })).toBeDefined();
  });

  it("menandai dirinya sebagai skeleton tanpa fitur bisnis", () => {
    render(<Home />);

    expect(screen.getByText(/belum ada fitur bisnis/i)).toBeDefined();
  });
});
