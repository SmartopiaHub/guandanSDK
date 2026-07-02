#!/usr/bin/env python3
"""
Guandan Automated Bot Test Script
==================================
Creates and monitors a fully automated test game using the Lobby REST API
and the Runtime SSE event stream.

Usage:
    python3 benchmark.py [--config config.yaml] [--num-rounds N] [--verbose]

All configuration comes from the YAML config file.  There are no built-in
defaults — every required field must be present in the config file.

Required config.yaml fields:
    developer_api_key    — developer automation API key
    lobby_url            — lobby server base URL (e.g. http://127.0.0.1:8686)
    bots                 — per-seat bot assignments for seats 1–4
    num_rounds           — number of rounds (can be overridden via --num-rounds)
    total_timeout        — max seconds to wait for the test game
    heartbeat_timeout    — disconnect if no SSE event within this window
"""

import argparse
import json
import os
import signal
import sys
import time
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Optional

# The benchmark only calls local HTTP endpoints.  urllib3 2 emits an OpenSSL
# compatibility warning on the LibreSSL-based system Python shipped by macOS,
# even though TLS is not used by this runner.
warnings.filterwarnings(
    "ignore",
    message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+.*",
    module=r"urllib3(\..*)?",
)

import requests
import yaml

# ---------------------------------------------------------------------------
# Shared HTTP session (no proxy — avoids local proxy interference)
# ---------------------------------------------------------------------------
_SESSION = requests.Session()
_NO_PROXY = {"http": None, "https": None}


