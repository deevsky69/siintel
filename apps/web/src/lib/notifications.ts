import { apiGet } from "./api";

/**
 * Antrean pekerjaan pengguna — bentuk respons `GET /notifications`.
 *
 * Isinya ditentukan **backend** menurut permission tindakan yang dipegang pengguna, bukan
 * disaring di sini. Menyaringnya di layar akan membuat dua tempat memutuskan hal yang sama,
 * dan yang di layar akan menyimpang tanpa ada yang menyadarinya.
 */

export type {
  NotificationFeed,
  NotificationGroup,
  NotificationItem,
} from "./notifications-shape";
export { urgentGroups } from "./notifications-shape";

import type { NotificationFeed } from "./notifications-shape";

export const getNotifications = () => apiGet<NotificationFeed>("/notifications");
