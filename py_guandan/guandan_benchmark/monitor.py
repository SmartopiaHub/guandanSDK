"""SSE event-stream monitoring for benchmark games."""

import json
import time
from typing import Optional

import requests

from .client import log, utc_now
from .display import _print_round_end, _print_round_start, _print_round_score, _update_seat_map, print_agent_message
from .tracker import GameTracker


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
        resp = requests.get(
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


def build_seat_map(events: list[dict]) -> dict[str, int]:
    """Scan collected SSE events to build a ``{player_id: seat}`` mapping.

    Looks for ``iNewRound`` (which contains a ``players`` list) inside
    ``agent.message`` events, as well as other player-identification events.
    """
    seat_map: dict[str, int] = {}

    for ev in events:
        _update_seat_map(ev.get("data", {}), seat_map)

    return seat_map
