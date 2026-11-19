"""Menyusun simulasi-ujian-sigap.html — prototipe simulasi ujian SIGAP.

Jalankan:  python3 buat.py   lalu cetak ke PDF dengan Chromium (--print-to-pdf).
Data contoh (perkara.json) diekspor dari tabel case_files (48 berkas DUMMY berlabel, benih tetap
sehingga sama di lokal dan produksi); menu tiap peran (menus.json) diturunkan dari
apps/web/src/components/shell/navigation.ts dan izin tiap akun peragaan.
"""
import glob
import json
from pathlib import Path

SANDI = "A-12345678"
ALAMAT = "sigap.awansurya.com"
perkara = json.loads(Path("perkara.json").read_text())
menus = json.loads(Path("menus.json").read_text())

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
TAHAP = {"DITERIMA": "Diterima", "LIDIK": "Penyelidikan", "SIDIK": "Penyidikan", "P21": "P21", "SP3": "SP3", "SELESAI": "Selesai"}
JENIS = {"CURANMOR": "Curanmor", "CURAT": "Curat", "CURAS": "Curas"}


def tgl(s):
    y, m, d = s.split("-")
    return f"{int(d)} {BULAN[int(m) - 1][:3]} {y}"


def bulan(s):
    y, m, _ = s.split("-")
    return f"{BULAN[int(m) - 1]} {y}"


def fig(name, caption, cls=""):
    return f'<figure class="{cls}"><img src="gambar/{name}.png" alt=""><figcaption>{caption}</figcaption></figure>'


def alur(*kotak):
    """Diagram alur: kotak berurut dengan panah. Tiap kotak = (pelaku, judul, keterangan[, kelas])."""
    out = []
    for k in kotak:
        cls = k[3] if len(k) > 3 else ""
        out.append(f'<div class="{cls}"><small>{k[0]}</small><b>{k[1]}</b><span>{k[2]}</span></div>')
    return '<div class="alur">' + '<i>→</i>'.join(out) + "</div>"


def langkah(rows):
    body = "".join(
        f"<tr><td class='c'>{i}</td><td><code>{a}</code></td><td>{m}</td><td>{t}</td><td>{h}</td></tr>"
        for i, (a, m, t, h) in enumerate(rows, 1)
    )
    return ('<table class="rapat"><thead><tr><th style="width:7mm">No</th><th style="width:25mm">Akun</th>'
            '<th style="width:36mm">Menu</th><th>Yang dilakukan</th><th style="width:48mm">Hasil yang terlihat</th></tr></thead>'
            f"<tbody>{body}</tbody></table>")


# ---------------------------------------------------------------- tabel data contoh
kendaraan = [p for p in perkara if p["plat"]]
baris_kendaraan = "".join(
    f"<tr><td class='c'>{i}</td><td><code>{p['plat']}</code></td><td><code>{p['rangka']}</code></td><td>{p['kendaraan']}</td>"
    f"<td>{p['kecamatan']}</td><td>{bulan(p['tgl'])}</td><td>{'Tercatat · <b>ditemukan</b>' if p['ditemukan'] else 'Tercatat'}</td></tr>"
    for i, p in enumerate(kendaraan, 1)
)
baris_lp = "".join(
    f"<tr><td class='c'>{i}</td><td><code>{p['lp']}</code></td><td><code><b>{p['pin']}</b></code></td><td>{JENIS[p['jenis']]}</td>"
    f"<td>{p['kelurahan']}</td><td>{tgl(p['tgl'])}</td><td>{TAHAP[p['tahap']]}</td></tr>"
    for i, p in enumerate(perkara, 1)
)

# ---------------------------------------------------------------- akun
AKUN = [
    ("demo.analis", "Analis Intelkam", "Menyusun draf produk bulanan, memeriksa tiap usulan, mengirim ke KBO."),
    ("demo.kbo", "KBO", "Memeriksa mutu produk: meneruskan ke Kasat atau mengembalikan dengan alasan."),
    ("demo.kasat", "Kasat Intelkam", "Menelaah: meneruskan ke Pimpinan atau mengembalikan dengan alasan."),
    ("demo.pimpinan", "Pimpinan", "Menetapkan kelurahan prioritas; menyetujui buletin mingguan; membaca evaluasi."),
    ("demo.humas", "Humas", "Menyetujui imbauan bulanan untuk masyarakat sebelum dikirim bot."),
    ("demo.fungsi", "Fungsi (Reskrim)", "Membaca keputusan dan mencatat pelaksanaan di kelurahan prioritas."),
    ("demo.polsek", "Polsek (Tebet)", "Seperti Fungsi, sebatas wilayah Polsek Tebet; menangani laporan warga dan berkas perkara wilayahnya."),
    ("demo.admin", "Administrator", "Pengguna, mutu data, laporan masyarakat, berkas perkara, moderasi survei, audit. Di luar rantai persetujuan."),
]
baris_akun = "".join(
    f"<tr><td><b>{r}</b></td><td><code>{u}</code></td><td><code>{SANDI}</code></td><td>{t}</td></tr>" for u, r, t in AKUN
)
baris_menu = "".join(
    f"<tr><td><code>{u}</code><br><span class='kecil'>{r}</span></td><td>"
    + "<br>".join(f"<b>{g}</b>: {', '.join(i)}" for g, i in menus[u.split('.')[1]])
    + "</td></tr>"
    for u, r, _ in AKUN
)

# Huruf aplikasi (Inter, Manrope, JetBrains Mono) diambil dari hasil build web: aturan
# @font-face-nya ditulis ulang supaya menunjuk berkas setempat dan memakai nama keluarga polos.
import re
MEDIA = "/home/kim/siintel/apps/web/.next/static"
faces = []
for f in glob.glob(MEDIA + "/css/*.css"):
    for face in re.findall(r"@font-face\{[^}]*\}", Path(f).read_text(errors="ignore")):
        for key, name in (("Inter", "Inter"), ("Manrope", "Manrope"), ("JetBrains", "JetBrains Mono")):
            if key in face and "Fallback" not in face:
                face = re.sub(r"font-family:[^;]*;", f'font-family:"{name}";', face)
                faces.append(face.replace("url(/_next/static", f"url(file://{MEDIA}"))
