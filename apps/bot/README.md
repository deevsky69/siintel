# LAPOR PRESISI — bot kanal perpesanan

Laporan masyarakat lewat **Telegram** (dan **WhatsApp** setelah akun WhatsApp Business
Platform tersedia). Bot ini hanya bercakap-cakap; seluruh aturan isian, kuota, audit, dan
penyimpanan tetap milik API lewat `/api/v1/messaging/*` (kunci bersama `MESSAGING_API_KEY`).

```text
pelapor ⇄ Telegram/WhatsApp ⇄ bot (apps/bot) ⇄ API /messaging/* ⇄ PostgreSQL
```

Keputusan pemilik proyek 8 Oktober 2026: pengenal percakapan **disimpan** (tabel
`citizen_report_contacts`) untuk mengabari perkembangan laporan. Yang tidak disimpan: nama,
nomor yang ditampilkan, foto profil.

## Menjalankan di lokal

```bash
cd apps/bot
uv sync
API_BASE=http://127.0.0.1:8100 MESSAGING_API_KEY=... TELEGRAM_BOT_TOKEN=... uv run python -m lapor_bot
```

Lihat `docs/10-panduan-deployment.md` §"Kanal perpesanan" untuk produksi.

## Uji

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy
```
