// Menyusun Simulasi-Ujian-SIGAP.docx dari simulasi-ujian-sigap.html (hasil buat.py), supaya isi
// versi Word selalu sama dengan versi PDF. Halaman dibaca lewat Chromium (playwright-core) menjadi
// daftar blok, lalu ditulis dengan pustaka `docx`.
//
//   CHROME=/jalur/chrome-headless-shell node word.mjs      (butuh: npm i docx playwright-core)
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright-core";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat, PageBreak, PageNumber,
  Packer, Paragraph, ShadingType, Table, TableCell, TableOfContents, TableRow, TextRun, VerticalAlign, WidthType,
} from "docx";

const DIR = path.dirname(new URL(import.meta.url).pathname);
const NAVY = "0B1F4B", GOLD = "8A6D0F", RULE = "C9A227", MUTED = "5B6880", LINE = "D9DFEB", HEAD = "EEF1F7";
const FONT = "Arial", MONO = "Consolas";
const MM = 56.7; // DXA per mm
const MARGIN = Math.round(15 * MM), PAGE_W = 11906, CONTENT = PAGE_W - 2 * MARGIN;

// ---------------------------------------------------------------- 1. baca HTML menjadi blok
const browser = await chromium.launch({ executablePath: process.env.CHROME, args: ["--no-sandbox", "--allow-file-access-from-files"] });
const page = await browser.newPage();
await page.goto(`file://${DIR}/simulasi-ujian-sigap.html`);
const doc = await page.evaluate(() => {
  const runs = (el) => {
    const out = [];
    const walk = (n, f) => {
      if (n.nodeType === 3) { const t = n.textContent.replace(/\s+/g, " "); if (t) out.push({ text: t, ...f }); return; }
      if (n.nodeType !== 1) return;
      const tag = n.tagName;
      if (tag === "BR") { out.push({ br: true }); return; }
      const g = { ...f };
      if (tag === "B" || tag === "STRONG") g.bold = true;
      if (tag === "I" || tag === "EM") g.italic = true;
      if (tag === "CODE") g.code = true;
      if (n.classList?.contains("kecil")) g.small = true;
      for (const c of n.childNodes) walk(c, g);
    };
    for (const c of el.childNodes) walk(c, {});
    // rapikan spasi di tepi
    while (out.length && !out[0].br && !out[0].text.trim()) out.shift();
    while (out.length && !out.at(-1).br && !out.at(-1).text.trim()) out.pop();
    if (out.length && out[0].text) out[0].text = out[0].text.replace(/^\s+/, "");
    if (out.length && out.at(-1).text) out.at(-1).text = out.at(-1).text.replace(/\s+$/, "");
    return out;
  };
  const fig = (f) => ({ t: "fig", src: f.querySelector("img").getAttribute("src"), caption: runs(f.querySelector("figcaption")) });
  const block = (el) => {
    const tag = el.tagName, cls = el.className || "";
    if (/^H[123]$/.test(tag)) return { t: "h", level: +tag[1], runs: runs(el) };
    if (tag === "P") return { t: "p", cls, runs: runs(el) };
    if (tag === "DIV" && /note|awas/.test(cls)) return { t: "box", kind: cls, runs: runs(el) };
    if (tag === "DIV" && cls === "kartu") return { t: "kartu", items: [...el.children].map((d) => ({ label: d.querySelector("small").textContent, value: d.querySelector("b").textContent })) };
    if (tag === "DIV" && cls === "alur") return { t: "alur", boxes: [...el.querySelectorAll(":scope > div")].map((d) => ({ cls: d.className, small: d.querySelector(":scope > small").textContent, title: runs(d.querySelector(":scope > b")), text: runs(d.querySelector(":scope > span")) })) };
    if (tag === "DIV" && cls === "two") return { t: "two", figs: [...el.querySelectorAll("figure")].map(fig) };
    if (tag === "FIGURE") return fig(el);
    if (tag === "UL" || tag === "OL") return { t: "list", ordered: tag === "OL", items: [...el.children].map(runs) };
    if (tag === "TABLE") {
      const head = [...el.querySelectorAll("thead th")];
      const first = el.querySelector("tr");
      const widths = (head.length ? head : [...first.children]).map((c) => { const m = /width:\s*([\d.]+)mm/.exec(c.getAttribute("style") || ""); return m ? +m[1] : null; });
      return { t: "table", cls, head: head.map(runs), widths, rows: [...el.querySelectorAll("tbody tr")].map((tr) => [...tr.children].map((c) => ({ runs: runs(c), center: c.classList.contains("c") }))) };
    }
    return null;
  };
  const out = { cover: null, sections: [] };
  const cover = document.querySelector(".cover");
  out.cover = { tag: cover.querySelector(".tag").textContent, title: cover.querySelector(".title").innerHTML.split(/<br\s*\/?>/).map((s) => s.trim()), subs: [...cover.querySelectorAll(".sub")].map(runs), foot: runs(cover.querySelector(".foot")) };
  for (const s of document.querySelectorAll("body > section")) {
    if (s.classList.contains("isi")) continue; // daftar isi dibuat Word sendiri
    out.sections.push([...s.children].map(block).filter(Boolean));
  }
  return out;
});
await browser.close();