FONT = "<style>" + "".join(faces) + "</style>"

CSS = """<style>
@page { size: A4; margin: 15mm 14mm 16mm; }
* { box-sizing: border-box; }
html { font-family: Inter, system-ui, sans-serif; font-size: 10pt; line-height: 1.5; color: #1b2433; }
body { margin: 0; background: #fff; }
h1, h2, h3, .cover * { font-family: Manrope, Inter, sans-serif; }
h1 { font-size: 17pt; color: #0b1f4b; margin: 0 0 3mm; padding-bottom: 2mm; border-bottom: 2.5px solid #c9a227; break-after: avoid; font-weight: 800; }
h2 { font-size: 12.5pt; color: #0b1f4b; margin: 5mm 0 2mm; break-after: avoid; font-weight: 800; }
h3 { font-size: 8.5pt; text-transform: uppercase; letter-spacing: .06em; color: #8a6d0f; margin: 3mm 0 1.5mm; break-after: avoid; font-weight: 700; }
p { margin: 0 0 2.5mm; } ol, ul { margin: 0 0 2.5mm; padding-left: 5mm; list-style: revert; } li { margin-bottom: 1mm; }
b, strong { font-weight: 700; }
.cover { height: 262mm; background: #0b1f4b; color: #fff; padding: 28mm 20mm; display: flex; flex-direction: column; break-after: page; }
.cover .tag { color: #e4c65a; font-weight: 700; letter-spacing: .14em; font-size: 10pt; text-transform: uppercase; }
.cover .title { font-size: 40pt; font-weight: 800; line-height: 1.08; margin: 10mm 0 5mm; }
.cover .sub { font-size: 14pt; color: #d8deee; max-width: 140mm; line-height: 1.4; }
.cover .rule { width: 40mm; height: 3px; background: #c9a227; margin: 9mm 0; }
.cover .foot { margin-top: auto; font-size: 10pt; color: #c5cde3; line-height: 1.6; }
.page { break-before: page; }
.lead { font-size: 11pt; color: #33405a; }
.kecil { font-size: 8.4pt; color: #5b6880; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3mm; }
th, td { text-align: left; vertical-align: top; padding: 1.6mm 2.2mm; border-bottom: 1px solid #d9dfeb; font-size: 9.2pt; }
thead { display: table-header-group; } tr { break-inside: avoid; }
thead th { background: #eef1f7; color: #0b1f4b; font-size: 8.2pt; text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }
td.c { text-align: center; color: #5b6880; }
table.rapat td { font-size: 8.8pt; padding: 1.3mm 2mm; }
table.data td, table.data th { font-size: 7.4pt; padding: .9mm 1.1mm; white-space: nowrap; }
table.data code { font-size: 7.2pt; background: none; padding: 0; }
.alur { display: flex; align-items: stretch; gap: 1.2mm; margin: 2mm 0 4mm; break-inside: avoid; }
.alur div { flex: 1 1 0; border: 1.5px solid #0b1f4b; padding: 2mm 2.4mm; background: #fff; min-width: 0; }
.alur i { align-self: center; font-style: normal; color: #c9a227; font-weight: 800; font-size: 12pt; flex: none; }
.alur > div > b { display: block; color: #0b1f4b; font-family: Manrope; font-size: 9.2pt; line-height: 1.25; }
.alur small { display: block; color: #8a6d0f; font-weight: 700; font-size: 7.2pt; text-transform: uppercase; letter-spacing: .04em; margin-bottom: .8mm; }
.alur span { font-size: 7.9pt; color: #45526b; line-height: 1.35; display: block; margin-top: .8mm; }
.alur .ai { background: #0b1f4b; } .alur .ai > b { color: #fff; } .alur .ai span { color: #d8deee; } .alur .ai small { color: #e4c65a; }
.alur .warga { border-color: #8a6d0f; background: #fbf7e8; }
.note { border-left: 3px solid #c9a227; background: #fbf7e8; padding: 2.5mm 3.5mm; margin: 0 0 3mm; font-size: 9.4pt; break-inside: avoid; }
.awas { border-left: 3px solid #b3261e; background: #fdf0ef; padding: 2.5mm 3.5mm; margin: 0 0 3mm; font-size: 9.4pt; break-inside: avoid; }
.kartu { border: 1.5px solid #0b1f4b; padding: 3mm 4mm; margin: 0 0 3mm; display: grid; grid-template-columns: 1.5fr 1fr 1.1fr; gap: 3mm; break-inside: avoid; }
.kartu small { display: block; color: #8a6d0f; font-weight: 700; font-size: 7.6pt; text-transform: uppercase; letter-spacing: .05em; }
.kartu b { font-family: "JetBrains Mono", monospace; font-size: 10.5pt; white-space: nowrap; color: #0b1f4b; }
figure { margin: 0 0 3mm; break-inside: avoid; }
figure img { width: 100%; display: block; border: 1px solid #c3cbdb; }
figcaption { font-size: 8.2pt; color: #5b6880; margin-top: 1.2mm; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
.small img { max-height: 88mm; object-fit: cover; object-position: top; }
code { font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 8.8pt; background: #eef1f7; padding: 0 1mm; white-space: nowrap; }
</style>"""

