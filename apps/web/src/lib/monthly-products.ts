import { apiGet, apiPost } from "./api";

/**
 * Produk bulanan (Modul 4 mekanisme), dua tahap sejak 10 November 2026 (catatan 177):
 * Analis menyusun & memeriksa (peringkat dibekukan otomatis) → Pimpinan menetapkan →
 * Fungsi/Polsek mencatat. `KBO_CHECKED` / `VALIDATED` hanya tinggalan alur empat tahap dan
 * diperlakukan sama dengan `ANALYST_REVIEWED`: menunggu Pimpinan.
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
  stage: "ANALYST" | "KBO" | "KASAT" | "PIMPINAN";
  outcome: string;
  reason: string | null;
  note: string | null;
  acted_at: string;
};

export type ProductStatus = "DRAFT" | "ANALYST_REVIEWED" | "KBO_CHECKED" | "VALIDATED" | "DECIDED";

export type MonthlyProduct = {
  product_id: string;
  target_month: string;
  status: ProductStatus;
  next_stage: "ANALYST" | "PIMPINAN" | null;
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

/** Status yang menunggu penetapan Pimpinan — satu tempat, dipakai lencana dan beranda. */
export const AWAITING_DECISION: readonly ProductStatus[] = [
  "ANALYST_REVIEWED",
  "KBO_CHECKED",
  "VALIDATED",
];
export const isAwaitingDecision = (status: ProductStatus) => AWAITING_DECISION.includes(status);

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
