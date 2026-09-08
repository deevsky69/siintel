"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { HistoricalPoint, MapDistrict } from "@/lib/map-data";
import { RISK_HEX, RISK_LABELS } from "@/lib/risk";
import type { AreaShape } from "@/lib/wilayah";
import {
  boundsOf,
  framingShapes,
  HOME_AREA,
  isWithin,
  labelSpan,
  polygonPoints,
  projectLatLon,
  shapesAt,
  toPercent,
  viewBoxOf,
} from "@/lib/wilayah";
import type { HistoricalMonths, MapLayer, MapLevel } from "./area";
import {
  DEFAULT_HISTORICAL_MONTHS,
  HISTORICAL_HEX,
  historicalOpacity,
  mapHref,
  PREDICTIVE_HEX,
  pointRadius,
  predictiveOpacity,
  toRiskClass,
} from "./area";

/**
 * Bidang gambar peta — dipakai halaman peta maupun panel ringkas dashboard.
 *
 * Wilayah digambar sebagai SVG, tanpa tile server dan tanpa pustaka peta. Setiap wilayah
 * adalah **tautan sungguhan** ke `/peta?wilayah=…`, sehingga pilihan dapat disalin,
 * dibuka di tab lain, dan dibagikan saat paparan. Menyorot dengan tetikus atau papan ketik
 * tidak memuat ulang apa pun; hanya klik yang mengubah alamat.
 *
 * Ini satu-satunya bagian peta yang berjalan di peramban, semata karena wilayah yang
 * sedang disorot adalah keadaan sesaat yang tidak pantas masuk ke alamat.
 *
 * Tiga layer digambar dengan cara yang berbeda **dengan sengaja**:
 *
 * - `historical` — **cacah kejadian**, bukan skor. Diwarnai kuning-jingga dengan kepekatan
 *   relatif terhadap wilayah terbanyak pada jendela yang tampil, sebab cacah tidak punya
 *   kelas dan tidak boleh diberi satu pun di sini. Hanya layer ini yang menggambar titik.
 * - `current` — diwarnai menurut `risk_class` yang dikirim backend. Kelas tidak pernah
 *   dihitung ulang di sini (CLAUDE.md §12).
 * - `predictive` — prediksi **tidak menyimpan kelas risiko** dan tidak diberi kelas oleh
 *   API, karena ambangnya masih DEMO / PROPOSED (U-01). Layer ini karenanya memakai satu
 *   warna dengan kepekatan mengikuti skor, bukan tangga warna risiko, dan layar
 *   menyatakan bahwa yang ditampilkan adalah skor mentah tanpa kelas resmi.
 *
 * Ketiganya memakai warna yang berjauhan supaya tidak ada layer yang terbaca sebagai
 * layer lain saat dipandang sekilas dari kursi belakang ruang paparan.
 */

/** Warna wilayah tanpa data — sewarna garis panel, jelas berbeda dari tangga risiko. */
// Warna peta menunjuk variabel tema. Peta adalah satu-satunya tempat warna digambar
// lewat atribut SVG dan bukan kelas Tailwind, jadi ia perlu rujukannya sendiri.
const NO_DATA_FILL = "rgb(var(--line))";

/**
 * Garis tepi wilayah dalam keadaan diam.
 *
 * Sebelumnya sewarna latar, sehingga wilayah hanya terpisah oleh perbedaan warna isian —
 * dan dua wilayah bertetangga yang kebetulan sekelas risiko menyatu menjadi satu bentuk
 * yang tidak dapat dipisahkan mata. Garis gelap tipis membuat batasnya selalu terbaca,
 * termasuk pada wilayah tanpa data yang isiannya nyaris tak berwarna.
 */
const EDGE = "rgb(var(--text) / 0.45)";

/** Saat disorot, garisnya menebal DAN menghitam — dua isyarat, bukan satu. */
const EDGE_HOVER = "rgb(var(--text) / 0.9)";
const EDGE_SELECTED = "rgb(var(--accent))";