html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Prototipe Simulasi Ujian SIGAP</title>{FONT}{CSS}</head><body>
<div class="cover"><div class="tag">Polres Metro Jakarta Selatan · Satintelkam</div>
<div class="title">Prototipe<br>Simulasi Ujian<br>SIGAP</div>
<div class="sub">Alur dan fitur yang dapat diperagakan: dari layanan masyarakat sampai rantai kerja petugas, lengkap dengan data contoh dan akun peragaan.</div>
<div class="rule"></div>
<div class="sub" style="font-size:11.5pt">Sistem Intelijen Geospasial dan Analitik Prediktif<br>Deteksi dini kejahatan 3C: curat, curas, curanmor</div>
<div class="foot">Keadaan aplikasi 19 November 2026 · {ALAMAT}<br>Seluruh nomor LP, PIN, plat, nomor rangka, dan akun pada dokumen ini adalah <b>data peragaan (dummy berlabel)</b>, bukan perkara, kendaraan, atau personel nyata. Dokumen ini memuat kata sandi akun peragaan — jangan disebarkan di luar keperluan ujian.</div></div>

<section><h1>1 · Ringkasan dan akun peragaan</h1>
<p class="lead">SIGAP punya dua wajah pada satu alamat. Simulasi ujian mengikuti urutan yang sama: <b>bagian A</b> memperagakan apa yang dapat dilakukan masyarakat tanpa akun, <b>bagian B</b> memperagakan pekerjaan petugas menurut perannya.</p>
<table><tbody>
<tr><td style="width:48mm"><b>SIGAP BERSAMA</b> (masyarakat)<br><code>{ALAMAT}</code></td><td>Tanpa akun dan tanpa identitas: keadaan wilayah, peta kelurahan, panduan pengamanan, survei rasa aman, lacak laporan, cek kendaraan, lapor kejadian, Darurat 110.</td></tr>
<tr><td><b>SIGAP</b> (petugas)<br><code>{ALAMAT}/ops</code></td><td>Dengan akun: mutu data, peringkat 65 kelurahan, produk bulanan berjenjang, pelaksanaan, evaluasi, laporan masyarakat, berkas perkara, imbauan.</td></tr>
</tbody></table>
<div class="kartu"><div><small>Alamat masuk petugas</small><b>{ALAMAT}/ops/masuk</b></div><div><small>Nama pengguna</small><b>demo.&lt;peran&gt;</b></div><div><small>Kata sandi (semua akun)</small><b>{SANDI}</b></div></div>
<h3>Delapan akun peragaan — satu kata sandi</h3>
<table><thead><tr><th style="width:30mm">Peran</th><th style="width:27mm">Nama pengguna</th><th style="width:27mm">Kata sandi</th><th>Tugas dalam sistem</th></tr></thead><tbody>{baris_akun}</tbody></table>
<div class="awas"><b>Kata sandi ini sengaja sederhana dan tertulis di dokumen.</b> Pakai hanya selama ujian, lalu ganti kembali lewat <code>scripts/sandi-peragaan-produksi.sh</code>. Akun <code>demo.polsek</code> terikat pada Polsek Tebet dan <code>demo.fungsi</code> pada fungsi Reskrim.</div>
<h3>Menu yang tampil pada tiap akun</h3>
<table class="rapat"><thead><tr><th style="width:34mm">Akun</th><th>Kelompok menu dan isinya</th></tr></thead><tbody>{baris_menu}</tbody></table>
<p class="kecil">Menu mengikuti hak akses, dan hak itu diperiksa di server — bukan sekadar tombol yang disembunyikan. Alamat yang dibuka tanpa hak dijawab “tidak berwenang”.</p>
</section>

<section class="page"><h1>2 · Bagian A — Masyarakat (SIGAP BERSAMA)</h1>
<p class="lead">Dibuka di <code>{ALAMAT}</code> tanpa masuk. Yang tampil hanya angka historis per wilayah dan tingkat kerawanan kasar — tidak ada skor, prediksi, atau titik kejadian.</p>
<table><thead><tr><th style="width:9mm">No</th><th style="width:36mm">Fitur</th><th style="width:22mm">Menu</th><th>Yang dapat dilakukan masyarakat</th></tr></thead><tbody>
<tr><td class="c">A1</td><td><b>Keadaan wilayah</b></td><td>Beranda</td><td>Melihat tingkat kerawanan (rendah/sedang/tinggi) per kecamatan, angka ringkas 12 bulan, dan imbauan Polres yang berlaku.</td></tr>
<tr><td class="c">A2</td><td><b>Peta kelurahan</b></td><td>Peta</td><td>Memilih kecamatan dan kelurahan: jumlah kejadian per jenis, tren 12 bulan, dan kontak Bhabinkamtibmas.</td></tr>
<tr><td class="c">A3</td><td><b>Panduan pengamanan</b></td><td>Panduan</td><td>Membaca panduan kos, tempat parkir, gedung, dan RT/RW beserta pola kejadian setahun terakhir.</td></tr>
<tr><td class="c">A4</td><td><b>Survei rasa aman</b></td><td>Survey</td><td>Memberi nilai 1–5 dan ulasan anonim per kelurahan; tayang setelah dimoderasi. Melihat hasil per triwulan.</td></tr>
<tr><td class="c">A5</td><td><b>Lacak laporan</b></td><td>Lacak</td><td>Memasukkan <b>nomor LP + PIN</b> untuk melihat tahap perkara (diterima → penyelidikan → penyidikan → P21/SP3 → selesai).</td></tr>
<tr><td class="c">A6</td><td><b>Cek kendaraan</b></td><td>Lacak → Cek kendaraan</td><td>Memasukkan <b>nomor plat</b> atau <b>nomor rangka</b> sebelum membeli kendaraan bekas; jawabannya hanya tercatat / tidak tercatat.</td></tr>
<tr><td class="c">A7</td><td><b>Lapor kejadian</b></td><td>Lapor</td><td>Mengirim laporan tanpa nama: jenis, waktu, wilayah, lokasi, uraian, foto. Menerima <b>nomor tiket</b>.</td></tr>
<tr><td class="c">A8</td><td><b>Darurat</b></td><td>Tombol merah</td><td>Diarahkan menghubungi <b>110</b>. Formulir lapor bukan pengganti laporan polisi dan bukan untuk keadaan darurat.</td></tr>
<tr><td class="c">A9</td><td><b>Bot Telegram dan WhatsApp</b></td><td>Percakapan pribadi dan grup kelurahan</td><td>Melapor, memeriksa status, meminta imbauan, berlangganan, panduan, kontak Bhabinkamtibmas; grup kelurahan menerima imbauan bulanan. Lihat bagian 6.</td></tr>
</tbody></table>
<div class="two">{fig("w1-beranda", "<b>A1 · Beranda.</b> Tingkat kerawanan per kecamatan dan layanan warga.", "small")}{fig("w2-peta", "<b>A2 · Peta.</b> Situasi satu kelurahan dan kontak Bhabinkamtibmas.", "small")}</div>
<div class="two">{fig("w3-panduan", "<b>A3 · Panduan.</b> Pengamanan kos, parkir, gedung, dan RT/RW.", "small")}{fig("w5-survey-triwulan", "<b>A4 · Survey Rasa Aman.</b> Hasil per triwulan dengan jumlah responden.", "small")}</div>
</section>

