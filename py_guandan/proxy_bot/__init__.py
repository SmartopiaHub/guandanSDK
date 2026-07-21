"""Proxy bot that lets an external agent make Guandan decisions.

Supports both HTTP and WebSocket transports for platform communication
while exposing an unauthenticated agent-facing HTTP API.
"""

from proxy_bot.proxy_bot import ProxyBotApplication, ProxyError, ProxySession
from proxy_bot.server import ProxyHttpServer
from proxy_bot.websocket import ProxyWebSocketBot, run_websocket_proxy_bot

__all__ = [
    "ProxyBotApplication",
    "ProxyError",
    "ProxyHttpServer",
    "ProxySession",
    "ProxyWebSocketBot",
    "run_websocket_proxy_bot",
]