// ---------------------------------------------------------------- 2. pembantu docx
const run = (r, base = {}) => new TextRun({
  text: r.text, bold: r.bold || base.bold, italics: r.italic, color: base.color, size: r.small && base.size ? base.size - 2 : base.size,
  font: r.code ? MONO : FONT, ...(r.code ? { shading: { type: ShadingType.CLEAR, fill: base.fill ?? HEAD, color: "auto" } } : {}),
});
/** Deretan run → satu atau beberapa paragraf (dipisah <br>). */
const paras = (rs, opt = {}, base = {}) => {
  const lines = [[]];
  for (const r of rs) (r.br ? lines.push([]) : lines.at(-1).push(r));
  return lines.filter((l, i) => l.length || i === 0).map((l) => new Paragraph({ ...opt, children: l.map((r) => run(r, base)) }));
};
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const thin = (color = LINE) => ({ style: BorderStyle.SINGLE, size: 4, color });
const noBorders = { top: none, bottom: none, left: none, right: none };
const cell = (children, width, extra = {}) => new TableCell({ children, width: { size: width, type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 90, right: 90 }, ...extra });
const textOf = (rs) => rs.map((r) => r.text ?? " ").join("");

function pngSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b }; }
function image(src, maxW, maxH) {
  const { w, h, data } = pngSize(path.join(DIR, src));
  let width = maxW, height = Math.round((h / w) * maxW);
  if (height > maxH) { height = maxH; width = Math.round((w / h) * maxH); }
  return new ImageRun({ type: "png", data, transformation: { width, height } });
}
const PX = (dxa) => Math.round((dxa / 1440) * 96); // DXA → piksel pada 96 dpi
const caption = (rs) => paras(rs, { spacing: { before: 40, after: 140 } }, { size: 16, color: MUTED });

function figure(f, widthDxa, maxH) {
  return [new Paragraph({ keepNext: true, spacing: { before: 60, after: 0 }, children: [image(f.src, PX(widthDxa), maxH)] }), ...caption(f.caption)];
}

