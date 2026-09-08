import Link from "next/link";
import { Panel } from "@/components/panel";

/**
 * Halaman menu yang belum dibangun.
 *
 * Menu-menu ini ada di sidebar sejak awal karena ikut menentukan bentuk sistem, tetapi
 * task-nya sengaja ditunda agar jalur kritis menuju paparan selesai lebih dulu
 * (`docs/09-rencana-menuju-paparan.md` §5).
 *
 * Halaman ini menyatakan hal itu terbuka. Dua alternatifnya sama-sama lebih buruk:
 * membiarkan menu 404 membuat sistem tampak rusak, sedangkan mengisinya dengan angka
 * contoh membuat yang belum dikerjakan tampak sudah jadi — persis yang dilarang
 * CLAUDE.md §11 dan §27. Menyembunyikan menunya pun menyesatkan, sebab rancangannya
 * memang memuat menu ini.
 */
export function RoadmapPage({
  title,
  purpose,
  tasks,
  ready,
}: {
  title: string;
  /** Apa yang akan dikerjakan layar ini bila sudah dibangun. */
  purpose: string;
  /** Nomor task pada `docs/08` beserta isinya. */
  tasks: { code: string; detail: string }[];
  /** Yang sudah ada dan akan menopang layar ini — bukan janji kosong. */
  ready: { label: string; href?: string }[];
}) {
  return (
    <div className="mx-auto max-w-3xl">
      <Panel title={title}>
        <div className="rounded border border-risk-moderate/40 bg-risk-moderate/5 px-4 py-3">
          <div className="stat-label text-risk-moderate">Belum dibangun</div>
          <p className="mt-1 text-sm leading-relaxed text-ink">{purpose}</p>
        </div>

        <div className="mt-5">
          <h3 className="stat-label">Pekerjaan yang direncanakan</h3>
          <ul className="mt-2 space-y-2">
            {tasks.map((task) => (
              <li key={task.code} className="flex gap-3 text-sm">
                <span className="shrink-0 font-mono text-xs uppercase tracking-wider text-ink-muted">
                  {task.code}
                </span>
                <span className="text-ink">{task.detail}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-5">
          <h3 className="stat-label">Yang sudah ada dan menopangnya</h3>
          <ul className="mt-2 space-y-1.5">
            {ready.map((item) => (
              <li key={item.label} className="text-sm text-ink">
                <span className="mr-2 text-risk-low">✓</span>
                {item.href ? (
                  <Link href={item.href} className="text-accent hover:underline">
                    {item.label}
                  </Link>
                ) : (
                  item.label
                )}
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-5 border-t border-base-800 pt-4 text-xs leading-relaxed text-ink-muted">
          Penundaan ini tercatat beserta alasannya di{" "}
          <span className="font-mono">docs/09-rencana-menuju-paparan.md</span> §5. Menyatakannya
          terbuka lebih dapat dipertanggungjawabkan daripada mengisi layar dengan angka contoh.
        </p>
      </Panel>
    </div>
  );
}
