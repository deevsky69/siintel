"""Smoke test skeleton API (TASK 002).

Membuktikan test runner berjalan dan aplikasi dapat melayani permintaan.
Test fitur bisnis menyusul bersama fiturnya.
"""

import pytest
from fastapi.testclient import TestClient

from prediksi_presisi_api.config import Settings
from prediksi_presisi_api.main import app

client = TestClient(app)


def test_root_returns_skeleton_state() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "prediksi-presisi-api"
    assert body["state"] == "skeleton"


def test_unknown_route_returns_404() -> None:
    # /health belum dibuat — endpoint tersebut lingkup TASK 030.
    assert client.get("/health").status_code == 404


def test_database_url_is_placeholder_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # TASK 002 hanya menyiapkan placeholder; koneksi dibuat pada TASK 010.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings().database_url == ""


def test_cors_origins_parsed_from_comma_separated_value() -> None:
    settings = Settings(cors_allowed_origins="http://a.test, http://b.test")

    assert settings.cors_origins == ["http://a.test", "http://b.test"]