<section class="page"><h1>3 · Alur A6 — Cek kendaraan</h1>
{alur(("Masyarakat", "Buka Lacak → Cek kendaraan", "Pilih cari berdasarkan nomor plat atau nomor rangka.", "warga"),
      ("Masyarakat", "Isi plat / rangka", "Contoh: <b>B 1493 TWM</b>. Spasi dan huruf kecil tidak berpengaruh.", "warga"),
      ("Sistem", "Mencocokkan", "Dengan berkas perkara curanmor yang tercatat pada sistem ini.", "ai"),
      ("Masyarakat", "Membaca jawaban", "Tercatat / tidak tercatat, jenis, kecamatan, bulan laporan. Tanpa nama pemilik dan nomor LP.", "warga"))}
<div class="two">{fig("s2-kendaraan-tercatat", "Plat <b>B 1493 TWM</b>: tercatat dalam laporan kehilangan — jangan lanjutkan transaksi.")}{fig("s3-kendaraan-tidak", "Plat <b>B 1234 ABC</b> (tidak ada di tabel): tidak ada catatan pada sistem ini.")}</div>
<div class="note"><b>Cara memperagakan.</b> (1) Ketik satu plat dari tabel → kotak merah “Tercatat dalam laporan kehilangan”. (2) Ketik <code>B 1234 ABC</code> → “tidak ada catatan”. (3) Pilih <i>Nomor rangka</i> dan ketik rangka baris 16 → tercatat dan <b>sudah ditemukan</b>. Pencarian dibatasi 10 kali per jam dari satu jaringan.</div>
<h3>Tabel data contoh cek kendaraan — {len(kendaraan)} kendaraan (dummy berlabel)</h3>
<table class="data"><thead><tr><th>No</th><th>Nomor plat</th><th>Nomor rangka</th><th>Kendaraan</th><th>Kecamatan</th><th>Bulan laporan</th><th>Jawaban sistem</th></tr></thead><tbody>{baris_kendaraan}</tbody></table>
<p class="kecil">Yang ditampilkan kepada masyarakat hanya kolom kecamatan, bulan laporan, dan status. Jenis kendaraan dan nomor rangka dicantumkan di sini untuk keperluan peragaan.</p>
</section>

<section class="page"><h1>4 · Alur A5 — Lacak laporan (nomor LP + PIN)</h1>
{alur(("Pelapor", "Melapor ke SPKT", "Menerima nomor LP dan PIN empat angka dari petugas.", "warga"),
      ("Petugas", "Mencatat berkas", "Data → Berkas Perkara: tahap diperbarui tiap perkembangan."),
      ("Pelapor", "Buka Lacak", "Isi nomor LP dan PIN, tekan Lacak.", "warga"),
      ("Pelapor", "Membaca tahap", "Riwayat tahap bertanggal dengan catatan (istilah SP2HP).", "warga"))}
<div class="two">{fig("s1-lacak-hasil", "LP <b>LP/B/250/IX/2025/SPKT/POLSEK TEBET</b>, PIN <b>2491</b>: empat tahap sampai Selesai, kendaraan sudah ditemukan.")}{fig("s4-berkas-perkara", "<b>Data → Berkas Perkara</b> (akun Administrator atau Polsek): daftar berkas dummy beserta PIN peragaannya.")}</div>
<div class="note"><b>Cara memperagakan.</b> Salin nomor LP persis seperti tertulis dan PIN-nya. PIN yang salah, LP yang tidak ada, dan LP tanpa PIN dijawab <b>sama</b> (“tidak ditemukan atau PIN tidak cocok”) supaya halaman ini tidak dapat dipakai memastikan sebuah LP ada. Lima kali PIN salah untuk satu LP mengunci LP itu selama satu jam — <b>jangan menguji PIN salah pada LP yang akan diperagakan</b>.</div>
<h3>Tabel data contoh lacak laporan — {len(perkara)} berkas (dummy berlabel)</h3>
<table class="data"><thead><tr><th>No</th><th>Nomor LP</th><th>PIN</th><th>Jenis</th><th>Kelurahan</th><th>Dilaporkan</th><th>Tahap</th></tr></thead><tbody>{baris_lp}</tbody></table>
<p class="kecil">Saran untuk ujian: baris berstatus <b>Selesai</b> atau <b>P21</b> menampilkan riwayat terpanjang; baris <b>Laporan diterima</b> menunjukkan perkara yang baru masuk. Tanggal mengikuti jam acuan aplikasi (awal Januari 2026).</p>
</section>

<section class="page"><h1>5 · Alur A7 — Lapor kejadian sampai ditangani petugas</h1>
{alur(("Masyarakat", "Isi formulir Lapor", "Jenis kejadian, waktu, kecamatan / kelurahan, lokasi, uraian, foto. Tanpa nama.", "warga"),
      ("Sistem", "Nomor tiket", "Laporan berstatus Diterima; belum menjadi dasar tindakan.", "ai"),
      ("Polsek / Admin", "Verifikasi", "Data → Laporan Masyarakat: periksa, ubah status, beri catatan."),
      ("Administrator", "Pencocokan", "Data → Mutu Data: tautkan ke kejadian resmi atau nyatakan tanpa padanan, dengan alasan."),
      ("Sistem", "Masuk hitungan", "Yang tertaut tidak menambah hitungan; tanpa padanan menjadi kejadian tambahan.", "ai"))}
