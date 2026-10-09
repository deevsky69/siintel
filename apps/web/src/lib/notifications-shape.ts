/**
 * Bentuk antrean pekerjaan (`GET /notifications`) dan pembantu murni di atasnya.
 *
 * Dipisahkan dari `notifications.ts` karena berkas itu mengimpor `./api` (yang menarik
 * `next/headers`), sehingga tidak boleh disentuh komponen klien seperti lonceng. Di sini
 * tidak ada impor sama sekali.
 */

export type NotificationItem = {
  code: string;
  headline: string;
  detail: string;
  /** Kategori mendesak (tawuran, begal) — disorot di layar. Absen pada respons lama. */
  urgent?: boolean;
};

export type NotificationGroup = {
  kind: string;
  title: string;
  /** Kata kerja yang menyebut apa yang dikerjakan di sana. */
  action: string;
  href: string;
  total: number;
  /** Contoh isi, paling banyak tiga. */
  items: NotificationItem[];
  /** Ada isi yang harus disorot (darurat selalu; laporan tawuran/begal). */
  urgent?: boolean;
  urgent_total?: number;
};

export type NotificationFeed = {
  reference_time: string;
  demo_clock: boolean;
  role: string | null;
  total: number;
  groups: NotificationGroup[];
  basis: string;
};

/** Kelompok yang layarnya mengedipkan: darurat, dan laporan berkategori mendesak. */
export function urgentGroups(feed: NotificationFeed | null): NotificationGroup[] {
  return (feed?.groups ?? []).filter((group) =>
    // Darurat selalu mendesak bila ada isinya — juga pada respons API lama tanpa penanda.
    group.kind === "PANIC"
      ? group.total > 0
      : Boolean(group.urgent) && (group.urgent_total ?? 0) > 0,
  );
}
