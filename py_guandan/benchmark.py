#!/usr/bin/env python3
"""Run a benchmark game using all built-in bots.

Reads an optional ``.env`` file from the current working directory to
resolve credentials and configuration:

* ``DEV_API_KEY`` — use this API key directly (skips login).
* ``USERNAME`` / ``PASSWORD`` — log in with these credentials, then
  create a new developer API key.
* ``CONFIG_FILE`` — path to a YAML config file (see
  ``guandan_benchmark/config.yaml.example``).  When absent the built-in
  defaults are printed and confirmed interactively.
* ``LOBBY_SERVER_URL`` — lobby server URL. This overrides the value in the YAML
  config when both are present.

When no API key is found in ``.env`` or the config file, a fresh key is
created and the user is offered to persist it to ``.env``.  The server
only stores key hashes, so existing keys cannot be retrieved.

If none of the above are found in ``.env``, the user is prompted
interactively.

Usage::

    python3 benchmark.py
"""

from __future__ import annotations

import json
import os
import select
import sys
from datetime import datetime
from typing import Any

from guandan_benchmark import (
    GameTracker,
    build_participants,
    check_game_server_reachable,
    check_lobby_reachable,
    create_benchmark,
    discover_deployments,
    monitor_events,
    print_report,
)
from guandan_benchmark.config import load_config
from py_guandan.http import http_client


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------


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
    print(
        f"  {Colour.CYAN}{name}:{Colour.RESET} {Colour.MAGENTA}{value}{Colour.RESET}",
        flush=True,
    )


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
    return http_client.request_json(
        method,
        url,
        body=body,
        headers=request_headers,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Timed input
# ---------------------------------------------------------------------------

def _timed_input(prompt: str, timeout: float) -> str | None:
    """Read a line from stdin with a timeout.  Returns *None* on timeout."""
    print(prompt, end="", flush=True)
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().strip()
    print()  # move past the prompt line after timeout
    return None


# ---------------------------------------------------------------------------
# .env file loading
# ---------------------------------------------------------------------------


def _load_dotenv(path: str | None = None) -> dict[str, str]:
    """Parse a ``.env`` file from the current working directory.

    Returns a dict of key-value pairs.  Handles comments (``#``), blank
    lines, and single- or double-quoted values.  Returns an empty dict if
    the file does not exist.
    """
    if path is None:
        path = os.path.join(os.getcwd(), ".env")
    elif not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)

    result: dict[str, str] = {}
    if not os.path.isfile(path):
        return result

    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip matching single or double quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            result[key] = value
    return result


def _resolve_lobby_url(
    env: dict[str, str],
    config_lobby_url: str,
    *,
    prompt=input,
) -> str:
    """Resolve the lobby URL using .env, YAML, then interactive input."""

    lobby_url = env.get("LOBBY_SERVER_URL", "").strip() or config_lobby_url.strip()
    if not lobby_url:
        lobby_url = (
            prompt("Lobby server URL [http://localhost:8686]: ").strip()
            or "http://localhost:8686"
        )
    return lobby_url.rstrip("/")


# ---------------------------------------------------------------------------
# Default benchmark config (everything except api_key / lobby_url)
# ---------------------------------------------------------------------------
DEFAULT_NUM_ROUNDS = 2
DEFAULT_TOTAL_TIMEOUT = 6000
DEFAULT_HEARTBEAT_TIMEOUT = 1200

# Seats 1 & 3 = Red team, seats 2 & 4 = Blue team
DEFAULT_BOT_CONFIGS: dict[int, dict] = {
    1: {"type": "builtin", "bot_code": "strongBot"},
    2: {"type": "builtin", "bot_code": "basicBot"},
    3: {"type": "builtin", "bot_code": "strongBot"},
    4: {"type": "builtin", "bot_code": "basicBot"},
}

# Seconds to wait before auto-confirming key deletion
_AUTO_DELETE_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Default config confirmation (when no CONFIG_FILE is provided)
# ---------------------------------------------------------------------------


