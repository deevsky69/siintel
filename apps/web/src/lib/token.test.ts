import { describe, expect, it } from "vitest";
import { tokenExpiresAt, tokenExpiringSoon, tokenMaxAge } from "./token";

function jwt(payload: Record<string, unknown>): string {
  const b64 = (value: string) =>
    Buffer.from(value)
      .toString("base64")
      .replace(/=+$/, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");
  return `${b64('{"alg":"HS256"}')}.${b64(JSON.stringify(payload))}.tandatangan`;
}

/**
 * Masa berlaku token dibaca tanpa verifikasi, hanya untuk menjadwalkan penyegaran di
 * middleware (audit 15 November 2026: cookie 60 menit vs token 15 menit).
 */
describe("pembacaan masa berlaku token", () => {
  const now = 1_700_000_000_000; // ms

  it("membaca klaim exp dan menghitung sisa umur", () => {
    const token = jwt({ sub: "u1", exp: now / 1000 + 600 });
    expect(tokenExpiresAt(token)).toBe(now / 1000 + 600);
    expect(tokenMaxAge(token, 900, now)).toBe(600);
    expect(tokenExpiringSoon(token, 90, now)).toBe(false);
    expect(tokenExpiringSoon(token, 700, now)).toBe(true);
  });

  it("token yang sudah lewat dianggap segera habis dan berumur nol", () => {
    const token = jwt({ exp: now / 1000 - 5 });
    expect(tokenExpiringSoon(token, 90, now)).toBe(true);
    expect(tokenMaxAge(token, 900, now)).toBe(0);
  });

  it("token yang tidak terbaca memakai nilai cadangan dan dianggap perlu disegarkan", () => {
    expect(tokenExpiresAt("bukan.jwt")).toBeNull();
    expect(tokenExpiresAt("tanpa-titik")).toBeNull();
    expect(tokenMaxAge("bukan.jwt", 900, now)).toBe(900);
    expect(tokenExpiringSoon("bukan.jwt", 90, now)).toBe(true);
  });
});
