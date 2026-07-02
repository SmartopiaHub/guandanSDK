"""Guandan benchmark — automated bot test-runner for the Guandan platform.

Create test games with configurable bot line-ups, monitor the SSE event
stream, and report per-round scores and win-rates.

Usage as CLI::

    python -m guandan_benchmark [--config config.yaml] [--num-rounds N] [--verbose]

Usage as library::

    from guandan_benchmark import (
        GameTracker, load_config, create_test_game, monitor_events, print_report,
    )
"""

__version__ = "0.2.0"

from .config import load_config, validate_api_key_format
from .tracker import GameTracker
from .client import (
    check_lobby_reachable,
    check_game_server_reachable,
    create_test_game,
    discover_deployments,
    pick_healthy_ws_deployment,
    check_deployment_health,
    build_participants,
)
from .monitor import monitor_events, build_seat_map
from .display import print_agent_message, print_report

__all__ = [
    "GameTracker",
    "build_participants",
    "build_seat_map",
    "check_deployment_health",
    "check_game_server_reachable",
    "check_lobby_reachable",
    "create_test_game",
    "discover_deployments",
    "load_config",
    "monitor_events",
    "pick_healthy_ws_deployment",
    "print_agent_message",
    "print_report",
    "validate_api_key_format",
]
