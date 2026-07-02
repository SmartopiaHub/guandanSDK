"""HTTP client helpers for the benchmark runner.

Handles lobby/game-server health checks, bot deployment discovery, and
test-game creation.
"""

import json
import sys
import uuid
from typing import Any, Optional

import requests


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


def _fatal(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Logging helper (imported lazily by other modules via this one)
# ---------------------------------------------------------------------------
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log(level: str, msg: str) -> None:
    print(f"[{utc_now()}] {level:5s}  {msg}")


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
# Bot deployment discovery
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
# Build participants from config
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
# Create test game
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