<div class="two">{fig("w7-lapor", "<b>Lapor</b> (masyarakat): formulir tanpa identitas; keadaan darurat diarahkan ke 110.", "small")}{fig("s5-laporan-masyarakat", "<b>Data → Laporan Masyarakat</b> (petugas): laporan dari web, WhatsApp, dan Telegram menunggu verifikasi.", "small")}</div>
<table class="rapat"><thead><tr><th style="width:36mm">Isian formulir</th><th>Contoh untuk simulasi</th></tr></thead><tbody>
<tr><td>Jenis kejadian</td><td>Pilih salah satu jenis yang tersedia, mis. <b>Pencurian Kendaraan</b>.</td></tr>
<tr><td>Waktu kejadian</td><td>Hari ini atau kemarin (paling lama 30 hari ke belakang).</td></tr>
<tr><td>Kecamatan / kelurahan</td><td>Tebet / Tebet Timur — supaya tampil pada akun <code>demo.polsek</code> (Polsek Tebet).</td></tr>
<tr><td>Lokasi</td><td>“Parkiran minimarket Jl. Tebet Raya” (keterangan tempat, bukan alamat rumah seseorang).</td></tr>
<tr><td>Uraian</td><td>“Sepeda motor hilang saat diparkir ±15 menit. SIMULASI UJIAN.”</td></tr>
</tbody></table>
<div class="note">Tulis kata <b>SIMULASI</b> pada uraian supaya laporan peragaan mudah dikenali dan dibersihkan sesudah ujian. Batas pengiriman: 10 laporan per jam dari satu jaringan.</div>
<h2>Alur A4 — Survei rasa aman</h2>
{alur(("Masyarakat", "Isi survei", "Pilih kelurahan, beri nilai 1–5 dan ulasan singkat.", "warga"),
      ("Administrator", "Moderasi", "Warga → Survey Rasa Aman: tayangkan atau tolak."),
      ("Masyarakat", "Hasil tampil", "Rata-rata per triwulan, jumlah responden, kelurahan terwakili.", "warga"))}
</section>

<section class="page"><h1>6 · Alur A9 — Bot Telegram dan WhatsApp</h1>
<p class="lead">Layanan yang sama lewat percakapan. Di <b>percakapan pribadi</b> warga dapat melapor dan meminta informasi; di <b>grup kelurahan</b> (RT/RW bersama Bhabinkamtibmas) bot hanya melayani imbauan dan kontak — alur laporan tidak berjalan di hadapan anggota grup.</p>
{alur(("Warga", "Percakapan pribadi", "<code>/mulai</code> melapor · <code>/status</code> · <code>/info</code> · <code>/langganan</code> · <code>/panduan</code> · <code>/babin</code>", "warga"),
      ("Bot", "Nomor tiket", "Laporan masuk ke Data → Laporan Masyarakat, sama seperti dari web.", "ai"),
      ("Petugas", "Verifikasi", "Perubahan status dikabarkan bot ke percakapan pelapor."),
      ("Humas", "Setujui imbauan", "Imbauan bulanan terjadwal ke grup dan pelanggan baru terkirim setelah disetujui."))}
