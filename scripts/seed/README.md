# SEED DATA DUMMY

Kode seed berada di dalam paket API (`apps/api/src/prediksi_presisi_api/seeding/`) agar
ikut tercakup lint, typecheck, dan test — bukan sebagai script lepas.
Direktori ini menyimpan dokumentasi dan script pembantu di luar paket.

## Menjalankan

```bash
pnpm db:up && pnpm db:migrate
pnpm seed:master        # TASK 020 — locations, police_units, roles, permissions, users
```

## Prinsip

1. `data/sample/` adalah sumber data dummy kanonik dan **tidak pernah disunting** oleh proses seed.
2. Pemetaan nilai Bahasa Indonesia → enum tersimpan berasal dari `config/taxonomy/mappings.yaml`.
3. Katalog permission berasal dari `config/rbac/permissions.yaml`, bukan dari `data/sample/permissions.csv`.
4. **Fail-fast**: satu baris yang melanggar integritas menghentikan seluruh seed; tidak ada koreksi diam-diam.
5. Idempoten: menjalankan ulang tidak menggandakan baris.
6. Akun demo dibuat dengan password **terkunci**; kredensial nyata diberikan pada TASK 050.
