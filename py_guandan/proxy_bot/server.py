"""Combined platform-facing and agent-facing HTTP server."""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import yaml

from guandan_bot.protocol import BotError, BotMessage, SessionEnd

from proxy_bot import ProxyBotApplication, ProxyError


HELP = """\
# Guandan HTTP Proxy Bot API

The public agent API has no authentication. Platform `/sessions` routes use
the configured invocation token.

## Selectors and multiple games

Use `session_id` (canonical) or `game_id` as a query parameter. Without a
selector, `GET /request` and `GET /state` return a list for every active
session. `POST /action` may omit the selector only when exactly one request is
pending.

## GET /request

Returns pending play/tribute/return requests as JSON.

Examples:
`GET /request`
`GET /request?session_id=<id>`
`GET /request?game_id=<id>`

## GET /state

Returns YAML containing the current round, initial hand, current hand, players,
turns, recent events, and the latest server game-state snapshot.

## POST /action

Submit a string-encoded action for a pending request.

- Plain text: body is `3H`, `3H 3D`, or `pass`.
- JSON: `{"action":"3H 3D","session_id":"..."}`.
- Form/query selector: `POST /action?game_id=...`.
- Play accepts a space-separated card list. Use `pass` for an empty play.
- Tribute and return accept exactly one card.
- Cards use `2-9,T,J,Q,K,A,BJ,RJ` plus suit `H,D,C,S`; current-level cards
  carry `*`, for example `2H*`.

## GET /help

Returns this specification as plain text.
"""


class ProxyHttpServer:
    def __init__(
        self,
        application: ProxyBotApplication,
        *,
        host: str = "127.0.0.1",
        port: int = 10001,
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
            raise RuntimeError("server has not started")
        return f"http://{self.host}:{self._server.server_port}"

    def start(self, *, background: bool = False) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                try:
                    path, query = self._path_query()
                    if path == "/health":
                        self._json(HTTPStatus.OK, {"status": "ok"})
                    elif path == "/request":
                        self._json(HTTPStatus.OK, owner.application.requests(**self._selectors(query)))
                    elif path == "/state":
                        body = yaml.safe_dump(
                            owner.application.states(**self._selectors(query)),
                            allow_unicode=True,
                            sort_keys=False,
                        )
                        self._write(HTTPStatus.OK, body.encode(), "application/yaml; charset=utf-8")
                    elif path == "/help":
                        self._write(HTTPStatus.OK, HELP.encode(), "text/plain; charset=utf-8")
                    else:
                        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                except ProxyError as exc:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

            def do_POST(self) -> None:  # noqa: N802
                path, query = self._path_query()
                if path == "/action":
                    self._action(query)
                else:
                    self._platform_dispatch(path)

            def do_DELETE(self) -> None:  # noqa: N802
                path, _ = self._path_query()
                self._platform_dispatch(path)

            def _action(self, query: dict[str, list[str]]) -> None:
                try:
                    body = self._body()
                    selectors = self._selectors(query)
                    content_type = self.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        data = json.loads(body or b"{}")
                        if not isinstance(data, dict):
                            raise ProxyError("JSON body must be an object")
                        action = str(data.get("action", ""))
                        selectors["session_id"] = data.get("session_id") or selectors["session_id"]
                        selectors["game_id"] = data.get("game_id") or selectors["game_id"]
                    else:
                        action = body.decode().strip()
                    result = owner.application.submit_action(action, **selectors)
                    self._json(HTTPStatus.OK, {"accepted": True, "response": result})
                except (ProxyError, ValueError, json.JSONDecodeError) as exc:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

            def _platform_dispatch(self, path: str) -> None:
                session_id = _session_id(path)
                if not self._authorized():
                    self._json(
                        HTTPStatus.UNAUTHORIZED,
                        BotError(session_id or "", "unauthorized", "valid bot invocation key required").to_dict(),
                    )
                    return
                try:
                    is_create = self.command == "POST" and path == "/sessions"
                    is_message = self.command == "POST" and session_id and path == f"/sessions/{session_id}/messages"
                    is_delete = self.command == "DELETE" and session_id and path == f"/sessions/{session_id}"
                    if not (is_create or is_message or is_delete):
                        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                        return
                    message = SessionEnd(session_id) if is_delete else BotMessage.parse(self._body())
                    if session_id and message.session_id != session_id:
                        raise ValueError("path and message session IDs differ")
                    response = owner.application.handle(message)
                    if response is None:
                        self.send_response(HTTPStatus.NO_CONTENT)
                        self.end_headers()
                    else:
                        self._json(HTTPStatus.OK, response.to_dict())
                except Exception as exc:
                    print(
                        f"[proxy] platform request failed: method={self.command} "
                        f"path={path} error={type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    self._json(
                        HTTPStatus.BAD_REQUEST,
                        BotError(session_id or "", "invalid_bot_message", str(exc)).to_dict(),
                    )

            def _authorized(self) -> bool:
                if not owner.invocation_key:
                    return True
                return (
                    self.headers.get("Authorization") == f"Bearer {owner.invocation_key}"
                    or self.headers.get("X-Api-Key") == owner.invocation_key
                )

            def _body(self) -> bytes:
                return self.rfile.read(int(self.headers.get("Content-Length", "0")))

            def _path_query(self) -> tuple[str, dict[str, list[str]]]:
                split = urlsplit(self.path)
                return unquote(split.path).rstrip("/") or "/", parse_qs(split.query)

            def _selectors(self, query: dict[str, list[str]]) -> dict[str, str | None]:
                return {
                    "session_id": query.get("session_id", [None])[0],
                    "game_id": query.get("game_id", [None])[0],
                }

            def _json(self, status: HTTPStatus, value: Any) -> None:
                self._write(
                    status,
                    json.dumps(value, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8",
                )

            def _write(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                print(f"[http] {self.address_string()} {format % args}", flush=True)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        print(f"[proxy] listening on {self.base_url}", flush=True)
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


def _session_id(path: str) -> str | None:
    parts = [part for part in path.split("/") if part]
    return parts[1] if len(parts) >= 2 and parts[0] == "sessions" else None