<table class="rapat"><thead><tr><th style="width:44mm">Perintah</th><th style="width:22mm">Tempat</th><th>Kegunaan</th></tr></thead><tbody>
<tr><td><code>/mulai</code> atau <code>lapor</code></td><td>Pribadi</td><td>Membuat laporan: jenis kejadian, kecamatan, lokasi (bagikan lokasi atau pilih kelurahan), uraian, foto/video → nomor tiket.</td></tr>
<tr><td><code>/status</code></td><td>Pribadi</td><td>Perkembangan laporan milik percakapan itu.</td></tr>
<tr><td><code>/info Tebet Timur</code></td><td>Pribadi, grup</td><td>Imbauan kehati-hatian bulan depan untuk satu kelurahan. Di grup terdaftar cukup <code>/info</code>.</td></tr>
<tr><td><code>/langganan Tebet Timur</code></td><td>Pribadi</td><td>Menerima imbauan kelurahan itu tiap bulan. Yang disimpan hanya pengenal percakapan dan kelurahan.</td></tr>
<tr><td><code>/berhenti</code></td><td>Pribadi</td><td>Berhenti berlangganan; datanya langsung dihapus.</td></tr>
<tr><td><code>/panduan kos</code></td><td>Pribadi</td><td>Panduan pengamanan (<code>kos</code>, <code>parkir</code>, <code>gedung</code>, <code>rtrw</code>).</td></tr>
<tr><td><code>/babin</code></td><td>Pribadi, grup</td><td>Kontak Bhabinkamtibmas kelurahan (di grup: kelurahan grup itu).</td></tr>
<tr><td><code>/dasbor</code></td><td>Pribadi</td><td>Tautan ke SIGAP BERSAMA.</td></tr>
<tr><td><code>/daftar Tebet Timur</code></td><td>Grup</td><td>Mendaftarkan grup ke satu kelurahan, sekali saja. Kelurahan itu harus sudah punya kontak Bhabinkamtibmas.</td></tr>
<tr><td><code>/bantuan</code></td><td>Pribadi, grup</td><td>Daftar perintah; di grup berupa pesan pengenalan bot.</td></tr>
</tbody></table>
<div class="awas"><b>Tentang gambar pada bagian ini.</b> Isi tiap balon adalah <b>balasan bot yang sebenarnya</b>, diambil dengan menjalankan program bot terhadap salinan lokal aplikasi lalu disusun menjadi tampilan percakapan. Gambar ini <b>bukan tangkapan layar ponsel</b>; tata letak di aplikasi Telegram dan WhatsApp sedikit berbeda. Kanal WhatsApp yang terpasang (WAHA) hanya nomor peragaan, bukan nomor resmi. Kontak Bhabinkamtibmas pada gambar adalah data contoh.</div>
{fig("b1-telegram-lapor", "<b>Telegram, percakapan pribadi — melapor.</b> Dari <code>/mulai</code> sampai nomor tiket, lalu <code>/status</code>. Pilihan tampil sebagai tombol.")}
</section>
<section class="page"><h1>6 · Bot Telegram dan WhatsApp (lanjutan)</h1>
{fig("b2-telegram-info", "<b>Telegram, percakapan pribadi — informasi.</b> <code>/bantuan</code>, <code>/info</code>, <code>/langganan</code>, dan <code>/berhenti</code>. Balasan panjang dipotong (…) pada gambar.")}
</section>
<section class="page"><h1>6 · Bot Telegram dan WhatsApp (lanjutan)</h1>
{fig("b3-whatsapp-pribadi", "<b>WhatsApp, percakapan pribadi.</b> <code>/panduan</code>, <code>/babin</code>, dan <code>/dasbor</code>. Di WhatsApp pilihan tampil sebagai daftar bernomor; warga membalas dengan nomor atau teksnya.")}
</section>
<section class="page"><h1>6 · Grup kelurahan di WhatsApp</h1>
{alur(("Bhabinkamtibmas / RT", "Masukkan bot ke grup", "Nomor bot ditambahkan sebagai anggota grup warga kelurahan.", "warga"),
      ("Anggota grup", "<code>/daftar &lt;kelurahan&gt;</code>", "Sekali saja; grup terikat pada kelurahan itu.", "warga"),
      ("Humas", "Setujui imbauan", "Warga → Buletin &amp; Imbauan, akun <code>demo.humas</code>."),
      ("Bot", "Kirim ke grup", "Imbauan bulan itu masuk ke grup; <code>/info</code> dan <code>/babin</code> dapat diminta kapan saja.", "ai"))}
{fig("b4-whatsapp-grup", "<b>WhatsApp, grup kelurahan (peragaan).</b> <code>/mulai</code> dijawab pesan pengenalan, <code>/daftar Tebet Timur</code> mendaftarkan grup, lalu <code>/info</code> dan <code>/babin</code> tanpa menyebut kelurahan.")}
<div class="note"><b>Cara memperagakan.</b> Pakai grup peragaan yang berisi nomor bot. Ketik <code>/daftar Tebet Timur</code> (lewati bila grup sudah terdaftar), lalu <code>/info</code> dan <code>/babin</code>. Pesan biasa di grup tidak dijawab bot. Teks pengenalan bot masih menyebut imbauan “dikirim otomatis setiap awal bulan”; sejak 19 November 2026 kiriman terjadwal itu menunggu persetujuan Humas.</div>
</section>

<section class="page"><h1>7 · Bagian B — Petugas: siklus bulanan</h1>
<p class="lead">Inti peragaan petugas. Data kejadian diolah menjadi peringkat kelurahan untuk bulan depan, usulan langkah ditimbang berjenjang oleh empat peran, dilaksanakan, lalu dievaluasi terhadap kejadian nyata.</p>
{alur(("1 · Administrator", "Mutu data", "Kelengkapan, pencocokan laporan warga, isian dampak."),
      ("2 · Model AI", "Peringkat", "65 kelurahan diurutkan; IKW di sampingnya.", "ai"),
      ("3 · Analis", "Draf &amp; periksa", "Terima, perbaiki, atau tolak tiap usulan."),
      ("4 · KBO", "Periksa mutu", "Teruskan atau kembalikan dengan alasan."))}
{alur(("5 · Kasat Intelkam", "Telaah", "Teruskan ke Pimpinan atau kembalikan."),
      ("6 · Pimpinan", "Penetapan", "Memilih kelurahan prioritas dan tindak lanjut."),
      ("7 · Fungsi &amp; Polsek", "Pelaksanaan", "Waktu, tempat, tindakan, hasil dicatat."),
      ("8 · Semua", "Evaluasi", "Cakupan, PAI, uji historis; dasar bulan berikutnya."))}
<div class="note"><b>Sistem mengusulkan; manusia memutuskan.</b> Tidak ada keluaran sistem yang menjadi perintah. KBO dan Kasat tidak mengubah isi — mereka meneruskan atau mengembalikan dengan alasan, dan produk yang dikembalikan melewati jenjang itu lagi.</div>
<h3>Langkah demi langkah — keluar lalu masuk dengan akun berikutnya pada tiap pergantian peran</h3>
{langkah([
 ("demo.admin", "Data → Mutu Data", "Baca <b>Kelengkapan</b>. Pada <b>Dampak belum terverifikasi</b> pilih kerugian, cedera, status, tulis rujukan sumber, tekan <b>Catat</b>. Pada <b>Laporan warga dan kejadian resmi</b> pilih padanan dan isi alasan.", "Persen kelengkapan; antrean dampak berkurang; IKW kelurahan itu tidak lagi “ditahan”."),
 ("demo.analis", "Bulan Ini → Produk Bulanan, tab Peringkat 65 Kelurahan", "Baca kolom <b>Perkiraan/bulan</b>, <b>Alasan model</b>, dan <b>IKW</b>. Buka peta pembanding lewat tautan di atas tabel.", "Peringkat bulan sasaran oleh model AI beserta alasannya."),
 ("demo.analis", "Bulan Ini → Produk Bulanan", "Tekan <b>Susun draf</b>. Untuk tiap usulan pilih <b>Terima</b>, <b>Perbaiki</b> (tulis teks dan alasan), atau <b>Tolak</b> (alasan). Tekan <b>Kirim ke KBO</b>.", "Peringkat dibekukan; usulan sepuluh kelurahan teratas; tahap berpindah ke KBO."),
 ("demo.kbo", "Bulan Ini → Produk Bulanan", "Lonceng menunjukkan produk menunggu. Periksa, lalu <b>Teruskan ke Kasat Intelkam</b> — atau tulis alasan dan <b>Kembalikan ke analis</b>.", "Tahap berpindah ke Kasat (atau kembali ke analis dengan alasannya)."),
 ("demo.kasat", "Bulan Ini → Produk Bulanan", "Baca usulan dan keputusan analis. <b>Teruskan ke Pimpinan</b>, atau kembalikan dengan alasan.", "Tahap berpindah ke Pimpinan."),
 ("demo.pimpinan", "Bulan Ini → Produk Bulanan", "Centang kelurahan prioritas (jumlah bebas), ubah teks tindak lanjut bila perlu, isi alasan, tekan tombol penetapan.", "Kelurahan berlabel PRIORITAS; peta menggarisi emas kelurahan itu."),
 ("demo.fungsi", "Bulan Ini → Produk Bulanan", "Pada kelurahan PRIORITAS isi waktu, tempat, tindakan, hasil, satuan; tekan <b>Catat</b>.", "Kegiatan tampil di bawah usulannya."),
 ("demo.polsek", "Bulan Ini → Produk Bulanan", "Sama, tetapi hanya pada kelurahan di wilayah Polsek Tebet.", "Kelurahan di luar wilayahnya tidak dapat diisi."),
 ("demo.pimpinan", "Bulan Ini → Evaluasi", "Baca <b>cakupan</b> kelurahan pilihan dibanding peta pembanding dan <b>PAI</b>; buka <b>Uji historis model</b> (4, 6, atau 8 kelurahan).", "Tabel cakupan, uji tanda, dan skenario tetap."),
 ("demo.humas", "Warga → Buletin &amp; Imbauan", "Baca pratinjau imbauan bulanan, tekan <b>Setujui imbauan</b>.", "Bot baru mengirim imbauan ke grup dan pelanggan setelah disetujui."),
])}
</section>

