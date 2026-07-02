#!/usr/bin/env python3
"""Run a complete developer WebSocket-bot test game against Guandan."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from guandan_bot import (
    BasicBot,
    BotApplication,
    BotError,
    BotMessage,
)


class Colour:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREY = "\033[90m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


def log(title: str, summary: str = "", *, colour: str = Colour.BLUE) -> None:
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
    suffix = f" {Colour.DIM}{summary}{Colour.RESET}" if summary else ""
    print(
        f"{Colour.GREY}[{timestamp}]{Colour.RESET} "
        f"{colour}{Colour.BOLD}[{title}]{Colour.RESET}{suffix}",
        flush=True,
    )


def log_value(name: str, value: Any) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, indent=2)
    print(f"  {Colour.CYAN}{name}:{Colour.RESET} {Colour.MAGENTA}{value}{Colour.RESET}", flush=True)


def step(number: int, title: str) -> None:
    print(
        f"\n{Colour.BOLD}{'━' * 8} Step {number}: {title} {'━' * 8}{Colour.RESET}",
        flush=True,
    )


def api_request(
    method: str,
    url: str,
    *,
    bearer: str = "",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if bearer:
        request_headers["Authorization"] = f"Bearer {bearer}"
    if headers:
        request_headers.update(headers)
    request = Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers=request_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else {"ok": True}
    except HTTPError as error:
        raw = error.read().decode(errors="replace")
        try:
            detail: Any = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        raise RuntimeError(f"{method} {url} returned HTTP {error.code}: {detail}") from error


def websocket_url(value: str) -> str:
    value = value.rstrip("/")
    if value.startswith("http://"):
        return "ws://" + value.removeprefix("http://")
    if value.startswith("https://"):
        return "wss://" + value.removeprefix("https://")
    return value


class BotRunner:
    """Run the SDK bot dispatcher on one reconnecting gateway connection."""

    def __init__(self, game_server_url: str, deployment_key: str) -> None:
        self.gateway_url = f"{websocket_url(game_server_url)}/bot-gateway/v1"
        self.deployment_key = deployment_key
        self.application = BotApplication(BasicBot, bot_code="DemoPythonBot")
        self.connected = threading.Event()
        self.stopped = threading.Event()
        self._thread = threading.Thread(target=self._thread_main, name="demo-websocket-bot", daemon=True)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._socket: Any = None

    def start(self) -> None:
        self._thread.start()

    def wait_until_connected(self, timeout: float) -> bool:
        return self.connected.wait(timeout)

    def close(self) -> None:
        self.stopped.set()
        loop = self._loop
        socket = self._socket
        if loop is not None and socket is not None:
            try:
                asyncio.run_coroutine_threadsafe(socket.close(), loop).result(timeout=5)
            except Exception:
                pass
        self._thread.join(timeout=8)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as error:
            if not self.stopped.is_set():
                log("Bot failure", str(error), colour=Colour.RED)

    async def _run(self) -> None:
        import websockets

        self._loop = asyncio.get_running_loop()
        header_name = (
            "additional_headers"
            if "additional_headers" in inspect.signature(websockets.connect).parameters
            else "extra_headers"
        )
        headers = {
            "Authorization": f"Bearer {self.deployment_key}",
            "X-Guandan-Bot-Protocol": "guandan-bot-v1",
        }
        while not self.stopped.is_set():
            try:
                log("Bot connecting", self.gateway_url)
                connection = websockets.connect(self.gateway_url, **{header_name: headers})
                async with connection as socket:
                    self._socket = socket
                    self.connected.set()
                    log("Bot connected", "gateway accepted the deployment key", colour=Colour.GREEN)
                    async for raw in socket:
                        if self.stopped.is_set():
                            break
                        if not isinstance(raw, str):
                            continue
                        try:
                            message = BotMessage.parse(raw)
                            summary = _bot_message_summary(message.to_dict())
                            log("Game server → bot", summary, colour=Colour.CYAN)
                            response = self.application.handle(message)
                        except Exception as error:
                            session_id = ""
                            try:
                                session_id = str(json.loads(raw).get("session_id", ""))
                            except Exception:
                                pass
                            log("Bot message error", str(error), colour=Colour.RED)
                            response = BotError(session_id, "bot_decision_error", str(error))
                        if response is not None:
                            log("Bot → game server", _bot_message_summary(response.to_dict()), colour=Colour.MAGENTA)
                            await socket.send(response.to_json())
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connected.clear()
                if not self.stopped.is_set():
                    log("Bot disconnected", f"{error}; retrying", colour=Colour.YELLOW)
                    await asyncio.sleep(1)
            finally:
                self._socket = None


def _bot_message_summary(message: dict[str, Any]) -> str:
    message_type = str(message.get("type", "unknown"))
    payload = message.get("payload")
    if isinstance(payload, dict):
        payload_type = payload.get("type", "unknown")
        return f"{message_type}/{payload_type} session={str(message.get('session_id', ''))[:24]}"
    return f"{message_type} session={str(message.get('session_id', ''))[:24]}"


def follow_game_events(events_url: str, access_token: str, timeout: float = 240.0) -> dict[str, Any]:
    """Subscribe to SSE; the first subscription is what starts auto-start games."""
    request = Request(
        events_url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "text/event-stream"},
    )
    deadline = time.monotonic() + timeout
    event_name = "message"
    data_lines: list[str] = []
    with urlopen(request, timeout=timeout) as response:
        while time.monotonic() < deadline:
            raw = response.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif not line and data_lines:
                text = "\n".join(data_lines)
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {"raw": text}
                data = payload.get("data", payload) if isinstance(payload, dict) else payload
                summary = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                log(f"Game event: {event_name}", summary[:500], colour=Colour.CYAN)
                if event_name in {"test.completed", "game.completed", "game.failed", "game.cancelled"}:
                    return {"event": event_name, "payload": payload}
                event_name = "message"
                data_lines = []
    raise TimeoutError("game event stream closed before a terminal event")


def main() -> int:
    print(f"{Colour.BOLD}Guandan WebSocket Bot — End-to-End Demo{Colour.RESET}", flush=True)
    lobby_url = input("Lobby server URL [http://localhost:8686]: ").strip() or "http://localhost:8686"
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    lobby_url = lobby_url.rstrip("/")
    game_server_url = os.environ.get("GUANDAN_GAME_SERVER_URL", "ws://127.0.0.1:9001")

    access_token = ""
    api_key = ""
    key_id = ""
    deployment_id = ""
    bot: BotRunner | None = None
    cancel_url = ""
    game_token = ""
    game_completed = False

    try:
        step(1, "Log in")
        login = api_request(
            "POST",
            f"{lobby_url}/api/auth/login",
            body={"account": username, "password": password},
        )
        access_token = login["tokens"]["accessToken"]["token"]
        log("Logged in", login["user"]["id"], colour=Colour.GREEN)

        step(2, "Create developer API key with all scopes")
        key = api_request(
            "POST",
            f"{lobby_url}/api/v1/developer/keys",
            bearer=access_token,
            body={
                "name": f"WebSocket demo {datetime.now().astimezone().isoformat(timespec='seconds')}",
                "environment": "test",
                "scopes": ["test_games:create", "test_games:read", "bots:manage", "bots:read"],
            },
        )
        api_key, key_id = key["api_key"], key["key_id"]
        log("API key created", key_id, colour=Colour.GREEN)
        log_value("API key", api_key)

        step(3, "Create bot definition")
        owned = api_request("GET", f"{lobby_url}/api/v1/developer/bots/providers", bearer=api_key)
        providers = owned.get("providers", [])
        if providers:
            provider_id = providers[0]["provider_id"]
            log("Provider selected", provider_id)
        else:
            provider = api_request(
                "POST",
                f"{lobby_url}/api/v1/developer/bots/providers",
                bearer=api_key,
                body={"display_name": "Python Demo Provider", "contact_email": "demo@example.com"},
            )
            provider_id = provider["provider"]["provider_id"]
            log("Provider created", provider_id, colour=Colour.GREEN)
        definition = api_request(
            "POST",
            f"{lobby_url}/api/v1/developer/bots/definitions",
            bearer=api_key,
            body={
                "provider_id": provider_id,
                "display_name": f"Python Demo Bot {uuid.uuid4().hex[:6]}",
                "version": "1.0.0",
                "bot_code": f"python_demo_{uuid.uuid4().hex[:8]}",
                "description": "Temporary end-to-end WebSocket demo bot",
                "supported_rule_sets": ["guandan-standard-v1"],
                "supported_protocol_versions": ["guandan-bot-v1"],
            },
        )
        definition_id = definition["definition"]["bot_definition_id"]
        log("Bot definition created", definition_id, colour=Colour.GREEN)

        step(4, "Deploy WebSocket bot")
        deployment = api_request(
            "POST",
            f"{lobby_url}/api/v1/developer/bots/deployments",
            bearer=api_key,
            body={
                "provider_id": provider_id,
                "transport_type": "websocket",
                "supported_bot_definition_ids": [definition_id],
                "supported_protocol_versions": ["guandan-bot-v1"],
                "max_concurrent_sessions": 4,
                "description": "Temporary Python demo deployment",
            },
        )
        deployment_id = deployment["deployment"]["deployment_id"]
        deployment_key = deployment["deployment_management_key"]
        log("Deployment created", deployment_id, colour=Colour.GREEN)
        log_value("Deployment ID", deployment_id)
        log_value("Deployment key", deployment_key)

        step(5, "Connect WebSocket bot")
        log("Game server", game_server_url)
        bot = BotRunner(game_server_url, deployment_key)
        bot.start()
        if not bot.wait_until_connected(15):
            raise TimeoutError("WebSocket bot did not connect to the game gateway")
        for _ in range(20):
            health = api_request(
                "GET",
                f"{lobby_url}/api/v1/developer/bots/deployments/{deployment_id}/health",
                bearer=api_key,
            )
            if health.get("connected") is True:
                log("Deployment healthy", deployment_id, colour=Colour.GREEN)
                break
            time.sleep(0.5)
        else:
            raise TimeoutError("lobby did not observe the WebSocket deployment connection")

        step(6, "Create one-round test game")
        game = api_request(
            "POST",
            f"{lobby_url}/api/v1/test-games",
            bearer=api_key,
            headers={"Idempotency-Key": str(uuid.uuid4())},
            body={
                "rule_set": "guandan-standard-v1",
                "participants": [
                    {
                        "seat": 1,
                        "type": "external_bot",
                        "deployment_id": deployment_id,
                        "bot_definition_id": definition_id,
                        "deployment_key": deployment_key,
                    },
                    {"seat": 2, "type": "internal_bot", "bot_code": "basicBot"},
                    {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
                    {"seat": 4, "type": "internal_bot", "bot_code": "basicBot"},
                ],
                "options": {
                    "auto_start": True,
                    "record_replay": True,
                    "num_rounds": 1,
                    "num_series": 1,
                    "expires_in_seconds": 300,
                },
            },
        )
        runtime = game["runtime"]
        cancel_url, game_token = runtime["cancel_url"], runtime["access_token"]
        log("Test game created", game["test_game_id"], colour=Colour.GREEN)
        log_value("Game ID", game["game_id"])
        log_value("Runtime server", runtime["runtime_server_id"])

        step(7, "Subscribe to game events and start the game")
        final_event = follow_game_events(runtime["events_url"], game_token)
        game_completed = final_event["event"] in {"test.completed", "game.completed"}
        if not game_completed:
            raise RuntimeError(f"game ended with {final_event['event']}")
        log("Game finished", final_event["event"], colour=Colour.GREEN)
        result_data = final_event["payload"].get("data", {})
        log_value(
            "Result summary",
            {
                "series_completed": result_data.get("num_series_completed"),
                "rounds_completed": result_data.get("num_rounds_completed"),
                "game_id": result_data.get("game_id"),
            },
        )
        return 0
    except (EOFError, KeyboardInterrupt):
        log("Interrupted", "cleaning up", colour=Colour.YELLOW)
        return 130
    except Exception as error:
        log("Demo failed", str(error), colour=Colour.RED)
        return 1
    finally:
        step(8, "Cleanup")
        if cancel_url and game_token and not game_completed:
            try:
                api_request("POST", cancel_url, bearer=game_token, timeout=10)
                log("Test game cancelled", colour=Colour.GREEN)
            except Exception as error:
                log("Game cleanup warning", str(error), colour=Colour.YELLOW)
        if bot is not None:
            bot.close()
            log("WebSocket bot closed", colour=Colour.GREEN)
        if deployment_id and api_key:
            try:
                api_request(
                    "DELETE",
                    f"{lobby_url}/api/v1/developer/bots/deployments/{deployment_id}",
                    bearer=api_key,
                )
                log("Deployment deleted", deployment_id, colour=Colour.GREEN)
            except Exception as error:
                log("Deployment cleanup warning", str(error), colour=Colour.YELLOW)
        if key_id and access_token:
            try:
                api_request(
                    "DELETE",
                    f"{lobby_url}/api/v1/developer/keys/{key_id}",
                    bearer=access_token,
                )
                log("API key deleted", key_id, colour=Colour.GREEN)
            except Exception as error:
                log("API-key cleanup warning", str(error), colour=Colour.YELLOW)


if __name__ == "__main__":
    sys.exit(main())
