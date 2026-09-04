import { apiGet } from "./api";

/**
 * Antrean pekerjaan pengguna — bentuk respons `GET /notifications`.
 *
 * Isinya ditentukan **backend** menurut permission tindakan yang dipegang pengguna, bukan
 * disaring di sini. Menyaringnya di layar akan membuat dua tempat memutuskan hal yang sama,
 * dan yang di layar akan menyimpang tanpa ada yang menyadarinya.
 */

export type NotificationItem = {
  code: string;
  headline: string;
  detail: string;
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
};

export type NotificationFeed = {
  reference_time: string;
  demo_clock: boolean;
  role: string | null;
  total: number;
  groups: NotificationGroup[];
  basis: string;
};

export const getNotifications = () => apiGet<NotificationFeed>("/notifications");