/** Lebar kolom: pakai lebar yang ditulis di HTML (mm); sisanya dibagi menurut panjang teks. */
function columnWidths(tb, total) {
  const n = tb.head.length || tb.rows[0].length;
  const all = [tb.head.map((h) => ({ runs: h })), ...tb.rows];
  const len = Array.from({ length: n }, (_, i) => Math.max(3, ...all.map((r) => (r[i] ? Math.min(60, textOf(r[i].runs).length) : 0))));
  const data = /data/.test(tb.cls);
  const fixed = tb.widths.map((mm) => (mm && !data ? Math.round(mm * MM) : null));
  const free = total - fixed.reduce((a, b) => a + (b ?? 0), 0);
  const sum = len.reduce((a, l, i) => a + (fixed[i] ? 0 : l), 0) || 1;
  const w = len.map((l, i) => fixed[i] ?? Math.floor((free * l) / sum));
  w[w.length - 1] += total - w.reduce((a, b) => a + b, 0);
  return w;
}
function table(tb) {
  const size = /data/.test(tb.cls) ? 14 : /rapat/.test(tb.cls) ? 17 : 18;
  const w = columnWidths(tb, CONTENT);
  const border = { top: none, left: none, right: none, bottom: thin() };
  const rows = [];
  if (tb.head.length) rows.push(new TableRow({ tableHeader: true, cantSplit: true, children: tb.head.map((h, i) => cell(paras([{ text: textOf(h).toUpperCase() }], {}, { bold: true, size: size - 2, color: NAVY }), w[i], { borders: border, shading: { type: ShadingType.CLEAR, fill: HEAD, color: "auto" } })) }));
  for (const r of tb.rows) rows.push(new TableRow({ cantSplit: true, children: r.map((c, i) => cell(paras(c.runs, { alignment: c.center ? AlignmentType.CENTER : AlignmentType.LEFT }, { size }), w[i], { borders: border })) }));
  return [new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, rows }), new Paragraph({ spacing: { after: 80 }, children: [] })];
}
function alur(a) {
  const n = a.boxes.length, arrow = 260, box = Math.floor((CONTENT - arrow * (n - 1)) / n);
  const w = [], cells = [];
  a.boxes.forEach((b, i) => {
    const dark = /ai/.test(b.cls), fill = dark ? NAVY : /warga/.test(b.cls) ? "FBF7E8" : "FFFFFF";
    const edge = { style: BorderStyle.SINGLE, size: 10, color: /warga/.test(b.cls) ? GOLD : NAVY };
    w.push(box);
    cells.push(cell([
      new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: b.small.toUpperCase(), bold: true, size: 13, color: dark ? "E4C65A" : GOLD, font: FONT })] }),
      ...paras(b.title, { spacing: { after: 20 } }, { bold: true, size: 17, color: dark ? "FFFFFF" : NAVY, fill: dark ? "24376A" : HEAD }),
      ...paras(b.text, {}, { size: 15, color: dark ? "D8DEEE" : "45526B", fill: dark ? "24376A" : HEAD }),
    ], box, { borders: { top: edge, bottom: edge, left: edge, right: edge }, shading: { type: ShadingType.CLEAR, fill, color: "auto" } }));
    if (i < n - 1) { w.push(arrow); cells.push(cell([new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "→", bold: true, color: RULE, size: 24, font: FONT })] })], arrow, { borders: noBorders, verticalAlign: VerticalAlign.CENTER, margins: { top: 0, bottom: 0, left: 0, right: 0 } })); }
  });
  w[w.length - 1] += CONTENT - w.reduce((x, y) => x + y, 0);
  return [new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, rows: [new TableRow({ cantSplit: true, children: cells })] }), new Paragraph({ spacing: { after: 100 }, children: [] })];
}
function kartu(k) {
  const w = [Math.round(CONTENT * 0.42), Math.round(CONTENT * 0.27)]; w.push(CONTENT - w[0] - w[1]);
  const edge = { style: BorderStyle.SINGLE, size: 10, color: NAVY };
  return [new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, rows: [new TableRow({ children: k.items.map((it, i) => cell([
    new Paragraph({ children: [new TextRun({ text: it.label.toUpperCase(), bold: true, size: 14, color: GOLD, font: FONT })] }),
    new Paragraph({ children: [new TextRun({ text: it.value, bold: true, size: 21, color: NAVY, font: MONO })] }),
  ], w[i], { borders: { top: edge, bottom: edge, left: i === 0 ? edge : none, right: i === 2 ? edge : none } })) })] }), new Paragraph({ spacing: { after: 100 }, children: [] })];
}
function two(t) {
  const gap = 200, half = Math.floor((CONTENT - gap) / 2), w = [half, gap, CONTENT - half - gap];
  const figs = [t.figs[0], t.figs[1]];
  const c = (f) => (f ? figure(f, half - 60, 300) : [new Paragraph({ children: [] })]);
  return [new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, rows: [new TableRow({ cantSplit: true, children: [
    cell(c(figs[0]), w[0], { borders: noBorders, margins: { top: 0, bottom: 0, left: 0, right: 0 } }),
    cell([new Paragraph({ children: [] })], w[1], { borders: noBorders }),
    cell(c(figs[1]), w[2], { borders: noBorders, margins: { top: 0, bottom: 0, left: 0, right: 0 } }),
  ] })] })];
}
const HEADING = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
function block(b, opt = {}) {
  switch (b.t) {
    case "h": return [new Paragraph({ heading: HEADING[b.level], pageBreakBefore: !!opt.breakBefore, ...(b.level === 1 ? { border: { bottom: { style: BorderStyle.SINGLE, size: 14, color: RULE, space: 4 } } } : {}), children: [new TextRun({ text: b.level === 3 ? textOf(b.runs).toUpperCase() : textOf(b.runs) })] })];
    case "p": return paras(b.runs, { spacing: { after: 110 } }, /lead/.test(b.cls) ? { size: 22, color: "33405A" } : /kecil/.test(b.cls) ? { size: 16, color: MUTED } : { size: 20 });
    case "box": { const awas = /awas/.test(b.kind); return paras(b.runs, { spacing: { before: 60, after: 140 }, indent: { left: 140, right: 100 }, shading: { type: ShadingType.CLEAR, fill: awas ? "FDF0EF" : "FBF7E8", color: "auto" }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: awas ? "B3261E" : RULE, space: 6 } } }, { size: 19, fill: "FFFFFF" }); }
    case "kartu": return kartu(b);
    case "alur": return alur(b);
    case "table": return table(b);
    case "fig": return figure(b, CONTENT, 640);
    case "two": return two(b);
    case "list": return b.items.flatMap((it) => paras(it, { numbering: { reference: b.ordered ? "angka" : "butir", level: 0 }, spacing: { after: 50 } }, { size: 20 }));
    default: return [];
  }
}

