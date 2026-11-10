import Link from "next/link";
import type { MonthlyProduct, ProductSummary } from "@/lib/monthly-products";
import { isAwaitingDecision } from "@/lib/monthly-products";

/**
 * Papan "Bulan Ini" di beranda (10 November 2026, keputusan pemilik proyek 2.i).
 *
 * Menggantikan ringkasan harian (peringatan, prediksi, rekomendasi) yang rantainya sudah
 * keluar dari menu. Satu kartu per mata rantai siklus bulanan; kartu yang menunggu PEMBACA
 * diberi tanda, selebihnya hanya menyatakan posisinya. Angka berasal dari API — tidak ada
 * nilai yang ditanam di kode.
 */
export type BoardInput = {
  month: string;
  summary: ProductSummary | null;
  product: MonthlyProduct | null;
  permissions: readonly string[];
  citizen: { advisoryPending: boolean; advisoryMonth: string | null; draftBulletins: number };
};

type Card = {
  key: string;
  title: string;
  state: string;
  href: string;
  cta: string | null;
  /** Benar bila giliran pembaca: kartu diberi bingkai aksen. */
  mine: boolean;
};

export function buildCards(input: BoardInput): Card[] {
  const can = (p: string) => input.permissions.includes(p);
  const { summary, product, month } = input;
  const status = summary?.status ?? null;
  const awaiting = status ? isAwaitingDecision(status) : false;
  const decided = status === "DECIDED";
  const cards: Card[] = [];

  // 1. Produk bulanan — posisi naskah dan siapa yang dinanti.
  const productState = !status
    ? "Belum disusun"
    : status === "DRAFT"
      ? "Draf menunggu pemeriksaan Analis"
      : awaiting
        ? "Menunggu penetapan Pimpinan"
        : `Ditetapkan · ${summary?.priority_count ?? 0} kelurahan prioritas`;
  const analystTurn = can("monthly_product:draft") && (!status || status === "DRAFT");
  const leaderTurn = can("monthly_product:decide") && awaiting;
  cards.push({
    key: "produk",
    title: `Produk bulanan ${month}`,
    state: productState,
    href: `/ops/produk-bulanan?bulan=${month}`,
    cta: analystTurn
      ? status
        ? "Periksa & kirim ke Pimpinan"
        : "Susun draf (membekukan peringkat)"
      : leaderTurn
        ? "Tetapkan kelurahan prioritas"
        : null,
    mine: analystTurn || leaderTurn,
  });

  // 2. Pelaksanaan — hanya bermakna setelah ditetapkan.
  if (can("monthly_product:execute") || can("monthly_product:decide")) {
    const selected = product?.items.filter((item) => item.selected) ?? [];
    const recorded = selected.reduce((sum, item) => sum + item.actions.length, 0);
    const executeTurn = can("monthly_product:execute") && decided;
    cards.push({
      key: "pelaksanaan",
      title: "Kegiatan di kelurahan prioritas",
      state: decided
        ? `${recorded} kegiatan tercatat di ${selected.length} kelurahan`
        : "Menunggu penetapan",
      href: `/ops/produk-bulanan?bulan=${month}`,
      cta: executeTurn ? "Catat kegiatan" : null,
      mine: executeTurn,
    });
  }

  // 3. Evaluasi — cakupan dihitung setelah bulan berakhir; tautannya selalu ada.
  if (can("evaluation:read")) {
    cards.push({
      key: "evaluasi",
      title: "Evaluasi cakupan",
      state: decided
        ? "Siap dihitung setelah bulan berakhir"
        : "Menunggu peringkat beku dan penetapan",
      href: `/ops/evaluasi-bulanan?bulan=${month}`,
      cta: decided ? "Lihat cakupan" : null,
      mine: false,
    });
  }

  // 4. Persetujuan warga — satu antrean: imbauan bulanan dan buletin mingguan (2.iii).
  if (can("bulletin:approve") || can("bulletin:manage")) {
    const waiting = (input.citizen.advisoryPending ? 1 : 0) + input.citizen.draftBulletins;
    const parts = [
      input.citizen.advisoryPending
        ? `imbauan ${input.citizen.advisoryMonth ?? ""} menunggu`
        : "imbauan bulan ini disetujui",
      `${input.citizen.draftBulletins} buletin draf`,
    ];
    const approveTurn = can("bulletin:approve") && waiting > 0;
    cards.push({
      key: "warga",
      title: "Persetujuan warga",
      state: parts.join(" · "),
      href: "/ops/buletin",
      cta: approveTurn ? `Setujui (${waiting})` : null,
      mine: approveTurn,
    });
  }

  return cards;
}

export function MonthlyBoard({ input }: { input: BoardInput }) {
  const cards = buildCards(input);
  const mine = cards.filter((card) => card.mine).length;
  return (
    <section aria-labelledby="papan-bulan-ini" className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 id="papan-bulan-ini" className="text-2xs uppercase tracking-wider text-ink-faint">
          Bulan ini · {input.month}
        </h2>
        <span className="text-2xs text-ink-faint">
          {mine === 0 ? "Tidak ada yang menunggu Anda" : `${mine} menunggu Anda`}
        </span>
      </div>
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <li
            key={card.key}
            className={`rounded border p-3 ${
              card.mine ? "border-accent/60 bg-accent/5" : "border-base-800 bg-base-900/40"
            }`}
          >
            <p className="text-2xs uppercase tracking-wider text-ink-faint">{card.title}</p>
            <p className="mt-1 text-sm text-ink">{card.state}</p>
            <Link
              href={card.href}
              className={`mt-2 inline-block text-xs ${card.mine ? "font-semibold text-accent" : "text-ink-muted"}`}
            >
              {card.cta ?? "Buka"} →
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
