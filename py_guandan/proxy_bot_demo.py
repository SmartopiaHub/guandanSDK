#!/usr/bin/env python3
"""Run the Guandan proxy bot.

Supports both HTTP and WebSocket transports for platform communication.  The
agent-facing API (``/request``, ``/state``, ``/action``, ``/help``) is always
served over HTTP.
"""

from __future__ import annotations

import argparse
import os

from proxy_bot import ProxyBotApplication, ProxyHttpServer, run_websocket_proxy_bot


def main() -> None:
    parser = argparse.ArgumentParser(description="Guandan proxy bot")
    parser.add_argument(
        "--protocol",
        choices=("websocket", "http"),
        default=os.getenv("PROXY_BOT_PROTOCOL", "websocket"),
        help="platform transport protocol (default: websocket)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("PROXY_BOT_HOST", "127.0.0.1"),
        help="agent API listen address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PROXY_BOT_PORT", "10001")),
        help="agent API listen port (default: 10001)",
    )
    parser.add_argument(
        "--game-server",
        default=os.getenv("PROXY_BOT_GAME_SERVER", os.getenv("GAME_SERVER_URL", "ws://127.0.0.1:9001")),
        help="WebSocket game-server URL (WebSocket protocol only)",
    )
    parser.add_argument(
        "--deployment-key",
        default=os.getenv("BOT_DEPLOYMENT_KEY", ""),
        help="platform-issued WebSocket deployment key (WebSocket protocol only)",
    )
    parser.add_argument(
        "--invocation-key",
        default=os.getenv("HTTP_BOT_INVOCATION_KEY", ""),
        help="platform-issued HTTP invocation token (HTTP protocol only)",
    )
    parser.add_argument(
        "--action-timeout",
        type=float,
        default=float(os.getenv("PROXY_ACTION_TIMEOUT", "600")),
        help="maximum wait for an agent action in seconds",
    )
    parser.add_argument(
        "--bot-code",
        default="proxyBot",
        help="bot code reported in responses (default: proxyBot)",
    )
    args = parser.parse_args()

    application = ProxyBotApplication(
        bot_code=args.bot_code,
        action_timeout=args.action_timeout,
    )

    if args.protocol == "http":
        if not args.invocation_key:
            parser.error(
                "HTTP protocol requires --invocation-key or HTTP_BOT_INVOCATION_KEY "
                "environment variable"
            )
        ProxyHttpServer(
            application,
            host=args.host,
            port=args.port,
            invocation_key=args.invocation_key,
        ).start()
    else:
        if not args.deployment_key:
            parser.error(
                "WebSocket protocol requires --deployment-key or BOT_DEPLOYMENT_KEY "
                "environment variable"
            )
        run_websocket_proxy_bot(
            application,
            game_server_url=args.game_server,
            deployment_key=args.deployment_key,
            agent_host=args.host,
            agent_port=args.port,
        )


if __name__ == "__main__":
    main()
