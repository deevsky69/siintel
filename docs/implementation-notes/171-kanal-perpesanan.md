# 171 — Kanal perpesanan: bot Telegram dan WhatsApp (8 Oktober 2026)

**Keputusan pemilik proyek:** (1) Telegram dikerjakan sekarang; (2) identitas pelapor boleh
disimpan untuk kabar perkembangan; (3) WhatsApp juga diinginkan.

## Bentuk

```text
pelapor ⇄ Telegram (long polling) ─┐
pelapor ⇄ WhatsApp (webhook)      ─┴─ apps/bot ──X-Messaging-Key──▶ API /messaging/* ──▶ PostgreSQL
```

- `apps/bot/src/lapor_bot/core.py` — mesin percakapan yang sama untuk kedua kanal:
  jenis → kecamatan → lokasi (bagikan/pilih/lewati) → uraian → foto → ringkasan → kirim.
  Pilihan dijawab nomor atau teks. Perintah `/mulai`, `/status`, `/batal`, `/bantuan`.
- `telegram.py` — Bot API, keyboard balasan, tombol `request_location`, unduh foto.
- `whatsapp.py` — Cloud API, daftar bernomor (judul list interaktif dibatasi 24 huruf),
  `location_request_message`, server webhook kecil (`/webhook/whatsapp`, verifikasi token).
- API: `routers/messaging.py` (kuota per percakapan, 503 tanpa kunci, 401 kunci salah);
  `accept_report()` dipisah dari `/public/citizen-reports` supaya aturan isian satu tempat;
  tabel `citizen_report_contacts` (0013) dengan `last_notified_status` → kabar = status
  laporan ≠ status terakhir dikabarkan; `ack` mencatat audit `NOTIFY_CITIZEN_REPORTER`.
- Produksi: kontainer `predpol-prod-bot`; `scripts/pasang-kanal-perpesanan.sh` menyimpan
  token tanpa mencetaknya; `periksa-produksi.sh` memastikan `/messaging/*` tertutup.

## Yang disimpan dari pelapor, dan batasnya

Kanal + pengenal percakapan, satu baris per laporan, tabel terpisah. Tidak ada endpoint
berperan yang mengembalikannya (dijaga test). Pada WhatsApp pengenalnya nomor telepon.

## Uji

API: `test_api_messaging.py` (9) — kunci, kuota per percakapan, kontak terpisah, kabar
muncul/hilang, lampiran, layar petugas tanpa chat_id; seluruh suite API lulus. Bot: 13 test
tanpa jaringan (alur percakapan, keyboard Telegram, render/parse WhatsApp, verifikasi
webhook); ruff + mypy strict lulus; image Docker terbangun dan menyala.

## Tambahan 9 Oktober 2026 — Twilio Sandbox dan server webhook bersama

Onboarding ke Meta memblokir akun pemilik proyek. Pilihan B pemilik proyek: adapter
**Twilio** (`twilio.py`) memakai mesin percakapan yang sama; webhook `/webhook/twilio`
(form-urlencoded, tanda tangan HMAC-SHA1 `X-Twilio-Signature` atas URL publik + parameter),
balasan lewat REST Twilio, lokasi dari field `Latitude`/`Longitude`, media diunduh dengan
autentikasi akun dan hanya dari host Twilio. `webhook.py` menjadi satu server untuk kedua
kanal yang didorong (Cloud API dan Twilio) di port 8080; rute Traefik menjadi `/webhook/`.
Kabar WHATSAPP dikirim oleh satu pengirim saja (Cloud API didahulukan bila keduanya ada).

## Tambahan 3 November 2026 — WAHA untuk peragaan (klien tidak resmi)

