# TILES PETA — PENGEMBANGAN LOKAL

Keputusan B-1 (opsi C): pengembangan memakai tile server lokal, bukan penyedia tile internet.

Letakkan berkas `.mbtiles` (ekstrak wilayah Jakarta) di direktori ini, lalu jalankan:

```bash
docker compose -f infra/docker/docker-compose.yml --profile gis up -d
```

Berkas tile **tidak di-commit** (ukurannya besar dan bukan bagian source code).
Sumber tile untuk produksi belum ditetapkan — lihat `docs/implementation-notes/000c-specification-lock.md` §3.0.
