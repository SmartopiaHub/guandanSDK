"""Standard-library HTTP transport for platform-invoked bots."""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .application import BotApplication
from .protocol import BotError, BotMessage, SessionEnd


class HttpBotServer:
    def __init__(
        self,
        application: BotApplication,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        invocation_key: str | None = None,
    ) -> None:
        self.application = application
        self.host = host
        self.port = port
        self.invocation_key = invocation_key
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("HTTP bot server has not been started")
        return f"http://{self.host}:{self._server.server_port}"

    def start(self, *, background: bool = False) -> None:
        """Start serving. Set ``background=True`` for tests or embedding."""
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._write(HTTPStatus.OK, {"status": "ok"})
                else:
                    self._write(HTTPStatus.NOT_FOUND, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                self._dispatch()

            def do_DELETE(self) -> None:  # noqa: N802
                self._dispatch()

            def _dispatch(self) -> None:
                session_id = _session_id(self.path)
                if not self._authorized():
                    self._write(HTTPStatus.UNAUTHORIZED, BotError(session_id or "", "unauthorized", "valid bot invocation key required").to_dict())
                    return
                try:
                    path = urlsplit(self.path).path.rstrip("/")
                    is_create = self.command == "POST" and path == "/sessions"
                    is_message = self.command == "POST" and session_id and path == f"/sessions/{session_id}/messages"
                    is_delete = self.command == "DELETE" and session_id and path == f"/sessions/{session_id}"
                    if not (is_create or is_message or is_delete):
                        self._write(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                        return
                    if is_delete:
                        message: BotMessage = SessionEnd(session_id)
                    else:
                        length = int(self.headers.get("Content-Length", "0"))
                        message = BotMessage.parse(self.rfile.read(length))
                    if session_id and message.session_id != session_id:
                        self._write(HTTPStatus.BAD_REQUEST, BotError(message.session_id, "session_id_mismatch", "path and message session IDs differ").to_dict())
                        return
                    response = owner.application.handle(message)
                    self._write(HTTPStatus.NO_CONTENT if response is None else HTTPStatus.OK, None if response is None else response.to_dict())
                except Exception as exc:
                    self._write(HTTPStatus.BAD_REQUEST, BotError(session_id or "", "invalid_bot_message", str(exc)).to_dict())

            def _authorized(self) -> bool:
                if not owner.invocation_key:
                    return True
                return self.headers.get("Authorization") == f"Bearer {owner.invocation_key}" or self.headers.get("X-Api-Key") == owner.invocation_key

            def _write(self, status: HTTPStatus, body: dict[str, Any] | None) -> None:
                encoded = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                if body is not None:
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                if encoded:
                    self.wfile.write(encoded)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        if background:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
        else:
            self._server.serve_forever()

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def __enter__(self) -> "HttpBotServer":
        self.start(background=True)
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _session_id(path: str) -> str | None:
    parts = [part for part in urlsplit(path).path.split("/") if part]
    return parts[1] if len(parts) >= 2 and parts[0] == "sessions" else None