<section class="page"><h1>8 · Layar tiap tahap siklus bulanan</h1>
<div class="two">{fig("o1-mutu-data", "<b>1 · Mutu Data</b> (Administrator).", "small")}{fig("o6-peringkat", "<b>2 · Peringkat 65 kelurahan</b> dengan alasan model dan IKW (Analis).", "small")}</div>
<div class="two">{fig("o8-produk-draf-analis", "<b>3 · Draf produk bulanan</b>: terima, perbaiki, atau tolak (Analis).", "small")}{fig("o9b-produk-kbo", "<b>4 · Pemeriksaan mutu</b> (KBO).", "small")}</div>
<div class="two">{fig("o10-produk-telaah-kasat", "<b>5 · Telaah</b> (Kasat Intelkam).", "small")}{fig("o11-produk-penetapan-pimpinan", "<b>6 · Penetapan prioritas</b> (Pimpinan).", "small")}</div>
</section>
<section class="page"><h1>8 · Layar tiap tahap siklus bulanan (lanjutan)</h1>
<div class="two">{fig("o12-produk-pelaksanaan", "<b>7 · Pencatatan pelaksanaan</b> (Fungsi dan Polsek).", "small")}{fig("o14b-uji-historis", "<b>8 · Evaluasi</b>: uji historis, PAI, uji tanda.", "small")}</div>
<div class="two">{fig("o15-humas-imbauan", "<b>Humas</b>: menyetujui imbauan bulanan.", "small")}{fig("o13-beranda-pimpinan", "<b>Beranda</b>: papan “Bulan ini” dengan kartu yang menunggu pembaca.", "small")}</div>
<h2>Alur petugas lain yang dapat diperagakan</h2>
<table class="rapat"><thead><tr><th style="width:38mm">Alur</th><th style="width:36mm">Akun</th><th>Langkah</th></tr></thead><tbody>
<tr><td><b>B2 · Laporan masyarakat</b></td><td><code>demo.polsek</code> atau <code>demo.admin</code></td><td>Data → Laporan Masyarakat → buka laporan (termasuk yang baru dikirim pada alur A7) → ubah status menjadi terverifikasi dengan catatan. Polsek hanya melihat wilayahnya.</td></tr>
<tr><td><b>B3 · Berkas perkara</b></td><td><code>demo.admin</code> atau <code>demo.polsek</code></td><td>Data → Berkas Perkara → pilih satu LP dummy → naikkan tahap (mis. Penyelidikan → Penyidikan) dengan catatan → buka kembali <b>Lacak</b> sebagai masyarakat dengan LP + PIN itu: tahap baru tampil.</td></tr>
<tr><td><b>B4 · Peta dan analitik</b></td><td>semua kecuali Humas (peta: semua)</td><td>Wilayah → Peta (historis, kelurahan prioritas digarisi) dan Wilayah → Analitik (tren, hari × rentang empat jam; tab Pola Gangguan: where, when, how, target, repeat).</td></tr>
<tr><td><b>B5 · Moderasi survei</b></td><td><code>demo.admin</code></td><td>Warga → Survey Rasa Aman → tayangkan atau tolak ulasan yang dikirim pada alur A4.</td></tr>
<tr><td><b>B6 · Kontak Babin</b></td><td><code>demo.admin</code></td><td>Warga → Babinkamtibmas → cari kelurahan, Tambah / Ubah / Hapus; kontak tampil pada peta warga.</td></tr>
<tr><td><b>B7 · Pengguna dan audit</b></td><td><code>demo.admin</code> (audit juga <code>demo.pimpinan</code>)</td><td>Sistem → Manajemen Pengguna (akun dan peran) dan Sistem → Audit Log (siapa melakukan apa, termasuk penolakan akses).</td></tr>
<tr><td><b>B8 · Batas wewenang</b></td><td><code>demo.humas</code>, <code>demo.kbo</code></td><td>Tunjukkan bahwa Humas tidak memiliki menu Produk Bulanan, dan KBO tidak dapat menyusun draf maupun menetapkan — pemisahan tugas dijaga server.</td></tr>
</tbody></table>
</section>

