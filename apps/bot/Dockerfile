# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_VERSION=0.12.7

FROM ${PYTHON_IMAGE} AS builder
ARG UV_VERSION
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install "uv==${UV_VERSION}"
WORKDIR /build
COPY apps/bot/pyproject.toml apps/bot/uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt \
 && uv venv /opt/venv \
 && uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt

FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:${PATH}" PYTHONPATH=/app/src
RUN groupadd --system --gid 10002 laporbot \
 && useradd --system --uid 10002 --gid laporbot --create-home --shell /usr/sbin/nologin laporbot
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY apps/bot/src ./src
USER laporbot
EXPOSE 8080
CMD ["python", "-m", "lapor_bot"]
