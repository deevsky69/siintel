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
  attachment_basis: string;
  max_attachments: number;
  max_attachment_bytes: number;
};

export type UploadState =
  | { status: "ok"; handle: string; kind: string; byteSize: number }
  | { status: "error"; message: string };

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

/**
 * Mengunggah satu lampiran dan mengembalikan handle-nya.
 *
 * Berkasnya melewati server web, bukan langsung dari peramban ke API. Itu konsekuensi dari
 * keputusan yang sudah ada: alamat API tidak dibuka ke publik, dan membukanya hanya untuk
 * unggahan berarti membuka pintu kedua yang harus dijaga sendiri.
 */
export async function uploadAttachment(form: FormData): Promise<UploadState> {
  const file = form.get("berkas");
  if (!(file instanceof File) || file.size === 0) {
    return { status: "error", message: "Tidak ada berkas yang dipilih." };
  }

  const client = await forwardedFor();
  const outgoing: Record<string, string> = {};
  if (client) outgoing["X-Forwarded-For"] = client;

  const relay = new FormData();
  relay.append("berkas", file);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/v1/public/attachments`, {
      method: "POST",
      headers: outgoing,
      body: relay,
      cache: "no-store",
    });
  } catch {
    return { status: "error", message: "Berkas tidak dapat dikirim. Periksa sambungan Anda." };
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorBody;
    return {
      status: "error",
      message: payload.error?.message ?? "Berkas tidak dapat diterima.",
    };
  }

  const sent = (await response.json()) as { handle: string; kind: string; byte_size: number };
  return { status: "ok", handle: sent.handle, kind: sent.kind, byteSize: sent.byte_size };
}

export async function submitReport(_previous: SubmitState, form: FormData): Promise<SubmitState> {
  const incidentTime = String(form.get("incident_time") ?? "").trim();
  const locationText = String(form.get("location_text") ?? "").trim();
  const latitude = String(form.get("latitude") ?? "").trim();
  const longitude = String(form.get("longitude") ?? "").trim();
  const accuracy = String(form.get("accuracy_m") ?? "").trim();
  const handles = form.getAll("attachments").map(String).filter(Boolean);

  const body: Record<string, unknown> = {
    category: String(form.get("category") ?? ""),
    kecamatan: String(form.get("kecamatan") ?? ""),
    description: String(form.get("description") ?? ""),
  };
  // Koordinat hanya dikirim bila pelapor benar-benar menekan tombol bagikan lokasi.
  // Mengirim nol-nol saat ia tidak menekannya akan menyimpan titik di lepas pantai Afrika
  // dan menandainya sebagai "titik kejadian menurut pelapor".
  if (latitude && longitude) {
    body.latitude = Number(latitude);
    body.longitude = Number(longitude);
    if (accuracy) body.accuracy_m = Number(accuracy);
  }
  if (handles.length > 0) body.attachments = handles;
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
