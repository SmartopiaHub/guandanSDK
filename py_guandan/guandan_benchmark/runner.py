"""Main orchestrator for the Guandan benchmark runner.

Ties together config loading, health checks, bot discovery, test-game
creation, SSE monitoring, and the final report.  This is the entry point
for both the CLI (via ``__main__.py``) and programmatic use.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import warnings

from .client import (
    check_game_server_reachable,
    check_lobby_reachable,
    create_test_game,
    discover_deployments,
    build_participants,
    log,
)
from .config import DEFAULT_CONFIG_PATH, load_config
from .display import print_report
from .monitor import monitor_events
from .tracker import GameTracker


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark from the given command-line arguments.

    Returns 0 on success, 1 on error.  This function is the single entry
    point for both ``python -m guandan_benchmark`` and programmatic
    invocation.
    """
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
    args = parser.parse_args(argv)

    warnings_list: list[str] = []
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
        print_report(config, participants, None, None, warnings_list, errors, None)
        return 1

    # ------------------------------------------------------------------
    # Monitor SSE events
    # ------------------------------------------------------------------
    runtime = game.get("runtime", {})
    events_url = runtime.get("events_url", "")
    access_token = runtime.get("access_token", "")

    if not events_url or not access_token:
        errors.append("No events_url or access_token in game creation response.")
        print_report(config, participants, game, None, warnings_list, errors, None)
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
                import requests
                requests.post(
                    cancel_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5,
                    proxies={"http": None, "https": None},
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
        warnings_list.append(
            "SSE heartbeat timeout — game may still be running "
            "but no events were received."
        )
    elif monitor_result["termination"] == "timeout":
        warnings_list.append(
            f"Game did not complete within {timeout_s}s. "
            "It may still be running on the server."
        )

    if len(monitor_result["events"]) == 0:
        warnings_list.append(
            "No SSE events received. The game may have started "
            "before the SSE subscription was established. "
            "Try adding --timeout with a larger value."
        )

    # ------------------------------------------------------------------
    # Print final report
    # ------------------------------------------------------------------
    print_report(config, participants, game, monitor_result, warnings_list, errors, tracker)

    # Return 0 if the game completed successfully, 1 otherwise
    if monitor_result["termination"] in ("completed", "failed", "cancelled", "test_completed"):
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