def _print_defaults() -> None:
    """Print the default benchmark configuration for user review."""
    print(f"\n{Colour.BOLD}Default benchmark configuration:{Colour.RESET}")
    print(f"  {Colour.CYAN}Lobby URL:{Colour.RESET}          (will prompt)")
    print(f"  {Colour.CYAN}Num rounds:{Colour.RESET}         {DEFAULT_NUM_ROUNDS}")
    print(f"  {Colour.CYAN}Total timeout:{Colour.RESET}      {DEFAULT_TOTAL_TIMEOUT}s")
    print(
        f"  {Colour.CYAN}Heartbeat timeout:{Colour.RESET}  {DEFAULT_HEARTBEAT_TIMEOUT}s"
    )
    print(f"  {Colour.CYAN}Bots:{Colour.RESET}")
    for seat in sorted(DEFAULT_BOT_CONFIGS):
        cfg = DEFAULT_BOT_CONFIGS[seat]
        label = cfg.get("bot_code") or cfg.get("deployment_id", "?")
        print(f"    Seat {seat}: {cfg['type']} / {label}")


def _confirm_defaults(timeout: float = 60.0) -> bool:
    """Ask the user to confirm the defaults or abort.

    Returns ``True`` if the user confirms, ``False`` otherwise.
    After *timeout* seconds of inactivity the defaults are accepted.
    """
    answer = _timed_input(
        f"\n  {Colour.YELLOW}Proceed with these defaults?"
        f" [Y/n]{Colour.RESET} "
        f"{Colour.DIM}(auto-confirm in {timeout:.0f}s){Colour.RESET}: ",
        timeout,
    )
    return answer is None or answer.strip().lower() in ("", "y", "yes")


# ---------------------------------------------------------------------------
# API key creation
# ---------------------------------------------------------------------------


