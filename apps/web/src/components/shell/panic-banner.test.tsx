import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { NotificationFeed } from "@/lib/notifications";
import { PanicBanner } from "./panic-banner";

const feed: NotificationFeed = {
  reference_time: "2026-01-01T00:00:00+07:00",
  demo_clock: true,
  role: "Polsek",
  total: 1,
  basis: "",
  groups: [
    {
      kind: "PANIC",
      title: "Permintaan bantuan darurat",
      action: "Terima",
      href: "/panic",
      total: 1,
      items: [{ code: "PNC-0001", headline: "Tebet Timur, Tebet", detail: "ditekan 10:05 WIB" }],
    },
  ],
};

describe("spanduk darurat", () => {
  it("tampil selama ada permintaan yang belum diterima, menautkan ke antrean", () => {
    render(<PanicBanner feed={feed} />);
    const banner = screen.getByRole("alert");
    expect(banner.getAttribute("href")).toBe("/panic");
    expect(screen.getByText(/1 permintaan bantuan belum diterima/)).toBeDefined();
    expect(screen.getByText(/Tebet Timur, Tebet/)).toBeDefined();
  });

  it("tidak tampil bila nol atau antrean gagal dimuat", () => {
    const { container } = render(
      <PanicBanner feed={{ ...feed, groups: [{ ...feed.groups[0], total: 0, items: [] }] }} />,
    );
    expect(container.innerHTML).toBe("");
    expect(render(<PanicBanner feed={null} />).container.innerHTML).toBe("");
  });
});
