import { type AreaLevel, LEVEL_CLASS, LEVEL_LABEL, monthLabel } from "@/lib/warga";

/** Tiga kata, tiga warna. */
export function LevelBadge({ level, size = "sm" }: { level: AreaLevel; size?: "sm" | "lg" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${LEVEL_CLASS[level]} ${
        size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      Kerawanan {LEVEL_LABEL[level]}
    </span>
  );
}

/** Batang per bulan, dua belas batang, tanpa sumbu yang membuat pusing. */
export function MonthBars({ months, values }: { months: string[]; values: number[] }) {
  const peak = Math.max(1, ...values);
  return (
    <div className="flex h-24 items-end gap-1" role="img" aria-label="Jumlah kejadian per bulan">
      {values.map((value, index) => (
        <div key={months[index]} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-[10px] font-semibold tabular-nums text-ink-muted">{value}</span>
          <div
            className="w-full rounded-t-md bg-accent/70"
            style={{ height: `${Math.max(4, (value / peak) * 64)}px` }}
          />
          <span className="text-[10px] text-ink-faint">{monthLabel(months[index])}</span>
        </div>
      ))}
    </div>
  );
}

/** Bintang 1–5 untuk ditampilkan (bukan untuk diisi). */
export function Stars({ value, size = "text-base" }: { value: number | null; size?: string }) {
  const rounded = Math.round(value ?? 0);
  return (
    <span
      role="img"
      className={`inline-flex ${size} leading-none`}
      aria-label={value === null ? "belum ada nilai" : `${value} dari 5`}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={n <= rounded ? "text-[rgb(var(--warga-amber))]" : "text-base-700"}
          aria-hidden="true"
        >
          ★
        </span>
      ))}
    </span>
  );
}
