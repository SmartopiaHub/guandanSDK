"""Async WebSocket transport for Python bots."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from .application import BotApplication
from .protocol import BotError, BotMessage

logger = logging.getLogger(__name__)


class WebSocketBot:
    """Connect a :class:`BotApplication` to the platform bot gateway."""

    def __init__(
        self,
        application: BotApplication,
        *,
        game_server_url: str,
        deployment_key: str,
        protocol_version: str = "guandan-bot-v1",
        reconnect_delay: float = 3.0,
    ) -> None:
        self.application = application
        self.game_server_url = game_server_url.rstrip("/")
        self.deployment_key = deployment_key
        self.protocol_version = protocol_version
        self.reconnect_delay = reconnect_delay
        self._running = False
        self._socket: Any = None

    async def run(self) -> None:
        """Connect and serve forever, reconnecting after connection loss."""
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError("WebSocket support requires: pip install 'py-guandan[websocket]'") from exc

        self._running = True
        uri = f"{self.game_server_url}/bot-gateway/v1"
        headers = {
            "Authorization": f"Bearer {self.deployment_key}",
            "X-Guandan-Bot-Protocol": self.protocol_version,
        }
        while self._running:
            try:
                logger.info("Connecting to %s", uri)
                header_argument = (
                    "additional_headers"
                    if "additional_headers" in inspect.signature(websockets.connect).parameters
                    else "extra_headers"
                )
                connection = websockets.connect(uri, **{header_argument: headers})
                async with connection as socket:
                    self._socket = socket
                    async for raw in socket:
                        if isinstance(raw, str):
                            await self._handle_frame(raw)
            except asyncio.CancelledError:
                raise
            except Exception:
                if self._running:
                    logger.exception("Bot gateway connection failed; retrying in %.1fs", self.reconnect_delay)
                    await asyncio.sleep(self.reconnect_delay)
            finally:
                self._socket = None

    async def _handle_frame(self, raw: str) -> None:
        try:
            message = BotMessage.parse(raw)
            response = self.application.handle(message)
        except Exception as exc:
            logger.exception("Unable to handle bot message")
            response = BotError("", "invalid_bot_message", str(exc))
        if response is not None and self._socket is not None:
            await self._socket.send(response.to_json())

    async def close(self) -> None:
        self._running = False
        if self._socket is not None:
            await self._socket.close()


def run_websocket_bot(application: BotApplication, **configuration: Any) -> None:
    """Synchronous convenience entry point for scripts."""
    asyncio.run(WebSocketBot(application, **configuration).run())