<section class="page"><h1>9 · Urutan simulasi ujian (± 15 menit)</h1>
<table><thead><tr><th style="width:8mm">No</th><th style="width:28mm">Akun</th><th>Yang ditunjukkan</th><th style="width:38mm">Data yang dipakai</th><th style="width:18mm">Waktu</th></tr></thead><tbody>
<tr><td class="c">1</td><td>— (tanpa akun)</td><td>Beranda SIGAP BERSAMA, peta satu kelurahan, Panduan.</td><td>Kebayoran Baru → Cipete Utara</td><td>1,5 mnt</td></tr>
<tr><td class="c">2</td><td>—</td><td>Cek kendaraan: satu plat tercatat, satu tidak, satu lewat nomor rangka.</td><td><code>B 1493 TWM</code>, <code>B 1234 ABC</code>, rangka <code>MH1R09PG6RUKECENC</code></td><td>1,5 mnt</td></tr>
<tr><td class="c">3</td><td>—</td><td>Lacak laporan dengan LP + PIN.</td><td><code>LP/B/250/IX/2025/SPKT/POLSEK TEBET</code> · PIN <code>2491</code></td><td>1 mnt</td></tr>
<tr><td class="c">4</td><td>—</td><td>Lapor kejadian; tunjukkan nomor tiket.</td><td>Tebet / Tebet Timur, uraian “SIMULASI UJIAN”</td><td>1,5 mnt</td></tr>
<tr><td class="c">4b</td><td>— (ponsel)</td><td>Bot: <code>/mulai</code> di percakapan pribadi; <code>/info</code> dan <code>/babin</code> di grup kelurahan.</td><td>Grup peragaan Tebet Timur</td><td>1,5 mnt</td></tr>
<tr><td class="c">5</td><td><code>demo.polsek</code></td><td>Laporan tadi muncul di Laporan Masyarakat; verifikasi.</td><td>Laporan langkah 4</td><td>1 mnt</td></tr>
<tr><td class="c">6</td><td><code>demo.admin</code></td><td>Mutu Data: kelengkapan, pencocokan laporan warga, satu isian dampak.</td><td>Antrean yang tersedia</td><td>1,5 mnt</td></tr>
<tr><td class="c">7</td><td><code>demo.analis</code></td><td>Peringkat, alasan model, IKW; susun draf; periksa dua usulan; kirim ke KBO.</td><td>Bulan yang belum punya produk</td><td>2,5 mnt</td></tr>
<tr><td class="c">8</td><td><code>demo.kbo</code></td><td>Lonceng; teruskan ke Kasat.</td><td>Produk langkah 7</td><td>0,5 mnt</td></tr>
<tr><td class="c">9</td><td><code>demo.kasat</code></td><td>Telaah; teruskan ke Pimpinan.</td><td>sda.</td><td>0,5 mnt</td></tr>
<tr><td class="c">10</td><td><code>demo.pimpinan</code></td><td>Tetapkan enam kelurahan prioritas.</td><td>sda.</td><td>1 mnt</td></tr>
<tr><td class="c">11</td><td><code>demo.fungsi</code></td><td>Catat satu kegiatan di kelurahan prioritas.</td><td>sda.</td><td>1 mnt</td></tr>
<tr><td class="c">12</td><td><code>demo.pimpinan</code></td><td>Evaluasi: cakupan, PAI, uji historis.</td><td>Bulan yang sudah berakhir</td><td>1 mnt</td></tr>
<tr><td class="c">13</td><td><code>demo.humas</code></td><td>Setujui imbauan bulanan (bila waktu cukup).</td><td>—</td><td>0,5 mnt</td></tr>
</tbody></table>
<h2>Sebelum ujian</h2>
<ul>
<li>Pastikan kedelapan akun dapat masuk dengan kata sandi <code>{SANDI}</code>.</li>
<li>Pastikan <b>belum ada produk bulanan</b> untuk bulan yang akan diperagakan — satu bulan hanya satu produk, dan produk yang sudah ditetapkan tidak dapat disusun ulang dari layar.</li>
<li>Isi dampak beberapa kelurahan teratas (Mutu Data) supaya kolom IKW-nya tampil, bukan “ditahan”.</li>
<li>Coba satu plat dan satu LP + PIN dari tabel; jangan menghabiskan batas pencarian (10 kali per jam per jaringan) menjelang ujian.</li>
<li>Siapkan dua jendela peramban: satu untuk sisi masyarakat, satu untuk petugas — atau jendela penyamaran untuk berganti akun dengan cepat.</li>
</ul>
<h2>Yang perlu disampaikan apa adanya</h2>
<table class="rapat"><tbody>
<tr><td style="width:40mm"><b>Data pada layar</b></td><td>Kejadian berasal dari data Pusiknas tanpa identitas (posisi 29 September 2026); aplikasi diperagakan seolah berdiri di awal Januari 2026. Berkas perkara, PIN, kendaraan, kontak Babin, laporan warga, dan isian dampak adalah data contoh berlabel.</td></tr>
<tr><td><b>Cek kendaraan</b></td><td>Hanya mencocokkan dengan berkas pada sistem ini, bukan seluruh data kepolisian; untuk kepastian hukum tetap ke Samsat/Polsek.</td></tr>
<tr><td><b>Yang disebut “AI”</b></td><td>Peringkat kelurahan disusun model pembelajaran mesin. Penandaan isian, usulan padanan, dan teks usulan langkah disusun aturan tertulis, bukan model.</td></tr>
<tr><td><b>Yang diukur</b></td><td>Ketepatan penunjukan wilayah — porsi kejadian nyata yang jatuh di kelurahan pilihan — <b>bukan</b> jumlah kejahatan yang berhasil dicegah.</td></tr>
<tr><td><b>Belum ada</b></td><td>Integrasi langsung dengan Pusiknas, kanal WhatsApp resmi, dan kebijakan resmi kata sandi serta masa simpan data.</td></tr>
</tbody></table>
</section></body></html>"""
Path("simulasi-ujian-sigap.html").write_text(html)
print("ditulis", len(html), "font-face:", len(faces))
