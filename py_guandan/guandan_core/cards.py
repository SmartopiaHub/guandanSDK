"""Card, hand, and deck encoding for Guandan.

Card encoding: <rank><suit>[<level-marker>]
  Rank: 2-9, T(10), J, Q, K, A, BJ (black joker), RJ (red joker)
  Suit: H(hearts), D(diamonds), C(clubs), S(spades)
  Level marker: * suffix (e.g., "2H*")

Hand encoding: <type>-<power> : <card-list>
  Types: single, pair, triple, fullHouse, straight, tube, plate, bomb, empty
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Card rank values (higher = more powerful)
# ---------------------------------------------------------------------------
RANK_VALUES: dict[str, int] = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}
LEVEL_CARD_VALUE = 15
BJ_VALUE = 16  # black joker
RJ_VALUE = 17  # red joker


def rank_value(rank: str, level_rank: Optional[str] = None) -> int:
    """Return the power value of a card rank, accounting for level promotion."""
    r = rank.rstrip("*")
    if rank.endswith("*") or (level_rank and r == level_rank):
        return LEVEL_CARD_VALUE
    if r == "BJ":
        return BJ_VALUE
    if r == "RJ":
        return RJ_VALUE
    return RANK_VALUES.get(r, 0)


def rank_power(rank: str) -> int:
    """Return the base power of a rank for hand comparison (2=2, ..., A=14, BJ=16, RJ=17)."""
    r = rank.rstrip("*")
    if r == "BJ":
        return BJ_VALUE
    if r == "RJ":
        return RJ_VALUE
    return RANK_VALUES.get(r, 0)


# Card parse regex: rank (2-9 or T/J/Q/K/A or BJ/RJ), suit (H/D/C/S), optional *
CARD_RE = re.compile(r"^(2|3|4|5|6|7|8|9|T|J|Q|K|A|BJ|RJ)([HDCS])?(\*)?$")


@dataclass(frozen=True)
class Card:
    """A single playing card."""

    rank: str  # "2"-"9", "T", "J", "Q", "K", "A", "BJ", "RJ"
    suit: str  # "H", "D", "C", "S", or "" for jokers
    is_level: bool = False

    @classmethod
    def parse(cls, s: str, level_rank: Optional[str] = None) -> "Card":
        """Parse a card string like '3H', 'TD', '2C*', 'BJ', 'RJ'.

        The is_level flag is set based on the '*' suffix only (matching Dart's
        PokerCard.fromString behavior). Callers should use mark_level() to
        apply level-rank promotion after parsing.
        """
        s = s.strip()
        m = CARD_RE.match(s)
        if not m:
            raise ValueError(f"Invalid card string: {s!r}")
        rank = m.group(1)
        suit = m.group(2) or ""
        has_star = m.group(3) == "*"
        return cls(rank=rank, suit=suit, is_level=has_star)

    @classmethod
    def wild_card(cls, level_rank: str) -> "Card":
        """Create a wild card (逢人配) for the given level rank."""
        return cls(rank=level_rank, suit="H", is_level=True)

    @classmethod
    def red_joker_card(cls) -> "Card":
        """Create a red joker card."""
        return cls(rank="RJ", suit="", is_level=False)

    @classmethod
    def black_joker_card(cls) -> "Card":
        """Create a black joker card."""
        return cls(rank="BJ", suit="", is_level=False)

    @property
    def is_wild(self) -> bool:
        """Wild card: hearts suit AND level card (逢人配)."""
        return self.is_level and self.suit == "H"

    @property
    def is_joker(self) -> bool:
        return self.rank in ("BJ", "RJ")

    @property
    def power(self) -> int:
        """Power value for comparison."""
        return rank_power(self.rank)

    @property
    def power_with_level(self) -> int:
        """Power value accounting for level promotion."""
        if self.is_level and not self.is_joker:
            return LEVEL_CARD_VALUE
        return self.power

    @property
    def power_rank(self) -> int:
        """Power rank matching Dart's PokerCard.powerRank.
        Wild/level cards = 15, BJ = 16, RJ = 17, others = rank value.
        """
        if self.is_wild:
            return LEVEL_CARD_VALUE
        if self.is_joker:
            return rank_power(self.rank)
        return rank_power(self.rank) if not self.is_level else LEVEL_CARD_VALUE

    @property
    def is_black_joker(self) -> bool:
        return self.rank == "BJ"

    @property
    def is_red_joker(self) -> bool:
        return self.rank == "RJ"

    @property
    def natural_rank(self) -> str:
        """The actual rank string, ignoring level promotion (for sorting)."""
        return self.rank

    @property
    def natural_sort_index(self) -> int:
        """Sort index for natural rank ordering.
        A=0, 2=1, ..., K=12, A=13, BJ=14, RJ=15
        """
        r = self.rank
        if r == "A":
            return 13  # high A for sorting purposes
        if r == "BJ":
            return 14
        if r == "RJ":
            return 15
        return RANK_VALUES.get(r, 0) - 2  # 2→0, 3→1, ..., K→11

    def __str__(self) -> str:
        star = "*" if self.is_level and not self.rank.endswith("*") else ""
        return f"{self.rank}{self.suit}{star}"

    def __lt__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.power_rank < other.power_rank

    def __le__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.power_rank <= other.power_rank

    def __gt__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.power_rank > other.power_rank

    def __ge__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.power_rank >= other.power_rank


class HandType(Enum):
    """Types of playable hands."""
    SINGLE = "single"
    PAIR = "pair"
    TRIPLE = "triple"
    FULL_HOUSE = "fullHouse"
    STRAIGHT = "straight"
    TUBE = "tube"
    PLATE = "plate"
    BOMB = "bomb"
    EMPTY = "empty"
    UNKNOWN = "unknown"
    INVALID = "invalid"

    @property
    def size(self) -> int:
        return {
            HandType.SINGLE: 1,
            HandType.PAIR: 2,
            HandType.TRIPLE: 3,
            HandType.FULL_HOUSE: 5,
            HandType.STRAIGHT: 5,
            HandType.TUBE: 6,
            HandType.PLATE: 6,
            HandType.BOMB: 4,  # minimum
            HandType.EMPTY: 0,
            HandType.UNKNOWN: 0,
            HandType.INVALID: 0,
        }[self]

    @property
    def is_unknown_or_invalid(self) -> bool:
        return self in (HandType.UNKNOWN, HandType.INVALID)


# Hand type detection: check if a group of same-rank cards forms a valid hand
def _detect_hand_type(cards: list[Card], level_rank: str = "2") -> Optional[tuple[HandType, int]]:
    """Detect hand type and power from a list of cards.

    Returns (HandType, power) or None if not a valid hand.
    For simplicity, this only handles basic types: single, pair, triple, bomb.
    Straights, tubes, plates, and full houses are not implemented yet
    (they require more complex pattern matching).
    """
    n = len(cards)
    if n == 0:
        return HandType.EMPTY, 0
    if n == 1:
        return HandType.SINGLE, cards[0].power_with_level
    if n == 2:
        # Must be a pair of same rank
        if cards[0].rank == cards[1].rank:
            return HandType.PAIR, cards[0].power_with_level
        return None
    if n == 3:
        # Triple
        if cards[0].rank == cards[1].rank == cards[2].rank:
            return HandType.TRIPLE, cards[0].power_with_level
        return None
    if n >= 4:
        # Check if all same rank → bomb
        ranks = {c.rank for c in cards}
        if len(ranks) == 1:
            return HandType.BOMB, cards[0].power_with_level
        return None
    return None


@dataclass
class Hand:
    """A played hand of cards with type and power information.

    Fields ordered (cards, type, power) so positional Hand(cards, type, power=...)
    works naturally.
    """

    cards: list[Card] = field(default_factory=list)
    type: HandType = HandType.EMPTY
    power: int = -1

    @classmethod
    def from_cards(cls, cards: list[Card], level_rank: str = "2") -> "Hand":
        """Create a Hand from a list of Card objects."""
        if not cards:
            return cls(type=HandType.EMPTY, power=0)
        result = _detect_hand_type(cards, level_rank)
        if result is None:
            return cls(type=HandType.EMPTY, power=0)
        return cls(type=result[0], power=result[1], cards=cards)

    @classmethod
    def parse(cls, hand_str: str) -> "Hand":
        """Parse a hand string like 'pair-7 : 7H 7D' or 'empty-0 :'."""
        hand_str = hand_str.strip()
        if not hand_str or hand_str in ("empty-0 :", "empty-0:"):
            return cls(type=HandType.EMPTY, power=0)

        if ":" not in hand_str:
            return cls(
                cards=[Card.parse(c) for c in hand_str.split() if c.strip()],
                type=HandType.UNKNOWN,
                power=-1,
            )

        # Split at ":"
        parts = hand_str.split(":", 1)
        type_power = parts[0].strip()
        cards_str = parts[1].strip() if len(parts) > 1 else ""

        # Parse type-power like "pair-7"
        tp_parts = type_power.split("-", 1)
        hand_type_str = tp_parts[0]
        power = int(tp_parts[1]) if len(tp_parts) > 1 else 0

        try:
            hand_type = HandType(hand_type_str)
        except ValueError:
            hand_type = HandType.EMPTY

        cards = [Card.parse(c) for c in cards_str.split() if c.strip()] if cards_str else []

        return cls(type=hand_type, power=power, cards=cards)

    @classmethod
    def from_json(cls, data: dict) -> "Hand":
        """Create a hand from a Dart-compatible JSON map."""
        cards = [Card.parse(token) for token in data.get("cards", "").split() if token.strip()]
        return cls(cards=cards, type=HandType(data["type"]), power=data.get("power", -1))

    def to_json(self) -> dict:
        """Serialize this hand using Dart-compatible JSON keys."""
        return {
            "cards": " ".join(str(c) for c in self.cards),
            "type": self.type.value,
            "power": self.power,
        }

    @classmethod
    def empty_hand(cls) -> "Hand":
        """Create an empty hand (used for leading)."""
        return cls(type=HandType.EMPTY, power=0)

    @classmethod
    def invalid_hand(cls, cards: list[Card] = None) -> "Hand":
        """Create an invalid hand."""
        return cls(type=HandType.INVALID, power=-1, cards=cards or [])

    @classmethod
    def unknown_hand(cls, cards: list[Card] = None) -> "Hand":
        """Create an unknown hand."""
        return cls(type=HandType.UNKNOWN, power=-1, cards=cards or [])

    @property
    def is_empty(self) -> bool:
        return self.type == HandType.EMPTY

    @property
    def is_bomb(self) -> bool:
        return self.type == HandType.BOMB

    @property
    def is_unknown_or_invalid(self) -> bool:
        return self.type in (HandType.UNKNOWN, HandType.INVALID)

    @property
    def first(self) -> Optional[Card]:
        """Return the first card in this hand, or ``None`` when empty."""
        if not self.cards:
            return None
        return self.cards[0]

    def sort_by_natural_rank(self):
        """Sort cards by natural rank index."""
        self.cards.sort(key=lambda c: c.natural_sort_index)

    def sort_by_power_rank(self):
        """Sort cards by power rank."""
        self.cards.sort(key=lambda c: c.power_rank)

    def sublist(self, start: int, end: Optional[int] = None) -> "PokerCardList":
        """Return a sublist of cards as a PokerCardList."""
        if end is None:
            return PokerCardList(self.cards[start:])
        return PokerCardList(self.cards[start:end])

    def where(self, predicate) -> "PokerCardList":
        """Filter cards and return a PokerCardList."""
        return PokerCardList([c for c in self.cards if predicate(c)])

    def any(self, predicate) -> bool:
        """Check if any card satisfies the predicate."""
        return any(predicate(c) for c in self.cards)

    def every(self, predicate) -> bool:
        """Check if all cards satisfy the predicate."""
        return all(predicate(c) for c in self.cards)

    def add(self, card: Card) -> None:
        """Append one card, matching ``PokerCardList`` mutability."""
        self.cards.append(card)

    def add_all(self, cards) -> None:
        """Append multiple cards, matching Dart ``Hand`` as a card list."""
        self.cards.extend(cards)

    def clear(self) -> None:
        """Remove all cards."""
        self.cards.clear()

    def remove_card(self, card: Card) -> None:
        """Remove one matching card if present."""
        for i, existing in enumerate(self.cards):
            if existing == card:
                self.cards.pop(i)
                return

    def remove_cards(self, cards) -> None:
        """Remove all requested cards by multiplicity."""
        for card in cards:
            self.remove_card(card)

    def has_card(self, card: Card) -> bool:
        """Return whether this hand contains ``card``."""
        return any(existing == card for existing in self.cards)

    def has_cards(self, cards) -> bool:
        """Return whether all requested cards are present with multiplicity."""
        remaining = list(self.cards)
        for card in cards:
            for i, existing in enumerate(remaining):
                if existing == card:
                    remaining.pop(i)
                    break
            else:
                return False
        return True

    @property
    def length(self) -> int:
        return len(self.cards)

    def __str__(self) -> str:
        if self.is_empty:
            return "empty-0 :"
        cards_str = " ".join(str(c) for c in self.cards)
        return f"{self.type.value}-{self.power} : {cards_str}"

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __getitem__(self, index):
        return self.cards[index]

    def __sub__(self, other):
        """Subtract cards from this hand, returning a new PokerCardList."""
        if isinstance(other, Hand):
            other_cards = other.cards
        elif isinstance(other, PokerCardList):
            other_cards = list(other)
        elif isinstance(other, list):
            other_cards = other
        else:
            return NotImplemented
        result = list(self.cards)
        for c in other_cards:
            for i, rc in enumerate(result):
                if str(rc) == str(c):
                    result.pop(i)
                    break
        return PokerCardList(result)

    def __lt__(self, other: "Hand") -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self.power < other.power

    def __gt__(self, other: "Hand") -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self.power > other.power

    def __le__(self, other: "Hand") -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self.power <= other.power

    def __ge__(self, other: "Hand") -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self.power >= other.power

    @property
    def cards_str(self) -> str:
        """Space-separated card string for protocol messages."""
        if self.is_empty:
            return ""
        return " ".join(str(c) for c in self.cards)


def parse_hand_on_table(hand_str: str) -> Hand:
    """Parse the hand currently on the table."""
    return Hand.parse(hand_str)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

# Non-joker suits (Dart's CardSuit.nonJokerSuits)
NON_JOKER_SUITS = ["D", "C", "H", "S"]

# Map rank string to value (2→2, ..., A→14, BJ→16, RJ→17)
# Level card value is 15
LEVEL_CARD_VALUE = 15

# For converting rank value back to rank string
_RANK_VALUE_TO_NAME: dict[int, str] = {
    1: "A",  # A can also be represented as 1 (for A-2-3 straights)
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
    10: "T", 11: "J", 12: "Q", 13: "K", 14: "A",
    15: "2",  # fallback for level card (will be overwritten by level_rank)
    16: "BJ", 17: "RJ",
}


def rank_from_value(v: int) -> str:
    """Convert a rank value to its string representation.
    Values 1 and 14 both map to 'A'. Value 15 maps to '2' by default (level card fallback).
    """
    if v == 1:
        return "A"
    if v == 14:
        return "A"
    if v == 15:
        return "2"  # default level rank
    return _RANK_VALUE_TO_NAME.get(v, "2")


def rank_value_of_level_card() -> int:
    """The power value of a level card (equivalent to Dart's CardRank.rankValueOfLevelCard)."""
    return 15


def suit_char(suit_name: Optional[str]) -> Optional[str]:
    """Convert a Dart-style suit enum name to a Python suit character, or return None."""
    if suit_name is None:
        return None
    mapping = {"hearts": "H", "diamonds": "D", "clubs": "C", "spades": "S", "black": "B", "red": "R"}
    return mapping.get(suit_name.lower() if suit_name else "", suit_name)


def group_cards(cards) -> dict[str, "PokerCardList"]:
    """Group cards by rank, returning a dict mapping rank string to PokerCardList.
    Wild cards are NOT grouped (they appear in their own group under their rank).
    """
    groups: dict[str, PokerCardList] = {}
    for c in cards:
        r = c.rank
        if r not in groups:
            groups[r] = PokerCardList()
        groups[r].add(c)
    return groups


class PokerCardList:
    """A collection of cards (a player's hand)."""

    def __init__(self, cards: Optional[list[Card]] = None):
        self._cards: list[Card] = list(cards) if cards else []

    @classmethod
    def parse(cls, cards_str: str, level_rank: str = "2") -> "PokerCardList":
        """Parse a space-separated card string (e.g., '3H 4D 5C').

        Handles the "unknown : card1 card2 ..." format used by the server
        when the hand is not revealed (e.g., other players' hands in SSE).
        """
        s = (cards_str or "").strip()
        if not s:
            return cls()
        # Strip "unknown :" prefix if present
        if s.startswith("unknown :") or s.startswith("unknown:"):
            s = s.split(":", 1)[-1].strip()
            if not s:
                return cls()
        cards = [Card.parse(c.strip(), level_rank) for c in s.split() if c.strip()]
        return cls(cards)

    @classmethod
    def empty(cls) -> "PokerCardList":
        """Create an empty PokerCardList."""
        return cls()

    @classmethod
    def from_list(cls, cards: list[Card]) -> "PokerCardList":
        """Create a PokerCardList from a list of Cards (like Dart PokerCardList.from)."""
        return cls(list(cards))

    @classmethod
    def from_string(cls, s: str, level_rank: str = "2") -> "PokerCardList":
        """Alias for parse."""
        return cls.parse(s, level_rank)

    @property
    def cards(self) -> list[Card]:
        return list(self._cards)

    def __len__(self) -> int:
        return len(self._cards)

    def __bool__(self) -> bool:
        return len(self._cards) > 0

    def __getitem__(self, index):
        if isinstance(index, slice):
            return PokerCardList(self._cards[index])
        return self._cards[index]

    def __iter__(self):
        return iter(self._cards)

    def __contains__(self, item):
        if isinstance(item, Card):
            return any(str(c) == str(item) for c in self._cards)
        return False

    def __sub__(self, other):
        """Subtract cards: returns new PokerCardList with other's cards removed."""
        if isinstance(other, Hand):
            other_cards = list(other.cards)
        elif isinstance(other, PokerCardList):
            other_cards = list(other)
        elif isinstance(other, list):
            other_cards = other
        else:
            return NotImplemented
        result = list(self._cards)
        for c in other_cards:
            for i, rc in enumerate(result):
                if str(rc) == str(c):
                    result.pop(i)
                    break
        return PokerCardList(result)

    def __add__(self, other):
        """Concatenate with another PokerCardList or list of Cards."""
        if isinstance(other, PokerCardList):
            return PokerCardList(self._cards + list(other))
        elif isinstance(other, list):
            return PokerCardList(self._cards + other)
        return NotImplemented

    def __eq__(self, other):
        if not isinstance(other, PokerCardList):
            return False
        return len(self._cards) == len(other._cards) and all(
            str(a) == str(b) for a, b in zip(sorted(self._cards, key=str), sorted(other._cards, key=str))
        )

    def __str__(self) -> str:
        sorted_cards = sorted(self._cards, key=lambda c: c.power_rank)
        return " ".join(str(c) for c in sorted_cards)

    def add(self, card: Card) -> None:
        self._cards.append(card)

    def add_all(self, cards) -> None:
        """Append multiple cards to this list."""
        self._cards.extend(cards)

    def clear(self) -> None:
        """Remove all cards from this list."""
        self._cards.clear()

    def remove_card(self, card: Card) -> None:
        """Remove one card matching the given card."""
        for i, c in enumerate(self._cards):
            if str(c) == str(card):
                self._cards.pop(i)
                return

    def remove_cards(self, cards: list[Card]) -> None:
        for c in cards:
            self.remove_card(c)

    def remove_last(self) -> Card:
        """Remove and return the last card."""
        return self._cards.pop()

    def has_card(self, card: Card) -> bool:
        """Return whether this list contains ``card``."""
        return any(c == card for c in self._cards)

    def has_cards(self, cards) -> bool:
        """Return whether all requested cards are present with multiplicity."""
        remaining = list(self._cards)
        for card in cards:
            for i, existing in enumerate(remaining):
                if existing == card:
                    remaining.pop(i)
                    break
            else:
                return False
        return True

    def find_missing(self, cards) -> list[Card]:
        """Return cards from ``cards`` missing from this list by multiplicity."""
        remaining = list(self._cards)
        missing: list[Card] = []
        for card in cards:
            for i, existing in enumerate(remaining):
                if existing == card:
                    remaining.pop(i)
                    break
            else:
                missing.append(card)
        return missing

    @staticmethod
    def create_deck(level_rank: str = "2", required_players: int = 4, shuffle: bool = True) -> "PokerCardList":
        """Create the Guandan deck for ``required_players``.

        A four-player game uses two standard decks. Level-rank cards are marked
        with ``*`` so hearts of that rank become wild cards.
        """
        import random

        deck: list[Card] = []
        deck_count = round(required_players / 2)
        for _ in range(deck_count):
            for suit in NON_JOKER_SUITS:
                for rank in RANK_VALUES:
                    deck.append(Card(rank, suit, rank == level_rank))
            deck.append(Card.black_joker_card())
            deck.append(Card.red_joker_card())
        if shuffle:
            random.shuffle(deck)
        return PokerCardList(deck)

    def sublist(self, start: int, end: Optional[int] = None) -> "PokerCardList":
        """Return a sublist of cards [start:end]."""
        if end is None:
            return PokerCardList(self._cards[start:])
        return PokerCardList(self._cards[start:end])

    def index_of(self, card: Card, start: int = 0) -> int:
        """Return the first index of ``card`` or ``-1`` when not present."""
        for i in range(start, len(self._cards)):
            if self._cards[i] == card:
                return i
        return -1

    def index_where(self, predicate, start: int = 0) -> int:
        """Return the first index matching ``predicate`` or ``-1``."""
        for i in range(start, len(self._cards)):
            if predicate(self._cards[i]):
                return i
        return -1

    def count(self, predicate) -> int:
        """Count cards satisfying ``predicate``."""
        return sum(1 for card in self._cards if predicate(card))

    def shuffle(self) -> None:
        """Shuffle cards in place."""
        import random

        random.shuffle(self._cards)

    def sort_by_power(self, reverse: bool = False) -> None:
        """Sort cards by power rank (ascending by default)."""
        self._cards.sort(key=lambda c: c.power_with_level, reverse=reverse)

    def sort_by_power_rank(self, reverse: bool = False) -> None:
        """Sort cards by power rank (same as sort_by_power)."""
        self.sort_by_power(reverse=reverse)

    def sort_by_natural_rank(self) -> None:
        """Sort cards by natural rank (A first, then 2,3,...,K,A)."""
        self._cards.sort(key=lambda c: c.natural_sort_index)

    def where(self, predicate) -> "PokerCardList":
        """Filter cards, returning a new PokerCardList."""
        return PokerCardList([c for c in self._cards if predicate(c)])

    def any(self, predicate) -> bool:
        """Check if any card satisfies the predicate."""
        return any(predicate(c) for c in self._cards)

    def every(self, predicate) -> bool:
        """Check if all cards satisfy the predicate."""
        return all(predicate(c) for c in self._cards)

    @property
    def first(self) -> Optional[Card]:
        """Return the first card."""
        return self._cards[0] if self._cards else None

    @property
    def is_empty(self) -> bool:
        return len(self._cards) == 0

    @property
    def length(self) -> int:
        return len(self._cards)

    def find_cards_by_rank(self, rank: str) -> list[Card]:
        """Find all cards with the given rank."""
        return [c for c in self._cards if c.rank == rank]

    def find_lowest_single(self) -> Optional[Card]:
        """Return the lowest non-wild card."""
        non_wild = [c for c in self._cards if not c.is_wild]
        if not non_wild:
            return self._cards[0] if self._cards else None
        return min(non_wild, key=lambda c: c.power_with_level)

    def find_highest(self) -> Optional[Card]:
        """Return the highest power card."""
        if not self._cards:
            return None
        return max(self._cards, key=lambda c: c.power_with_level)

    def find_highest_non_wild(self) -> Optional[Card]:
        """Return the highest power card that is not a wild card."""
        non_wild = [c for c in self._cards if not c.is_wild]
        if not non_wild:
            return self._cards[0] if self._cards else None
        return max(non_wild, key=lambda c: c.power_with_level)

    def find_hand_to_beat(self, hand_on_table: Hand, level_rank: str = "2") -> Hand:
        """Find cards that can beat the hand on table. Returns empty hand if passing."""
        if hand_on_table.is_empty:
            # We're leading — play the lowest single card
            card = self.find_lowest_single()
            if card is None:
                return Hand()
            return Hand(type=HandType.SINGLE, power=card.power_with_level, cards=[card])

        # Separate wild cards (hearts of level rank) from regular cards.
        wild_cards = [c for c in self._cards if c.is_wild]

        # Group non-wild, non-joker cards by literal rank.
        by_rank: dict[str, list[Card]] = {}
        for c in self._cards:
            if not c.is_wild:
                by_rank.setdefault(c.rank, []).append(c)

        # Helper: total cards available for a rank (regular + wilds).
        # Wilds can only substitute for non-joker ranks.
        def _total(rank: str, group: list[Card]) -> int:
            if rank in ("BJ", "RJ"):
                return len(group)
            return len(group) + len(wild_cards)

        # Helper: build a card list for a target count, using regular cards
        # first and then wild cards to fill the gap.
        def _fill(group: list[Card], needed: int) -> list[Card]:
            if len(group) >= needed:
                return group[:needed]
            result = list(group)
            extra = needed - len(group)
            result.extend(wild_cards[:extra])
            return result

        # -----------------------------------------------------------------
        # Same-type matching: only attempt for simple rank-based types
        # (single, pair, triple).
        # -----------------------------------------------------------------
        if hand_on_table.type in (HandType.SINGLE, HandType.PAIR, HandType.TRIPLE):
            needed = hand_on_table.type.size
            for rank, group in sorted(by_rank.items(), key=lambda kv: rank_power(kv[0])):
                if _total(rank, group) >= needed:
                    power = rank_power(rank)
                    if power > hand_on_table.power:
                        return Hand(
                            type=hand_on_table.type,
                            power=power,
                            cards=_fill(group, needed),
                        )

        # -----------------------------------------------------------------
        # Bomb-vs-bomb: need a higher bomb (more cards or higher rank).
        # -----------------------------------------------------------------
        if hand_on_table.is_bomb:
            target_len = len(hand_on_table.cards)
            for rank, group in sorted(by_rank.items(), key=lambda kv: rank_power(kv[0])):
                total = _total(rank, group)
                if total >= target_len:
                    power = rank_power(rank)
                    if total > target_len or power > hand_on_table.power:
                        return Hand(
                            type=HandType.BOMB,
                            power=power,
                            cards=_fill(group, target_len),
                        )
            # Check for larger bombs.
            for bomb_size in range(target_len + 1, len(self._cards) + 1):
                for rank, group in sorted(by_rank.items(), key=lambda kv: rank_power(kv[0])):
                    if _total(rank, group) >= bomb_size:
                        return Hand(
                            type=HandType.BOMB,
                            power=rank_power(rank),
                            cards=_fill(group, bomb_size),
                        )

        # -----------------------------------------------------------------
        # Any bomb beats a non-bomb (straight, tube, plate, full house, etc.).
        # Count wild cards toward bomb formation (e.g. 3×T + 1 wild = bomb).
        # -----------------------------------------------------------------
        if not hand_on_table.is_bomb:
            # Check regular-rank groups supplemented by wild cards.
            for rank, group in sorted(by_rank.items(), key=lambda kv: rank_power(kv[0])):
                if _total(rank, group) >= 4:
                    return Hand(
                        type=HandType.BOMB,
                        power=rank_power(rank),
                        cards=_fill(group, 4),
                    )
            # Pure-wild bomb: 4+ wild cards alone form a bomb of level rank.
            if len(wild_cards) >= 4:
                return Hand(
                    type=HandType.BOMB,
                    power=LEVEL_CARD_VALUE,
                    cards=wild_cards[:4],
                )

        # Can't beat — pass
        return Hand()

    def __str__(self) -> str:
        sorted_cards = sorted(self._cards, key=lambda c: c.power_with_level)
        return " ".join(str(c) for c in sorted_cards)
