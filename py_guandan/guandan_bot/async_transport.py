"""Generic asynchronous transports for stateful Guandan bot handlers."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from ._websocket import loopback_proxy_options

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AsyncBotRequest:
    """A raw protocol message plus transport routing information."""

    raw: str = ""
    session_id: str = ""
    create_session: bool = False
    end_session: bool = False


AsyncBotHandler = Callable[
    [AsyncBotRequest],
    Awaitable[Optional[dict[str, Any]]],
]


def _error_response(session_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "type": "error",
        "session_id": session_id,
        "code": code,
        "message": message,
    }


class AsyncHttpBotServer:
    """aiohttp server for an application-provided async bot handler."""

    def __init__(
        self,
        handler: AsyncBotHandler,
        *,
        host: str = "127.0.0.1",
        port: int = 10001,
        invocation_key: str = "",
        session_count: Callable[[], int] | None = None,
    ) -> None:
        self.handler = handler
        self.host = host
        self.port = port
        self.invocation_key = invocation_key
        self._session_count = session_count
        self._runner: Any = None

    def _is_authorized(self, headers: Any) -> bool:
        if not self.invocation_key:
            return True
        return (
            headers.get("Authorization", "") == f"Bearer {self.invocation_key}"
            or headers.get("X-Api-Key", "") == self.invocation_key
        )

    async def start(self) -> None:
        try:
            from aiohttp import web
        except ImportError as error:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Async HTTP support requires: pip install 'py-guandan[async-http]'"
            ) from error

        app = web.Application()

        async def health(request: Any) -> Any:
            return web.json_response({"status": "ok"})

        async def dispatch(request: Any) -> Any:
            if not self._is_authorized(request.headers):
                return web.json_response(
                    _error_response(
                        request.match_info.get("sid", ""),
                        "unauthorized",
                        "Authorization: Bearer <key> is required.",
                    ),
                    status=401,
                )

            session_id = request.match_info.get("sid", "")
            path = request.path.rstrip("/")
            is_create = request.method == "POST" and path == "/sessions"
            is_message = (
                request.method == "POST"
                and session_id
                and path == f"/sessions/{session_id}/messages"
            )
            is_delete = (
                request.method == "DELETE"
                and session_id
                and path == f"/sessions/{session_id}"
            )
            if not (is_create or is_message or is_delete):
                return web.json_response({"error": "not_found"}, status=404)

            try:
                raw = await request.text()
                response = await self.handler(
                    AsyncBotRequest(
                        raw=raw,
                        session_id=session_id,
                        create_session=is_create,
                        end_session=is_delete,
                    )
                )
            except Exception as error:
                logger.warning("Unable to handle HTTP bot message: %s", error)
                return web.json_response(
                    _error_response(
                        session_id,
                        "invalid_bot_message",
                        str(error),
                    ),
                    status=400,
                )

            if response is None:
                return web.Response(status=204)
            return web.json_response(response)

        app.router.add_get("/health", health)
        app.router.add_post("/sessions", dispatch)
        app.router.add_post("/sessions/{sid}/messages", dispatch)
        app.router.add_delete("/sessions/{sid}", dispatch)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]
        logger.info("AsyncHttpBotServer listening at http://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    @property
    def session_count(self) -> int:
        return self._session_count() if self._session_count is not None else 0


class AsyncWebSocketBotClient:
    """Reconnect a generic async bot handler to the platform gateway."""

    def __init__(
        self,
        handler: AsyncBotHandler,
        *,
        game_server_url: str,
        deployment_key: str,
        protocol_version: str = "guandan-bot-v1",
        initial_reconnect_delay: float = 3.0,
        max_reconnect_delay: float = 60.0,
        reconnect_backoff: float = 2.0,
        session_count: Callable[[], int] | None = None,
    ) -> None:
        self.handler = handler
        self.game_server_url = game_server_url.rstrip("/")
        self.deployment_key = deployment_key
        self.protocol_version = protocol_version
        self.initial_reconnect_delay = initial_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.reconnect_backoff = reconnect_backoff
        self._session_count = session_count
        self._socket: Any = None
        self._running = False
        self._reconnect_delay = initial_reconnect_delay

    async def connect(self) -> None:
        try:
            import websockets
        except ImportError as error:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "WebSocket support requires: pip install 'py-guandan[websocket]'"
            ) from error

        self._running = True
        while self._running:
            try:
                uri = f"{self.game_server_url}/bot-gateway/v1"
                headers = {
                    "Authorization": f"Bearer {self.deployment_key}",
                    "X-Guandan-Bot-Protocol": self.protocol_version,
                }
                header_argument = (
                    "additional_headers"
                    if "additional_headers"
                    in inspect.signature(websockets.connect).parameters
                    else "extra_headers"
                )
                logger.info("Connecting to bot gateway at %s", uri)
                connection = websockets.connect(
                    uri,
                    **{header_argument: headers},
                    **loopback_proxy_options(websockets.connect, uri),
                    ping_interval=30,
                    ping_timeout=10,
                )
                async with connection as socket:
                    self._socket = socket
                    self._reconnect_delay = self.initial_reconnect_delay
                    logger.info("Connected to bot gateway")
                    async for raw in socket:
                        if isinstance(raw, str):
                            await self._handle_frame(raw)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self._running:
                    logger.warning("Connection error: %s", error)
            finally:
                self._socket = None

            if self._running:
                logger.info("Reconnecting in %.1fs...", self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * self.reconnect_backoff,
                    self.max_reconnect_delay,
                )

    async def _handle_frame(self, raw: str) -> None:
        try:
            response = await self.handler(
                AsyncBotRequest(raw=raw, create_session=True)
            )
        except Exception as error:
            logger.warning("Unable to handle WebSocket bot message: %s", error)
            response = _error_response("", "invalid_bot_message", str(error))
        if response is not None and self._socket is not None:
            await self._socket.send(json.dumps(response))

    async def disconnect(self) -> None:
        self._running = False
        if self._socket is not None:
            await self._socket.close()
            self._socket = None

    @property
    def session_count(self) -> int:
        return self._session_count() if self._session_count is not None else 0
