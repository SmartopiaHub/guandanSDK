#!/usr/bin/env python3
"""Run a benchmark game using all built-in bots.

Prompts for lobby credentials, discovers or creates a developer API key,
then runs a fully automated test game with the :mod:`guandan_benchmark`
module.

Usage::

    python3 benchmark.py
"""

from __future__ import annotations

import json
import select
import sys
from datetime import datetime
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from guandan_benchmark import (
    GameTracker,
    build_participants,
    check_game_server_reachable,
    check_lobby_reachable,
    create_test_game,
    monitor_events,
    print_report,
)

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
        raise RuntimeError(
            f"{method} {url} returned HTTP {error.code}: {detail}"
        ) from error


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

# Maximum number of existing keys to display
_MAX_KEYS_TO_SHOW = 5
# Seconds to wait before auto-selecting the most recent key
_AUTO_SELECT_TIMEOUT = 10

# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------


def _fetch_valid_keys(
    lobby_url: str, access_token: str
) -> list[dict[str, Any]]:
    """Fetch and return active keys that have ``test_games:create`` scope.

    Keys are sorted by ``created_at`` descending (most recent first).
    """
    resp = api_request(
        "GET",
        f"{lobby_url}/api/v1/developer/keys",
        bearer=access_token,
    )
    all_keys: list[dict[str, Any]] = resp.get("keys", [])
    valid: list[dict[str, Any]] = []
    for k in all_keys:
        if k.get("status") != "active":
            continue
        if "test_games:create" in k.get("scopes", []):
            valid.append(k)
    valid.sort(key=lambda k: k.get("created_at", ""), reverse=True)
    return valid


def _display_keys(keys: list[dict[str, Any]]) -> None:
    """Print a formatted table of keys for the user to choose from."""
    print(
        f"\n  {'':4s} {'KEY ID':12s}  {'NAME':36s}"
        f"  {'SCOPES':48s}  {'CREATED':10s}"
    )
    print(
        f"  {'':4s} {'-' * 12}  {'-' * 36}"
        f"  {'-' * 48}  {'-' * 10}"
    )
    for i, k in enumerate(keys, 1):
        scopes_str = ", ".join(k.get("scopes", []))
        created = (k.get("created_at", "") or "")[:10]
        name = (k.get("name", "") or "")[:36]
        print(
            f"  [{i}]  {k['key_id']:12s}  {name:36s}"
            f"  {scopes_str:48s}  {created:10s}"
        )


def _prompt_for_api_key_value(key_id: str) -> str:
    """Ask the user to paste the API key value for an existing key."""
    print()
    print(
        f"  {Colour.YELLOW}The API key value is only shown at creation"
        f" time and cannot be retrieved later.{Colour.RESET}"
    )
    print(
        f"  {Colour.YELLOW}If you no longer have it, re-run and choose"
        f" 'n' to create a new key instead.{Colour.RESET}"
    )
    while True:
        value = input(
            f"  Paste API key for {Colour.CYAN}{key_id}{Colour.RESET}: "
        ).strip()
        if value:
            return value
        print(f"  {Colour.RED}API key value cannot be empty.{Colour.RESET}")


def _select_existing_key(
    lobby_url: str, access_token: str, valid_keys: list[dict[str, Any]]
) -> tuple[str, str, bool]:
    """Let the user pick an existing key or create a new one.

    Returns ``(api_key, key_id, should_delete)``.
    *should_delete* is always ``False`` for existing keys.
    """
    display_keys = valid_keys[:_MAX_KEYS_TO_SHOW]
    _display_keys(display_keys)

    extra = (
        f" (showing most recent {_MAX_KEYS_TO_SHOW} of {len(valid_keys)})"
        if len(valid_keys) > _MAX_KEYS_TO_SHOW
        else ""
    )
    print(
        f"\n  {Colour.GREEN}⏳  Auto-selecting key [1] in"
        f" {_AUTO_SELECT_TIMEOUT} seconds …{Colour.RESET}{extra}"
    )
    print(
        f"  {Colour.DIM}Enter 1-{len(display_keys)} to pick a key,"
        f" 'n' to create a new one, or wait for auto-select:{Colour.RESET}"
    )

    choice = _timed_input("  > ", _AUTO_SELECT_TIMEOUT)

    if choice is None:
        # ── timeout: auto-select most recent ──
        selected = display_keys[0]
        log(
            "Auto-selected key",
            f"{selected['key_id']}  ({selected.get('name', '')})",
            colour=Colour.GREEN,
        )
        api_key = _prompt_for_api_key_value(selected["key_id"])
        return api_key, selected["key_id"], False

    choice = choice.strip()

    if choice.lower() in ("n", "new"):
        return _create_new_key(lobby_url, access_token)

    # Try numeric choice
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(display_keys):
            selected = display_keys[idx]
            log(
                "Selected key",
                f"{selected['key_id']}  ({selected.get('name', '')})",
                colour=Colour.GREEN,
            )
            api_key = _prompt_for_api_key_value(selected["key_id"])
            return api_key, selected["key_id"], False
    except ValueError:
        pass

    # Unrecognised — fall back to auto-select
    log(
        "Unrecognised input",
        "auto-selecting most recent key",
        colour=Colour.YELLOW,
    )
    selected = display_keys[0]
    api_key = _prompt_for_api_key_value(selected["key_id"])
    return api_key, selected["key_id"], False


