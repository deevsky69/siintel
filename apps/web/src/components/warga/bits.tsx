import { type AreaLevel, LEVEL_LABEL, monthLabel } from "@/lib/warga";

/** Lencana tingkat: kotak warna kecil + "Kerawanan <tingkat>", warna mengikuti mockup. */
export function LevelBadge({ level, size = "sm" }: { level: AreaLevel; size?: "sm" | "lg" }) {
  return (
    <span
      className={`warga-level is-${level.toLowerCase()}${size === "lg" ? " warga-level-lg" : ""}`}
    >
      <i aria-hidden="true" />
      Kerawanan {LEVEL_LABEL[level]}
    </span>
  );
}

/** Batang per bulan, dua belas batang navy, tanpa sumbu yang membuat pusing. */
export function MonthBars({ months, values }: { months: string[]; values: number[] }) {
  const peak = Math.max(1, ...values);
  return (
    <div className="flex h-24 items-end gap-1" role="img" aria-label="Jumlah kejadian per bulan">
      {values.map((value, index) => (
        <div key={months[index]} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-[10px] font-semibold tabular-nums text-ink-muted">{value}</span>
          <div
            className="w-full bg-accent/80"
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
      className={`inline-flex ${size} leading-none tracking-[2px]`}
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
