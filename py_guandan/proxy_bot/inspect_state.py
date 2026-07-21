#!/usr/bin/env python3
"""Read-only diagnostics for a running Guandan proxy bot.

The inspector only performs ``GET /state``.  It never calls ``/action`` and
does not rank or recommend plays.

Card primitives and hand analysis are reused from :mod:`guandan_core.cards`
and :mod:`guandan_core.utility` so that parsing, identity, deck generation,
bomb enumeration, and straight-flush enumeration stay in one place.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

import yaml

from guandan_core.cards import (
    Card,
    HandType,
    NON_JOKER_SUITS,
    PokerCardList,
    RANK_VALUES,
)
from guandan_core.utility import find_bombs, find_straight_flushes


# ---------------------------------------------------------------------------
# Helpers that build on guandan_core primitives
# ---------------------------------------------------------------------------

def _parse_card_tokens(value: Any) -> list[str]:
    """Extract card tokens from a hand string using ``PokerCardList.parse``."""
    if not isinstance(value, str):
        return []
    try:
        cards = PokerCardList.parse(value)
        return [str(c) for c in cards]
    except (ValueError, KeyError):
        return []


def _cards_to_poker_list(tokens: Iterable[str]) -> PokerCardList:
    """Convert a sequence of card-token strings into a ``PokerCardList``."""
    return PokerCardList([Card.parse(t) for t in tokens])


def _build_deck_counter(deck_count: int) -> Counter[str]:
    """Return a :class:`Counter` of full-deck card identities (no level markers)."""
    counter: Counter[str] = Counter()
    for _ in range(deck_count):
        for rank in RANK_VALUES:
            for suit in NON_JOKER_SUITS:
                counter[f"{rank}{suit}"] += 1
        counter["BJ"] += 1
        counter["RJ"] += 1
    return counter


def _card_identity(token: str) -> str:
    """Strip the level-rank ``*`` marker from a card token."""
    return token.rstrip("*")


# ---------------------------------------------------------------------------
# Analysis wrappers that delegate to guandan_core.utility
# ---------------------------------------------------------------------------


# Straight rank sequence used for window-rank derivation.
_STRAIGHT_RANK_SEQUENCE = (
    "A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A",
)


def _straight_flush_report(
    card_tokens: list[str], level_rank: str
) -> dict[str, Any]:
    """Enumerate straight flushes via :func:`guandan_core.utility.find_straight_flushes`.

    Results are split into ``natural`` and ``wildcard_assisted`` buckets for
    the inspector report format.
    """
    if not card_tokens:
        return {"natural": [], "wildcard_assisted": []}

    cards = _cards_to_poker_list(card_tokens)
    wildcard_identity = f"{level_rank}H"
    hands = find_straight_flushes(cards, level_rank, find_all=True)

    natural: list[dict[str, Any]] = []
    wildcard_assisted: list[dict[str, Any]] = []
    for hand in hands:
        tokens = [str(c) for c in hand.cards]
        wildcards_used = sum(
            1 for c in hand.cards
            if not c.is_joker and str(c).rstrip("*") == wildcard_identity
        )
        # Derive the conceptual rank window from the hand's power (start rank).
        # The hand power for a straight flush is a bomb-6xx value; the start
        # rank value is encoded in the power.
        start_value = hand.power % 100
        try:
            start_index = _STRAIGHT_RANK_SEQUENCE.index(
                "A" if start_value == 1 else
                "2" if start_value == 2 else
                "3" if start_value == 3 else
                "4" if start_value == 4 else
                "5" if start_value == 5 else
                "6" if start_value == 6 else
                "7" if start_value == 7 else
                "8" if start_value == 8 else
                "9" if start_value == 9 else
                "T" if start_value == 10 else
                "J" if start_value == 11 else
                "Q" if start_value == 12 else
                "K" if start_value == 13 else
                "A"
            )
        except ValueError:
            start_index = 0
        window_ranks = list(_STRAIGHT_RANK_SEQUENCE[start_index : start_index + 5])

        # Suit from any non-wild, non-joker card in the hand.
        regular_cards = [
            c for c in hand.cards
            if not c.is_joker and str(c).rstrip("*") != wildcard_identity
        ]
        suit = regular_cards[0].suit if regular_cards else "H"

        entry: dict[str, Any] = {
            "ranks": window_ranks,
            "suit": suit,
            "cards": tokens,
            "wildcards_needed": wildcards_used,
        }
        if wildcards_used == 0:
            natural.append(entry)
        else:
            wildcard_assisted.append(entry)

    return {"natural": natural, "wildcard_assisted": wildcard_assisted}


def _bomb_report(
    card_tokens: list[str], level_rank: str, deck_count: int
) -> dict[str, Any]:
    """Enumerate bombs via :func:`guandan_core.utility.find_bombs`.

    Straight flushes are excluded (they appear in the straight-flush section).
    Results are split into ``natural`` and ``wildcard_assisted`` buckets.
    """
    if not card_tokens:
        return {"natural": [], "wildcard_assisted": []}

    cards = _cards_to_poker_list(card_tokens)
    wildcard_identity = f"{level_rank}H"
    # include_straight_flush=False: keep bomb and straight-flush sections separate
    hands = find_bombs(
        cards, level_rank, find_all=True,
        include_straight_flush=False,
        number_of_standard_decks=deck_count,
    )

    natural: list[dict[str, Any]] = []
    wildcard_assisted: list[dict[str, Any]] = []
    for hand in hands:
        tokens = [str(c) for c in hand.cards]
        wildcards_used = sum(
            1 for c in hand.cards
            if not c.is_joker and str(c).rstrip("*") == wildcard_identity
        )
        # Determine the rank: use the first non-wild, non-joker card's rank
        regular_cards = [
            c for c in hand.cards
            if not c.is_joker and str(c).rstrip("*") != wildcard_identity
        ]
        if regular_cards:
            rank = regular_cards[0].rank
            kind = "rank_bomb"
        elif all(c.is_joker for c in hand.cards):
            rank = "BJ+RJ"
            kind = "joker_bomb"
        else:
            rank = level_rank
            kind = "rank_bomb"

        entry: dict[str, Any] = {
            "kind": kind,
            "size": len(hand.cards),
            "rank": rank,
            "cards": tokens,
            "wildcards_needed": wildcards_used,
        }
        if wildcards_used == 0:
            natural.append(entry)
        else:
            wildcard_assisted.append(entry)

    return {"natural": natural, "wildcard_assisted": wildcard_assisted}


# ---------------------------------------------------------------------------
# Round-level-rank tracking
# ---------------------------------------------------------------------------


def _round_level_ranks(state: dict[str, Any]) -> dict[str, str]:
    """Collect round-to-level mappings from the current state and snapshots."""
    levels: dict[str, str] = {}

    def record(value: Any) -> None:
        if not isinstance(value, dict):
            return
        round_id = value.get("round_id")
        level_rank = value.get("level_rank")
        if round_id and level_rank is not None:
            levels[str(round_id)] = str(level_rank).upper()

    def record_snapshot(snapshot: Any) -> None:
        if not isinstance(snapshot, dict):
            return
        for round_value in snapshot.get("rounds") or []:
            record(round_value)
            if isinstance(round_value, dict):
                record(round_value.get("round_result"))
                record(round_value.get("previous_round_result"))

    round_state = state.get("round") or {}
    record(round_state)
    record_snapshot(state.get("game_state_snapshot"))
    for event in state.get("recent_events") or []:
        if not isinstance(event, dict):
            continue
        record(event)
        record(event.get("round_result"))
        record(event.get("previous_round_result"))
        record_snapshot(event.get("game_state_snapshot"))

    record(round_state)
    return levels


def _infer_marked_level(cards: Iterable[str]) -> str | None:
    marked = {
        _card_identity(card)[:-1]
        for card in cards
        if card.endswith("*") and _card_identity(card) not in {"BJ", "RJ"}
    }
    return next(iter(marked)) if len(marked) == 1 else None


# ---------------------------------------------------------------------------
# Player / event helpers
# ---------------------------------------------------------------------------


def _players_by_seat(state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    players: dict[int, dict[str, Any]] = {}

    def add(values: Any) -> None:
        if not isinstance(values, list):
            return
        for player in values:
            if not isinstance(player, dict):
                continue
            try:
                seat = int(player["seat"])
            except (KeyError, TypeError, ValueError):
                continue
            players.setdefault(seat, {}).update(player)

    round_state = state.get("round") or {}
    add(round_state.get("players"))
    snapshot = state.get("game_state_snapshot") or {}
    add(snapshot.get("players"))
    for event in state.get("recent_events") or []:
        if not isinstance(event, dict):
            continue
        add(event.get("players"))
        add((event.get("game_state_snapshot") or {}).get("players"))
    return players


def _event_rounds(events: list[dict[str, Any]]) -> list[str | None]:
    """Associate round-less notification events with their surrounding round."""
    result: list[str | None] = []
    current: str | None = None
    for event in events:
        explicit = event.get("round_id")
        if explicit:
            current = str(explicit)
        result.append(current)

    first_known = next((value for value in result if value), None)
    if first_known:
        for index, value in enumerate(result):
            if value:
                break
            result[index] = first_known
    return result


def _remove_cards_from_list(
    cards: list[str], played: Iterable[str], warnings: list[str], label: str
) -> None:
    """Remove played cards from a mutable token list, warning on mismatch."""
    for card in played:
        identity = _card_identity(card)
        index = next(
            (i for i, held in enumerate(cards) if _card_identity(held) == identity),
            None,
        )
        if index is None:
            warnings.append(f"{label}: cannot remove unheld card {card}")
        else:
            del cards[index]


def _apply_later_events(
    cards: list[str],
    *,
    player_id: str,
    events: list[dict[str, Any]],
    start_index: int,
    round_id: str,
    event_rounds: list[str | None],
    warnings: list[str],
) -> list[str]:
    updated = list(cards)
    for index in range(start_index + 1, len(events)):
        if event_rounds[index] != round_id:
            continue
        event = events[index]
        event_type = event.get("type")
        if event_type == "iHandPlayed" and event.get("player_id") == player_id:
            _remove_cards_from_list(
                updated,
                _parse_card_tokens(event.get("cards")),
                warnings,
                f"recent_events[{index}]",
            )
        elif event_type == "iTributeResult":
            tributes = (event.get("tribute_result") or {}).get("tributes") or []
            for tribute in tributes:
                if not isinstance(tribute, dict):
                    continue
                tribute_card = _parse_card_tokens(tribute.get("tribute_card"))
                return_card = _parse_card_tokens(tribute.get("return_card"))
                if tribute.get("payer_id") == player_id:
                    _remove_cards_from_list(
                        updated, tribute_card, warnings,
                        f"recent_events[{index}] tribute",
                    )
                    updated.extend(return_card)
                if tribute.get("receiver_id") == player_id:
                    updated.extend(tribute_card)
                    _remove_cards_from_list(
                        updated, return_card, warnings,
                        f"recent_events[{index}] return",
                    )
    return updated


# ---------------------------------------------------------------------------
# Exact-hand reconstruction
# ---------------------------------------------------------------------------


def _exact_hand_candidates(
    state: dict[str, Any],
    players: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    events = [
        event
        for event in (state.get("recent_events") or [])
        if isinstance(event, dict)
    ]
    event_rounds = _event_rounds(events)
    id_to_seat = {
        player.get("player_id"): seat
        for seat, player in players.items()
        if player.get("player_id")
    }
    candidates: dict[int, dict[str, Any]] = {}

    def record(
        *,
        seat: int,
        cards: str,
        round_id: str | None,
        source: str,
        event_index: int,
        player_id: str | None,
        played_at_snapshot: str | None = None,
    ) -> None:
        candidates[seat] = {
            "cards": _parse_card_tokens(cards),
            "round_id": round_id,
            "source": source,
            "event_index": event_index,
            "player_id": player_id,
            "played_at_snapshot": (
                _parse_card_tokens(played_at_snapshot)
                if played_at_snapshot is not None
                else None
            ),
        }

    for index, event in enumerate(events):
        event_round = event_rounds[index]
        if event.get("type") == "iCardsOnHand":
            for player_id, cards in (event.get("cards_on_hand") or {}).items():
                seat = id_to_seat.get(player_id)
                if seat is not None and isinstance(cards, str):
                    record(
                        seat=seat, cards=cards, round_id=event_round,
                        source=f"recent_events[{index}].iCardsOnHand",
                        event_index=index, player_id=player_id,
                    )

        snapshot_players = (
            (event.get("game_state_snapshot") or {}).get("players") or []
        )
        for player in snapshot_players:
            if not isinstance(player, dict) or "cards_on_hand" not in player:
                continue
            try:
                seat = int(player["seat"])
            except (KeyError, TypeError, ValueError):
                continue
            cards = player.get("cards_on_hand")
            if isinstance(cards, str):
                record(
                    seat=seat, cards=cards, round_id=event_round,
                    source=f"recent_events[{index}].game_state_snapshot",
                    event_index=index, player_id=player.get("player_id"),
                    played_at_snapshot=player.get("played_cards", ""),
                )

    current_round = str((state.get("round") or {}).get("round_id") or "")
    for player in (state.get("round") or {}).get("players") or []:
        if not isinstance(player, dict):
            continue
        try:
            seat = int(player["seat"])
        except (KeyError, TypeError, ValueError):
            continue
        cards = player.get("cards_on_hand")
        if isinstance(cards, str):
            record(
                seat=seat, cards=cards, round_id=current_round,
                source="round.players", event_index=len(events),
                player_id=player.get("player_id"),
                played_at_snapshot=player.get("played_cards", ""),
            )

    warnings: list[str] = []
    current_played = {
        player.get("player_id"): _parse_card_tokens(player.get("played_cards"))
        for player in (state.get("round") or {}).get("players") or []
        if isinstance(player, dict) and player.get("player_id")
    }
    for candidate in candidates.values():
        if candidate["round_id"] == current_round and candidate["event_index"] < len(events):
            baseline = candidate["played_at_snapshot"]
            cumulative = current_played.get(candidate["player_id"])
            if baseline is not None and cumulative is not None:
                delta = Counter(_card_identity(card) for card in cumulative)
                delta.subtract(_card_identity(card) for card in baseline)
                newly_played = [
                    card for card, count in delta.items()
                    for _ in range(max(0, count))
                ]
                _remove_cards_from_list(
                    candidate["cards"], newly_played, warnings,
                    candidate["source"],
                )
                candidate["source"] += " + cumulative played-card delta"
            else:
                candidate["cards"] = _apply_later_events(
                    candidate["cards"],
                    player_id=candidate["player_id"], events=events,
                    start_index=candidate["event_index"],
                    round_id=current_round, event_rounds=event_rounds,
                    warnings=warnings,
                )
                candidate["source"] += " + later public events"
    if warnings:
        candidates[-1] = {"warnings": warnings}
    return candidates


# ---------------------------------------------------------------------------
# Main inspection entry point
# ---------------------------------------------------------------------------


def inspect_state(state: dict[str, Any]) -> dict[str, Any]:
    round_state = state.get("round") or {}
    current_round = str(round_state.get("round_id") or "")
    own = state.get("player") or {}
    own_seat = int(own.get("seat") or 0)
    own_cards = _parse_card_tokens(round_state.get("cards_on_hand"))
    deck_count = int(state.get("deck_count") or 2)
    players = _players_by_seat(state)
    exact = _exact_hand_candidates(state, players)
    round_levels = _round_level_ranks(state)
    warnings = list(exact.pop(-1, {}).get("warnings", []))

    played_by_seat: dict[int, list[str]] = {
        seat: _parse_card_tokens(player.get("played_cards"))
        for seat, player in players.items()
    }
    for player in round_state.get("players") or []:
        if not isinstance(player, dict):
            continue
        try:
            seat = int(player["seat"])
        except (KeyError, TypeError, ValueError):
            continue
        played_by_seat[seat] = _parse_card_tokens(player.get("played_cards"))

    turn_played: dict[int, list[str]] = {}
    for turn in round_state.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        try:
            seat = int(turn["seat"])
        except (KeyError, TypeError, ValueError):
            continue
        turn_played.setdefault(seat, []).extend(
            _parse_card_tokens(turn.get("cards"))
        )
    for seat, cards in turn_played.items():
        if len(cards) > len(played_by_seat.get(seat, [])):
            played_by_seat[seat] = cards

    deck = _build_deck_counter(deck_count)
    visible = Counter(_card_identity(card) for card in own_cards)
    for cards in played_by_seat.values():
        visible.update(_card_identity(card) for card in cards)
    unseen = deck - visible
    overdrawn = visible - deck
    if overdrawn:
        warnings.append(
            "visible cards exceed the configured deck: "
            + ", ".join(
                f"{card} x{count}" for card, count in sorted(overdrawn.items())
            )
        )

    seats: dict[str, Any] = {}
    expected_unseen = 0
    total_cards = 54 * deck_count
    default_start_count = total_cards // 4
    for seat in sorted(players):
        if seat == own_seat:
            continue
        player = players[seat]
        played = played_by_seat.get(seat, [])
        remaining = default_start_count - len(played)
        expected_unseen += remaining
        known = exact.get(seat)
        latest: dict[str, Any]
        if known is None:
            latest = {"known": False}
        else:
            known_cards = known["cards"]
            is_current = known["round_id"] == current_round
            known_level = (
                round_levels.get(str(known["round_id"]))
                or _infer_marked_level(known_cards)
            )
            latest = {
                "known": True,
                "round_id": known["round_id"],
                "current_round": is_current,
                "source": known["source"],
                "count": len(known_cards),
                "cards": known_cards,
                "straight_flush_windows": {
                    "level_rank": known_level,
                    **(
                        _straight_flush_report(known_cards, known_level)
                        if known_level is not None
                        else {
                            "natural": [],
                            "wildcard_assisted": [],
                            "note": "round level is unknown; windows were not evaluated",
                        }
                    ),
                },
                "bombs": {
                    "level_rank": known_level,
                    **(
                        _bomb_report(known_cards, known_level, deck_count)
                        if known_level is not None
                        else {
                            "natural": [],
                            "wildcard_assisted": [],
                            "note": "round level is unknown; bombs were not evaluated",
                        }
                    ),
                },
            }
            if is_current and len(known_cards) != remaining:
                warnings.append(
                    f"seat {seat}: exact-hand count {len(known_cards)} "
                    f"does not match inferred remaining count {remaining}"
                )
        seats[str(seat)] = {
            "player_id": player.get("player_id"),
            "team": player.get("team"),
            "played_count": len(played),
            "remaining_count": remaining,
            "latest_exact_hand": latest,
        }

    unseen_total = sum(unseen.values())
    if unseen_total != expected_unseen:
        warnings.append(
            f"unseen pool has {unseen_total} cards, but other-seat counts sum to "
            f"{expected_unseen}"
        )

    rank_counts: Counter[str] = Counter()
    for card, count in unseen.items():
        rank = card if card in {"BJ", "RJ"} else card[0]
        rank_counts[rank] += count

    report: dict[str, Any] = {
        "session_id": state.get("session_id"),
        "game_id": state.get("game_id"),
        "round_id": current_round or None,
        "level_rank": round_state.get("level_rank"),
        "observer": {
            "seat": own_seat,
            "player_id": own.get("player_id"),
            "cards_on_hand_count": len(own_cards),
            "cards_on_hand": own_cards,
        },
        "other_seats": seats,
        "unseen_card_pool": {
            "count": unseen_total,
            "expected_from_other_seat_counts": expected_unseen,
            "counts_by_rank": dict(sorted(rank_counts.items())),
            "counts_by_card": dict(sorted(unseen.items())),
            "note": "Card identities omit the '*' level-rank marker.",
        },
    }
    if warnings:
        report["warnings"] = warnings
    return report


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def _fetch_state(
    base_url: str, session_id: str | None, game_id: str | None, timeout: float
) -> Any:
    query = {
        key: value
        for key, value in (("session_id", session_id), ("game_id", game_id))
        if value
    }
    url = f"{base_url.rstrip('/')}/state"
    if query:
        url += "?" + urlencode(query)
    opener = build_opener(ProxyHandler({}))
    with opener.open(url, timeout=timeout) as response:  # noqa: S310
        return yaml.safe_load(response)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read proxy /state and report exact-hand observations plus the "
            "current unseen-card multiset. No actions or move advice."
        )
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--state-file", help="inspect a saved /state YAML file")
    source.add_argument(
        "--base-url",
        default="http://127.0.0.1:10001",
        help="proxy base URL (default: %(default)s)",
    )
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--session-id")
    selector.add_argument("--game-id")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--format", choices=("yaml", "json"), default="yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.state_file:
            with open(args.state_file, encoding="utf-8") as stream:
                states = yaml.safe_load(stream)
        else:
            states = _fetch_state(
                args.base_url, args.session_id, args.game_id, args.timeout
            )
        reports = (
            [inspect_state(state) for state in states]
            if isinstance(states, list)
            else inspect_state(states)
        )
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(f"inspect_state: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        print(yaml.safe_dump(reports, allow_unicode=True, sort_keys=False).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
