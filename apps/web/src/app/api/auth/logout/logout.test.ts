import { describe, expect, it } from "vitest";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";
import { POST } from "./route";

/**
 * Keluar harus mendaratkan pengguna di halaman masuk.
 *
 * Sampai sebelum test ini ada, rute ini menjawab `{"ok":true}` dan pengguna yang menekan
 * "Keluar" melihat JSON di layar. Sesinya benar-benar berakhir, jadi tidak ada yang
 * tampak rusak dari sisi keamanan — yang rusak adalah kepercayaan penggunanya, karena
 * layar tidak menyatakan apa yang sebenarnya terjadi.
 */
describe("keluar dari sesi", () => {
  it("mengarahkan ke halaman masuk, bukan menjawab JSON", async () => {
    const response = await POST();

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("/masuk");
  });

  it("memakai 303 supaya peramban mengubah POST menjadi GET", async () => {
    // Dengan 302, sebagian peramban meneruskan POST-nya ke /masuk dan halaman masuk
    // menerima permintaan yang tidak diharapkannya.
    const response = await POST();

    expect(response.status).not.toBe(302);
    expect(response.status).toBe(303);
  });

  it("memakai alamat relatif supaya tidak melempar pengguna ke alamat internal", async () => {
    // URL absolut yang disusun dari request.url adalah alamat di balik reverse proxy;
    // pengguna akan mendarat di localhost.
    const response = await POST();
    const location = response.headers.get("location") ?? "";

    expect(location.startsWith("/")).toBe(true);
    expect(location).not.toContain("localhost");
    expect(location).not.toContain("http");
  });

  it("menghapus kedua cookie sesi pada respons yang sama", async () => {
    const response = await POST();
    const cookies = response.headers.getSetCookie();

    for (const name of [ACCESS_COOKIE, REFRESH_COOKIE]) {
      const header = cookies.find((value) => value.startsWith(`${name}=`));
      expect(header, `cookie ${name} tidak dihapus`).toBeDefined();
      // Penghapusan pada Next dinyatakan sebagai nilai kosong beserta masa berlaku lampau.
      expect(header).toMatch(/Max-Age=0|Expires=Thu, 01 Jan 1970/);
    }
  });
});