/**
 * Angka besar di tengah wilayah pada layer yang sedang tampil; `null` bila tidak ada data.
 *
 * Pada layer historis angka ini adalah **cacah kejadian**, bukan skor 0–100. Keduanya
 * digambar di tempat yang sama, jadi satuannya dinyatakan di legenda dan di tooltip —
 * angka telanjang 214 dan 78 mustahil dibedakan hanya dari rupanya.
 */
export function layerValue(district: MapDistrict, layer: MapLayer): number | null {
  if (layer === "historical") return district.historical?.incidents ?? null;
  const area = layer === "current" ? district.current : district.predictive;
  return area?.risk_score ?? null;
}

/**
 * Isi tooltip saat kursor melewati satu wilayah.
 *
 * Aturannya diambil dari cara aplikasi pemantauan lain menyusun tooltip peta — Grafana
 * Geomap, ArcGIS Dashboards, Datadog, ESRI Operations Dashboard: **cukup untuk memutuskan
 * apakah perlu diklik, tidak lebih.** Susunannya seragam di mana-mana:
 *
 * ```text
 * identitas  →  angka utama  →  status  →  satu pembanding  →  isyarat klik
 * ```
 *
 * Tiga hal yang sengaja TIDAK masuk ke sini:
 *
 * 1. **Apa pun yang harus diklik.** Tooltip mengikuti kursor dan hilang begitu kursor
 *    bergeser; tautan di dalamnya mustahil diraih. Karena itu seluruh lapisannya
 *    `pointer-events-none`.
 * 2. **Rincian lengkap.** Riwayat, daftar prediksi, dan peringatan aktif adalah isi panel
 *    **klik**. Menaruhnya di hover membuat kotak yang menutupi peta yang sedang dibaca.
 * 3. **Angka yang menuntut pembanding.** Satu angka tanpa acuan tidak dapat dinilai
 *    sekilas, dan tooltip tidak punya ruang untuk menjelaskan acuannya.
 */
export type TooltipRow = { label: string; value: string };

export function tooltipRows(district: MapDistrict, layer: MapLayer): TooltipRow[] {
  if (layer === "historical") {
    const area = district.historical;
    if (!area) return [{ label: "Kejadian", value: "tidak ada catatan" }];
    const dominant = area.by_threat_type[0];
    return [
      { label: "Kejadian", value: `${area.incidents}` },
      ...(dominant
        ? [{ label: "Terbanyak", value: `${dominant.threat_type} (${dominant.incidents})` }]
        : []),
    ];
  }

  if (layer === "predictive") {
    const area = district.predictive;
    if (!area) return [{ label: "Prediksi", value: "tidak ada" }];
    return [
      { label: "Skor prediksi", value: `${area.risk_score}/100` },
      { label: "Ancaman", value: area.threat_type },
      ...(area.time_window ? [{ label: "Jendela", value: area.time_window }] : []),
      // Prediksi tidak berkelas (U-01), dan ketiadaannya disebut supaya tidak terbaca
      // sebagai kelas yang kebetulan tidak muat.
      { label: "Kelas", value: "belum ditetapkan" },
    ];
  }

  const area = district.current;
  if (!area) return [{ label: "Risiko", value: "tidak ada data" }];
  const risk = toRiskClass(area.risk_class);
  const dominant = area.threats[0];
  return [
    { label: "Skor risiko", value: `${area.risk_score}/100` },
    ...(risk ? [{ label: "Kelas", value: RISK_LABELS[risk] }] : []),
    ...(dominant ? [{ label: "Ancaman utama", value: dominant.threat_type }] : []),
    ...(dominant?.time_window ? [{ label: "Jam rawan", value: dominant.time_window }] : []),
  ];
}

/**
 * Keterangan ringkas satu wilayah — dipakai panel ringkas dan pembaca layar.
 *
 * Pada layer prediktif keterangan berhenti di angka: menyebut kelas di sini akan
 * mengarang kelas yang tidak dikirim API.
 */
