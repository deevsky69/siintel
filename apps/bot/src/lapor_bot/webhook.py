"""Satu server webhook kecil untuk kanal yang DIDORONG pihak luar (WhatsApp Cloud API,
Twilio Sandbox). Tiap kanal mendaftarkan jalurnya sendiri; satu port, satu proses.

Setiap pawang menerima isi mentah dan header, dan WAJIB memverifikasi tanda tangan
sebelum membaca isinya — server ini tidak tahu apa pun tentang kanal.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

log = logging.getLogger("lapor_bot.webhook")

#: (status, content_type, body)
Response = tuple[int, str, bytes]
GetHandler = Callable[[dict[str, list[str]]], Response]
PostHandler = Callable[[bytes, dict[str, str], str], Response]


class WebhookServer:
    def __init__(self, port: int) -> None:
        self._port = port
        self._gets: dict[str, GetHandler] = {}
        self._posts: dict[str, PostHandler] = {}

    def route(
        self, path: str, *, get: GetHandler | None = None, post: PostHandler | None = None
    ) -> None:
        if get is not None:
            self._gets[path] = get
        if post is not None:
            self._posts[path] = post

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(set(self._gets) | set(self._posts)))

    def serve_forever(self) -> None:
        gets, posts = self._gets, self._posts

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                log.debug(format, *args)

            def _reply(self, response: Response) -> None:
                status, content_type, body = response
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                handler = gets.get(parsed.path.rstrip("/"))
                if handler is None:
                    self._reply((404, "text/plain", b""))
                    return
                self._reply(handler(parse_qs(parsed.query)))

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                handler = posts.get(parsed.path.rstrip("/"))
                if handler is None:
                    self._reply((404, "text/plain", b""))
                    return
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                headers = {k.lower(): v for k, v in self.headers.items()}
                self._reply(handler(raw, headers, self.path))

        server = ThreadingHTTPServer(("0.0.0.0", self._port), Handler)  # noqa: S104 — di kontainer
        log.info("Webhook mendengarkan di port %s: %s", self._port, ", ".join(self.paths))
        server.serve_forever()


def run_later(target: Callable[[], None]) -> None:
    """Menjalankan pemrosesan setelah jawaban HTTP dikirim (Meta/Twilio menuntut jawaban cepat)."""
    threading.Thread(target=target, daemon=True).start()
