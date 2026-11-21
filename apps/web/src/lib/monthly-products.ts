import { cache } from "react";
import { apiGet, apiPost } from "./api";

/**
 * Produk bulanan (Modul 4 mekanisme), dua tahap sejak 10 November 2026 (catatan 177):
 * Tiga tahap sejak 17 November 2026: Staf Intelkam menyusun & memeriksa (peringkat dibekukan
 * otomatis) → Kasat Intelkam menelaah → Pimpinan menetapkan → Fungsi/Polsek mencatat.
 * `KBO_CHECKED` adalah tinggalan alur empat tahap dan diperlakukan sama dengan
 * `ANALYST_REVIEWED`: menunggu telaah Kasat.
 */
export type ProductItem = {
  rank: number;
  kelurahan: string;
  kecamatan: string;
  polsek: string;
  predicted_count: number;
  pattern: {
    counts?: Record<string, number>;
    dominant_threat?: string | null;
    peak_block_label?: string | null;
  };
  proposal_text: string;
  proposed_function: string;
  analyst_status: "ACCEPTED" | "REVISED" | "REJECTED" | null;
  analyst_text: string | null;
  analyst_reason: string | null;
  selected: boolean;
  decided_action: string | null;
  actions: {
    unit: string;
    acted_at: string;
    place: string;
    action: string;
    result: string | null;
  }[];
};

export type ProductStage = {
  stage: "ANALYST" | "KBO" | "WAKASAT" | "KASAT" | "PIMPINAN";
  outcome: string;
  reason: string | null;
  note: string | null;
  acted_at: string;
};

export type ProductStatus =
  | "DRAFT"
  | "ANALYST_REVIEWED"
  | "KBO_CHECKED"
  | "WAKASAT_CHECKED"
  | "VALIDATED"
  | "DECIDED";

export type MonthlyProduct = {
  product_id: string;
  target_month: string;
  status: ProductStatus;
  next_stage: "ANALYST" | "KBO" | "WAKASAT" | "KASAT" | "PIMPINAN" | null;
  awaiting_kbo: boolean;
  awaiting_wakasat: boolean;
  awaiting_review: boolean;
  awaiting_decision: boolean;
  facts: Record<string, string | number | boolean>;
  priority_count: number | null;
  items: ProductItem[];
  stages: ProductStage[];
  basis: string;
};

export type ProductSummary = {
  target_month: string;
  status: ProductStatus;
  priority_count: number | null;
};

export type ProductList = {
  data: ProductSummary[];
  suggested_month: string;
  basis: string;
};

/** Status yang menunggu pemeriksaan mutu oleh KBO. */
export const AWAITING_KBO: readonly ProductStatus[] = ["ANALYST_REVIEWED"];
export const isAwaitingKbo = (status: ProductStatus) => AWAITING_KBO.includes(status);

/** Status yang menunggu pemeriksaan Wakasat Intelkam: sudah diperiksa KBO (21 November 2026). */
export const AWAITING_WAKASAT: readonly ProductStatus[] = ["KBO_CHECKED"];
export const isAwaitingWakasat = (status: ProductStatus) => AWAITING_WAKASAT.includes(status);

/** Status yang menunggu telaah Kasat Intelkam: sudah diperiksa Wakasat. */
export const AWAITING_REVIEW: readonly ProductStatus[] = ["WAKASAT_CHECKED"];
export const isAwaitingReview = (status: ProductStatus) => AWAITING_REVIEW.includes(status);

/** Status yang menunggu penetapan Pimpinan — satu tempat, dipakai lencana dan beranda. */
export const AWAITING_DECISION: readonly ProductStatus[] = ["VALIDATED"];
export const isAwaitingDecision = (status: ProductStatus) => AWAITING_DECISION.includes(status);

export const listProducts = cache(() => apiGet<ProductList>("/monthly-products"));
export const getProduct = (month: string) => apiGet<MonthlyProduct>(`/monthly-products/${month}`);
export const draftProduct = (month: string) =>
  apiPost<MonthlyProduct>("/monthly-products", { month });
export const analystReview = (
  month: string,
  body: {
    items: { kelurahan: string; status: string; text?: string; reason?: string }[];
    note?: string;
  },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/analyst`, body);
export const kboCheck = (
  month: string,
  body: { outcome: "ACCEPTED" | "REJECTED"; reason?: string },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/kbo`, body);
export const wakasatCheck = (
  month: string,
  body: { outcome: "ACCEPTED" | "REJECTED"; reason?: string },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/wakasat`, body);
export const kasatReview = (
  month: string,
  body: { outcome: "ACCEPTED" | "REJECTED"; reason?: string },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/kasat`, body);
export const recordWorkLog = (
  month: string,
  body: {
    quality_sigap: Record<string, number>;
    quality_manual?: Record<string, number>;
    received_at?: string;
    data_ready_at?: string;
    map_ready_at?: string;
    note?: string;
  },
) => apiPost<unknown>(`/monthly-products/${month}/work-log`, body);
export const decideProduct = (
  month: string,
  body: { selected: { kelurahan: string; action?: string }[]; reason?: string },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/decide`, body);
export const recordAction = (
  month: string,
  kelurahan: string,
  body: { unit?: string; acted_at: string; place: string; action: string; result?: string },
) =>
  apiPost<unknown>(
    `/monthly-products/${month}/items/${encodeURIComponent(kelurahan)}/actions`,
    body,
  );

/** Produk bulanan yang menunggu penetapan Pimpinan — lencana sidebar. */
export const countAwaitingDecision = async (): Promise<number> =>
  (await listProducts()).data.filter((row) => isAwaitingDecision(row.status)).length;

/**
 * Kelurahan prioritas bulan ini: dari produk bulanan terakhir yang DITETAPKAN Pimpinan.
 * Dipakai peta (/ops/peta, beranda) untuk menggarisi kelurahan itu — pengganti lapisan skor
 * harian (12 November 2026, catatan 179). `null` bila belum ada produk yang ditetapkan.
 */
export async function getPriorityKelurahan(): Promise<{
  month: string;
  items: { kelurahan: string; kecamatan: string; polsek: string }[];
} | null> {
  const list = await listProducts();
  const decided = list.data.find((row) => row.status === "DECIDED");
  if (!decided) return null;
  const product = await getProduct(decided.target_month);
  return {
    month: product.target_month,
    items: product.items
      .filter((item) => item.selected)
      .map((item) => ({
        kelurahan: item.kelurahan,
        kecamatan: item.kecamatan,
        polsek: item.polsek,
      })),
  };
}
