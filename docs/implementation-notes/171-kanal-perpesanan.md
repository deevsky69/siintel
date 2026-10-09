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

## Belum

- WhatsApp menunggu akun bisnis Meta (gate di docs/01 §19.2).
- Keadaan percakapan di memori: bot yang dijalankan ulang melupakan percakapan yang
  belum selesai (pelapor ketik `/mulai` lagi). Laporan terkirim tidak terpengaruh.
- Belum diuji dengan bot Telegram sungguhan dari server ini (butuh token dari pemilik).
