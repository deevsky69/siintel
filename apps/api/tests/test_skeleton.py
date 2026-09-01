"""Test dasar aplikasi API.

Sejak TASK 030 seluruh endpoint berada di bawah `/api/v1`. Route penanda skeleton
pada akar dihapus dan digantikan `/api/v1/health` yang benar-benar memeriksa database.
"""

import pytest
from fastapi.testclient import TestClient

from prediksi_presisi_api.config import Settings
from prediksi_presisi_api.main import app

client = TestClient(app)


def test_api_is_versioned() -> None:
    # Akar sengaja tidak melayani apa pun: kontrak memakai /api/v1 (docs/05 §1).
    assert client.get("/").status_code == 404


def test_openapi_document_is_available_outside_production() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "PREDIKSI PRESISI API"


def test_health_endpoint_is_registered() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths


def test_database_url_is_placeholder_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # TASK 002 hanya menyiapkan placeholder; koneksi dibuat pada TASK 010.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings().database_url == ""


def test_cors_origins_parsed_from_comma_separated_value() -> None:
    settings = Settings(cors_allowed_origins="http://a.test, http://b.test")

    assert settings.cors_origins == ["http://a.test", "http://b.test"]