export function districtSummary(district: MapDistrict, layer: MapLayer): string {
  if (layer === "historical") {
    const incidents = district.historical?.incidents;
    if (incidents === undefined) return "tidak ada kejadian tercatat";
    const dominant = district.historical?.by_threat_type[0];
    return dominant
      ? `${incidents} kejadian · terbanyak ${dominant.threat_type}`
      : `${incidents} kejadian`;
  }

  if (layer === "predictive") {
    const score = district.predictive?.risk_score;
    if (score === undefined) return "tidak ada prediksi";
    return `${score}/100 · skor prediksi, tanpa kelas`;
  }

  const area = district.current;
  if (!area) return "tidak ada data";
  const risk = toRiskClass(area.risk_class);
  return risk ? `${area.risk_score}/100 · ${RISK_LABELS[risk]}` : `${area.risk_score}/100`;
}

function ariaLabel(shape: AreaShape, district: MapDistrict | undefined, layer: MapLayer) {
  if (!district) return `${shape.name} — tidak ada data`;

  if (layer === "historical") {
    const incidents = district.historical?.incidents;
    if (incidents === undefined) return `${shape.name} — tidak ada kejadian tercatat`;
    return `${shape.name} — ${incidents} kejadian pada jendela yang ditampilkan`;
  }

  if (layer === "predictive") {
    const area = district.predictive;
    if (!area) return `${shape.name} — tidak ada prediksi`;
    return `${shape.name} — skor prediksi ${area.risk_score} dari 100, tanpa kelas risiko`;
  }

  const area = district.current;
  if (!area) return `${shape.name} — tidak ada data risiko`;
  const risk = toRiskClass(area.risk_class);
  return risk
    ? `${shape.name} — skor risiko ${area.risk_score} dari 100, kelas ${RISK_LABELS[risk]}`
    : `${shape.name} — skor risiko ${area.risk_score} dari 100, kelas tidak dikenali`;
}

function fillOf(district: MapDistrict | undefined, layer: MapLayer): string {
  if (!district) return NO_DATA_FILL;
  if (layer === "historical") return district.historical ? HISTORICAL_HEX : NO_DATA_FILL;
  if (layer === "predictive") return district.predictive ? PREDICTIVE_HEX : NO_DATA_FILL;

  const risk = toRiskClass(district.current?.risk_class ?? null);
  return risk ? RISK_HEX[risk] : NO_DATA_FILL;
}

function opacityOf(
  district: MapDistrict | undefined,
  layer: MapLayer,
  emphasis: "selected" | "active" | "rest",
  peakIncidents = 0,
): number {
  // Sama seperti layer prediktif: kepekatan sedang memikul nilai, jadi penyorotan hanya
  // menambah sedikit dan sisanya dikerjakan garis tepi.
  if (layer === "historical" && district?.historical) {
    const base = historicalOpacity(district.historical.incidents, peakIncidents);
    return emphasis === "selected" ? Math.min(1, base + 0.12) : base;
  }

  // Layer prediktif memakai kepekatan sebagai skala nilai, jadi penyorotan tidak boleh
  // menimpanya; wilayah terpilih hanya dipertegas sedikit dan selebihnya oleh garis tepi.
  if (layer === "predictive" && district?.predictive) {
    const base = predictiveOpacity(district.predictive.risk_score);
    return emphasis === "selected" ? Math.min(1, base + 0.12) : base;
  }
  return emphasis === "selected" ? 0.85 : emphasis === "active" ? 0.68 : 0.45;
}

