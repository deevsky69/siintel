"use server";

import { headers } from "next/headers";
import { BASE_URL } from "@/lib/api";

/**
 * Pemanggilan kanal publik.
 *
 * Berkas ini **tidak** memakai `apiGet`/`apiPost` seperti layar internal, dan itu
 * disengaja: keduanya membaca cookie sesi lalu menyisipkan token. Kanal publik dilayani
 * tanpa autentikasi, dan menyertakan token pengguna lain yang kebetulan sedang masuk di
 * peramban yang sama akan mengubah laporan anonim menjadi laporan atas nama orang itu.
 *
 * Permintaan tetap berangkat dari **server**, bukan dari peramban pelapor, sehingga alamat
 * API tidak perlu dibuka ke publik.
 *
 * Akibatnya satu hal harus dikerjakan dengan sadar: backend akan melihat alamat IP
 * **container web**, bukan alamat pelapor. Dibiarkan begitu, pembatas laju memperlakukan
 * seluruh pengunjung sebagai satu pengirim — dan sepuluh laporan dari siapa pun akan
 * membungkam semua orang selama sejam. Itu lebih buruk daripada tidak ada pembatas sama
 * sekali, dan tidak akan terlihat sampai ada yang benar-benar melapor. Karena itu
 * `X-Forwarded-For` yang diterima dari proxy diteruskan apa adanya.
 */

export type ReportOptions = {
  categories: string[];
  kecamatan: string[];
  max_description: number;
  coordinate_basis: string;
  intake_basis: string;
};

export type SubmitState =
  | { status: "idle" }
  | { status: "error"; message: string }
  | { status: "sent"; ticket: string; message: string; basis: string };

type ApiErrorBody = { error?: { message?: string } };

export async function getReportOptions(): Promise<ReportOptions> {
  const response = await fetch(`${BASE_URL}/api/v1/public/report-options`, {
    // Pilihan isian jarang berubah, tetapi halaman ini harus tetap menampilkan daftar
    // kecamatan yang benar setelah master lokasi diperbarui.
    next: { revalidate: 300 },
  });
  if (!response.ok) throw new Error(`Gagal memuat pilihan isian (${response.status})`);
  return (await response.json()) as ReportOptions;
}

/**
 * Alamat pelapor, untuk diteruskan ke backend.
 *
 * Diambil dari header yang dipasang proxy. Bila tidak ada satu pun, dikembalikan `null`
 * dan backend memakai alamat yang dilihatnya sendiri — tidak dikarang, karena alamat
 * karangan pada pembatas laju sama saja dengan tidak ada pembatas.
 */
async function forwardedFor(): Promise<string | null> {
  const incoming = await headers();
  return incoming.get("x-forwarded-for") ?? incoming.get("x-real-ip");
}

export async function submitReport(_previous: SubmitState, form: FormData): Promise<SubmitState> {
  const incidentTime = String(form.get("incident_time") ?? "").trim();
  const locationText = String(form.get("location_text") ?? "").trim();

  const body: Record<string, unknown> = {
    category: String(form.get("category") ?? ""),
    kecamatan: String(form.get("kecamatan") ?? ""),
    description: String(form.get("description") ?? ""),
  };
  // Field opsional hanya dikirim bila benar-benar diisi: backend menolak field yang tidak
  // dikenal maupun bernilai kosong, dan mengirim string kosong akan menjadi galat yang
  // membingungkan pelapor yang justru tidak mengisi apa-apa.
  if (locationText) body.location_text = locationText;
  if (incidentTime) body.incident_time = new Date(incidentTime).toISOString();

  const client = await forwardedFor();
  const outgoing: Record<string, string> = { "Content-Type": "application/json" };
  if (client) outgoing["X-Forwarded-For"] = client;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/v1/public/citizen-reports`, {
      method: "POST",
      headers: outgoing,
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return {
      status: "error",
      message:
        "Laporan tidak dapat dikirim karena sistem sedang tidak dapat dihubungi. " +
        "Untuk keadaan mendesak, hubungi 110.",
    };
  }

  if (!response.ok) {
    // Pesan dari backend diteruskan apa adanya bila ada: ia yang tahu field mana yang
    // salah, dan menggantinya dengan kalimat umum menghilangkan satu-satunya petunjuk
    // yang dipunyai pelapor untuk memperbaikinya.
    const payload = (await response.json().catch(() => ({}))) as ApiErrorBody;
    return {
      status: "error",
      message:
        payload.error?.message ??
        "Laporan tidak dapat dikirim. Periksa kembali isian Anda, lalu coba lagi.",
    };
  }

  const sent = (await response.json()) as { ticket: string; message: string; basis: string };
  return { status: "sent", ticket: sent.ticket, message: sent.message, basis: sent.basis };
}