def _write_to_dotenv(env_path: str, key: str, value: str) -> None:
    """Write or update a key-value pair in the ``.env`` file.

    If the file does not exist it is created.  Existing lines for *key*
    are replaced in-place; other comments and keys are preserved.
    """
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    else:
        lines = []

    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_key, _, _ = stripped.partition("=")
            if existing_key.strip() == key:
                lines[i] = f"{key}={value}\n"
                updated = True
                break

    if not updated:
        # Append to existing file (with a trailing newline if needed)
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def _prompt_api_key_workflow(
    lobby_url: str, access_token: str, env_path: str
) -> tuple[str, str, bool]:
    """Prompt the user to create a new developer API key.

    The server only stores key hashes, so existing keys cannot be
    retrieved.  This workflow always creates a fresh key and offers to
    persist it.

    Returns ``(api_key, key_id, should_delete)``.
    """
    print()
    print(
        f"  {Colour.YELLOW}No API key found in .env or config.yaml.{Colour.RESET}"
    )
    answer = input(
        f"  Create a new developer API key? [Y/n]: "
    ).strip().lower()
    if answer not in ("", "y", "yes"):
        log("Aborted by user — no API key available", colour=Colour.RED)
        sys.exit(1)

    # ── Create the key ──
    key = api_request(
        "POST",
        f"{lobby_url}/api/v1/developer/keys",
        bearer=access_token,
        body={
            "name": (
                "Benchmark"
                f" {datetime.now().astimezone().isoformat(timespec='seconds')}"
            ),
            "environment": "test",
            "scopes": ["benchmarks:create"],
        },
    )
    api_key_val: str = key["api_key"]
    key_id_val: str = key["key_id"]
    log("API key created", key_id_val, colour=Colour.GREEN)
    log_value("API key", api_key_val)

    # ── Offer to persist to .env ──
    print()
    answer = input(
        f"  {Colour.YELLOW}Save API key to .env as DEV_API_KEY? [Y/n]{Colour.RESET} "
    ).strip().lower()
    if answer in ("", "y", "yes"):
        _write_to_dotenv(env_path, "DEV_API_KEY", api_key_val)
        log("API key saved to .env", env_path, colour=Colour.GREEN)
        return api_key_val, key_id_val, False

    # ── Not saving — ask about deletion ──
    print()
    answer = _timed_input(
        f"  {Colour.YELLOW}Delete this key after the benchmark?"
        f" [Y/n]{Colour.RESET} "
        f"{Colour.DIM}(auto-delete in {_AUTO_DELETE_TIMEOUT} s){Colour.RESET}: ",
        _AUTO_DELETE_TIMEOUT,
    )
    should_delete = answer is None or answer.strip().lower() not in ("n", "no")
    if should_delete:
        log("Will auto-delete key after benchmark", colour=Colour.DIM)
    else:
        log("Will keep key after benchmark", key_id_val, colour=Colour.DIM)
    return api_key_val, key_id_val, should_delete


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(
        f"{Colour.BOLD}Guandan Benchmark — Automated Bot Test{Colour.RESET}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Load .env from the current working directory
    # ------------------------------------------------------------------
    env = _load_dotenv()
    env_path = os.path.join(os.getcwd(), ".env")

    # ------------------------------------------------------------------
    # Resolve benchmark configuration
    # ------------------------------------------------------------------
    config_file = env.get("CONFIG_FILE", "").strip()
    if config_file:
        log("Config file", config_file, colour=Colour.GREEN)
        cfg = load_config(
            config_file,
            require_api_key=False,
            require_lobby_url=not bool(env.get("LOBBY_SERVER_URL", "").strip()),
        )
        num_rounds: int = cfg["num_rounds"]
        total_timeout: int = cfg["total_timeout"]
        heartbeat_timeout: int = cfg["heartbeat_timeout"]
        bot_configs: dict[int, dict] = cfg["bot_configs"]
        cfg_lobby_url: str = cfg["lobby_url"]
        cfg_api_key: str = cfg["api_key"]
        config_name: str = cfg.get("name", "")
        log("Config loaded", f"{num_rounds} rounds, lobby={cfg_lobby_url}")
    else:
        _print_defaults()
        if not _confirm_defaults():
            log("Aborted by user", colour=Colour.YELLOW)
            return 1
        num_rounds = DEFAULT_NUM_ROUNDS
        total_timeout = DEFAULT_TOTAL_TIMEOUT
        heartbeat_timeout = DEFAULT_HEARTBEAT_TIMEOUT
        bot_configs = DEFAULT_BOT_CONFIGS
        cfg_lobby_url = ""
        cfg_api_key = ""
        config_name = ""

    # ------------------------------------------------------------------
    # Resolve credentials
    # ------------------------------------------------------------------
    dev_api_key = env.get("DEV_API_KEY", "").strip()
    env_username = env.get("USERNAME", "").strip()
    env_password = env.get("PASSWORD", "").strip()

    access_token = ""
    api_key = ""
    key_id = ""
    should_delete_key = False
    skip_login = False

    if dev_api_key:
        # ── DEV_API_KEY from .env takes top priority ──
        api_key = dev_api_key
        log("Using DEV_API_KEY from .env", colour=Colour.GREEN)
        skip_login = True
    elif cfg_api_key:
        # ── api_key from config file ──
        api_key = cfg_api_key
        log("Using API key from config", colour=Colour.GREEN)
        skip_login = True

    # .env intentionally overrides the YAML value for local/environment-
    # specific execution; prompt only when neither source provides a URL.
    lobby_url = _resolve_lobby_url(env, cfg_lobby_url)

    cancel_url = ""
    game_token = ""
    game_completed = False
    game = None

    try:
        if skip_login:
            # Credentials were provided — skip login and key resolution
            current_step = 1
        else:
            # ------------------------------------------------------------------
            # Step 1: Log in
            # ------------------------------------------------------------------
            step(1, "Log in")
            username = env_username or input("Username: ").strip()
            password = env_password or input("Password: ").strip()
            if not username or not password:
                log("Credentials required", colour=Colour.RED)
                return 1
            login = api_request(
                "POST",
                f"{lobby_url}/api/auth/login",
                body={"account": username, "password": password},
            )
            access_token = login["tokens"]["accessToken"]["token"]
            log("Logged in", login["user"]["id"], colour=Colour.GREEN)

            # ------------------------------------------------------------------
            # Step 2: Create API key
            # ------------------------------------------------------------------
            step(2, "Developer API key")
            api_key, key_id, should_delete_key = _prompt_api_key_workflow(
                lobby_url, access_token, env_path
            )
            current_step = 3

        # ------------------------------------------------------------------
        # Lobby health check
        # ------------------------------------------------------------------
        step(current_step, "Lobby health check")
        check_lobby_reachable(lobby_url)
        log("Lobby is healthy", colour=Colour.GREEN)
        current_step += 1

        # ------------------------------------------------------------------
        # Build participants
        # ------------------------------------------------------------------
        step(current_step, "Build participants")
        deployments = []
        if any(cfg.get("type") == "deployed" for cfg in bot_configs.values()):
            deployments = discover_deployments(lobby_url)
        participants = build_participants(
            bot_configs,
            deployments=deployments,
            lobby_url=lobby_url,
            api_key=api_key,
        )
        log(
            "Participants",
            ", ".join(
                f"Seat {p['seat']}: {p.get('bot_code', p.get('type', '?'))}"
                for p in participants
            ),
        )
        current_step += 1

        # ------------------------------------------------------------------
        # Create benchmark (lobby provisions the test game + runs the monitor)
        # ------------------------------------------------------------------
        step(current_step, "Create benchmark")
        game = create_benchmark(
            lobby_url=lobby_url,
            api_key=api_key,
            participants=participants,
            num_rounds=num_rounds,
            name=config_name,
            total_timeout=total_timeout,
            heartbeat_timeout=heartbeat_timeout,
        )
        if game is None:
            raise RuntimeError("Benchmark creation failed")

        runtime = game["runtime"]
        cancel_url = runtime.get("cancel_url", "")
        game_token = runtime.get("access_token", "")
        log(
            "Benchmark created",
            f"{game.get('benchmark_id')} — {game.get('benchmark_name', '')}",
            colour=Colour.GREEN,
        )
        log_value("Game ID", game["game_id"])
        log_value("Runtime server", runtime.get("runtime_server_id", "?"))
        current_step += 1

        # ------------------------------------------------------------------
        # Game server health check
        # ------------------------------------------------------------------
        step(current_step, "Game server health check")
        check_game_server_reachable(runtime.get("base_url", ""))
        log("Game server is healthy", colour=Colour.GREEN)
        current_step += 1

        # ------------------------------------------------------------------
        # Monitor SSE events & track scores
        # ------------------------------------------------------------------
        step(current_step, "Monitor game events")
        tracker = GameTracker(total_rounds=num_rounds)

        warnings_list: list[str] = []
        errors: list[str] = []

        monitor_result = monitor_events(
            events_url=runtime["events_url"],
            access_token=game_token,
            timeout_s=total_timeout,
            heartbeat_timeout=heartbeat_timeout,
            verbose=True,
            tracker=tracker,
        )
        game_completed = monitor_result["termination"] in (
            "completed",
            "failed",
            "cancelled",
            "test_completed",
        )

        # Collect diagnostics
        if monitor_result["termination"] == "connection_error":
            errors.append(f"SSE connection error: {monitor_result['error']}")
        elif monitor_result["termination"] == "heartbeat_timeout":
            warnings_list.append(
                "SSE heartbeat timeout — game may still be running "
                "but no events were received."
            )
        elif monitor_result["termination"] == "timeout":
            warnings_list.append(
                f"Game did not complete within {total_timeout}s. "
                "It may still be running on the server."
            )

        if len(monitor_result["events"]) == 0:
            warnings_list.append(
                "No SSE events received. The game may have started "
                "before the SSE subscription was established."
            )

        current_step += 1

        # ------------------------------------------------------------------
        # Print report
        # ------------------------------------------------------------------
        step(current_step, "Final report")
        config_for_report = {
            "lobby_url": lobby_url,
            "api_key": api_key,
        }
        print_report(
            config_for_report,
            participants,
            game,
            monitor_result,
            warnings_list,
            errors,
            tracker,
        )

        if not game_completed and errors:
            return 1
        return 0

    except (EOFError, KeyboardInterrupt):
        log("Interrupted", "cleaning up", colour=Colour.YELLOW)
        return 130
    except Exception as error:
        log("Benchmark failed", str(error), colour=Colour.RED)
        return 1
    finally:
        step(9, "Cleanup")
        if cancel_url and game_token and not game_completed:
            try:
                api_request("POST", cancel_url, bearer=game_token, timeout=10)
                log("Test game cancelled", colour=Colour.GREEN)
            except Exception as error:
                log("Game cleanup warning", str(error), colour=Colour.YELLOW)
        if key_id and access_token and should_delete_key:
            try:
                api_request(
                    "DELETE",
                    f"{lobby_url}/api/v1/developer/keys/{key_id}",
                    bearer=access_token,
                )
                log("API key deleted", key_id, colour=Colour.GREEN)
            except Exception as error:
                log("API-key cleanup warning", str(error), colour=Colour.YELLOW)
        elif key_id and not should_delete_key:
            log("API key kept", key_id, colour=Colour.DIM)


if __name__ == "__main__":
    sys.exit(main())
