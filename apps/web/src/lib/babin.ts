import { apiGet, apiPost } from "./api";

/** Kontak Babinkamtibmas dan buletin mingguan (tahap 3). */
export type BabinRow = {
  kelurahan: string;
  kecamatan: string;
  polsek: string;
  rank: string | null;
  name: string;
  phone_display: string;
  whatsapp_group_link: string | null;
  telegram_chat_id: string | null;
  whatsapp_number: string | null;
  /** Grup WhatsApp warga (…@g.us) yang didaftarkan lewat /daftar; tujuan imbauan bulanan. */
  whatsapp_group_chat_id: string | null;
  advisory_sent_month: string | null;
  is_dummy: boolean;
  updated_at: string;
};

export const getBabinList = () => apiGet<{ data: BabinRow[]; total: number }>("/babin");

export async function putBabin(
  kelurahan: string,
  body: Record<string, unknown>,
): Promise<BabinRow> {
  const { BASE_URL } = await import("./api");
  const { readSession } = await import("./session");
  const session = await readSession();
  const response = await fetch(`${BASE_URL}/api/v1/babin/${encodeURIComponent(kelurahan)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session?.accessToken ?? ""}`,
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message ?? `API ${response.status}`);
  return payload as BabinRow;
}

export async function deleteBabin(kelurahan: string): Promise<void> {
  const { BASE_URL } = await import("./api");
  const { readSession } = await import("./session");
  const session = await readSession();
  const response = await fetch(`${BASE_URL}/api/v1/babin/${encodeURIComponent(kelurahan)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload?.error?.message ?? `API ${response.status}`);
  }
}

export type BulletinRow = {
  id: string;
  week_start: string;
  kelurahan: string;
  kecamatan: string;
  polsek: string;
  content: string;
  figures: {
    total?: number;
    counts?: Record<string, number>;
    alerts?: string[];
    decided_recommendations?: number;
  };
  status: "DRAFT" | "APPROVED" | "SENT";
  generated_at: string;
  approved_at: string | null;
  sent_at: string | null;
  delivery: Record<string, string>;
};

export type BulletinList = {
  data: BulletinRow[];
  weeks: string[];
  suggested_week: string;
  basis: string;
};

export const getBulletins = (week: string, status: string) => {
  const query = new URLSearchParams();
  if (week) query.set("week", week);
  if (status) query.set("status", status);
  const suffix = query.toString();
  return apiGet<BulletinList>(`/bulletins${suffix ? `?${suffix}` : ""}`);
};

export const generateBulletins = (week: string | null) =>
  apiPost<{ week_start: string; created: number; refreshed: number }>(
    "/bulletins/generate",
    week ? { week } : {},
  );

export const approveBulletin = (id: string) => apiPost<BulletinRow>(`/bulletins/${id}/approve`, {});

/** Persetujuan imbauan bulanan ke grup warga (3A, 6 November 2026). */
export type AdvisoryApproval = {
  month: string;
  approved: boolean;
  approved_at: string | null;
  note: string | null;
  groups_registered: number;
  sample: { kelurahan: string; text: string } | null;
};

export const getAdvisoryApproval = (month?: string) =>
  apiGet<AdvisoryApproval>(`/advisories/approvals${month ? `?month=${month}` : ""}`);

export const approveAdvisory = (month: string, note?: string) =>
  apiPost<{ month: string; approved: boolean }>("/advisories/approvals", { month, note });