export function MapCanvas({
  districts,
  layer,
  selected,
  /**
   * Tinggi maksimum peta, dinyatakan sebagai satuan CSS.
   *
   * Dipakai untuk menghitung lebar maksimum pembungkus — bukan dipasang pada SVG.
   * Menjepit tinggi SVG langsung membuat gambarnya tercentang di dalam kotak yang lebih
   * lebar, dan lapisan label kehilangan acuannya.
   */
  maxHeight = "62vh",
  showScores = true,
  historical,
  months = DEFAULT_HISTORICAL_MONTHS,
  linkTo = "map",
  level = "kecamatan",
  focus = null,
}: {
  districts: MapDistrict[];
  layer: MapLayer;
  selected: string | null;
  maxHeight?: string;
  /** Angka besar di tengah wilayah; dapat dimatikan bila ruangnya sempit. */
  showScores?: boolean;
  /**
   * Titik lokasi dan puncak cacah untuk layer historis.
   *
   * Opsional karena panel ringkas dashboard memakai bidang gambar yang sama tanpa pernah
   * menampilkan layer historis. Bila layer historis diminta tanpa data ini, wilayah tetap
   * digambar dan titiknya saja yang tidak muncul — bukan halaman yang gagal.
   */
  historical?: { points: HistoricalPoint[]; peakIncidents: number; peakPointIncidents: number };
  months?: HistoricalMonths;
  /**
   * Ke mana klik pada sebuah wilayah membawa pembaca.
   *
   * Berupa **kata kunci, bukan fungsi**, dan itu bukan pilihan gaya. Komponen ini berjalan
   * di peramban (`"use client"`), sedangkan pemanggilnya adalah komponen server; React
   * tidak dapat mengirim fungsi melintasi batas itu, dan permintaan gagal dengan 500 saat
   * dijalankan — bukan saat build, bukan saat test. Kata kunci ini dapat diserialkan, jadi
   * penyusunan alamatnya dikerjakan di sini, di sisi yang memang berjalan di peramban.
   *
   * - `map` — memilih wilayah pada halaman peta, membawa serta layer dan jendelanya;
   * - `home` — membuka rincian di beranda tanpa meninggalkan halamannya.
   */
  linkTo?: "map" | "home";
  /**
   * Tingkat penyelaman. Ketiganya digambar dari data batas yang sama pada satu sistem
   * koordinat, jadi berpindah tingkat hanya mengubah `viewBox` — bukan menghitung ulang
   * bentuk, dan titik kejadian tetap jatuh di tempat yang sama.
   */
  level?: MapLevel;
  /** Kecamatan yang kelurahannya digambar; hanya berarti pada tingkat `kelurahan`. */
  focus?: string | null;
}) {
  const byName = useMemo(
    () => new Map(districts.map((district) => [district.kecamatan, district])),
    [districts],
  );

  /** Wilayah yang sedang disentuh tetikus **atau** sedang menerima fokus papan ketik. */
  const [active, setActive] = useState<string | null>(null);

  const shapes = useMemo(() => shapesAt(level, focus ?? undefined), [level, focus]);

  // Bidang gambar mengikuti wilayah yang sedang tampil. Pada tingkat kelurahan, kecamatan
  // induknya ikut menentukan bidang supaya penyelaman tidak melompat: pembaca melihat
  // wilayah yang sama, diperbesar.
  const bounds = useMemo(() => boundsOf(framingShapes(shapes)), [shapes]);

  /**
   * Lebar maksimum label tiap wilayah, dinyatakan sebagai persen lebar peta.
   *
   * Jangkar label sudah terbukti berada di dalam poligonnya, tetapi itu belum cukup:
   * kotak label dipusatkan pada jangkar, sehingga nama panjang di atas wilayah sempit
   * tetap menjulur ke luar — "Mampang Prapatan" selebar 124 piksel di atas wilayah yang
   * jauh lebih sempit terbaca sebagai nama milik tetangganya.
   *
   * `labelSpan` menjawab lebar poligon tepat pada ketinggian jangkarnya — bukan lebar
   * kotak pembatasnya, yang untuk wilayah bertakik bisa hampir dua kali lipat. Nama yang
   * tidak muat lalu turun ke baris kedua, bukan menjulur.
   *
   * Ada lantai 7%: wilayah tersempit sekalipun harus menyisakan ruang bagi satu kata,
   * dan memaksanya lebih sempit hanya memindahkan masalah menjadi kata yang terpenggal.
   */
  const labelWidth = useMemo(() => {
    const widths = new Map<string, string>();
    for (const shape of shapes) {
      const percent = Math.max((labelSpan(shape) / bounds.width) * 100, 7);
      widths.set(shape.name, `${percent}%`);
    }
    return widths;
  }, [shapes, bounds]);
  const viewBox = useMemo(() => viewBoxOf(shapes), [shapes]);

  // Tebal garis dan jari-jari titik dinyatakan sebagai pecahan dari bentang bidang gambar,
  // bukan angka tetap. Satuan gambar adalah meter: garis setebal 3 satuan wajar untuk peta
  // selebar 50 kilometer dan menjadi pita selebar 30 meter pada peta satu kelurahan.
  // Lebar terbesar yang masih memenuhi batas tinggi, pada nisbah bidang gambar.
  const frameWidth = `calc(${maxHeight} * ${bounds.width / bounds.height})`;

  const span = Math.max(bounds.width, bounds.height);
  const strokeWidth = span / 500;
  const pointScale = span / 1500;

  const hovered = active === null ? undefined : byName.get(active);
  const hoveredShape = shapes.find((shape) => shape.name === active);

  /** Wilayah yang dapat diklik pada tingkat ini, dan ke mana perginya. */
  const hrefOf = (name: string): string | null => {
    if (level === "polda") {
      // Hanya Jakarta Selatan yang dapat diselami: sebelas wilayah lain berada di luar
      // wilayah hukum Polres ini, dan sistem tidak memegang datanya.
      if (name !== HOME_AREA) return null;
      return linkTo === "home" ? "/?tingkat=kecamatan" : mapHref(null, layer, months, "kecamatan");
    }
    // Kelurahan tidak dapat diselami lebih jauh: tidak ada tingkat di bawahnya, dan tidak
    // ada data yang menunggu di sana.
    if (level === "kelurahan") return null;
    return linkTo === "home"
      ? `/?tingkat=kecamatan&wilayah=${encodeURIComponent(name)}`
      : mapHref(name, layer, months, "kelurahan");
  };

  return (
    /*
      Pembungkus ini bernisbah sisi PERSIS sama dengan bidang gambar, dan itu bukan
      kerapian belaka.

      Sebelumnya tinggi peta dibatasi `max-h-…` langsung pada SVG. SVG mempertahankan
      nisbahnya sendiri (`preserveAspectRatio` bawaan), sehingga ketika tingginya dijepit,
      gambarnya menyusut dan tercentang di tengah — menyisakan pita kosong di kiri dan
      kanan. Lapisan label diposisikan dengan PERSENTASE terhadap kotak pembungkus, yang
      tetap selebar induknya, sehingga label terlempar ke luar gambar. Yang paling jauh
      adalah wilayah terluar: "Pesanggrahan" melayang di kiri peta dan "Tebet" di kanannya.

      Dengan nisbah pembungkus disamakan, tidak ada lagi pita kosong: persentase label dan
      koordinat SVG menunjuk titik yang sama.
    */
    <div
      className="relative mx-auto w-full"
      style={{ aspectRatio: `${bounds.width} / ${bounds.height}`, maxWidth: frameWidth }}
    >
      {/* biome-ignore lint/a11y/useSemanticElements: peta adalah SVG; tidak ada
          elemen HTML semantik yang dapat menggantikan wadah wilayah di dalamnya. */}
      <svg
        viewBox={viewBox}
        role="group"
        aria-label={
          level === "polda"
            ? "Peta wilayah hukum Polda Metro Jaya, Jakarta Selatan disorot"
            : level === "kelurahan"
              ? `Peta kelurahan di Kecamatan ${focus ?? ""}`
              : layer === "historical"
                ? "Peta cacah kejadian kamtibmas per kecamatan"
                : layer === "predictive"
                  ? "Peta skor prediksi kamtibmas per kecamatan"
                  : "Peta risiko kamtibmas per kecamatan"
        }
        className="h-full w-full"
      >
        {shapes.map((shape) => {
          const district = byName.get(shape.name);
          const isSelected = selected === shape.name;
          const isActive = active === shape.name;
          const href = hrefOf(shape.name);

          // Di luar wilayah hukum Polres ini, wilayah digambar tembus pandang: tidak ada
          // datanya, dan warna apa pun akan menyiratkan pengetahuan yang tidak ada.
          const outside = level === "polda" && shape.name !== HOME_AREA;
          const flat = outside || level === "kelurahan";
          // Satuan sendiri diwarnai aksen, bukan warna risiko: pada tingkat ini tidak ada
          // satu skor untuk seluruh Jakarta Selatan, dan memberinya warna dari tangga
          // risiko akan menyatakan penilaian yang tidak pernah dihitung.
          const home = level === "polda" && shape.name === HOME_AREA;

          const polygons = shape.rings.map((ring) => (
            // Kunci diambil dari simpul pertama cincin, bukan dari indeksnya: dua cincin
            // pada satu wilayah tidak pernah berawal di titik yang sama, dan kunci
            // berbasis koordinat tetap benar seandainya urutan cincin berubah.
            <polygon
              key={`${shape.name}-${ring[0][0]},${ring[0][1]}`}
              points={polygonPoints(ring)}
              className={
                href ? "cursor-pointer transition-[fill-opacity]" : "transition-[fill-opacity]"
              }
              fill={home ? EDGE_SELECTED : flat ? NO_DATA_FILL : fillOf(district, layer)}
              fillOpacity={
                home
                  ? isActive
                    ? 0.75
                    : 0.6
                  : flat
                    ? isActive
                      ? 0.45
                      : 0.18
                    : opacityOf(
                        district,
                        layer,
                        isSelected ? "selected" : isActive ? "active" : "rest",
                        historical?.peakIncidents ?? 0,
                      )
              }
              stroke={isSelected || home ? EDGE_SELECTED : isActive ? EDGE_HOVER : EDGE}
              // Tebalnya bertingkat: tipis saat diam, dua kali lipat saat disorot, dan
              // paling tebal saat terpilih. Perubahan tebal saja tidak cukup terlihat pada
              // peta sepadat ini; warnanya ikut berubah pada baris di atas.
              strokeWidth={strokeWidth * (isSelected || home ? 2.5 : isActive ? 2 : 1)}
              strokeLinejoin="round"
            />
          ));

          const hover = {
            onMouseEnter: () => setActive(shape.name),
            onMouseLeave: () => setActive(null),
            onFocus: () => setActive(shape.name),
            onBlur: () => setActive(null),
          };

          // Wilayah tanpa tujuan bukan tautan. Membungkusnya dalam <Link> yang tidak
          // membawa ke mana-mana akan menjanjikan sesuatu kepada pembaca papan ketik yang
          // tidak dapat ditepati.
          return href ? (
            <Link
              key={shape.name}
              href={href}
              scroll={false}
              aria-label={ariaLabel(shape, district, layer)}
              aria-current={isSelected ? "true" : undefined}
              {...hover}
            >
              {polygons}
            </Link>
          ) : (
            <g key={shape.name} aria-label={shape.name} {...hover}>
              {polygons}
            </g>
          );
        })}
        {/* Titik kejadian digambar setelah seluruh wilayah supaya tidak tertimpa poligon
            tetangga, dan `pointerEvents="none"` supaya klik tetap mengenai wilayah di
            bawahnya — titik bukan tautan, wilayah tetap satu-satunya sasaran.

            Lingkarannya tidak membawa teks dan tidak dapat difokus, jadi tidak ada yang
            perlu disembunyikan dari pembaca layar: keterangan yang sama sudah dibawa
            `aria-label` tiap wilayah dan panel rincian. */}
        {layer === "historical" && historical ? (
          <g pointerEvents="none">
            {historical.points.map((point) => {
              const position = projectLatLon(point.latitude, point.longitude);
              // Titik di luar bidang gambar dibuang, bukan dijepitkan ke tepi: menjepitkan
              // akan menaruhnya di wilayah yang bukan wilayahnya.
              if (!isWithin(position, bounds)) return null;
              const radius = pointRadius(point.incidents, historical.peakPointIncidents);

              return (
                <circle
                  key={point.location_code}
                  cx={position[0]}
                  cy={position[1]}
                  r={radius * pointScale}
                  fill={HISTORICAL_HEX}
                  fillOpacity={0.55}
                  // Titik kejadian diberi tepi sewarna latar supaya lingkaran yang
                  // bertumpuk tetap dapat dihitung satu per satu.
                  stroke="rgb(var(--surface-app))"
                  strokeWidth={strokeWidth}
                />
              );
            })}
          </g>
        ) : null}
      </svg>

      {/*
        Nama wilayah dan skornya digambar sebagai HTML di ATAS peta, bukan sebagai <text>
        di dalamnya.

        Alasannya ukuran huruf. Di dalam SVG, `font-size` adalah satuan gambar yang ikut
        mengecil bersama viewBox: label 26 satuan pada bidang selebar 1000 yang dipaksa
        masuk ke panel selebar 316 piksel tergambar 8,2 piksel — dan tetap 8,2 piksel di
        layar mana pun, karena petanya selalu menyesuaikan lebar induknya. Tidak ada nilai
        yang benar untuk semua ukuran layar.

        Sebagai HTML, ukurannya piksel sungguhan: sama terbacanya di ponsel dan di layar
        lebar. `pointer-events-none` menjaga klik tetap mengenai wilayah di bawahnya.
      */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        {shapes.map((shape) => {
          const district = byName.get(shape.name);
          const score = district ? layerValue(district, layer) : null;
          const outside = level === "polda" && shape.name !== HOME_AREA;

          // Dua belas nama pada bingkai selebar seratus kilometer saling menimpa sampai
          // tidak satu pun terbaca. Pada tingkat ini hanya satuan sendiri yang bernama
          // tetap; nama tetangga muncul saat disorot — persis yang diminta pemilik proyek.
          if (outside && active !== shape.name) return null;

          return (
            <div
              key={shape.name}
              className="absolute -translate-x-1/2 -translate-y-1/2 text-center leading-tight"
              style={{ ...toPercent(shape.label, bounds), maxWidth: labelWidth.get(shape.name) }}
            >
              <div
                className={`font-heading text-2xs font-semibold drop-shadow-[0_1px_2px_rgb(var(--surface-app))] sm:text-xs ${
                  outside ? "text-ink-faint" : "text-ink"
                }`}
              >
                {shape.name}
              </div>
              {/* Angka hanya bermakna pada tingkat kecamatan — hanya di situ ada skor per
                  wilayah. Pada tingkat wilayah hukum, Jakarta Selatan tidak punya satu skor,
                  dan menggambar "—" di bawah namanya membuat pembaca mengira datanya hilang. */}
              {showScores && level === "kecamatan" ? (
                <div
                  className={`font-heading text-sm font-bold drop-shadow-[0_1px_2px_rgb(var(--surface-app))] sm:text-base ${
                    score === null ? "text-ink-faint" : "text-ink"
                  }`}
                >
                  {score ?? "—"}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Wilayah di luar wilayah hukum Polres ini tetap menjawab sorotan — dengan menyebut
          namanya dan menyatakan mengapa ia kosong. Wilayah yang diam saat disorot terbaca
          seperti peta yang rusak. */}
      {hoveredShape && !hovered ? (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[135%] whitespace-nowrap rounded border border-base-700 bg-base-950/95 px-2.5 py-1.5 shadow-panel"
          style={toPercent(hoveredShape.label, bounds)}
        >
          <p className="font-heading text-xs font-semibold text-ink">{hoveredShape.name}</p>
          <p className="mt-0.5 text-2xs text-ink-faint">
            {level === "polda"
              ? "Di luar wilayah hukum Polres Metro Jakarta Selatan"
              : level === "kelurahan"
                ? "Belum ada data setingkat kelurahan"
                : "Tidak ada data"}
          </p>
        </div>
      ) : null}

      {hoveredShape && hovered ? (
        <div
          // Tooltip hanya penguat visual: keterangan yang sama sudah ada pada
          // `aria-label` tiap wilayah, sehingga pembaca layar tidak kehilangan apa pun.
          aria-hidden="true"
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[135%] whitespace-nowrap rounded border border-base-700 bg-base-950/95 px-2.5 py-1.5 shadow-panel"
          style={toPercent(hoveredShape.label, bounds)}
        >
          <p className="font-heading text-xs font-semibold text-ink">{hoveredShape.name}</p>
          <dl className="mt-1 space-y-0.5">
            {tooltipRows(hovered, layer).map((row) => (
              <div key={row.label} className="flex items-baseline gap-3">
                <dt className="text-2xs text-ink-faint">{row.label}</dt>
                <dd className="ml-auto font-mono text-xs text-ink">{row.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-1.5 border-t border-base-800 pt-1 text-2xs uppercase tracking-wider text-ink-faint">
            Klik untuk rincian
          </p>
        </div>
      ) : null}
    </div>
  );
}
