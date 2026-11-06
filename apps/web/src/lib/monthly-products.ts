import { apiGet, apiPost } from "./api";

/** Produk bulanan (Modul 4 mekanisme). */
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
  stage: "ANALYST" | "KBO" | "KASAT" | "PIMPINAN";
  outcome: string;
  reason: string | null;
  note: string | null;
  acted_at: string;
};

export type MonthlyProduct = {
  product_id: string;
  target_month: string;
  status: "DRAFT" | "ANALYST_REVIEWED" | "KBO_CHECKED" | "VALIDATED" | "DECIDED";
  next_stage: "ANALYST" | "KBO" | "KASAT" | "PIMPINAN" | null;
  facts: Record<string, string | number>;
  priority_count: number | null;
  items: ProductItem[];
  stages: ProductStage[];
  basis: string;
};

export type ProductList = {
  data: { target_month: string; status: string; priority_count: number | null }[];
  suggested_month: string;
  basis: string;
};

export const listProducts = () => apiGet<ProductList>("/monthly-products");
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
export const stageOutcome = (
  month: string,
  stage: "kbo" | "kasat",
  body: { outcome: string; reason?: string },
) => apiPost<MonthlyProduct>(`/monthly-products/${month}/${stage}`, body);
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
