/**
 * Ikon garis sederhana untuk sidebar.
 *
 * Digambar sendiri sebagai SVG, bukan memakai pustaka ikon: jumlahnya sedikit,
 * dan demo harus berjalan tanpa mengunduh apa pun dari internet.
 */
type IconProps = { className?: string };

const base = "h-5 w-5";

function Svg({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className ?? base}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

const ICONS: Record<string, (props: IconProps) => React.ReactElement> = {
  dashboard: (p) => (
    <Svg {...p}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
      <path d="M9.5 21v-6h5v6" />
    </Svg>
  ),
  map: (p) => (
    <Svg {...p}>
      <path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" />
      <circle cx="12" cy="10" r="2.5" />
    </Svg>
  ),
  prediction: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7v5l3 2" />
    </Svg>
  ),
  warning: (p) => (
    <Svg {...p}>
      <path d="M12 3.8 21 19H3l9-15.2Z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </Svg>
  ),
  analytics: (p) => (
    <Svg {...p}>
      <path d="M4 20V10" />
      <path d="M10 20V4" />
      <path d="M16 20v-7" />
      <path d="M22 20H2" />
    </Svg>
  ),
  recommendation: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
    </Svg>
  ),
  operation: (p) => (
    <Svg {...p}>
      <path d="M12 3 5 5.8v6c0 4.2 2.9 7.6 7 9.2 4.1-1.6 7-5 7-9.2v-6L12 3Z" />
      <path d="m9 12 2.2 2.2L15.5 10" />
    </Svg>
  ),
  evaluation: (p) => (
    <Svg {...p}>
      <path d="M4 7h9M4 12h6M4 17h9" />
      <path d="m15 14 2.5 2.5L22 12" />
    </Svg>
  ),
  intelligence: (p) => (
    <Svg {...p}>
      <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
      <circle cx="12" cy="12" r="3.2" />
    </Svg>
  ),
  admin: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2 2 2 0 1 1-4 0 1.7 1.7 0 0 0-2.9-1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.2-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 11.5 4a2 2 0 1 1 4 0 1.7 1.7 0 0 0 2.9 1.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.7 1.7 0 0 0 22 11a2 2 0 1 1 0 4 1.7 1.7 0 0 0-2.6 0Z" />
    </Svg>
  ),
};

export function NavIcon({ name, className }: { name: string; className?: string }) {
  const Icon = ICONS[name];
  return Icon ? <Icon className={className} /> : null;
}
