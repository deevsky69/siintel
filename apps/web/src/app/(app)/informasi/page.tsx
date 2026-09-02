import Link from "next/link";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { ApiError } from "@/lib/api";
import { getCitizenReports, getCrimes, getIntelligenceReports } from "@/lib/reports";

export const dynamic = "force-dynamic";

const PER_CHANNEL = 15;

/**
 * Informasi Terbaru — apa yang masuk dari ketiga kanal (TASK 161).
 *
 * Tiga kanal ditampilkan **berdampingan, bukan dilebur** menjadi satu aliran tunggal.
 * Aliran tunggal terlihat lebih rapi dan memang lebih mudah dibaca sekilas — tetapi ia
 * menyamakan tiga hal yang keandalannya berbeda:
 *
 * | Kanal | Keandalan |
 * |---|---|
 * | Kejadian | dicatat petugas, sudah terverifikasi |
 * | Intelijen | membawa penilaian keandalan sendiri (A–F) |
 * | Masyarakat | sebagian belum diperiksa siapa pun |
 *
 * Dalam satu aliran, ketiganya tampil sebagai baris yang setara, dan pembaca yang
 * membacanya sambil lalu akan memperlakukan laporan yang belum diverifikasi sama dengan
 * kejadian yang sudah dipastikan. Itu bukan kekeliruan tampilan; itu kekeliruan yang
 * berakhir pada keputusan.
 *
 * Kanal yang gagal dimuat ditandai apa adanya, dan **tidak menjatuhkan** kanal lain:
 * halaman yang kosong seluruhnya karena satu endpoint bermasalah menyembunyikan dua kanal
 * yang sebenarnya baik-baik saja.
 */
export default async function InformasiPage() {
  const [crimes, citizen, intel] = await Promise.all([
    load(() => getCrimes({ page_size: PER_CHANNEL })),
    load(() => getCitizenReports({ page_size: PER_CHANNEL })),
    load(() => getIntelligenceReports({ page_size: PER_CHANNEL })),
  ]);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <Channel
          title="Kejadian Terbaru"
          href="/laporan-petugas"
          total={crimes.total}
          state={crimes.state}
          note="Dicatat petugas — sudah terverifikasi."
        >
          {crimes.rows?.map((row) => (
            <Row
              key={row.code}
              code={row.code}
              headline={row.incident_type}
              when={`${row.incident_date} ${row.incident_time.slice(0, 5)}`}
              where={row.kecamatan}
              detail={row.modus ?? row.location_type}
            />
          ))}
        </Channel>

        <Channel
          title="Laporan Masyarakat"
          href="/masyarakat"
          total={citizen.total}
          state={citizen.state}
          note="Sebagian belum diverifikasi — belum menjadi dasar tindakan."
        >
          {citizen.rows?.map((row) => (
            <Row
              key={row.code}
              code={row.code}
              headline={row.category}
              when={row.reported_at.slice(0, 16).replace("T", " ")}
              where={row.kecamatan ?? "tanpa lokasi"}
              detail={row.status}
            />
          ))}
        </Channel>

        <Channel
          title="Laporan Intelijen"
          href="/intelijen"
          total={intel.total}
          state={intel.state}
          note="Membawa penilaian keandalan sendiri."
        >
          {intel.rows?.map((row) => (
            <Row
              key={row.code}
              code={row.code}
              headline={row.category}
              when={row.report_date}
              where={row.kecamatan ?? "—"}
              detail={row.reliability ? `keandalan ${row.reliability}` : null}
            />
          ))}
        </Channel>
      </div>

      <p className="text-[10px] leading-relaxed text-ink-faint">
        Ketiga kanal sengaja <strong>tidak digabung</strong> menjadi satu aliran. Aliran tunggal
        lebih enak dibaca sekilas, tetapi ia menyamakan tiga hal yang keandalannya berbeda — dan
        pembaca yang membacanya sambil lalu akan memperlakukan laporan yang belum diverifikasi sama
        dengan kejadian yang sudah dipastikan.
      </p>
    </div>
  );
}

type Loaded<T> = { rows: T[] | null; total: number; state: "ok" | "denied" | "error" };

/**
 * Memuat satu kanal tanpa menjatuhkan halaman.
 *
 * `403` dibedakan dari galat lain: yang pertama berarti kanal itu memang di luar kewenangan
 * pembaca — keadaan yang benar, bukan kerusakan — dan layar menyatakannya begitu.
 */
async function load<T>(
  fetcher: () => Promise<{ data: T[]; pagination: { total_items: number } }>,
): Promise<Loaded<T>> {
  try {
    const page = await fetcher();
    return { rows: page.data, total: page.pagination.total_items, state: "ok" };
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      return { rows: null, total: 0, state: "denied" };
    }
    return { rows: null, total: 0, state: "error" };
  }
}

function Channel({
  title,
  href,
  total,
  state,
  note,
  children,
}: {
  title: string;
  href: string;
  total: number;
  state: Loaded<unknown>["state"];
  note: string;
  children: React.ReactNode;
}) {
  return (
    <Panel
      title={title}
      action={
        state === "ok" ? (
          <Link href={href} className="text-[10px] text-ink-faint hover:text-accent">
            {total} seluruhnya →
          </Link>
        ) : null
      }
      className="h-full"
    >
      {state === "denied" ? (
        <EmptyState label="Kanal ini berada di luar kewenangan akun Anda." />
      ) : state === "error" ? (
        <EmptyState label="Kanal ini gagal dimuat. Kanal lain di halaman ini tidak terpengaruh." />
      ) : (
        <ul className="space-y-1.5">{children}</ul>
      )}
      <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">{note}</p>
    </Panel>
  );
}

function Row({
  code,
  headline,
  when,
  where,
  detail,
}: {
  code: string;
  headline: string;
  when: string;
  where: string;
  detail: string | null | undefined;
}) {
  return (
    <li className="border-t border-base-800 pt-1.5 first:border-t-0 first:pt-0">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-ink">{headline}</span>
        <span className="shrink-0 font-mono text-[9px] text-ink-faint">{code}</span>
      </div>
      <div className="text-[10px] text-ink-faint">
        {when} · {where}
        {detail ? ` · ${detail}` : ""}
      </div>
    </li>
  );
}
