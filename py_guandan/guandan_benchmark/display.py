"""Pretty-printing and report generation for the benchmark runner."""

import json
from typing import Any, Optional

from .client import log


# ---------------------------------------------------------------------------
# ANSI terminal color codes
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main entry point for printing agent messages
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
def print_report(
    config: dict,
    participants: list[dict],
    game: Optional[dict],
    monitor_result: Optional[dict],
    warnings: list[str],
    errors: list[str],
    tracker=None,
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
            from .monitor import build_seat_map
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
