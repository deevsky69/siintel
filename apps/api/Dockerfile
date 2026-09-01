# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# PREDIKSI PRESISI — image API (FastAPI + uvicorn)
#
# KONTEKS BUILD ADALAH AKAR REPOSITORY, bukan apps/api. Ini bukan selera, melainkan
# akibat dari susunan proyek yang sudah ada:
#   - apps/api/alembic.ini menunjuk ke ../../database/migrations
#   - seeding mencari akar repository lewat penanda pnpm-workspace.yaml + CLAUDE.md
#     (apps/api/src/prediksi_presisi_api/seeding/paths.py)
#   - konfigurasi taksonomi/RBAC/risiko ada di config/, data dummy di data/sample/
# Karena itu image menyusun ulang direktori yang sama di dalam /app.
#
# Paket TIDAK dipasang ke site-packages; hanya dependensinya. Kode dijalankan langsung
# dari /app/apps/api/src lewat PYTHONPATH, supaya perhitungan letak akar repository di
# config.py dan seeding/paths.py tetap benar.
#
# Build (dari akar repository):
#   docker build -f apps/api/Dockerfile -t prediksi-presisi-api .
# ---------------------------------------------------------------------------

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_VERSION=0.12.7

# ---------- Tahap 1 — menyiapkan dependensi ----------
FROM ${PYTHON_IMAGE} AS builder
ARG UV_VERSION

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install "uv==${UV_VERSION}"

WORKDIR /build

# Hanya manifest yang disalin lebih dulu: selama pyproject.toml dan uv.lock tidak
# berubah, seluruh lapisan pemasangan dependensi dipakai ulang dari cache.
COPY apps/api/pyproject.toml apps/api/uv.lock ./

# --frozen        : gagal bila uv.lock tidak sepadan dengan pyproject.toml
# --no-dev        : ruff/mypy/pytest tidak ikut ke produksi
# --no-emit-project: paket proyek sendiri tidak dipasang (lihat catatan di atas)
RUN uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt \
 && uv venv /opt/venv \
 && uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt

# ---------- Tahap 2 — image yang benar-benar dijalankan ----------
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app/apps/api/src \
    APP_ENV=production

# Pengguna tanpa hak istimewa. Proses aplikasi tidak pernah berjalan sebagai root.
RUN groupadd --system --gid 10001 predpol \
 && useradd --system --uid 10001 --gid predpol --create-home --shell /usr/sbin/nologin predpol

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Penanda akar repository — dibaca seeding/paths.py untuk menemukan config/ dan data/sample/.
COPY pnpm-workspace.yaml CLAUDE.md ./

COPY config ./config
COPY data/sample ./data/sample
COPY database/migrations ./database/migrations
COPY apps/api/alembic.ini apps/api/pyproject.toml ./apps/api/
COPY apps/api/src ./apps/api/src

RUN chown -R predpol:predpol /app

# Direktori kerja dibuat sama dengan tempat alembic.ini berada, sehingga
# `alembic upgrade head` dapat dijalankan langsung tanpa argumen tambahan.
WORKDIR /app/apps/api

USER predpol

EXPOSE 8000

# Health endpoint memeriksa database sungguhan (routers/health.py), bukan sekadar 200.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=6 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"

# --proxy-headers: alamat klien yang benar saat berada di belakang reverse proxy.
CMD ["uvicorn", "prediksi_presisi_api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
