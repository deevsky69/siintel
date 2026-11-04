"""Klien ke API PREDIKSI PRESISI — satu-satunya jalan bot menyentuh data.

Bot TIDAK membuka basis data. Seluruh aturan isian, kuota, dan audit tetap milik API
(`routers/messaging.py`); bot hanya bercakap-cakap lalu menyerahkan hasilnya.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


class BackendError(Exception):
    """Jawaban API yang bukan keberhasilan, dengan pesan yang layak diteruskan ke pelapor."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class Kelurahan:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Options:
    categories: list[str]
    kecamatan: list[str]
    areas: dict[str, list[Kelurahan]] = field(default_factory=dict)
    max_description: int = 1000
    max_attachments: int = 3


class Backend(Protocol):
    def options(self) -> Options: ...
    def submit(self, channel: str, chat_id: str, report: dict[str, Any]) -> dict[str, Any]: ...
    def stage_attachment(
        self, channel: str, chat_id: str, filename: str, content: bytes, media_type: str
    ) -> str: ...
    def reports_of(self, channel: str, chat_id: str) -> list[dict[str, Any]]: ...
    def updates(self, channel: str) -> list[dict[str, Any]]: ...
    def ack(self, channel: str, ticket: str, status: str) -> None: ...
    def babin(self, kelurahan: str) -> dict[str, Any] | None: ...
    def pending_bulletins(self) -> list[dict[str, Any]]: ...
    def bulletin_sent(self, bulletin_id: str, delivery: dict[str, str]) -> None: ...
    def register_group(
        self, channel: str, chat_id: str, kelurahan: str, sender: str | None = None
    ) -> dict[str, Any]: ...
    def advisory(self, kelurahan: str, month: str | None = None) -> dict[str, Any]: ...
    def pending_advisories(self) -> list[dict[str, Any]]: ...
    def advisory_sent(self, kelurahan: str, month: str, delivery: dict[str, str]) -> None: ...


def _message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict):
        error = body.get("error") or body
        if isinstance(error, dict):
            return str(error.get("message") or error.get("detail") or body)
        return str(body.get("detail") or body)
    return str(body)


class ApiBackend:
    """Implementasi HTTP atas `/api/v1/public/report-options` dan `/api/v1/messaging/*`."""

    def __init__(self, base: str, key: str, timeout: float = 20.0) -> None:
        self._client = httpx.Client(
            base_url=base.rstrip("/") + "/api/v1",
            headers={"X-Messaging-Key": key},
            timeout=timeout,
        )

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise BackendError(response.status_code, _message(response))

    def options(self) -> Options:
        response = self._client.get("/public/report-options")
        self._raise(response)
        body = response.json()
        areas = {
            row["kecamatan"]: [
                Kelurahan(k["name"], float(k["latitude"]), float(k["longitude"]))
                for k in row.get("kelurahan", [])
            ]
            for row in body.get("areas", [])
        }
        return Options(
            categories=list(body["categories"]),
            kecamatan=list(body["kecamatan"]),
            areas=areas,
            max_description=int(body.get("max_description", 1000)),
            max_attachments=int(body.get("max_attachments", 3)),
        )

    def submit(self, channel: str, chat_id: str, report: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(
            "/messaging/reports", json={**report, "channel": channel, "chat_id": chat_id}
        )
        self._raise(response)
        result: dict[str, Any] = response.json()
        return result

    def stage_attachment(
        self, channel: str, chat_id: str, filename: str, content: bytes, media_type: str
    ) -> str:
        response = self._client.post(
            "/messaging/attachments",
            data={"channel": channel, "chat_id": chat_id},
            files={"berkas": (filename, content, media_type)},
        )
        self._raise(response)
        return str(response.json()["handle"])

    def reports_of(self, channel: str, chat_id: str) -> list[dict[str, Any]]:
        response = self._client.get(
            "/messaging/reports", params={"channel": channel, "chat_id": chat_id}
        )
        self._raise(response)
        rows: list[dict[str, Any]] = response.json()["data"]
        return rows

    def updates(self, channel: str) -> list[dict[str, Any]]:
        response = self._client.get("/messaging/updates", params={"channel": channel})
        self._raise(response)
        rows: list[dict[str, Any]] = response.json()["data"]
        return rows

    def ack(self, channel: str, ticket: str, status: str) -> None:
        response = self._client.post(
            "/messaging/updates/ack", json={"channel": channel, "ticket": ticket, "status": status}
        )
        self._raise(response)

    def babin(self, kelurahan: str) -> dict[str, Any] | None:
        response = self._client.get("/public/babin", params={"kelurahan": kelurahan})
        self._raise(response)
        data: dict[str, Any] | None = response.json().get("data")
        return data

    def pending_bulletins(self) -> list[dict[str, Any]]:
        response = self._client.get("/messaging/bulletins/pending")
        self._raise(response)
        rows: list[dict[str, Any]] = response.json()["data"]
        return rows

    def bulletin_sent(self, bulletin_id: str, delivery: dict[str, str]) -> None:
        response = self._client.post(
            f"/messaging/bulletins/{bulletin_id}/sent", json={"delivery": delivery}
        )
        self._raise(response)

    def register_group(
        self, channel: str, chat_id: str, kelurahan: str, sender: str | None = None
    ) -> dict[str, Any]:
        response = self._client.post(
            "/messaging/groups",
            json={"channel": channel, "chat_id": chat_id, "kelurahan": kelurahan, "sender": sender},
        )
        self._raise(response)
        data: dict[str, Any] = response.json()
        return data

    def advisory(self, kelurahan: str, month: str | None = None) -> dict[str, Any]:
        params: dict[str, str] = {"kelurahan": kelurahan}
        if month:
            params["month"] = month
        response = self._client.get("/messaging/advisory", params=params)
        self._raise(response)
        data: dict[str, Any] = response.json()
        return data

    def pending_advisories(self) -> list[dict[str, Any]]:
        response = self._client.get("/messaging/advisories/pending")
        self._raise(response)
        rows: list[dict[str, Any]] = response.json()["data"]
        return rows

    def advisory_sent(self, kelurahan: str, month: str, delivery: dict[str, str]) -> None:
        response = self._client.post(
            "/messaging/advisories/sent",
            json={"kelurahan": kelurahan, "month": month, "delivery": delivery},
        )
        self._raise(response)