Pemilik proyek meminta kajian WAHA (https://github.com/devlikeapro/waha). Kajian: Apache-2.0,
seluruh fitur gratis sejak 2026.6, mesin NOWEB/GOWS tanpa Chromium, webhook `message` dengan
`payload.location.{latitude,longitude}` (string) dan `payload.media.url`, tanda tangan
`X-Webhook-Hmac` HMAC-SHA512 heksadesimal (vektor dokumentasi diverifikasi dan dijadikan
test), tombol interaktif dinyatakan rusak. Konflik dengan keputusan 9 Oktober 2026 (jalur
tidak resmi ditolak) diangkat; **pilihan A**: peragaan saja, nomor cadangan, keputusan lama
direvisi menjadi "ditolak untuk produksi".

Implementasi: `waha.py` mengikuti pola Twilio — kanal tetap `WHATSAPP`, `628…@c.us` ↔
`+628…` (`…@lid` diteruskan apa adanya), `sendSeen` lalu `sendText`, media hanya dari host
WAHA, webhook `/webhook/waha` dipanggil dari jaringan internal (bukan Traefik) dan diproses
setelah jawaban 200. Bot membuat sesi (`POST /api/sessions`, `start: true`, webhook `message`
+ HMAC + retries) bila belum ada, dicoba ulang tiap 15 detik sampai WAHA siap; sesi yang ada
tidak ditimpa. Compose: layanan `waha` dengan `profiles: ["waha"]`, dinyalakan
`deploy-produksi.sh` hanya bila `WAHA_API_KEY` terisi; volume `waha-sessions`.
`scripts/waha-qr.sh` mengambil QR lewat kontainer bot (WAHA tidak terbuka ke host).
Prioritas pengirim kabar WHATSAPP: Cloud API → Twilio → WAHA. Pembuatan/pengawasan sesi berjalan di thread tersendiri (`watch_session_forever`), terlepas dari siapa pengirim kabar — deploy pertama 4 November 2026 memperlihatkan sesi tidak dibuat karena Twilio masih terpasang. Test: 12 kasus `test_waha.py`
(38 total bot), ruff + mypy strict lulus; `docker compose config` valid dengan/tanpa profile.

Belum diuji dengan WAHA sungguhan (butuh nomor cadangan dan deploy oleh pemilik proyek);
bentuk `payload.location` pada mesin NOWEB belum dikonfirmasi dari sumber — bila kosong,
periksa `payload._data` pada pesan lokasi pertama.

## Tambahan 4 November 2026 — uji WAHA dari ponsel sungguhan, dan cap waktu laporan warga

Uji nyata: nomor cadangan dipasangkan (QR dicetak di terminal oleh `scripts/waha-qr.sh`),
`mulai` → kategori → kecamatan → lokasi → uraian → foto → tiket, semuanya berhasil. Tiga
cacat ditemukan dan diperbaiki di hari yang sama: sesi WAHA tidak dibuat bila Twilio masih
terpasang (thread sesi dipisah), sesi `FAILED` setelah QR tidak dipindai ±3 menit (`restart`,
bukan `start`, dengan jeda 2 menit), dan URL media WAHA berhost `localhost` ditolak pengaman
host (kini hanya jalur `/api/files/` yang dipakai, unduhan selalu ke host WAHA milik bot).

Laporan hasil uji tercatat **1 Januari 2026 00.00**: `reported_at` memakai jam acuan demo.
Pemilik proyek memilih **A**: laporan warga bercap waktu sebenarnya (`clock.citizen_now`
di `public_intake`, `closed_at` di `data_entry`, dan pembersih retensi), jam acuan tetap
untuk yang lain. Test `test_reported_at_uses_the_real_clock_not_the_demo_reference`.

## Belum

- WhatsApp menunggu akun bisnis Meta (gate di docs/01 §19.2).
- Keadaan percakapan di memori: bot yang dijalankan ulang melupakan percakapan yang
  belum selesai (pelapor ketik `/mulai` lagi). Laporan terkirim tidak terpengaruh.
- Belum diuji dengan bot Telegram sungguhan dari server ini (butuh token dari pemilik).
