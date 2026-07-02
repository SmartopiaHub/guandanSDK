"""Hand validation for Guandan.

Validates that a card string represents a legal play given the player's
available cards and the current hand on the table. Supports wild cards
(逢人配) that can substitute for any non-joker rank.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from .cards import (
    Card,
    Hand,
    HandType,
    PokerCardList,
    RANK_VALUES,
    rank_power,
    rank_value,
)


# ---------------------------------------------------------------------------
# Rank ordering for straights / tubes / plates
# ---------------------------------------------------------------------------
_RANK_ORDER = ["A"] + [str(i) for i in range(2, 10)] + ["T", "J", "Q", "K", "A"]
# Note: 'A' appears twice — once as low (index 0) and once as high (index 13).
# For straights: consecutive indices in this list.
#   A-low:  indices 0-4  → A,2,3,4,5
#   A-high: indices 9-13 → 10,J,Q,K,A

_STRAIGHT_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


def _rank_index(rank: str) -> int:
    """Return the position of a rank in the consecutive-rank ordering.

    Raises ValueError for jokers.
    """
    if rank in ("BJ", "RJ"):
        raise ValueError(f"Joker {rank} has no rank index")
    return _STRAIGHT_RANKS.index(rank)


def _consecutive_ranks(ranks: list[str]) -> bool:
    """Check if a sorted list of rank strings is consecutive."""
    return _consecutive_start_index(ranks) is not None


def _consecutive_start_index(ranks: list[str]) -> Optional[int]:
    """Return the matching rank-window start, treating Ace as low or high."""
    if not ranks or len(set(ranks)) != len(ranks):
        return None
    if any(rank in ("BJ", "RJ") for rank in ranks):
        return None
    wanted = set(ranks)
    width = len(ranks)
    for start in range(len(_STRAIGHT_RANKS) - width + 1):
        window = _STRAIGHT_RANKS[start:start + width]
        if len(set(window)) == width and set(window) == wanted:
            return start
    return None


# ---------------------------------------------------------------------------
# Hand detection (comprehensive, with wild cards)
# ---------------------------------------------------------------------------

def detect_hand(
    cards: list[Card],
    level_rank: str = "2",
) -> Optional[tuple[HandType, int]]:
    """Detect the hand type and power of a list of cards.

    Wild cards (heart-suit level cards) can substitute for any non-joker rank.
    Returns (HandType, power) or None if the cards don't form a valid hand.

    Power values:
      - Single/Pair/Triple/FullHouse/Straight/Tube/Plate: base power rank
      - Bomb: major×100 + minor (major = card count, except 6 for straight flush)
      - Joker bomb: maxNonJokerBombPower × 10 (approximated as 9999)
    """
    n = len(cards)
    if n == 0:
        return HandType.EMPTY, 0

    # Separate wild cards from normal cards
    wilds = [c for c in cards if c.is_wild]
    normal = [c for c in cards if not c.is_wild]
    n_wilds = len(wilds)
    n_normal = len(normal)

    # If only wild cards → treat as a bomb of wild cards (same rank = level rank)
    if n_normal == 0:
        if n_wilds == 1:
            return HandType.SINGLE, LEVEL_POWER
        elif n_wilds == 2:
            return HandType.PAIR, LEVEL_POWER
        elif n_wilds == 3:
            return HandType.TRIPLE, LEVEL_POWER
        elif n_wilds >= 4:
            return HandType.BOMB, _bomb_power(n_wilds, LEVEL_POWER)
        return None

    # If no wild cards, do strict detection
    if n_wilds == 0:
        return _detect_strict(normal)

    # With wild cards: try assigning wild cards to complete valid hands
    # Strategy: group normal cards by rank, find the best completion
    return _detect_with_wilds(normal, wilds, level_rank)


# ---------------------------------------------------------------------------
# Internal: strict detection (no wild cards)
# ---------------------------------------------------------------------------

LEVEL_POWER = 15  # rank_value for level cards


def _detect_strict(cards: list[Card]) -> Optional[tuple[HandType, int]]:
    """Detect hand type without wild cards."""
    n = len(cards)
    if n == 1:
        return HandType.SINGLE, cards[0].power_with_level

    # Group by rank
    by_rank: dict[str, list[Card]] = {}
    for c in cards:
        by_rank.setdefault(c.rank, []).append(c)

    ranks = sorted(by_rank.keys(), key=lambda r: rank_power(r))
    rank_counts = [(r, len(by_rank[r])) for r in ranks]

    # Single rank (all same rank)
    if len(by_rank) == 1:
        rank = ranks[0]
        count = len(by_rank[rank])
        # The wire format marks every current-level card with ``*``.  Its
        # promoted power is 15 even though its natural rank may be low (for
        # example, ``2D*``).  Using rank_power(rank) here made the validator
        # disagree with find_pairs()/can_play(), which correctly use the
        # promoted card power.
        power = by_rank[rank][0].power_with_level
        if count == 1:
            return HandType.SINGLE, power
        elif count == 2:
            return HandType.PAIR, power
        elif count == 3:
            return HandType.TRIPLE, power
        elif count == 4:
            return HandType.BOMB, _bomb_power(4, power)
        elif count >= 5:
            return HandType.BOMB, _bomb_power(count, power)

    # Multiple ranks
    if n == 5:
        # Check full house: triple + pair
        result = _check_full_house(rank_counts, by_rank)
        if result:
            return result

        # Check straight: 5 consecutive ranks, no jokers
        result = _check_straight_strict(cards)
        if result:
            return result

        # Check straight flush: 5 consecutive same suit → bomb
        result = _check_straight_flush_strict(cards)
        if result:
            return result

    elif n == 6:
        # Check tube: 3 consecutive pairs
        result = _check_tube_strict(rank_counts)
        if result:
            return result

        # Check plate: 2 consecutive triples
        result = _check_plate_strict(rank_counts)
        if result:
            return result

    # Check for bomb (4+ same rank, might be mixed with other cards if wild)
    # Strict detection doesn't handle mixed ranks well; bombs with wilds
    # are handled in _detect_with_wilds
    return None


def _check_full_house(
    rank_counts: list[tuple[str, int]],
    by_rank: dict[str, list[Card]],
) -> Optional[tuple[HandType, int]]:
    """Check for full house: one triple + one pair."""
    triples = [r for r, c in rank_counts if c >= 3]
    pairs = [r for r, c in rank_counts if c >= 2]
    if len(triples) >= 1 and len(pairs) >= 1:
        # Use first triple and first pair (different ranks)
        for t_rank in triples:
            for p_rank in pairs:
                if t_rank != p_rank:
                    return HandType.FULL_HOUSE, rank_power(t_rank)
    return None


def _check_straight_strict(cards: list[Card]) -> Optional[tuple[HandType, int]]:
    """Check for a 5-card straight (no jokers allowed)."""
    # Must be 5 cards, all different ranks, consecutive
    ranks = [c.rank for c in cards]
    if len(set(ranks)) != 5:
        return None
    start_idx = _consecutive_start_index(ranks)
    if start_idx is None:
        return None
    # Power = value of the starting rank (1 for A-low)
    start_rank = _STRAIGHT_RANKS[start_idx]
    power = 1 if start_rank == "A" else rank_power(start_rank)
    return HandType.STRAIGHT, power


def _check_straight_flush_strict(cards: list[Card]) -> Optional[tuple[HandType, int]]:
    """Check for a 5-card straight flush → classified as bomb."""
    straight_result = _check_straight_strict(cards)
    if straight_result is None:
        return None
    # Check all same suit (exclude jokers)
    non_joker = [c for c in cards if not c.is_joker]
    if not non_joker:
        return None
    suit = non_joker[0].suit
    if not suit:  # jokers only, can't be straight flush
        return None
    if all(c.suit == suit for c in non_joker):
        # Straight flush bomb: major=6, minor=starting rank power
        start_idx = _consecutive_start_index([c.rank for c in cards])
        if start_idx is None:
            return None
        start_rank = _STRAIGHT_RANKS[start_idx]
        minor = 1 if start_rank == "A" else rank_power(start_rank)
        return HandType.BOMB, 6 * 100 + minor
    return None


def _check_tube_strict(
    rank_counts: list[tuple[str, int]],
) -> Optional[tuple[HandType, int]]:
    """Check for tube: 3 consecutive pairs."""
    if len(rank_counts) != 3:
        return None
    if not all(c >= 2 for _, c in rank_counts):
        return None
    ranks = [r for r, _ in rank_counts]
    start_idx = _consecutive_start_index(ranks)
    if start_idx is None:
        return None
    # Power = starting rank value
    start_rank = _STRAIGHT_RANKS[start_idx]
    power = 1 if start_rank == "A" else rank_power(start_rank)
    return HandType.TUBE, power


def _check_plate_strict(
    rank_counts: list[tuple[str, int]],
) -> Optional[tuple[HandType, int]]:
    """Check for plate: 2 consecutive triples."""
    if len(rank_counts) != 2:
        return None
    if not all(c >= 3 for _, c in rank_counts):
        return None
    ranks = [r for r, _ in rank_counts]
    start_idx = _consecutive_start_index(ranks)
    if start_idx is None:
        return None
    start_rank = _STRAIGHT_RANKS[start_idx]
    power = 1 if start_rank == "A" else rank_power(start_rank)
    return HandType.PLATE, power


# ---------------------------------------------------------------------------
# Internal: detection with wild cards
# ---------------------------------------------------------------------------

def _detect_with_wilds(
    normal: list[Card],
    wilds: list[Card],
    level_rank: str,
) -> Optional[tuple[HandType, int]]:
    """Detect hand type with wild card substitution.

    Wild cards can fill gaps to complete any hand type.
    Strategy: try each possible hand type that the total card count suggests.
    """
    total = len(normal) + len(wilds)
    n_wilds = len(wilds)

    # Group normal cards by rank
    by_rank: dict[str, list[Card]] = {}
    for c in normal:
        by_rank.setdefault(c.rank, []).append(c)

    if total == 1:
        return HandType.SINGLE, LEVEL_POWER if n_wilds > 0 else normal[0].power_with_level

    if total == 2:
        # Must form a pair
        if n_wilds >= 1:
            # Wild card plus any card → pair of that card's rank
            return HandType.PAIR, normal[0].power_with_level if normal else LEVEL_POWER
        elif len(by_rank) == 1:
            return HandType.PAIR, normal[0].power_with_level
        return None

    if total == 3:
        # Must form a triple
        if len(by_rank) == 1 and len(normal) >= 2:
            return HandType.TRIPLE, normal[0].power_with_level
        # With wilds, we can complete a triple
        max_count = max((len(g) for g in by_rank.values()), default=0)
        if max_count + n_wilds >= 3:
            # Use the rank with most cards as the triple rank
            best_rank = max(by_rank.keys(), key=lambda r: len(by_rank[r]))
            return HandType.TRIPLE, rank_power(best_rank)
        return None

    if total == 4:
        # Could be bomb (4 of same rank)
        max_count = max((len(g) for g in by_rank.values()), default=0)
        if max_count + n_wilds >= 4:
            best_rank = max(by_rank.keys(), key=lambda r: len(by_rank[r]))
            return HandType.BOMB, _bomb_power(4, rank_power(best_rank))
        return None

    if total == 5:
        # Could be: full house, straight, or 5-card bomb, or straight flush bomb
        return _detect_5_with_wilds(normal, by_rank, n_wilds)

    if total == 6:
        # Could be: tube, plate, or 6-card bomb
        return _detect_6_with_wilds(normal, by_rank, n_wilds)

    if total >= 7:
        # Bomb of that size
        max_count = max((len(g) for g in by_rank.values()), default=0)
        if max_count + n_wilds >= total:
            best_rank = max(by_rank.keys(), key=lambda r: len(by_rank[r]))
            return HandType.BOMB, _bomb_power(total, rank_power(best_rank))
        return None

    return None


def _detect_5_with_wilds(
    normal: list[Card],
    by_rank: dict[str, list[Card]],
    n_wilds: int,
) -> Optional[tuple[HandType, int]]:
    """Detect 5-card hand with wild cards."""
    # Try full house: triple + pair
    rank_counts = sorted(
        [(r, len(g)) for r, g in by_rank.items()],
        key=lambda rc: rc[1],
        reverse=True,
    )
    if rank_counts:
        # Can we form a triple and a pair?
        primary = rank_counts[0]
        if primary[1] + n_wilds >= 3:
            # Use wilds to complete triple if needed
            wilds_used_for_triple = max(0, 3 - primary[1])
            remaining_wilds = n_wilds - wilds_used_for_triple
            # Find a pair from remaining cards
            for r, c in rank_counts[1:]:
                if c + remaining_wilds >= 2:
                    return HandType.FULL_HOUSE, rank_power(primary[0])
            # If remaining wilds >= 2, can form a pair with any card
            if remaining_wilds >= 2 and len(by_rank) >= 2:
                return HandType.FULL_HOUSE, rank_power(primary[0])
            # If remaining wilds >= 1 and there's another card
            if remaining_wilds >= 1:
                for r, c in rank_counts[1:]:
                    if c >= 1:
                        return HandType.FULL_HOUSE, rank_power(primary[0])

    # Try straight: 5 cards of consecutive ranks (no jokers in normal cards)
    if n_wilds > 0:
        normal_ranks = set(c.rank for c in normal if not c.is_joker)
        # Wild cards can represent any missing rank
        # Try to find a straight that uses all 5 cards
        if len(normal_ranks) + n_wilds >= 5:
            # For simplicity: treat this as a straight with wilds filling gaps
            # Check if normal ranks are all non-joker and form (or can form with wilds) a consecutive sequence
            if len(normal_ranks) <= 5:
                sorted_ranks = sorted(normal_ranks, key=lambda r: _rank_index(r))
                indices = [_rank_index(r) for r in sorted_ranks]
                if indices:
                    min_idx, max_idx = min(indices), max(indices)
                    # The span between min and max inclusive
                    span = max_idx - min_idx + 1
                    needed = span - len(normal_ranks)
                    if needed <= n_wilds and span <= 5:
                        # Power = start of straight
                        start_idx = min_idx
                        # Adjust for A-low case
                        if start_idx == 0:  # A-low
                            power = 1
                        else:
                            power = rank_power(_STRAIGHT_RANKS[start_idx])
                        return HandType.STRAIGHT, power

    # Try 5-card bomb
    max_count = max((len(g) for g in by_rank.values()), default=0)
    if max_count + n_wilds >= 5:
        best_rank = max(by_rank.keys(), key=lambda r: len(by_rank[r]))
        return HandType.BOMB, _bomb_power(5, rank_power(best_rank))

    return None


def _detect_6_with_wilds(
    normal: list[Card],
    by_rank: dict[str, list[Card]],
    n_wilds: int,
) -> Optional[tuple[HandType, int]]:
    """Detect 6-card hand with wild cards."""
    rank_counts = sorted(
        [(r, len(g)) for r, g in by_rank.items()],
        key=lambda rc: rc[1],
        reverse=True,
    )
    if not rank_counts:
        return None

    # Try tube: 3 consecutive pairs
    # Use wilds to fill missing pairs
    normal_ranks = set(c.rank for c in normal if not c.is_joker)
    if len(normal_ranks) <= 3:
        sorted_ranks = sorted(normal_ranks, key=lambda r: _rank_index(r))
        if sorted_ranks:
            indices = [_rank_index(r) for r in sorted_ranks]
            span = max(indices) - min(indices) + 1
            if span <= 3 and span <= len(indices) + n_wilds:
                # Check if we have enough cards for 3 pairs
                total_cards_needed = 6
                available = sum(c for _, c in rank_counts) + n_wilds
                if available >= total_cards_needed:
                    # Each of 3 ranks needs 2 cards
                    pairs_covered = sum(min(c, 2) for _, c in rank_counts)
                    if pairs_covered + n_wilds * 2 >= 6:
                        start_idx = min(indices)
                        power = 1 if _STRAIGHT_RANKS[start_idx] == "A" else rank_power(_STRAIGHT_RANKS[start_idx])
                        return HandType.TUBE, power

    # Try plate: 2 consecutive triples
    if len(normal_ranks) <= 2:
        sorted_ranks = sorted(normal_ranks, key=lambda r: _rank_index(r))
        if len(sorted_ranks) == 2:
            indices = [_rank_index(r) for r in sorted_ranks]
            if indices[1] == indices[0] + 1:
                # Can we form two triples?
                c1 = sum(c for r, c in rank_counts if r == sorted_ranks[0])
                c2 = sum(c for r, c in rank_counts if r == sorted_ranks[1])
                if c1 + c2 + n_wilds >= 6:
                    start_idx = indices[0]
                    power = 1 if _STRAIGHT_RANKS[start_idx] == "A" else rank_power(_STRAIGHT_RANKS[start_idx])
                    return HandType.PLATE, power
        elif len(sorted_ranks) == 1 and n_wilds >= 3:
            # One triple + 3 wilds can form two consecutive triples
            r = sorted_ranks[0]
            idx = _rank_index(r)
            if idx < len(_STRAIGHT_RANKS) - 1:
                power = 1 if _STRAIGHT_RANKS[idx] == "A" else rank_power(r)
                return HandType.PLATE, power

    # Try 6-card bomb
    max_count = max((len(g) for g in by_rank.values()), default=0)
    if max_count + n_wilds >= 6:
        best_rank = max(by_rank.keys(), key=lambda r: len(by_rank[r]))
        return HandType.BOMB, _bomb_power(6, rank_power(best_rank))

    return None


# ---------------------------------------------------------------------------
# Bomb power
# ---------------------------------------------------------------------------

def _bomb_power(size: int, rank_power_val: int) -> int:
    """Compute bomb power as major×100 + minor.

    major = size (4 for 4-card, 5 for 5-card, etc.)
    Straight flush uses major=6 (handled separately).
    """
    return size * 100 + rank_power_val


def _is_joker_bomb(cards: list[Card]) -> bool:
    """Check if this is the joker bomb: 2×BJ + 2×RJ."""
    ranks = Counter(c.rank for c in cards)
    return ranks.get("BJ", 0) == 2 and ranks.get("RJ", 0) == 2


# ---------------------------------------------------------------------------
# Public validation API
# ---------------------------------------------------------------------------

def validate_play(
    cards_str: str,
    available: PokerCardList,
    hand_on_table: Hand,
    level_rank: str = "2",
) -> tuple[bool, str]:
    """Validate that a card string represents a legal play.

    Args:
        cards_str: Space-separated card string (e.g. "3H 3D 3C 3S") or "" for pass.
        available: The player's current hand.
        hand_on_table: The hand currently on the table (empty if leading).
        level_rank: Current level rank.

    Returns:
        (is_valid, error_message). If valid, error_message is empty.
    """
    # --- Pass ---
    if not cards_str.strip():
        if hand_on_table.is_empty:
            return False, "Cannot pass when leading a phase — must play a hand"
        return True, ""

    # --- Parse cards ---
    try:
        cards = [Card.parse(c.strip(), level_rank) for c in cards_str.split() if c.strip()]
    except ValueError as e:
        return False, f"Invalid card format: {e}"

    if not cards:
        return False, "Empty card string after parsing"

    # --- Verify cards are in hand (accounting for two decks — duplicates allowed) ---
    from collections import Counter
    available_counts = Counter(str(c) for c in available.cards)
    played_counts = Counter(str(c) for c in cards)
    for card_str, count in played_counts.items():
        if available_counts.get(card_str, 0) < count:
            return False, (
                f"Card {card_str} used {count}× but only "
                f"{available_counts.get(card_str, 0)}× in hand"
            )

    # --- Detect hand type ---
    result = detect_hand(cards, level_rank)
    if result is None:
        return False, f"Cards '{cards_str}' do not form a valid hand"

    hand_type, power = result

    # --- Leading (no hand on table) ---
    if hand_on_table.is_empty:
        # Any valid hand is OK to lead
        return True, ""

    # --- Following: must beat the hand on table ---
    # Joker bomb beats everything
    if _is_joker_bomb(cards):
        if hand_on_table.is_bomb and _is_joker_bomb(hand_on_table.cards):
            return False, "Cannot beat joker bomb with another joker bomb"
        return True, ""

    # Bomb beats any non-bomb
    if hand_type == HandType.BOMB:
        if not hand_on_table.is_bomb:
            return True, ""

    # Same type comparison
    if hand_type == hand_on_table.type:
        if power > hand_on_table.power:
            return True, ""
        elif power == hand_on_table.power and hand_type == HandType.BOMB:
            # Same bomb power → can't play (strictly greater needed)
            return False, f"Bomb power {power} does not beat hand on table power {hand_on_table.power}"
        else:
            return False, f"Hand power {power} does not beat hand on table power {hand_on_table.power} (same type {hand_type.value})"

    # Bomb vs bomb
    if hand_type == HandType.BOMB and hand_on_table.is_bomb:
        if power > hand_on_table.power:
            return True, ""
        else:
            return False, f"Bomb power {power} does not beat bomb power {hand_on_table.power}"

    # Cross-type: plate ↔ tube
    if hand_on_table.type in (HandType.TUBE, HandType.PLATE) and hand_type in (HandType.TUBE, HandType.PLATE):
        if power > hand_on_table.power:
            return True, ""
        else:
            return False, f"Cross-type power {power} does not beat {hand_on_table.power}"

    # Bomb beats non-bomb (already handled above), but non-bomb can't beat bomb
    if hand_on_table.is_bomb and hand_type != HandType.BOMB:
        return False, f"Cannot play {hand_type.value} against a bomb — must play a higher bomb"

    # Type mismatch
    return False, (
        f"Hand type {hand_type.value} does not match hand on table type "
        f"{hand_on_table.type.value}. Must play same type, a bomb, or pass."
    )


def validate_tribute_card(
    card_str: str,
    available: PokerCardList,
) -> tuple[bool, str]:
    """Validate a tribute card selection.

    Args:
        card_str: Single card string.
        available: The player's current hand.

    Returns:
        (is_valid, error_message).
    """
    card_str = card_str.strip()
    if not card_str:
        return False, "Must select a tribute card"

    # Parse
    try:
        card = Card.parse(card_str)
    except ValueError as e:
        return False, f"Invalid card format: {e}"

    # Check in hand
    available_strs = {str(c) for c in available.cards}
    if str(card) not in available_strs:
        return False, f"Card {card} is not in your hand. Available: {available}"

    return True, ""


def validate_return_card(
    card_str: str,
    available: PokerCardList,
) -> tuple[bool, str]:
    """Validate a return card (anti-tribute) selection.

    The return card must have power ≤ 10 (i.e., at most rank 10).

    Args:
        card_str: Single card string.
        available: The player's current hand (after receiving tribute).

    Returns:
        (is_valid, error_message).
    """
    card_str = card_str.strip()
    if not card_str:
        return False, "Must select a return card"

    # Parse
    try:
        card = Card.parse(card_str)
    except ValueError as e:
        return False, f"Invalid card format: {e}"

    # Check in hand
    available_strs = {str(c) for c in available.cards}
    if str(card) not in available_strs:
        return False, f"Card {card} is not in your hand. Available: {available}"

    # Check power ≤ 10
    if not card.is_joker and rank_power(card.rank) > 10:
        return False, f"Return card {card} has power {rank_power(card.rank)} > 10 — must be ≤ 10"

    return True, ""
