import Link from "next/link";
import { Basis } from "@/components/basis";
import { Panel } from "@/components/panel";
import type { AreaDetail, KelurahanOverlay, MapData } from "@/lib/map-data";
import { HOME_AREA, shapesAt } from "@/lib/wilayah";
import type { HistoricalMonths, MapLayer, MapLevel } from "./area";
import { HISTORICAL_MONTH_LABELS, HISTORICAL_MONTHS, MAP_LAYERS, mapHref } from "./area";
import { DistrictDetail } from "./district-detail";
import { RiskLegend } from "./legend";
import { MapCanvas } from "./map-canvas";

/**
 * Halaman peta: bidang gambar, pemilih layer, legenda, dan panel rincian wilayah.
 *
 * Wilayah terpilih **dan** layer adalah parameter alamat (`/peta?wilayah=Tebet&layer=…`),
 * bukan keadaan di dalam komponen: rinciannya diambil di server dan tautannya dapat
 * dibagikan saat paparan. Hanya penyorotan yang berjalan di peramban — lihat `MapCanvas`.
 */
export function RiskMap({
  data,
  selected,
  detail,
  layer,
  months,
  level,
  overlay = null,
  selectedKelurahan = null,
}: {
  data: MapData;
  selected: string | null;
  detail: AreaDetail | null;
  layer: MapLayer;
  months: HistoricalMonths;
  level: MapLevel;
  /** Baris per kelurahan untuk kecamatan terpilih; hanya ada pada tingkat `kelurahan`. */
  overlay?: KelurahanOverlay | null;
  /** Kelurahan yang rinciannya sedang dibuka; hanya berarti pada tingkat `kelurahan`. */
  selectedKelurahan?: string | null;
}) {
  // Pada tingkat kelurahan kanvas menggambar baris kelurahan, dan skala kepekatan historis
  // mengikuti puncak antar-kelurahan — bukan puncak antar-kecamatan, yang akan membuat
  // seluruh kelurahan tampak pucat karena dibandingkan dengan jumlah satu kecamatan utuh.
  const zoomed = level === "kelurahan" && overlay !== null;
  const canvasDistricts = zoomed ? overlay.districts : data.districts;
  const canvasHistorical = zoomed
    ? { ...data.historical, peakIncidents: overlay.historicalPeakIncidents }
    : data.historical;
  const district = data.districts.find((row) => row.kecamatan === selected) ?? null;
  const kelurahan = level === "kelurahan" && selected ? shapesAt("kelurahan", selected) : [];

  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="col-span-12 xl:col-span-7">
        <Panel
          title="Live Kamtibmas Map"
          action={
            <span className="text-2xs uppercase tracking-wider text-ink-faint">
              {level === "polda"
                ? "12 Kota/Kabupaten · Wilayah Hukum Polda Metro Jaya"
                : level === "kelurahan"
                  ? `${kelurahan.length} Kelurahan · Kecamatan ${selected}`
                  : `${shapesAt("kecamatan").length} Kecamatan · Polres Metro Jakarta Selatan`}
            </span>
          }
          bodyClassName="flex flex-col gap-3"
        >
          {/* Remah jejak. Peta yang dapat diselami tanpa jalan naik adalah perangkap:
              tombol mundur peramban memang bekerja, tetapi ia tidak terlihat di layar dan
              tidak berguna bagi orang yang membuka tautan langsung ke tingkat terdalam. */}
          <nav aria-label="Tingkat wilayah" className="flex flex-wrap items-center gap-1.5">
            <BreadcrumbLink
              href={mapHref(null, layer, months, "polda")}
              current={level === "polda"}
            >
              Polda Metro Jaya
            </BreadcrumbLink>
            <Chevron />
            <BreadcrumbLink
              href={mapHref(selected, layer, months, "kecamatan")}
              current={level === "kecamatan"}
            >
              {HOME_AREA}
            </BreadcrumbLink>
            {level === "kelurahan" && selected ? (
              <>
                <Chevron />
                <BreadcrumbLink href={mapHref(selected, layer, months, "kelurahan")} current>
                  {selected}
                </BreadcrumbLink>
              </>
            ) : null}
          </nav>

          <nav aria-label="Layer peta" className="flex flex-wrap items-center gap-2">
            {MAP_LAYERS.map((option) => (
              <Link
                key={option.id}
                href={mapHref(selected, option.id, months)}
                scroll={false}
                aria-current={layer === option.id ? "true" : undefined}
                className={`rounded border px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
                  layer === option.id
                    ? "border-accent/60 bg-accent/10 text-accent"
                    : "border-base-800 text-ink-muted hover:text-ink"
                }`}
              >
                {option.label}
              </Link>
            ))}
            <span className="text-2xs text-ink-faint">
              {layer === "historical"
                ? `${data.historical.windowFrom} s.d. ${data.historical.windowTo}`
                : layer === "current"
                  ? data.assessmentDate
                    ? `Penilaian ${data.assessmentDate}`
                    : "Belum ada tanggal penilaian"
                  : `Horizon ${data.horizon}`}
              {/* Versi bobot ikut tampil supaya pertanyaan "bobotnya dari mana"
                  dapat dijawab dari layar, bukan dari ingatan (CLAUDE.md §25). */}
              {layer === "current" && data.weightsVersion
                ? ` · bobot ${data.weightsVersion}`
                : null}
            </span>
          </nav>

          {/* Pemilih jendela hanya muncul pada layer historis: menampilkannya di layer
              lain akan menjanjikan pengaruh yang tidak ada. */}
          {layer === "historical" ? (
            <nav aria-label="Jendela waktu historis" className="flex flex-wrap items-center gap-2">
              <span className="stat-label">Jendela</span>
              {HISTORICAL_MONTHS.map((option) => (
                <Link
                  key={option}
                  href={mapHref(selected, "historical", option)}
                  scroll={false}
                  aria-current={months === option ? "true" : undefined}
                  className={`rounded border px-2 py-0.5 text-xs transition-colors ${
                    months === option
                      ? "border-risk-high/60 bg-risk-high/10 text-risk-high"
                      : "border-base-800 text-ink-muted hover:text-ink"
                  }`}
                >
                  {HISTORICAL_MONTH_LABELS[option]}
                </Link>
              ))}
              {data.historical.observedFrom === null ? (
                <span className="text-2xs text-ink-faint">
                  Tidak ada kejadian tercatat pada jendela ini
                </span>
              ) : (
                <span className="text-2xs text-ink-faint">
                  Data ditemukan {data.historical.observedFrom} s.d. {data.historical.observedTo}
                </span>
              )}
            </nav>
          ) : null}

          <MapCanvas
            districts={canvasDistricts}
            layer={layer}
            selected={zoomed ? (selectedKelurahan ?? null) : selected}
            historical={canvasHistorical}
            months={months}
            level={level}
            focus={selected}
          />

          <RiskLegend
            layer={layer}
            historical={{
              peakIncidents: data.historical.peakIncidents,
              totalIncidents: data.historical.totalIncidents,
            }}
          />

          {level === "kelurahan" ? (
            <p className="text-2xs leading-relaxed text-ink-faint">
              {zoomed ? (
                <>
                  Kelurahan diwarnai dari <strong>sel penilaian setingkat kelurahan</strong> —
                  satuan lokasi pada data Pusiknas. Kelurahan tanpa warna tidak memiliki data pada
                  layer ini.
                  {overlay.unassigned.cells > 0 || overlay.unassigned.incidents > 0
                    ? ` ${overlay.unassigned.incidents} kejadian (${overlay.unassigned.cells} sel) pada kecamatan ini tidak mencantumkan kelurahan pada Laporan Polisi dan hanya terhitung pada angka kecamatan.`
                    : ""}
                </>
              ) : (
                <>
                  Kelurahan digambar <strong>tanpa warna</strong>: tidak ada baris setingkat
                  kelurahan yang dapat ditampilkan untuk kewenangan Anda.
                </>
              )}
            </p>
          ) : null}

          {level === "polda" ? (
            <p className="text-2xs leading-relaxed text-ink-faint">
              Hanya <strong>{HOME_AREA}</strong> yang diwarnai. Sebelas wilayah lain berada di luar
              wilayah hukum Polres ini dan sistem tidak memegang datanya — mewarnainya akan
              menyiratkan penilaian yang tidak ada. Namanya muncul saat disorot.{" "}
              <strong>Kepulauan Seribu</strong> termasuk wilayah hukum Polda Metro Jaya tetapi
              berada di luar bingkai: gugusannya membentang puluhan kilometer ke utara, dan
              memuatnya akan mengerutkan daratan tempat seluruh data berada.
            </p>
          ) : null}

          <p className="text-2xs leading-relaxed text-ink-faint">
            Batas wilayah bersumber dari{" "}
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline-offset-2 hover:underline"
            >
              © Kontributor OpenStreetMap
            </a>{" "}
            (ODbL), disederhanakan untuk keperluan gambar.
          </p>

          <Basis>
            {layer === "historical"
              ? data.historicalBasis
              : layer === "current"
                ? data.currentRiskBasis
                : data.predictiveBasis}
          </Basis>
        </Panel>
      </div>

      <div className="col-span-12 xl:col-span-5">
        <Panel title="Potensi Ancaman Wilayah" className="h-full">
          <DistrictDetail district={district} detail={detail} horizon={data.horizon} />
        </Panel>
      </div>
    </div>
  );
}

function BreadcrumbLink({
  href,
  current,
  children,
}: {
  href: string;
  current: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      scroll={false}
      aria-current={current ? "page" : undefined}
      className={`rounded px-1.5 py-0.5 text-xs transition-colors ${
        current ? "font-semibold text-ink" : "text-ink-muted hover:text-accent"
      }`}
    >
      {children}
    </Link>
  );
}

function Chevron() {
  return (
    <span aria-hidden="true" className="text-2xs text-ink-faint">
      &#8250;
    </span>
  );
}
