import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { FollowUpState } from "./actions";
import { FollowUpForm } from "./follow-up-form";

/**
 * Server action digantikan tiruan: yang diuji di sini adalah formulirnya — bahwa
 * tombol yang ditekan benar-benar terkirim, dan bahwa kegagalan dari backend muncul
 * sebagai kalimat, bukan kode kesalahan (CLAUDE.md §23).
 */
const followUp = vi.fn<(previous: FollowUpState, form: FormData) => Promise<FollowUpState>>();

vi.mock("./actions", () => ({
  followUp: (previous: FollowUpState, form: FormData) => followUp(previous, form),
}));

beforeEach(() => {
  followUp.mockReset();
});

describe("formulir tindak lanjut", () => {
  it("mengirim kode dan tindakan yang benar-benar ditekan", async () => {
    followUp.mockResolvedValue({ error: null, done: { code: "WRN-0053", action: "resolve" } });
    render(<FollowUpForm code="WRN-0053" offers={["acknowledge", "resolve"]} />);

    fireEvent.click(screen.getByRole("button", { name: /nyatakan selesai/i }));

    await waitFor(() => expect(followUp).toHaveBeenCalledTimes(1));
    const sent = followUp.mock.calls[0][1];
    expect(sent.get("code")).toBe("WRN-0053");
    expect(sent.get("action")).toBe("resolve");
  });

  it("hanya menampilkan tombol yang ditawarkan pemanggil", () => {
    // Peran Polsek: memiliki `warning:acknowledge`, tidak memiliki `warning:resolve`.
    render(<FollowUpForm code="WRN-0053" offers={["acknowledge"]} />);

    expect(screen.getByRole("button", { name: /terima peringatan/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /nyatakan selesai/i })).toBeNull();
  });

  it("menampilkan penolakan backend sebagai kalimat yang dapat ditindaklanjuti", async () => {
    followUp.mockResolvedValue({
      error: "Akun Anda tidak berwenang menerima peringatan.",
      done: null,
    });
    render(<FollowUpForm code="WRN-0053" offers={["acknowledge"]} />);

    fireEvent.click(screen.getByRole("button", { name: /terima peringatan/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/tidak berwenang menerima peringatan/i);
  });

  it("menyatakan keberhasilan beserta peringatan yang ditindaklanjuti", async () => {
    followUp.mockResolvedValue({ error: null, done: { code: "WRN-0053", action: "acknowledge" } });
    render(<FollowUpForm code="WRN-0053" offers={["acknowledge"]} />);

    fireEvent.click(screen.getByRole("button", { name: /terima peringatan/i }));

    const status = await screen.findByRole("status");
    expect(status.textContent).toMatch(/WRN-0053/);
    expect(status.textContent).toMatch(/diterima atas nama akun Anda/i);
  });
});
