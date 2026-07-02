"""Configuration loading and validation for the benchmark runner."""

import os
import sys
from typing import Optional

import yaml


def _fatal(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# API key validation
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
# Config loading
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


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
