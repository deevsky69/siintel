import { NextResponse } from "next/server";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";

/**
 * Keluar dari sesi.
 *
 * Menjawab **redirect ke halaman masuk**, bukan JSON. Tombol "Keluar" adalah
 * `<form method="post">` biasa tanpa JavaScript, sehingga peramban benar-benar berpindah
 * ke apa pun yang dijawab rute ini. Sebelumnya rute ini menjawab `{"ok":true}`, dan
 * pengguna yang menekan Keluar mendarat di halaman berisi JSON: sesinya memang berakhir,
 * tetapi layarnya menyatakan hal lain.
 *
 * Dua hal yang menentukan bentuk rute ini:
 *
 * 1. **Status 303, bukan 302.** 303 mewajibkan peramban mengubah POST menjadi GET saat
 *    mengikuti redirect. Dengan 302, sebagian peramban meneruskan POST-nya ke `/masuk`.
 *
 * 2. **`Location` relatif, bukan absolut.** `NextResponse.redirect` menuntut URL absolut,
 *    dan URL absolut yang disusun dari `request.url` adalah alamat *internal* di balik
 *    reverse proxy — pengguna akan dilempar ke `localhost:3000`. Header `Location`
 *    relatif sah menurut RFC 7231, diikuti seluruh peramban, dan tidak menuntut satu pun
 *    variabel lingkungan baru yang bisa lupa diisi saat deploy.
 *
 * Cookie tetap dihapus pada respons yang sama. Penghapusan itulah yang mengakhiri sesi;
 * redirect hanya membawa penggunanya ke tempat yang benar.
 */
export async function POST(): Promise<NextResponse> {
  const response = new NextResponse(null, {
    status: 303,
    headers: { Location: "/masuk" },
  });
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}