def _create_new_key(
    lobby_url: str, access_token: str
) -> tuple[str, str, bool]:
    """Create a fresh API key and ask whether to delete it after the run.

    Returns ``(api_key, key_id, should_delete)``.
    """
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
            "scopes": ["test_games:create", "test_games:read"],
        },
    )
    api_key, key_id = key["api_key"], key["key_id"]
    log("API key created", key_id, colour=Colour.GREEN)
    log_value("API key", api_key)

    # Ask about cleanup
    print()
    answer = _timed_input(
        f"  {Colour.YELLOW}Delete this key after the benchmark?"
        f" [Y/n]{Colour.RESET} "
        f"{Colour.DIM}(auto-delete in {_AUTO_SELECT_TIMEOUT} s){Colour.RESET}: ",
        _AUTO_SELECT_TIMEOUT,
    )
    should_delete = answer is None or answer.strip().lower() not in ("n", "no")
    if should_delete:
        log("Will auto-delete key after benchmark", colour=Colour.DIM)
    else:
        log("Will keep key after benchmark", key_id, colour=Colour.DIM)
    return api_key, key_id, should_delete


def _resolve_api_key(
    lobby_url: str, access_token: str
) -> tuple[str, str, bool]:
    """Resolve a developer API key for the benchmark.

    Returns ``(api_key, key_id, should_delete)`` where *should_delete*
    indicates whether the cleanup step should delete the key.

    Logic:
    1. Fetch all active keys with ``test_games:create`` scope.
    2. If any exist, display the most recent 5 and let the user pick one
       (or create a new key).  Auto-select the most recent key after
       {_AUTO_SELECT_TIMEOUT} seconds of inactivity.
    3. If none exist, create a new key automatically.
    """
    valid_keys = _fetch_valid_keys(lobby_url, access_token)

    if valid_keys:
        return _select_existing_key(lobby_url, access_token, valid_keys)

    # No valid keys — create one automatically
    log(
        "No existing test-game keys",
        "creating a new one automatically",
        colour=Colour.YELLOW,
    )
    return _create_new_key(lobby_url, access_token)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(
        f"{Colour.BOLD}Guandan Benchmark — Automated Bot Test{Colour.RESET}",
        flush=True,
    )
    lobby_url = (
        input("Lobby server URL [http://localhost:8686]: ").strip()
        or "http://localhost:8686"
    )
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    lobby_url = lobby_url.rstrip("/")

    access_token = ""
    api_key = ""
    key_id = ""
    should_delete_key = False
    cancel_url = ""
    game_token = ""
    game_completed = False
    game = None

    try:
        # ------------------------------------------------------------------
        # Step 1: Log in
        # ------------------------------------------------------------------
        step(1, "Log in")
        login = api_request(
            "POST",
            f"{lobby_url}/api/auth/login",
            body={"account": username, "password": password},
        )
        access_token = login["tokens"]["accessToken"]["token"]
        log("Logged in", login["user"]["id"], colour=Colour.GREEN)

        # ------------------------------------------------------------------
        # Step 2: Resolve API key (select existing or create new)
        # ------------------------------------------------------------------
        step(2, "Developer API key")
        api_key, key_id, should_delete_key = _resolve_api_key(
            lobby_url, access_token
        )

        # ------------------------------------------------------------------
        # Step 3: Lobby health check
        # ------------------------------------------------------------------
        step(3, "Lobby health check")
        check_lobby_reachable(lobby_url)
        log("Lobby is healthy", colour=Colour.GREEN)

        # ------------------------------------------------------------------
        # Step 4: Build participants & create test game
        # ------------------------------------------------------------------
        step(4, "Build participants")
        participants = build_participants(
            DEFAULT_BOT_CONFIGS,
            deployments=[],  # no deployed bots — all built-in
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

        step(5, "Create test game")
        game = create_test_game(
            lobby_url=lobby_url,
            api_key=api_key,
            participants=participants,
            num_rounds=DEFAULT_NUM_ROUNDS,
        )
        if game is None:
            raise RuntimeError("Test game creation failed")

        runtime = game["runtime"]
        cancel_url = runtime.get("cancel_url", "")
        game_token = runtime.get("access_token", "")
        log("Test game created", game["test_game_id"], colour=Colour.GREEN)
        log_value("Game ID", game["game_id"])
        log_value("Runtime server", runtime.get("runtime_server_id", "?"))

        # ------------------------------------------------------------------
        # Step 6: Game server health check
        # ------------------------------------------------------------------
        step(6, "Game server health check")
        check_game_server_reachable(runtime.get("base_url", ""))
        log("Game server is healthy", colour=Colour.GREEN)

        # ------------------------------------------------------------------
        # Step 7: Monitor SSE events & track scores
        # ------------------------------------------------------------------
        step(7, "Monitor game events")
        tracker = GameTracker(total_rounds=DEFAULT_NUM_ROUNDS)

        warnings_list: list[str] = []
        errors: list[str] = []

        monitor_result = monitor_events(
            events_url=runtime["events_url"],
            access_token=game_token,
            timeout_s=DEFAULT_TOTAL_TIMEOUT,
            heartbeat_timeout=DEFAULT_HEARTBEAT_TIMEOUT,
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
                f"Game did not complete within {DEFAULT_TOTAL_TIMEOUT}s. "
                "It may still be running on the server."
            )

        if len(monitor_result["events"]) == 0:
            warnings_list.append(
                "No SSE events received. The game may have started "
                "before the SSE subscription was established."
            )

        # ------------------------------------------------------------------
        # Step 8: Print report
        # ------------------------------------------------------------------
        step(8, "Final report")
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
