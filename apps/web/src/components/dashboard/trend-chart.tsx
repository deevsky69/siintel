import { Panel } from "@/components/panel";
import type { TrendSeries } from "@/lib/dashboard";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
// Menunjuk variabel tema, bukan nilai: grafik yang warnanya dipatok akan tetap gelap
// di mode terang, dan garis kuning muda di atas kertas putih praktis tak terlihat.
const COLORS = [
  "rgb(var(--series-1))",
  "rgb(var(--series-2))",
  "rgb(var(--series-3))",
  "rgb(var(--series-4))",
  "rgb(var(--series-5))",
];

/**
 * Grafik tren digambar sebagai SVG langsung.
 *
 * Tidak memakai pustaka grafik: satu grafik garis sederhana tidak sepadan dengan
 * menambah dependensi, dan demo harus berjalan tanpa mengunduh apa pun.
 */
export function TrendChart({ series }: { series: TrendSeries[] }) {
  if (series.length === 0) {
    return (
      <Panel title="Crime Trend">
        <p className="text-sm text-ink-muted">Belum ada data tren.</p>
      </Panel>
    );
  }

  const peak = Math.max(1, ...series.flatMap((row) => row.monthly));
  const width = 300;
  const height = 110;

  const pathOf = (monthly: number[]) =>
    monthly
      .map((value, index) => {
        const x = (index / (MONTHS.length - 1)) * width;
        const y = height - (value / peak) * height;
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

  return (
    <Panel
      title="Crime Trend"
      action={
        <div className="flex gap-2.5">
          {series.map((row, index) => (
            <span key={row.year} className="flex items-center gap-1 text-2xs text-ink-muted">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              {row.year}
            </span>
          ))}
        </div>
      }
    >
      <svg
        viewBox={`0 0 ${width} ${height + 20}`}
        className="w-full"
        role="img"
        aria-label={`Tren kejadian bulanan ${series.map((s) => s.year).join(", ")}`}
      >
        <title>Tren kejadian per bulan</title>
        {series.map((row, index) => (
          <path
            key={row.year}
            d={pathOf(row.monthly)}
            fill="none"
            stroke={COLORS[index % COLORS.length]}
            strokeWidth={1.6}
            strokeLinejoin="round"
          />
        ))}
        {MONTHS.map((month, index) => (
          <text
            key={month}
            x={(index / (MONTHS.length - 1)) * width}
            y={height + 15}
            textAnchor="middle"
            className="fill-ink-muted"
            // Satuan gambar, bukan piksel. Lebar viewBox 300 kira-kira sama dengan lebar
            // panelnya, jadi 12 satuan tergambar mendekati 12 piksel.
            style={{ fontSize: 14 }}
          >
            {month}
          </text>
        ))}
      </svg>
      <p className="mt-1 text-2xs text-ink-muted">Puncak bulanan: {peak} kejadian</p>
    </Panel>
  );
}
