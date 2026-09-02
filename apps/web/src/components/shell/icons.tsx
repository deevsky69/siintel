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
  brief: (p) => (
    <Svg {...p}>
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M15 3v4h4" />
      <path d="M9 12h6M9 16h4" />
    </Svg>
  ),
  pattern: (p) => (
    <Svg {...p}>
      <path d="M6 4v6a3 3 0 0 0 6 0V4" />
      <path d="M12 20v-6a3 3 0 0 1 6 0v6" />
      <path d="M6.5 8h5M12.5 16h5" />
    </Svg>
  ),
  community: (p) => (
    <Svg {...p}>
      <circle cx="9" cy="9" r="3" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <path d="M16 6.5a3 3 0 0 1 0 5.8" />
      <path d="M17.5 20a5.5 5.5 0 0 0-2-4.2" />
    </Svg>
  ),
  scoring: (p) => (
    <Svg {...p}>
      <path d="M12 20.5A8.5 8.5 0 1 1 20.5 12" />
      <path d="M12 12 17 8" />
      <path d="M12 3.5v2M4.4 6.6l1.4 1.4M3.5 14h2" />
    </Svg>
  ),
  entry: (p) => (
    <Svg {...p}>
      <path d="M12 5v14M5 12h14" />
      <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
    </Svg>
  ),
  audit: (p) => (
    <Svg {...p}>
      <path d="M5 4h11l3 3v13H5z" />
      <path d="M8 11h8M8 15h5" />
      <path d="m15.5 4 0 3.5 3.5 0" />
    </Svg>
  ),
  feed: (p) => (
    <Svg {...p}>
      <path d="M4 6h10M4 10h10M4 14h7" />
      <path d="M17 5v14M17 5l3 3M17 5l-3 3" />
    </Svg>
  ),
  panic: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22" />
      <path d="m5 5 1.8 1.8M17.2 17.2 19 19M19 5l-1.8 1.8M6.8 17.2 5 19" />
    </Svg>
  ),
  area: (p) => (
    <Svg {...p}>
      <path d="M4 7.5 9.5 5l5 2.5L20 5v11.5L14.5 19l-5-2.5L4 19Z" />
      <path d="M9.5 5v11.5M14.5 7.5V19" />
    </Svg>
  ),
  write: (p) => (
    <Svg {...p}>
      <path d="M4 20h16" />
      <path d="M14.5 4.5a2.1 2.1 0 0 1 3 3L9 16l-4 1 1-4Z" />
    </Svg>
  ),
  settings: (p) => (
    <Svg {...p}>
      <path d="M4 7h10M18 7h2M4 12h2M10 12h10M4 17h12M18 17h2" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="8" cy="12" r="2" />
      <circle cx="16" cy="17" r="2" />
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