// ---------------------------------------------------------------- 3. susun dokumen
const children = [];
const cv = doc.cover;
children.push(
  new Paragraph({ spacing: { before: 1800, after: 500 }, children: [new TextRun({ text: cv.tag.toUpperCase(), bold: true, color: GOLD, size: 20, font: FONT })] }),
  ...cv.title.map((line) => new Paragraph({ spacing: { after: 0, line: 880 }, children: [new TextRun({ text: line, bold: true, color: NAVY, size: 80, font: FONT })] })),
  new Paragraph({ spacing: { before: 300, after: 300 }, border: { bottom: { style: BorderStyle.SINGLE, size: 24, color: RULE, space: 1 } }, indent: { right: CONTENT - 2300 }, children: [] }),
  ...paras(cv.subs[0], { spacing: { after: 360 } }, { size: 28, color: "33405A" }),
  ...paras(cv.subs[1], { spacing: { after: 80 } }, { size: 23, color: "33405A" }),
  ...paras(cv.foot, { spacing: { before: 2400, after: 60 } }, { size: 18, color: MUTED }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ spacing: { after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 14, color: RULE, space: 4 } }, children: [new TextRun({ text: "Daftar isi", bold: true, color: NAVY, size: 34, font: FONT })] }),
  new TableOfContents("Daftar isi", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ spacing: { before: 200 }, children: [new TextRun({ text: "Bila daftar isi belum tampil atau nomor halamannya belum sesuai: klik di dalamnya lalu tekan F9 (Perbarui bidang), atau pilih “Ya” saat Word menanyakan pembaruan bidang ketika berkas dibuka.", italics: true, size: 16, color: MUTED, font: FONT })] }),
);
for (const section of doc.sections) {
  let first = true;
  for (const b of section) { children.push(...block(b, { breakBefore: first && b.t === "h" && b.level === 1 })); first = false; }
}

const heading = (size, color, before, after) => ({ run: { font: FONT, size, bold: true, color }, paragraph: { spacing: { before, after }, keepNext: true } });
const out = new Document({
  creator: "SIGAP", title: "Prototipe Simulasi Ujian SIGAP",
  features: { updateFields: true },
  styles: { default: { document: { run: { font: FONT, size: 20 }, paragraph: { spacing: { line: 276 } } }, heading1: heading(34, NAVY, 0, 160), heading2: heading(25, NAVY, 240, 100), heading3: heading(17, GOLD, 160, 80) } },
  numbering: { config: [
    { reference: "butir", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] },
    { reference: "angka", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { margin: { top: MARGIN, bottom: Math.round(17 * MM), left: MARGIN, right: MARGIN } }, titlePage: true },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Prototipe Simulasi Ujian SIGAP  ·  ", size: 15, color: "8A94A8", font: FONT }), new TextRun({ children: [PageNumber.CURRENT], size: 17, bold: true, color: MUTED, font: FONT })] })] }),
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
    },
    children,
  }],
});
const file = path.join(DIR, "Simulasi-Ujian-SIGAP.docx");
fs.writeFileSync(file, await Packer.toBuffer(out));
console.log("ditulis", file, fs.statSync(file).size, "byte;", doc.sections.length, "bagian;", children.length, "blok");
