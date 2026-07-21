"""WebSocket transport for the proxy bot.

Connects to the game-server bot gateway and runs the agent-facing HTTP API
concurrently so an external agent can supply decisions through the usual
``/request``, ``/state``, and ``/action`` endpoints.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from typing import Any

from guandan_bot._websocket import loopback_proxy_options
from guandan_bot.protocol import BotMessage

from proxy_bot import ProxyBotApplication, ProxyHttpServer

logger = logging.getLogger(__name__)


class ProxyWebSocketBot:
    """Connect a :class:`ProxyBotApplication` to the platform bot gateway
    while also serving the agent-facing HTTP API.

    Game messages arriving through the WebSocket are dispatched to
    ``application.handle()`` in a thread executor so the blocking wait for
    an external agent does not stall the async event loop.
    """

    def __init__(
        self,
        application: ProxyBotApplication,
        *,
        game_server_url: str,
        deployment_key: str,
        agent_host: str = "127.0.0.1",
        agent_port: int = 10001,
        protocol_version: str = "guandan-bot-v1",
        reconnect_delay: float = 3.0,
    ) -> None:
        self.application = application
        self.game_server_url = game_server_url.rstrip("/")
        self.deployment_key = deployment_key
        self.agent_host = agent_host
        self.agent_port = agent_port
        self.protocol_version = protocol_version
        self.reconnect_delay = reconnect_delay
        self._running = False
        self._socket: Any = None
        self._http_server: ProxyHttpServer | None = None
        self._http_thread: threading.Thread | None = None

    async def run(self) -> None:
        """Connect to the game-server gateway and serve the agent API forever.

        Reconnects after connection loss.  The agent HTTP server is started
        once and stays up across reconnects.
        """
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "WebSocket support requires: pip install 'py-guandan[websocket]'"
            ) from exc

        self._running = True
        self._start_agent_server()

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
                connection = websockets.connect(
                    uri,
                    **{header_argument: headers},
                    **loopback_proxy_options(websockets.connect, uri),
                )
                async with connection as socket:
                    self._socket = socket
                    async for raw in socket:
                        if isinstance(raw, str):
                            await self._handle_frame(raw)
            except asyncio.CancelledError:
                raise
            except Exception:
                if self._running:
                    logger.exception(
                        "Bot gateway connection failed; retrying in %.1fs",
                        self.reconnect_delay,
                    )
                    await asyncio.sleep(self.reconnect_delay)
            finally:
                self._socket = None

    async def _handle_frame(self, raw: str) -> None:
        """Parse a WebSocket frame and dispatch to the application in a thread.

        ``ProxyBotApplication.handle()`` blocks while waiting for an external
        agent action, so we offload it to a thread executor to keep the
        event loop free.
        """
        try:
            message = BotMessage.parse(raw)
        except Exception as exc:
            logger.exception("Unable to parse bot message")
            return
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self.application.handle, message)
        except Exception as exc:
            logger.exception("Unable to handle bot message")
            return
        if response is not None and self._socket is not None:
            await self._socket.send(response.to_json())

    # ------------------------------------------------------------------
    # Agent-facing HTTP server
    # ------------------------------------------------------------------

    def _start_agent_server(self) -> None:
        """Start the agent HTTP API in a background daemon thread."""
        if self._http_server is not None:
            return
        self._http_server = ProxyHttpServer(
            self.application,
            host=self.agent_host,
            port=self.agent_port,
            invocation_key=None,  # agent routes are unauthenticated
        )
        self._http_thread = threading.Thread(
            target=self._http_server.start,
            kwargs={"background": False},
            daemon=True,
            name="proxy-agent-http",
        )
        self._http_thread.start()
        logger.info(
            "Agent API listening on http://%s:%d",
            self.agent_host,
            self.agent_port,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Shut down the WebSocket connection and agent HTTP server."""
        self._running = False
        if self._socket is not None:
            await self._socket.close()
        if self._http_server is not None:
            self._http_server.close()


def run_websocket_proxy_bot(application: ProxyBotApplication, **configuration: Any) -> None:
    """Synchronous convenience entry point for scripts."""
    asyncio.run(ProxyWebSocketBot(application, **configuration).run())