def _get(url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("proxies", _NO_PROXY)
    return _SESSION.get(url, **kwargs)


def _post(url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("proxies", _NO_PROXY)
    return _SESSION.post(url, **kwargs)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


# ---------------------------------------------------------------------------
# Config — strict: every required field must be present, no built-in defaults
# ---------------------------------------------------------------------------
def load_config(path: str) -> dict:
    """Load and validate the YAML configuration file.

    Returns a dict with the validated config on success.  Prints errors and
    calls ``sys.exit(1)`` on any missing or invalid field.
    """
    if not os.path.exists(path):
        _fatal(f"Config file not found: {path}")

    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    errors: list[str] = []

    # -- api_key ---------------------------------------------------------------
    api_key = (cfg.get("developer_api_key", "") or "").strip()
    if not api_key:
        errors.append("developer_api_key is missing or empty")
    else:
        key_err = validate_api_key_format(api_key)
        if key_err:
            errors.append(f"developer_api_key: {key_err}")

    # -- lobby_url -------------------------------------------------------------
    lobby_url = (cfg.get("lobby_url", "") or "").strip()
    if not lobby_url:
        errors.append("lobby_url is missing or empty")

    # -- num_rounds ------------------------------------------------------------
    num_rounds = cfg.get("num_rounds")
    if num_rounds is None:
        errors.append("num_rounds is missing")
    elif not isinstance(num_rounds, int) or num_rounds < 1:
        errors.append(f"num_rounds must be a positive integer, got: {num_rounds}")

    # -- total_timeout ---------------------------------------------------------
    total_timeout = cfg.get("total_timeout")
    if total_timeout is None:
        errors.append("total_timeout is missing")
    elif not isinstance(total_timeout, (int, float)) or total_timeout < 1:
        errors.append(
            f"total_timeout must be a positive number, got: {total_timeout}"
        )

    # -- heartbeat_timeout ---------------------------------------------------
    heartbeat_timeout = cfg.get("heartbeat_timeout")
    if heartbeat_timeout is None:
        errors.append("heartbeat_timeout is missing")
    elif not isinstance(heartbeat_timeout, (int, float)) or heartbeat_timeout < 1:
        errors.append(
            f"heartbeat_timeout must be a positive number, got: {heartbeat_timeout}"
        )

    # -- bots ------------------------------------------------------------------
    bots_raw = cfg.get("bots", {})
    if not isinstance(bots_raw, dict):
        errors.append("bots must be a mapping (e.g. bots: { seat_1: {...}, ... })")
    else:
        bot_configs: dict[int, dict] = {}
        expected_keys = {f"seat_{s}" for s in range(1, 5)}
        missing_seats = expected_keys - set(bots_raw.keys())
        if missing_seats:
            errors.append(
                f"bots: missing seat(s): {', '.join(sorted(missing_seats))}"
            )
        for seat in range(1, 5):
            key = f"seat_{seat}"
            entry = bots_raw.get(key)
            if isinstance(entry, dict):
                bot_type = entry.get("type", "")
                if bot_type not in ("builtin", "deployed"):
                    errors.append(
                        f"bots.{key}.type must be 'builtin' or 'deployed', "
                        f"got: {bot_type!r}"
                    )
                if bot_type == "builtin":
                    code = entry.get("bot_code", "")
                    if code not in ("basicBot", "strongBot"):
                        errors.append(
                            f"bots.{key}.bot_code must be 'basicBot' or "
                            f"'strongBot', got: {code!r}"
                        )
                bot_configs[seat] = entry
            else:
                # This shouldn't happen if missing_seats already caught it,
                # but guard against non-dict values.
                errors.append(
                    f"bots.{key} must be a mapping, got: {type(entry).__name__}"
                )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        _fatal(f"{len(errors)} config error(s) — see above")

    return {
        "api_key": api_key,
        "lobby_url": lobby_url.rstrip("/"),
        "num_rounds": num_rounds,
        "total_timeout": int(total_timeout),
        "heartbeat_timeout": int(heartbeat_timeout),
        "bot_configs": bot_configs,
    }


def _fatal(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log(level: str, msg: str) -> None:
    print(f"[{utc_now()}] {level:5s}  {msg}")


# ---------------------------------------------------------------------------
# Step 1: Validate API key format
# ---------------------------------------------------------------------------
def validate_api_key_format(api_key: str) -> Optional[str]:
    """Check the API key looks well-formed. Returns error string or None."""
    if not api_key:
        return "API key is empty. Set developer_api_key in config.yaml."

    # Current format: sk-zq-{publicKeyId}_{secret}
    if api_key.startswith("sk-zq-"):
        payload = api_key[6:]  # strip 'sk-zq-'
        if '_' not in payload:
            return (
                "API key is missing '_' separator between public key ID "
                "and secret. Expected format: sk-zq-{publicKeyId}_{secret}"
            )
        key_id, secret = payload.split('_', 1)
        if not key_id.startswith("zq_") or len(key_id) != 10:
            return (
                f"API key public key ID '{key_id}' looks wrong. "
                "Expected format: zq_<8-alphanumeric>"
            )
        if len(secret) < 32:
            return (
                f"API key secret is too short ({len(secret)} chars, "
                "expected at least 32)."
            )
        return None

    # Legacy format: gdk_test_kid_<8-char-key-id>.<32-char-secret>
    if api_key.startswith("gdk_test_kid_"):
        parts = api_key[len("gdk_test_kid_"):].split(".", 1)
        if len(parts) != 2:
            return "API key is missing '.' separator between key ID and secret."
        kid, secret = parts
        if len(kid) != 8:
            return f"API key ID is {len(kid)} chars, expected 8."
        if len(secret) != 32:
            return f"API key secret is {len(secret)} chars, expected 32."
        return None

    return (
        "API key has unrecognised prefix. Expected "
        "sk-zq-{publicKeyId}_{secret} or gdk_test_kid_<key-id>.<secret>"
    )


# ---------------------------------------------------------------------------
# Pre-flight health checks
# ---------------------------------------------------------------------------
def check_lobby_reachable(lobby_url: str) -> None:
    """Verify the lobby server is reachable and healthy.

    Calls ``_fatal`` and exits if the server is unreachable or unhealthy.
    """
    health_url = f"{lobby_url}/internal/health"
    log("INFO", f"Checking lobby health at {health_url} ...")
    try:
        resp = _get(health_url, timeout=10)
    except requests.RequestException as e:
        _fatal(f"Lobby server unreachable at {lobby_url}: {e}")

    if resp.status_code != 200:
        _fatal(
            f"Lobby health check failed: HTTP {resp.status_code} "
            f"from {health_url}"
        )

    try:
        body = resp.json()
    except ValueError:
        body = {}

    status = body.get("status", "unknown")
    if status not in ("healthy", "ok", "UP"):
        _fatal(
            f"Lobby server at {lobby_url} is not healthy (status={status})"
        )

    log("INFO", f"Lobby server is healthy (status={status})")


def check_game_server_reachable(base_url: str) -> None:
    """Verify the assigned game server is reachable and accepting rooms.

    Must be called after the test game is created and the runtime
    ``base_url`` is known.  Calls ``_fatal`` on failure.
    """
    health_url = f"{base_url}/internal/health"
    log("INFO", f"Checking game server health at {health_url} ...")
    try:
        resp = _get(health_url, timeout=10)
    except requests.RequestException as e:
        _fatal(f"Game server unreachable at {base_url}: {e}")

    if resp.status_code != 200:
        _fatal(
            f"Game server health check failed: HTTP {resp.status_code} "
            f"from {health_url}"
        )

    try:
        body = resp.json()
    except ValueError:
        body = {}

    status = body.get("status", "unknown")
    accepting = body.get("accepting_new_rooms", False)
    if not accepting:
        _fatal(
            f"Game server at {base_url} is not accepting new rooms "
            f"(status={status}, accepting_new_rooms={accepting})"
        )

    log("INFO",
        f"Game server is healthy (status={status}, "
        f"active_rooms={body.get('active_rooms', '?')}, "
        f"accepting_new_rooms={accepting})")


# ---------------------------------------------------------------------------
# Game state tracker (win-rate, scores)
# ---------------------------------------------------------------------------
class GameTracker:
    """Tracks round results, team scores, and win rates across a test game."""

    def __init__(self, total_rounds: int):
        self.total_rounds = total_rounds
        self.rounds_completed = 0
        # Cumulative scores per team
        self.red_score = 0
        self.blue_score = 0
        # Rounds won per team
        self.red_wins = 0
        self.blue_wins = 0
        # Per-round details
        self.round_details: list[dict] = []

    def record_round_result(
        self,
        round_result: dict,
        seat_map: dict[str, int],
    ) -> None:
        """Parse a round result and update team scores + win counts.

        Scoring (Guandan convention):
            The team with the banker (1st) wins the round (no draws).

            Winning team:
                banker + follower  (1st + 2nd)  → +3  (double-down)
                banker + third     (1st + 3rd)  → +2
                banker + dweller   (1st + 4th)  → +1

            Losing team:
                follower + third   (2nd + 3rd)  → -1
                follower + dweller (2nd + 4th)  → -2
                two dwellers       (3rd + 4th)  → -3  (double-down)
        """
        self.rounds_completed += 1

        # Collect team assignments from rankings
        rankings: dict[str, str] = {}  # rank_name → team ("red" | "blue")
        seat_team: dict[int, str] = {
            1: "red", 3: "red",
            2: "blue", 4: "blue",
        }

        def _pid(entry: Any) -> str:
            if isinstance(entry, dict):
                return entry.get("player_id", entry.get("id", ""))
            return entry if isinstance(entry, str) else ""

        def _team(entry: Any, pid: str) -> str:
            if isinstance(entry, dict):
                team = entry.get("team", "")
                if team in ("red", "redTeam"):
                    return "red"
                if team in ("blue", "blueTeam"):
                    return "blue"
            seat = seat_map.get(pid)
            return seat_team.get(seat, "unknown") if seat is not None else "unknown"

        rank_entries: dict[str, Any] = {
            "first": round_result.get("first", round_result.get("banker")),
            "second": round_result.get("second", round_result.get("follower")),
            "third": round_result.get("third"),
            "fourth": round_result.get("fourth"),
        }
        if rank_entries["fourth"] is None:
            dwellers = round_result.get("dwellers")
            if isinstance(dwellers, list) and dwellers:
                rank_entries["fourth"] = dwellers[0]

        for rank_key, entry in rank_entries.items():
            pid = _pid(entry)
            if pid:
                rankings[rank_key] = _team(entry, pid)

        # Determine winner: the team holding first place (banker)
        winner_team = rankings.get("first", "unknown")
        if winner_team not in ("red", "blue"):
            # Fallback: cannot determine winner
            return

        loser_team = "blue" if winner_team == "red" else "red"

        # Score based on what ranks the WINNING team holds
        winner_ranks = {r for r, t in rankings.items() if t == winner_team}
        loser_ranks = {r for r, t in rankings.items() if t == loser_team}

        # Winning team scoring
        if {"first", "second"}.issubset(winner_ranks):
            winner_pts = 3   # banker + follower (double-down)
        elif "first" in winner_ranks and "third" in winner_ranks:
            winner_pts = 2   # banker + third
        elif "first" in winner_ranks and "fourth" in winner_ranks:
            winner_pts = 1   # banker + dweller
        else:
            winner_pts = 0   # unexpected

        # Losing team scoring (determined by which ranks they hold)
        if {"third", "fourth"}.issubset(loser_ranks):
            loser_pts = -3   # two dwellers (double-down)
        elif {"second", "fourth"}.issubset(loser_ranks):
            loser_pts = -2   # follower + dweller
        elif {"second", "third"}.issubset(loser_ranks):
            loser_pts = -1   # follower + third
        else:
            loser_pts = 0    # unexpected

        if winner_team == "red":
            red_round_pts = winner_pts
            blue_round_pts = loser_pts
            self.red_wins += 1
            winner = "red"
        else:
            red_round_pts = loser_pts
            blue_round_pts = winner_pts
            self.blue_wins += 1
            winner = "blue"

        self.red_score += red_round_pts
        self.blue_score += blue_round_pts

        detail = {
            "round": self.rounds_completed,
            "rankings": rankings,
            "red_pts": red_round_pts,
            "blue_pts": blue_round_pts,
            "winner": winner,
        }
        self.round_details.append(detail)

    @property
    def red_win_rate(self) -> str:
        return f"{self.red_wins}/{self.total_rounds}"

    @property
    def blue_win_rate(self) -> str:
        return f"{self.blue_wins}/{self.total_rounds}"


# ---------------------------------------------------------------------------
# Step 2: Discover bot deployments
# ---------------------------------------------------------------------------
def discover_deployments(lobby_url: str) -> list[dict]:
    """Fetch public bot deployments from the lobby.

    Returns a list of deployment dicts. Prints a summary table.
    """
    log("INFO", f"Fetching public bot deployments from {lobby_url}/api/bots ...")
    try:
        resp = _get(f"{lobby_url}/api/bots", timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log("ERROR", f"Failed to fetch bot deployments: {e}")
        return []

    data = resp.json()
    deployments = data.get("deployments", [])
    definitions = {d["bot_definition_id"]: d for d in data.get("definitions", [])}

    if not deployments:
        log("WARN", "No bot deployments found. Only internal bots can be used.")
        return []

    log("INFO", f"Found {len(deployments)} deployment(s):")
    for dep in deployments:
        did = dep["deployment_id"]
        transport = dep["transport_type"]
        status = dep["status"]
        base_url = dep.get("base_url", "N/A")
        def_ids = dep.get("supported_bot_definition_ids", [])
        def_names = [
            definitions.get(did, {}).get("display_name", did) for did in def_ids
        ]
        log(
            "INFO",
            f"  {did[:20]:20s}  {transport:9s}  {status:20s}  "
            f"defs={def_names}  url={base_url}",
        )

    return deployments


def pick_healthy_ws_deployment(deployments: list[dict]) -> Optional[dict]:
    """Return the first healthy WebSocket deployment, or None."""
    for dep in deployments:
        if (
            dep["transport_type"] == "websocket"
            and dep["status"] == "healthy"
        ):
            return dep
    return None


def check_deployment_health(
    lobby_url: str, api_key: str, deployment_id: str,
    deployment_key: str = "",
) -> dict:
    """Query the deployment health endpoint for a specific deployment.

    If *deployment_key* is provided, it is sent as the ``X-Deployment-Key``
    header so the lobby can verify ownership without relying on the
    automation API key's owner account.

    Returns a dict with keys:
        - healthy: bool — whether the deployment is connected
        - response: the full JSON response from the server
        - error: error message if the request failed
    """
    health_url = f"{lobby_url}/api/bots/deployments/{deployment_id}/health"
    log("INFO", f"Checking deployment health at {health_url} ...")
    headers = {"Authorization": f"Bearer {api_key}"}
    if deployment_key:
        headers["X-Deployment-Key"] = deployment_key
    try:
        resp = _get(
            health_url,
            headers=headers,
            timeout=10,
        )
    except requests.RequestException as e:
        return {"healthy": False, "response": None, "error": str(e)}

    if resp.status_code == 404:
        return {
            "healthy": False,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {},
            "error": f"Deployment '{deployment_id}' not found.",
        }

    if not resp.ok:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return {
            "healthy": False,
            "response": body,
            "error": body.get("message", f"HTTP {resp.status_code}"),
        }

    try:
        body = resp.json()
    except ValueError:
        return {"healthy": False, "response": None, "error": "Invalid JSON response."}

    connected = body.get("connected", False)
    if connected:
        log("INFO", f"  Deployment {deployment_id} is connected (game_server={body.get('game_server_id', '?')})")
    else:
        log("WARN", f"  Deployment {deployment_id} is NOT connected: {body.get('error', 'unknown')}")

    return {"healthy": connected, "response": body, "error": body.get("error") if not connected else None}


# ---------------------------------------------------------------------------
# Step 3: Build participants from config
# ---------------------------------------------------------------------------
def _resolve_deployed_bot(
    seat: int,
    bot_cfg: dict,
    deployments: list[dict],
    lobby_url: str = "",
    api_key: str = "",
) -> tuple[Optional[dict], Optional[str]]:
    """Resolve a deployed bot config into a participant dict.

    Uses the deployment health endpoint to verify connectivity rather than
    relying solely on the deployment's stored status.  This allows bots with
    ``pending_verification`` status that are actually connected to the gateway
    to pass the health check.

    Returns (participant, warning) — participant is None on failure.
    """
    dep_id = bot_cfg.get("deployment_id", "").strip()
    deployment_key = (bot_cfg.get("deployment_key", "") or "").strip()

    # If no specific deployment_id, auto-pick a healthy one
    if not dep_id:
        dep = pick_healthy_ws_deployment(deployments)
        if dep is None:
            for d in deployments:
                if d["transport_type"] == "http" and d["status"] == "healthy":
                    dep = d
                    break
        if dep is None:
            return None, (
                f"Seat {seat}: no healthy deployment found for deployed bot "
                f"and no deployment_id specified"
            )
        dep_id = dep["deployment_id"]
    else:
        # Look up the specified deployment
        dep = None
        for d in deployments:
            if d["deployment_id"] == dep_id:
                dep = d
                break
        if dep is None:
            return None, (
                f"Seat {seat}: deployment '{dep_id}' not found in "
                f"discovered deployments"
            )

    # Verify deployment health via the health endpoint.
    # This bypasses the pending_verification status — if the bot is connected
    # to the gateway, it passes the check regardless of its DB status.
    # The deployment key is forwarded so the lobby can verify ownership.
    health_result = check_deployment_health(
        lobby_url, api_key, dep_id, deployment_key=deployment_key,
    )
    if not health_result["healthy"]:
        status = dep.get("status", "unknown") if dep else "unknown"
        error_detail = health_result.get("error", "health check failed")
        return None, (
            f"Seat {seat}: deployment '{dep_id}' is not healthy "
            f"(status: {status}, health: {error_detail})"
        )

    # dep may be None if the deployment was found via health check without
    # being in the discovery list (shouldn't happen with current flow).
    if dep is None:
        return None, (
            f"Seat {seat}: deployment '{dep_id}' metadata not available"
        )

    def_ids = dep.get("supported_bot_definition_ids", [])
    def_id = def_ids[0] if def_ids else None
    log("INFO",
        f"  Seat {seat}: deployed bot  deployment={dep_id}  "
        f"definition={def_id}  transport={dep['transport_type']}"
        f"{'  (with deployment key)' if deployment_key else ''}")
    participant = {
        "seat": seat,
        "type": "external_bot",
        "bot_definition_id": def_id,
        "deployment_id": dep_id,
    }
    if deployment_key:
        participant["deployment_key"] = deployment_key
    return participant, None


def _resolve_builtin_bot(
    seat: int,
    bot_cfg: dict,
) -> tuple[dict, Optional[str]]:
    """Resolve a builtin bot config into a participant dict."""
    bot_code = bot_cfg.get("bot_code", "strongBot")
    log("INFO", f"  Seat {seat}: builtin bot  bot_code={bot_code}")
    return {
        "seat": seat,
        "type": "internal_bot",
        "bot_code": bot_code,
    }, None


def build_participants(
    bot_configs: dict[int, dict],
    deployments: list[dict],
    lobby_url: str = "",
    api_key: str = "",
) -> list[dict]:
    """Build the participants list from per-seat bot configs.

    Each bot_config entry:
        { "type": "builtin", "bot_code": "strongBot" }
        { "type": "deployed", "deployment_id": "<id>" }  # id optional

    Exits the script immediately (via _fatal) if any seat's bot cannot be
    resolved — there is no fallback.
    """
    participants: list[dict] = []

    for seat in range(1, 5):
        bot_cfg = bot_configs.get(seat, {"type": "builtin", "bot_code": "strongBot"})
        bot_type = bot_cfg.get("type", "builtin")

        if bot_type == "deployed":
            participant, error = _resolve_deployed_bot(
                seat, bot_cfg, deployments, lobby_url, api_key,
            )
        else:
            participant, error = _resolve_builtin_bot(seat, bot_cfg)

        if participant is None:
            _fatal(error or f"Seat {seat}: failed to resolve bot configuration")

        participants.append(participant)

    participants.sort(key=lambda p: p["seat"])
    return participants


# ---------------------------------------------------------------------------
# Step 4: Create test game
# ---------------------------------------------------------------------------
def create_test_game(
    lobby_url: str,
    api_key: str,
    participants: list[dict],
    num_rounds: int = 10,
    num_series: int = 1,
) -> Optional[dict]:
    """POST /api/v1/test-games to create an automated test game.

    Returns the parsed JSON response on success, or None.
    """
    idempotency_key = str(uuid.uuid4())
    payload = {
        "rule_set": "guandan-standard-v1",
        "participants": participants,
        "options": {
            "auto_start": True,
            "record_replay": True,
            "expires_in_seconds": 3600,
            "num_rounds": num_rounds,
            "num_series": num_series,
        },
    }

    log("INFO", f"Creating test game via {lobby_url}/api/v1/test-games ...")
    log("INFO", f"  Idempotency-Key: {idempotency_key}")
    log("INFO", f"  Participants: {json.dumps(participants, indent=2)}")

    try:
        resp = _post(
            f"{lobby_url}/api/v1/test-games",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Idempotency-Key": idempotency_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except requests.RequestException as e:
        log("ERROR", f"Request failed: {e}")
        return None

    if not resp.ok:
        try:
            body = resp.json()
            code = body.get("code", "unknown")
            msg = body.get("message", resp.text)
        except (ValueError, AttributeError):
            code = "non_json_response"
            msg = resp.text[:500]
        log("ERROR", f"Test game creation failed: HTTP {resp.status_code}  "
                      f"code={code}  message={msg}")
        return None

    data = resp.json()
    log("INFO", "Test game created successfully!")
    log("INFO", f"  test_game_id: {data.get('test_game_id')}")
    log("INFO", f"  game_id:      {data.get('game_id')}")
    log("INFO", f"  status:       {data.get('status')}")
    runtime = data.get("runtime", {})
    log("INFO", f"  runtime:      {runtime.get('runtime_server_id')} "
                 f"at {runtime.get('base_url')}")
    log("INFO", f"  events_url:   {runtime.get('events_url')}")
    log("INFO", f"  status_url:   {runtime.get('status_url')}")
    log("INFO", f"  cancel_url:   {runtime.get('cancel_url')}")
    return data


# ---------------------------------------------------------------------------
# Step 5: Monitor SSE events
# ---------------------------------------------------------------------------
def monitor_events(
    events_url: str,
    access_token: str,
    last_event_id: str = "",
    timeout_s: int = 120,
    heartbeat_timeout: int = 45,
    verbose: bool = False,
    tracker: Optional[GameTracker] = None,
) -> dict:
    """Subscribe to the runtime SSE event stream and collect events.

    Args:
        events_url: The SSE endpoint URL.
        access_token: Runtime access token.
        last_event_id: Optional Last-Event-ID for reconnect.
        timeout_s: Maximum seconds to wait.
        heartbeat_timeout: Disconnect if no SSE event within this window.
        verbose: If True, print all agent messages. If False, only print
                 round start/end messages with results.
        tracker: Optional GameTracker to record round results and scores.

    Returns a dict with keys:
        - events: list of parsed event dicts
        - termination: one of 'completed', 'failed', 'cancelled', 'timeout',
          'heartbeat_timeout', 'connection_error'
        - error: error message (if applicable)
    """
    collected: list[dict] = []
    termination = "timeout"
    error_msg = ""
    last_event_time = time.monotonic()
    game_ended = False
    seat_map: dict[str, int] = {}  # player_id → seat, built incrementally

    log("INFO", f"Subscribing to SSE events at {events_url} ...")
    if last_event_id:
        log("INFO", f"  Last-Event-ID: {last_event_id}")

    try:
        resp = _get(
            events_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Last-Event-ID": last_event_id,
            },
            stream=True,
            timeout=(10, timeout_s),  # (connect_timeout, read_timeout)
        )
        if resp.status_code != 200:
            try:
                body = resp.json()
                error_msg = body.get("message", body.get("code", str(body)))
            except Exception:
                error_msg = resp.text[:500]
            log("ERROR", f"SSE connection failed: HTTP {resp.status_code}  "
                          f"{error_msg}")
            return {
                "events": collected,
                "termination": "connection_error",
                "error": error_msg,
            }

        # Check Content-Type (allow text/event-stream or application/octet-stream
        # as some frameworks don't set it correctly)
        content_type = resp.headers.get("Content-Type", "")
        log("INFO", f"SSE connected (Content-Type: {content_type})")

        current_event = ""
        current_data = ""
        current_id = ""

        def _flush_event() -> str:
            nonlocal current_event, current_data, current_id, last_event_time
            flushed_event = current_event
            if current_event:
                try:
                    parsed = json.loads(current_data) if current_data else {}
                except json.JSONDecodeError:
                    parsed = {"raw": current_data}
                collected.append({
                    "id": current_id,
                    "event": current_event,
                    "data": parsed,
                    "received_at": utc_now(),
                })

                # ── Update seat map incrementally ──
                _update_seat_map(parsed, seat_map)

                # ── Handle agent.message events ──
                if current_event == "agent.message" and isinstance(parsed, dict):
                    # BotTestGameEventMessage: outer data has 'data' with the payload
                    inner = parsed.get("data", parsed)
                    agent_data = inner if isinstance(inner, dict) else {}
                    message = agent_data.get("message", {})
                    msg_type = message.get("type", "")

                    if verbose:
                        # Verbose mode: print ALL agent messages
                        print_agent_message(agent_data, seat_map=seat_map)
                    else:
                        # Non-verbose: only print round start/end messages
                        if msg_type in ("iNewRound",):
                            _print_round_start(message, seat_map)
                        elif msg_type in ("iRoundEnded", "iRoundResult"):
                            _print_round_end(message, seat_map)

                # ── Handle round.completed (BotTestGameEventMessage) ──
                elif current_event == "round.completed" and isinstance(parsed, dict):
                    # Unwrap the BotTestGameEventMessage envelope:
                    #   { type, test_game_id, event, data: { ... } }
                    inner = parsed.get("data", parsed)
                    # The round_result field contains round.toJson() which
                    # wraps the actual rankings under a nested 'round_result'.
                    raw_rr = inner.get("round_result", {})
                    actual_rr = raw_rr.get("round_result", raw_rr) if isinstance(raw_rr, dict) else {}
                    if tracker and actual_rr:
                        tracker.record_round_result(actual_rr, seat_map)
                    nr = inner.get("num_rounds_completed", "?")
                    tr = inner.get("target_rounds", "?")
                    ns = inner.get("num_series_completed", "?")
                    ts = inner.get("target_series", "?")
                    log("INFO",
                        f"🏁 Round {nr}/{tr} completed "
                        f"(series {ns}/{ts})")
                    if tracker and tracker.round_details:
                        last = tracker.round_details[-1]
                        _print_round_score(last)
                    print()  # blank line between rounds

                # ── Handle test.completed ──
                elif current_event == "test.completed" and isinstance(parsed, dict):
                    # Unwrap the BotTestGameEventMessage envelope
                    inner = parsed.get("data", parsed)
                    log("INFO", "=" * 60)
                    log("INFO", "TEST COMPLETED")
                    if tracker:
                        log("INFO",
                            f"  Red  wins: {tracker.red_win_rate}  "
                            f"score: {tracker.red_score}")
                        log("INFO",
                            f"  Blue wins: {tracker.blue_win_rate}  "
                            f"score: {tracker.blue_score}")

                        # Per-round summary
                        log("INFO", "  Per-round results:")
                        for d in tracker.round_details:
                            rn = d["round"]
                            pts = f"R{d['red_pts']}–B{d['blue_pts']}"
                            winner = d["winner"]
                            rankings = d["rankings"]
                            rank_str = " | ".join(
                                f"{rk}: {tm}" for rk, tm in rankings.items()
                            )
                            log("INFO",
                                f"    Round {rn:2d}: {pts:7s}  "
                                f"winner={winner:4s}  [{rank_str}]")
                    log("INFO", "=" * 60)

                elif verbose:
                    # In verbose mode, log all other SSE events too
                    log(
                        "INFO",
                        f"SSE event: id={current_id} event={current_event} "
                        f"data_keys={list(parsed.keys()) if isinstance(parsed, dict) else '?'}",
                    )

                last_event_time = time.monotonic()
            current_event = ""
            current_data = ""
            current_id = ""
            return flushed_event

        # Read SSE stream line by line
        for line in resp.iter_lines(decode_unicode=True):
            if line is None:
                continue

            if line == "":
                # Empty line = end of event block
                flushed_event = _flush_event()

                # Check for terminal events
                if flushed_event in (
                    "game.completed",
                    "game.failed",
                    "game.cancelled",
                    "test.completed",
                ):
                    game_ended = True
                    raw_name = flushed_event.replace("game.", "").replace("test.", "test_")
                    termination = raw_name
                    log("INFO", f"Game terminated: {termination}")
                    break

                continue

            if line.startswith("id:"):
                current_id = line[3:].strip()
            elif line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                current_data = line[5:].strip()
            else:
                # Continuation of data
                if line.startswith(":"):
                    # SSE comment — update heartbeat timer
                    last_event_time = time.monotonic()
                continue

            # Heartbeat timeout check
            elapsed = time.monotonic() - last_event_time
            if elapsed > heartbeat_timeout:
                error_msg = (
                    f"No SSE event received for {elapsed:.0f}s "
                    f"(heartbeat timeout: {heartbeat_timeout}s)"
                )
                log("WARN", error_msg)
                termination = "heartbeat_timeout"
                break

        # Flush any remaining buffered event
        _flush_event()

        if not game_ended:
            log("INFO", f"SSE stream ended. Collected {len(collected)} event(s). "
                         f"Termination: {termination}")

    except requests.Timeout:
        log("WARN", f"SSE connection timed out after {timeout_s}s")
        termination = "timeout"
    except requests.ConnectionError as e:
        error_msg = str(e)
        log("ERROR", f"SSE connection error: {e}")
        termination = "connection_error"
    except Exception as e:
        error_msg = str(e)
        log("ERROR", f"Unexpected error reading SSE stream: {e}")
        termination = "connection_error"

    return {
        "events": collected,
        "termination": termination,
        "error": error_msg,
    }


# ---------------------------------------------------------------------------
# Agent message pretty-printer
# ---------------------------------------------------------------------------
# ANSI terminal color codes
_COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}

# Consistent colors for seats 1–4 (red team: 1,3; blue team: 2,4)
_SEAT_COLORS = {1: "red", 2: "blue", 3: "yellow", 4: "green"}

# Fallback color list for hash-based assignment when seat is unknown
_FALLBACK_COLORS = ("cyan", "magenta", "white", "yellow", "red", "blue", "green")


def _c(name: str) -> str:
    """Return the ANSI escape for a named color/style, or empty string."""
    return _COLORS.get(name, "")


def _player_color(player_id: str, seat_map: Optional[dict] = None) -> str:
    """Return a consistent color name for a player."""
    if seat_map and player_id in seat_map:
        return _SEAT_COLORS.get(seat_map[player_id], "white")
    idx = abs(hash(player_id)) % len(_FALLBACK_COLORS)
    return _FALLBACK_COLORS[idx]


def _fmt_player(player_id: str, seat_map: Optional[dict] = None) -> str:
    """Return a colorised player label like 'P1 (seat 3)'."""
    color = _player_color(player_id, seat_map)
    seat_str = f" seat {seat_map[player_id]}" if (seat_map and player_id in seat_map) else ""
    return f"{_c(color)}{_c('bold')}{player_id}{seat_str}{_c('reset')}"


def _fmt_type(msg_type: str) -> str:
    """Return a dimmed type label."""
    return f"{_c('dim')}[{msg_type}]{_c('reset')}"


def _fmt_count(label: str, count: int) -> str:
    return f"{label}={count}"


def _format_hand_on_table(hand_str: str) -> str:
    """Format the hand_on_table string for display."""
    if not hand_str or hand_str == "pass":
        return f"{_c('dim')}(pass){_c('reset')}"
    return f"{_c('bold')}{hand_str}{_c('reset')}"


def _format_cards(cards_str: Optional[str]) -> str:
    """Format a cards string, showing count and first few cards."""
    if not cards_str:
        return f"{_c('dim')}(none){_c('reset')}"
    parts = cards_str.split()
    return f"{len(parts)} cards: {_c('bold')}{cards_str}{_c('reset')}"


def _format_tribute_info(msg: dict) -> str:
    """Format tribute/return card info from a message."""
    parts: list[str] = []
    if "tribute" in msg:
        parts.append(f"tribute={_c('bold')}{msg['tribute']}{_c('reset')}")
    if "return_card" in msg:
        parts.append(f"return_card={_c('bold')}{msg['return_card']}{_c('reset')}")
    if "payer_id" in msg:
        parts.append(f"payer={msg['payer_id']}")
    if "winner_id" in msg:
        parts.append(f"winner={msg['winner_id']}")
    return ", ".join(parts) if parts else ""


def _format_scores(scores: Optional[dict]) -> str:
    """Format team scores dict."""
    if not scores:
        return ""
    items = []
    for team, score in scores.items():
        if isinstance(score, dict):
            items.append(f"{team}={score}")
        else:
            items.append(f"{team}={score}")
    return ", ".join(items)


def _format_red_joker_counts(counts: Optional[dict]) -> str:
    """Format red joker counts per seat."""
    if not counts:
        return ""
    return ", ".join(f"seat {k}: {v} RJ" for k, v in sorted(counts.items()))


def _update_seat_map(event_data: dict, seat_map: dict[str, int]) -> None:
    """Update the player→seat mapping from a single SSE event's data.

    Handles both raw event data and BotTestGameEventMessage-wrapped payloads.
    """
    # Unwrap BotTestGameEventMessage: outer 'data' → inner 'data' → 'message'
    inner = event_data.get("data", event_data)
    msg = inner.get("message", inner if isinstance(inner, dict) else {})

    msg_type = msg.get("type", "")

    # iNewRound.players
    for p in msg.get("players", []):
        pid = p.get("player_id", p.get("id", ""))
        seat = p.get("seat")
        if pid and seat is not None:
            seat_map[pid] = seat

    # iPlayerSeat
    if msg_type == "iPlayerSeat":
        pid = msg.get("player_id", "")
        seat = msg.get("seat")
        if pid and seat is not None:
            seat_map[pid] = seat

    # iPlayerJoinedRoom
    if msg_type == "iPlayerJoinedRoom":
        player = msg.get("player", {})
        pid = player.get("id", "")
        seat = player.get("seat")
        if pid and seat is not None:
            seat_map[pid] = seat


def _print_round_start(msg: dict, seat_map: Optional[dict] = None) -> None:
    """Print a condensed round-start line (non-verbose mode)."""
    round_id = msg.get("round_id", "?")[:12]
    level_rank = msg.get("level_rank", "?")
    tlr = msg.get("team_level_rank", {})
    start_pid = msg.get("start_player_id", "")
    start_seat = seat_map.get(start_pid, "?") if seat_map else "?"
    red_lr = tlr.get("red", tlr.get("redTeam", "?"))
    blue_lr = tlr.get("blue", tlr.get("blueTeam", "?"))
    log("INFO",
        f"▶ Round {round_id}  level={level_rank}  "
        f"teamLR=(R:{red_lr} B:{blue_lr})  "
        f"start=seat{start_seat}")


def _print_round_end(msg: dict, seat_map: Optional[dict] = None) -> None:
    """Print a condensed round-end line with rankings (non-verbose mode)."""
    round_id = msg.get("round_id", "?")[:12]
    rr = msg.get("round_result", {})
    if not rr:
        log("INFO", f"◀ Round {round_id} ended")
        return

    seat_team: dict[int, str] = {1: "red", 3: "red", 2: "blue", 4: "blue"}
    parts = []
    rank_entries = {
        "first": rr.get("first", rr.get("banker")),
        "second": rr.get("second", rr.get("follower")),
        "third": rr.get("third"),
        "fourth": rr.get("fourth"),
    }
    if rank_entries["fourth"] is None:
        dwellers = rr.get("dwellers")
        if isinstance(dwellers, list) and dwellers:
            rank_entries["fourth"] = dwellers[0]

    for rank_key, entry in rank_entries.items():
        if isinstance(entry, dict):
            pid = entry.get("player_id", entry.get("id", "?"))
        elif isinstance(entry, str):
            pid = entry
        else:
            continue
        seat = seat_map.get(pid, "?") if seat_map else "?"
        team = entry.get("team", "") if isinstance(entry, dict) else ""
        if team == "redTeam":
            team = "red"
        elif team == "blueTeam":
            team = "blue"
        else:
            team = seat_team.get(seat, "?")
        parts.append(f"{rank_key}=S{seat}({team})")
    log("INFO", f"◀ Round {round_id}  {' | '.join(parts)}")


def _print_round_score(detail: dict) -> None:
    """Print the round score summary line."""
    rn = detail["round"]
    red_pts = detail["red_pts"]
    blue_pts = detail["blue_pts"]
    winner = detail["winner"]
    log("INFO",
        f"   Score: Red {red_pts} – Blue {blue_pts}  "
        f"(winner: {winner})")


def print_agent_message(event_data: dict, seat_map: Optional[dict] = None) -> None:
    """Pretty-print an ``agent.message`` SSE event.

    This is the main entry point for displaying bot-directed game messages.
    It extracts the *player_id*, *game_id*, and inner *message* from the
    event envelope, then formats the output based on the game-message type
    (as defined in ``message.dart``).

    Args:
        event_data: Parsed JSON ``data`` field from the ``agent.message`` SSE event.
        seat_map: Optional ``{player_id: seat}`` dict for consistent per-seat coloring.
    """
    player_id = event_data.get("player_id", "?")
    game_id = event_data.get("game_id", "?")
    message = event_data.get("message", {})
    msg_type = message.get("type", "unknown")

    color = _player_color(player_id, seat_map)
    c = _c(color)
    r = _c("reset")
    b = _c("bold")
    d = _c("dim")

    # Header: player + type
    header = (
        f"{c}{b}▸ {player_id}{r}"
        f"{d}  [{msg_type}]{r}"
    )
    print(header)

    # Common fields
    room_id = message.get("room_id", "")
    round_id = message.get("round_id", "")
    turn_id = message.get("turn_id", "")

    indent = "   "

    # ── Dispatch by message type ──
    if msg_type == "sPlayHandRequest":
        hand_on_table = message.get("hand_on_table", "")
        seat_of = message.get("seat_of_hand_on_table", "")
        level_rank = message.get("level_rank", "")
        available = message.get("available_cards", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  "
              f"{d}turn={turn_id}{r}")
        print(f"{indent}{d}hand on table{_c('reset')} "
              f"{_format_hand_on_table(hand_on_table)}  "
              f"{d}(from seat {seat_of}){r}")
        print(f"{indent}{d}level rank={r}{b}{level_rank}{r}  "
              f"{d}available={r}{_format_cards(available)}")

    elif msg_type == "sTributeCardRequest":
        available = message.get("available_cards", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{d}available={r}{_format_cards(available)}")

    elif msg_type == "sReturnCardRequest":
        available = message.get("available_cards", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{d}available={r}{_format_cards(available)}")

    elif msg_type == "iNewRound":
        lr = message.get("level_rank", "?")
        tlr = message.get("team_level_rank", {})
        hand = message.get("hand", "")
        players = message.get("players", [])
        prev = message.get("previous_round_result")
        start_pid = message.get("start_player_id", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  "
              f"{d}start={r}{_fmt_player(start_pid, seat_map)}")
        print(f"{indent}{d}level rank={r}{b}{lr}{r}  "
              f"{d}team ranks={r}{_format_scores(tlr)}")
        print(f"{indent}{d}hand={r}{_format_cards(hand)}")
        if players:
            p_labels = []
            for p in players:
                pid = p.get("player_id", p.get("id", "?"))
                seat = p.get("seat", "?")
                team = p.get("team", "?")
                pc = _player_color(pid, seat_map)
                p_labels.append(f"{_c(pc)}seat{seat}({team}){r}")
            print(f"{indent}{d}players:{r} {' | '.join(p_labels)}")
        if prev:
            print(f"{indent}{d}previous round result:{r} {prev.get('level_rank', '?')}")

    elif msg_type == "iNewPhase":
        phase_id = message.get("phase_id", "")
        start_pid = message.get("start_player_id", "")
        print(f"{indent}{d}room={room_id}{r}  {d}phase={phase_id}{r}")
        print(f"{indent}{d}start player={r}{_fmt_player(start_pid, seat_map)}")

    elif msg_type == "iStartPlayer":
        phase_id = message.get("phase_id", "")
        start_pid = message.get("start_player_id", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  "
              f"{d}phase={phase_id}{r}")
        print(f"{indent}{d}start player={r}{_fmt_player(start_pid, seat_map)}")

    elif msg_type == "iHandPlayed":
        played_by = message.get("player_id", "")
        cards = message.get("cards", "")
        bot_model = message.get("bot_model", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  "
              f"{d}turn={turn_id}{r}")
        print(f"{indent}{d}played by={r}{_fmt_player(played_by, seat_map)}  "
              f"{d}cards={r}{_format_cards(cards)}")
        if bot_model:
            print(f"{indent}{d}bot_model={r}{bot_model}")

    elif msg_type == "pPlayHandRequest":
        cards = message.get("cards", "")
        bot_model = message.get("bot_model", "")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  "
              f"{d}turn={turn_id}{r}")
        print(f"{indent}{d}cards played={r}{_format_cards(cards)}")
        if bot_model:
            print(f"{indent}{d}bot_model={r}{bot_model}")

    elif msg_type == "iPlayerEmptiedCards":
        emptied_pid = message.get("player_id", "")
        rank_of = message.get("rank_of_player", "?")
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{d}emptied={r}{_fmt_player(emptied_pid, seat_map)}  "
              f"{d}rank={r}{b}{rank_of}{r}")

    elif msg_type == "iTributeCard":
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{_format_tribute_info(message)}")

    elif msg_type == "iReturnCard":
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{_format_tribute_info(message)}")

    elif msg_type == "iTributeResult":
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        tr = message.get("tribute_result", {})
        if tr:
            print(f"{indent}{d}tribute_result={r}{tr}")

    elif msg_type == "iTributeResistance":
        start_pid = message.get("start_player_id", "")
        rj = message.get("red_joker_counts", {})
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")
        print(f"{indent}{d}start_player={r}{_fmt_player(start_pid, seat_map)}  "
              f"{d}red jokers={r}{_format_red_joker_counts(rj)}")

    elif msg_type == "iRoundEnded":
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}")

    elif msg_type == "iRoundResult":
        is_partial = message.get("is_partial", False)
        partial_str = f"{_c('yellow')}(partial){r}" if is_partial else ""
        print(f"{indent}{d}room={room_id}{r}  {d}round={round_id}{r}  {partial_str}")
        rr = message.get("round_result", {})
        for rank_key in ("first", "second", "third", "fourth"):
            if rank_key in rr:
                entry = rr[rank_key]
                pid = entry.get("player_id", "") if isinstance(entry, dict) else str(entry)
                print(f"{indent}  {d}{rank_key}:{r} {_fmt_player(pid, seat_map)}")

    elif msg_type == "iTeamScores":
        scores = message.get("team_scores", {})
        print(f"{indent}{d}room={room_id}{r}")
        red = scores.get("red", scores.get("redTeam", {}))
        blue = scores.get("blue", scores.get("blueTeam", {}))
        print(f"{indent}  {_c('red')}{b}Red Team:{r}   {red}")
        print(f"{indent}  {_c('blue')}{b}Blue Team:{r}  {blue}")

    elif msg_type == "iJieFeng":
        phase_id = message.get("phase_id", "")
        jf_pid = message.get("player_id", "")
        print(f"{indent}{d}room={room_id}{r}  {d}phase={phase_id}{r}")
        print(f"{indent}  接风 player={r}{_fmt_player(jf_pid, seat_map)}")

    elif msg_type == "iRequestResult":
        request = message.get("request", "?")
        result = message.get("result", "?")
        result_color = _c("green") if result == "success" else _c("red")
        print(f"{indent}{d}request={r}{request}  "
              f"{d}result={r}{result_color}{result}{r}")

    elif msg_type == "iGameEnded":
        print(f"{indent}{d}room={room_id}{r}")
        print(f"{indent}{_c('bold')}🏆 Game Ended{r}")

    elif msg_type == "iMoreTimeAllocated":
        new_time = message.get("new_allocated_seconds", 0)
        print(f"{indent}{d}room={room_id}{r}  "
              f"{d}new_time={r}{new_time}s")

    elif msg_type == "iTimeOut":
        timed_out_pid = message.get("player_id", "")
        request = message.get("request", "?")
        print(f"{indent}{d}room={room_id}{r}")
        print(f"{indent}{_c('red')}⏱ TIMEOUT{r} "
              f"{_fmt_player(timed_out_pid, seat_map)}  "
              f"{d}request={r}{request}")

    else:
        # Generic fallback: print all keys compactly
        print(f"{indent}{d}room={room_id}{r}")
        skip_keys = {"type", "room_id", "game_id", "access_token", "message_id"}
        extra = {k: v for k, v in message.items() if k not in skip_keys}
        for k, v in extra.items():
            if isinstance(v, dict):
                v = json.dumps(v, default=str)
            elif isinstance(v, list):
                v = f"[{len(v)} items]"
            elif isinstance(v, str) and len(str(v)) > 80:
                v = str(v)[:77] + "..."
            print(f"{indent}  {d}{k}={r}{v}")


def build_seat_map(events: list[dict]) -> dict[str, int]:
    """Scan collected SSE events to build a ``{player_id: seat}`` mapping.

    Looks for ``iNewRound`` (which contains a ``players`` list) inside
    ``agent.message`` events, as well as other player-identification events.
    """
    seat_map: dict[str, int] = {}

    for ev in events:
        _update_seat_map(ev.get("data", {}), seat_map)

    return seat_map


# ---------------------------------------------------------------------------
# Step 6: Report
# ---------------------------------------------------------------------------
def print_report(
    config: dict,
    participants: list[dict],
    game: Optional[dict],
    monitor_result: Optional[dict],
    warnings: list[str],
    errors: list[str],
    tracker: Optional[GameTracker] = None,
) -> None:
    """Print a final summary report."""
    print()
    print("=" * 72)
    print("  GUANDAN AUTO-TEST REPORT")
    print("=" * 72)

    # Configuration
    print(f"  Lobby URL:     {config['lobby_url']}")
    api_key = config.get("api_key", "")
    if api_key:
        masked = api_key[:20] + "..." + api_key[-8:] if len(api_key) > 30 else api_key
        print(f"  API Key:       {masked}")
    else:
        print("  API Key:       (not set)")
    print()

    # Participants
    print("  Participants:")
    for p in participants:
        seat = p["seat"]
        ptype = p["type"]
        detail = ""
        if ptype == "external_bot":
            detail = f"  def={p.get('bot_definition_id', '?')[:30]}  " \
                     f"deploy={p.get('deployment_id', '?')[:30]}"
        else:
            bot_code = p.get("bot_code", "")
            if bot_code:
                detail = f"  bot_code={bot_code}"
            else:
                detail = f"  difficulty={p.get('difficulty', '?')}"
        print(f"    Seat {seat}: {ptype:14s} {detail}")
    print()

    # Game creation
    if game:
        print("  Game Creation:  SUCCESS")
        print(f"    test_game_id:  {game.get('test_game_id')}")
        print(f"    game_id:       {game.get('game_id')}")
        runtime = game.get("runtime", {})
        print(f"    runtime:       {runtime.get('runtime_server_id')} "
              f"at {runtime.get('base_url')}")
    else:
        print("  Game Creation:  FAILED")
    print()

    # SSE monitoring
    if monitor_result:
        print(f"  SSE Monitoring: {monitor_result['termination']}")
        events = monitor_result["events"]
        print(f"    Events collected: {len(events)}")

        # Count by type
        type_counts: dict[str, int] = {}
        agent_msg_count = 0
        for ev in events:
            ev_type = ev["event"]
            type_counts[ev_type] = type_counts.get(ev_type, 0) + 1
            if ev_type == "agent.message":
                agent_msg_count += 1
        for ev_type, count in sorted(type_counts.items()):
            print(f"      {ev_type:30s} {count:4d}")

        if agent_msg_count > 0:
            # Build seat map and show player info
            seat_map = build_seat_map(events)
            if seat_map:
                print(f"    Player → Seat mapping:")
                for pid, seat in sorted(seat_map.items(), key=lambda kv: kv[1]):
                    color = _SEAT_COLORS.get(seat, "white")
                    print(f"      {_c(color)}seat {seat}:{_c('reset')} {pid}")

        if monitor_result["error"]:
            print(f"    Error: {monitor_result['error']}")
    else:
        print("  SSE Monitoring: SKIPPED (game creation failed)")
    print()

    # ── Scoreboard ──
    if tracker and tracker.round_details:
        print("  Scoreboard:")
        print(f"    Total rounds: {tracker.total_rounds}  "
              f"(completed: {tracker.rounds_completed})")
        print()
        print(f"    {'Team':12s} {'Wins':10s} {'Score':10s}")
        print(f"    {'-' * 12} {'-' * 10} {'-' * 10}")
        print(f"    {'Red':12s} {tracker.red_win_rate:10s} {tracker.red_score:<10d}")
        print(f"    {'Blue':12s} {tracker.blue_win_rate:10s} {tracker.blue_score:<10d}")
        print()
        # Per-round breakdown
        print("    Per-round:")
        print(f"    {'Round':6s} {'Red':6s} {'Blue':6s} {'Winner':8s}  Rankings")
        print(f"    {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 8}  {'-' * 30}")
        for d in tracker.round_details:
            rn = d["round"]
            rp = d["red_pts"]
            bp = d["blue_pts"]
            wn = d["winner"]
            ranks = d["rankings"]
            rank_str = " | ".join(f"{rk}: {tm}" for rk, tm in ranks.items())
            print(f"    {rn:<6} {rp:<6} {bp:<6} {wn:<8}  {rank_str}")
        print()
    elif tracker:
        print("  Scoreboard:  No rounds completed.")
        print()

    # Issues
    all_issues = list(warnings) + list(errors)
    if all_issues:
        print("  Issues Found:")
        for i, issue in enumerate(all_issues, 1):
            prefix = "WARN" if issue in warnings else "ERROR"
            print(f"    [{prefix}] {issue}")
    else:
        print("  Issues Found:   None")
    print()
    print("=" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guandan Automated Bot Test Runner"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--external-only",
        action="store_true",
        help="Require external bots; fail if none are healthy.",
    )
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Force using only internal bots (ignore external deployments).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Max seconds to wait for game completion (overrides config.yaml total_timeout)",
    )
    parser.add_argument(
        "--num-rounds",
        type=int,
        default=None,
        help="Number of rounds (overrides config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print all received game messages (default: only round start/end)",
    )
    args = parser.parse_args()

    warnings: list[str] = []
    errors: list[str] = []

    # ------------------------------------------------------------------
    # Load config (exits on missing / invalid fields)
    # ------------------------------------------------------------------
    config = load_config(args.config)

    # Resolve CLI overrides
    num_rounds = args.num_rounds if args.num_rounds is not None else config["num_rounds"]
    timeout_s = args.timeout if args.timeout is not None else config["total_timeout"]

    # ------------------------------------------------------------------
    # Pre-flight: lobby health check
    # ------------------------------------------------------------------
    check_lobby_reachable(config["lobby_url"])

    # ------------------------------------------------------------------
    # Discover bots (only needed if config references deployed bots)
    # ------------------------------------------------------------------
    bot_configs: dict[int, dict] = config["bot_configs"]
    deployments: list[dict] = []
    has_deployed = any(
        cfg.get("type") == "deployed" for cfg in bot_configs.values()
    )
    if args.internal_only:
        log("INFO", "Forcing internal-only mode (--internal-only flag).")
        # Override any deployed entries
        for seat in bot_configs:
            if bot_configs[seat].get("type") == "deployed":
                bot_configs[seat] = {"type": "builtin", "bot_code": "strongBot"}
    elif has_deployed:
        deployments = discover_deployments(config["lobby_url"])

    if args.external_only:
        if not has_deployed:
            log("ERROR", "--external-only specified but no deployed bots in config.")
            return 1
        if not deployments:
            log("ERROR", "--external-only specified but no deployments found.")
            return 1

    # Build participants from config
    log("INFO", "Bot assignments from config:")
    participants = build_participants(
        bot_configs, deployments,
        lobby_url=config["lobby_url"],
        api_key=config["api_key"],
    )

    if args.external_only:
        has_external = any(p["type"] == "external_bot" for p in participants)
        if not has_external:
            log("ERROR", "--external-only specified but no healthy external "
                         "deployments available.")
            return 1

    # ------------------------------------------------------------------
    # Create test game
    # ------------------------------------------------------------------
    log("INFO", f"Test configuration: {num_rounds} round(s)")
    game = create_test_game(
        lobby_url=config["lobby_url"],
        api_key=config["api_key"],
        participants=participants,
        num_rounds=num_rounds,
    )

    if game is None:
        errors.append("Test game creation failed. Check lobby server and API key.")
        print_report(config, participants, None, None, warnings, errors, None)
        return 1

    # ------------------------------------------------------------------
    # Monitor SSE events
    # ------------------------------------------------------------------
    runtime = game.get("runtime", {})
    events_url = runtime.get("events_url", "")
    access_token = runtime.get("access_token", "")

    if not events_url or not access_token:
        errors.append("No events_url or access_token in game creation response.")
        print_report(config, participants, game, None, warnings, errors, None)
        return 1

    # ------------------------------------------------------------------
    # Pre-flight: game server health check
    # ------------------------------------------------------------------
    check_game_server_reachable(runtime.get("base_url", ""))

    # Handle SIGINT gracefully
    interrupted = False

    def _on_sigint(signum, frame):
        nonlocal interrupted
        interrupted = True

    old_handler = signal.signal(signal.SIGINT, _on_sigint)

    tracker = GameTracker(total_rounds=num_rounds)
    monitor_result = monitor_events(
        events_url=events_url,
        access_token=access_token,
        timeout_s=timeout_s,
        heartbeat_timeout=config["heartbeat_timeout"],
        verbose=args.verbose,
        tracker=tracker,
    )

    signal.signal(signal.SIGINT, old_handler)
    if interrupted:
        log("INFO", "Interrupted by user. Attempting to cancel game...")
        cancel_url = runtime.get("cancel_url", "")
        if cancel_url:
            try:
                _post(
                    cancel_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5,
                )
                log("INFO", "Game cancelled.")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Collect diagnostics
    # ------------------------------------------------------------------
    if monitor_result["termination"] == "connection_error":
        errors.append(f"SSE connection error: {monitor_result['error']}")
    elif monitor_result["termination"] == "heartbeat_timeout":
        warnings.append(
            "SSE heartbeat timeout — game may still be running "
            "but no events were received."
        )
    elif monitor_result["termination"] == "timeout":
        warnings.append(
            f"Game did not complete within {timeout_s}s. "
            "It may still be running on the server."
        )

    if len(monitor_result["events"]) == 0:
        warnings.append(
            "No SSE events received. The game may have started "
            "before the SSE subscription was established. "
            "Try adding --timeout with a larger value."
        )

    # ------------------------------------------------------------------
    # Print final report
    # ------------------------------------------------------------------
    print_report(config, participants, game, monitor_result, warnings, errors, tracker)

    # Return 0 if the game completed successfully, 1 otherwise
    if monitor_result["termination"] in ("completed", "failed", "cancelled", "test_completed"):
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
