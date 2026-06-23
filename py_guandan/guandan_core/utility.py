"""Utility functions for hand analysis in Guandan.

Ported from guandan_core/lib/src/utility.dart.
"""

from __future__ import annotations

from typing import Optional

from .cards import (
    LEVEL_CARD_VALUE,
    NON_JOKER_SUITS,
    Card,
    Hand,
    HandType,
    PokerCardList,
    group_cards,
    rank_from_value,
    rank_power,
    rank_value_of_level_card,
)


# =============================================================================
# Card counting and string helpers
# =============================================================================

def count_cards(cards, rank: str, suit: Optional[str] = None,
                exclude_wild_card: bool = True) -> int:
    count = 0
    for card in cards:
        if card.rank != rank:
            continue
        if suit is not None and card.suit != suit:
            continue
        if exclude_wild_card and card.is_wild:
            continue
        count += 1
    return count


def cards_from_string(string_of_cards: str, level_rank: str = "2") -> list[Card]:
    if not string_of_cards.strip():
        return []
    cards = []
    for token in string_of_cards.split():
        if not token:
            continue
        cards.append(Card.parse(token, level_rank))
    return cards


def cards_to_string(cards) -> str:
    return " ".join(str(c) for c in cards)


# =============================================================================
# Card extraction helpers
# =============================================================================

def separate_wild_cards(cards) -> list[PokerCardList]:
    wild_cards = PokerCardList([c for c in cards if c.is_wild])
    regular_cards = PokerCardList([c for c in cards if not c.is_wild])
    return [wild_cards, regular_cards]


def extract_regular_cards(cards) -> PokerCardList:
    if isinstance(cards, PokerCardList):
        return cards.where(lambda c: not c.is_wild)
    return PokerCardList([c for c in cards if not c.is_wild])


def extract_wild_cards(cards) -> PokerCardList:
    if isinstance(cards, PokerCardList):
        return cards.where(lambda c: c.is_wild)
    return PokerCardList([c for c in cards if c.is_wild])


# =============================================================================
# Bomb power functions
# =============================================================================

def get_non_joker_bomb_power(major: int, minor: int) -> int:
    return major * 100 + minor


def max_non_joker_bomb_power(number_of_decks: int) -> int:
    return get_non_joker_bomb_power(5 * number_of_decks + 1, rank_value_of_level_card())


def get_joker_bomb_power(number_of_decks: int) -> int:
    return max_non_joker_bomb_power(number_of_decks) * 10


def get_bomb_power(m: int, rank: int, number_of_decks: int,
                   straight_flush: bool, joker_bomb: bool) -> int:
    if joker_bomb:
        return get_joker_bomb_power(number_of_decks)
    if straight_flush:
        return get_non_joker_bomb_power(6, rank)
    if m <= 5:
        return get_non_joker_bomb_power(m, rank)
    return get_non_joker_bomb_power(m + 1, rank)


# =============================================================================
# SeriesResult and find_series
# =============================================================================

class SeriesResult:
    def __init__(self, is_valid: bool, wild_cards_used: int, series_length: int,
                 series: PokerCardList, start_rank_value: int):
        self.is_valid = is_valid
        self.wild_cards_used = wild_cards_used
        self.series_length = series_length
        self.series = series
        self.start_rank_value = start_rank_value

    def to_hand(self, level_rank: str) -> Hand:
        if not self.is_valid:
            return Hand.invalid_hand(self.series.cards)

        cards = PokerCardList.from_list(self.series.cards)
        if self.wild_cards_used > 0:
            for _ in range(self.wild_cards_used):
                cards.add(Card.wild_card(level_rank))

        hand_type = HandType.UNKNOWN
        power = -1

        if self.series_length == 5:
            hand_type = HandType.STRAIGHT
            power = self.start_rank_value
            check_result = check_straight_flush(cards)
            if check_result.valid:
                hand_type = HandType.BOMB
                power = check_result.power

        if self.series_length == 3:
            hand_type = HandType.TUBE
            power = self.start_rank_value

        if self.series_length == 2:
            hand_type = HandType.PLATE
            power = self.start_rank_value

        if self.series_length == 1 and len(self.series) == 3:
            hand_type = HandType.TRIPLE
            power = self.start_rank_value

        if self.series_length == 1 and len(self.series) == 2:
            hand_type = HandType.PAIR
            power = self.start_rank_value

        if self.series_length == 1 and len(self.series) == 1:
            hand_type = HandType.SINGLE
            power = self.series[0].power_rank

        if hand_type == HandType.UNKNOWN:
            if len(self.series) >= 4:
                check_result = check_bomb(cards)
                if check_result.valid:
                    hand_type = HandType.BOMB
                    power = check_result.power

        return Hand(cards.cards, hand_type, power=power)


def find_series(cards, start_rank_value: int, series_length: int,
                wild_cards_available: int, count_of_each_rank: int,
                suit: Optional[str] = None) -> SeriesResult:
    assert start_rank_value > 0 and start_rank_value + series_length - 1 <= 14

    series = PokerCardList.empty()
    cards_lacking = 0

    for k in range(start_rank_value, start_rank_value + series_length):
        r = rank_from_value(k)
        cards_lacking += max(count_of_each_rank -
                             count_cards(cards, r, suit, exclude_wild_card=True), 0)

    if cards_lacking > wild_cards_available:
        return SeriesResult(is_valid=False, wild_cards_used=0,
                            series_length=series_length,
                            series=PokerCardList.empty(), start_rank_value=0)

    wild_cards_used = cards_lacking
    for k in range(start_rank_value, start_rank_value + series_length):
        r = rank_from_value(k)
        j = 0
        for c in cards:
            if c.rank == r and (suit is None or c.suit == suit) and not c.is_wild:
                if j < count_of_each_rank:
                    series.add(c)
                    j += 1

    return SeriesResult(is_valid=True, wild_cards_used=wild_cards_used,
                        series_length=series_length, series=series,
                        start_rank_value=start_rank_value)


# =============================================================================
# Hand type checking
# =============================================================================

class HandTypeCheckResult:
    def __init__(self, valid: bool, power: int, series_start_rank_value: Optional[int] = None):
        self.valid = valid
        self.power = power
        self.series_start_rank_value = series_start_rank_value

    @classmethod
    def invalid_result(cls) -> "HandTypeCheckResult":
        return cls(False, -1)


def check_single(cards: PokerCardList) -> HandTypeCheckResult:
    if len(cards) != 1:
        return HandTypeCheckResult.invalid_result()
    return HandTypeCheckResult(True, cards[0].power_rank)


def is_single(cards: PokerCardList) -> bool:
    return check_single(cards).valid


def check_pair(cards: PokerCardList, wild_as_regular: bool = False) -> HandTypeCheckResult:
    if len(cards) != 2:
        return HandTypeCheckResult.invalid_result()

    if cards[0].rank == cards[1].rank:
        return HandTypeCheckResult(True, cards[0].power_rank)

    if not wild_as_regular:
        separated = separate_wild_cards(cards)
        wild = separated[0]
        regular = separated[1]
        if len(wild) > 0:
            if len(regular) == 0:
                return HandTypeCheckResult(True, wild[0].power_rank)
            else:
                return HandTypeCheckResult(not regular[0].is_joker, regular[0].power_rank)

    return HandTypeCheckResult.invalid_result()


def is_pair(cards: PokerCardList, wild_as_regular: bool = False) -> bool:
    return check_pair(cards, wild_as_regular=wild_as_regular).valid


def check_triple(cards: PokerCardList, wild_as_regular: bool = False) -> HandTypeCheckResult:
    if len(cards) != 3:
        return HandTypeCheckResult.invalid_result()

    if cards[0].rank == cards[1].rank == cards[2].rank:
        return HandTypeCheckResult(True, cards[0].power_rank)

    if not wild_as_regular:
        separated = separate_wild_cards(cards)
        wild = separated[0]
        regular = separated[1]
        if len(regular) == 0:
            return HandTypeCheckResult(True, wild[0].power_rank)

        r = regular[0].rank
        if regular.every(lambda c: c.rank == r):
            if not regular[0].is_joker:
                return HandTypeCheckResult(True, regular[0].power_rank)
            else:
                if len(wild) == 0:
                    return HandTypeCheckResult(True, regular[0].power_rank)
                else:
                    return HandTypeCheckResult.invalid_result()

    return HandTypeCheckResult.invalid_result()


def is_triple(cards: PokerCardList, wild_as_regular: bool = False) -> bool:
    return check_triple(cards, wild_as_regular=wild_as_regular).valid


def check_full_house(cards: PokerCardList) -> HandTypeCheckResult:
    if len(cards) != 5:
        return HandTypeCheckResult.invalid_result()

    cards.sort_by_natural_rank()

    triple_result = check_triple(cards.sublist(0, 3), wild_as_regular=True)
    if triple_result.valid and check_pair(cards.sublist(3), wild_as_regular=True).valid:
        return HandTypeCheckResult(True, triple_result.power)

    triple_result = check_triple(cards.sublist(2))
    if check_pair(cards.sublist(0, 2)).valid and triple_result.valid:
        return HandTypeCheckResult(True, triple_result.power)

    separated = separate_wild_cards(cards)
    wild = separated[0]
    regular = separated[1]

    regular.sort_by_power_rank()

    if len(regular) > 4:
        return HandTypeCheckResult.invalid_result()

    if len(regular) == 0:
        return HandTypeCheckResult(True, wild[0].power_rank)

    if len(wild) > 0:
        if len(regular) == 1:
            if regular[0].is_joker:
                return HandTypeCheckResult.invalid_result()
            else:
                return HandTypeCheckResult(True, regular[0].power_rank)

        if len(regular) == 2:
            if regular[0].rank == regular[1].rank:
                return HandTypeCheckResult(True, wild[0].power_rank)
            elif regular[0].is_joker or regular[1].is_joker:
                return HandTypeCheckResult.invalid_result()
            else:
                return HandTypeCheckResult(True, regular[1].power_rank)

        if len(regular) == 3:
            if regular[0].rank == regular[1].rank == regular[2].rank:
                return HandTypeCheckResult(True, regular[0].power_rank)
            elif regular[0].rank != regular[1].rank and regular[1].rank != regular[2].rank:
                return HandTypeCheckResult.invalid_result()
            elif regular[0].is_joker:
                return HandTypeCheckResult.invalid_result()
            elif regular[2].is_joker:
                return HandTypeCheckResult(True, regular[0].power_rank)
            else:
                return HandTypeCheckResult(True, regular[2].power_rank)

        if len(regular) == 4:
            black_jokers = regular.where(lambda c: c.is_black_joker)
            red_jokers = regular.where(lambda c: c.is_red_joker)
            m = len(black_jokers)
            n = len(red_jokers)

            if m == 1 or n == 1 or m + n == 4 or (m == 2 and n == 2):
                return HandTypeCheckResult.invalid_result()

            if m == 3:
                return HandTypeCheckResult(True, black_jokers[0].power_rank)
            if n == 3:
                return HandTypeCheckResult(True, red_jokers[0].power_rank)

            if regular[0].rank == regular[1].rank == regular[2].rank:
                return HandTypeCheckResult(True, regular[0].power_rank)
            if regular[1].rank == regular[2].rank == regular[3].rank:
                return HandTypeCheckResult(True, regular[3].power_rank)
            if regular[0].rank == regular[1].rank and regular[2].rank == regular[3].rank:
                return HandTypeCheckResult(True, regular[0].power_rank if m == 2 or n == 2 else regular[3].power_rank)

    return HandTypeCheckResult.invalid_result()


def is_full_house(cards: PokerCardList) -> bool:
    return check_full_house(cards).valid


def check_plate(cards: PokerCardList) -> HandTypeCheckResult:
    if len(cards) != 6:
        return HandTypeCheckResult.invalid_result()

    cards.sort_by_natural_rank()

    if cards.any(lambda c: c.is_joker):
        return HandTypeCheckResult.invalid_result()

    triple1 = check_triple(cards.sublist(0, 3), wild_as_regular=True)
    triple2 = check_triple(cards.sublist(3, 6), wild_as_regular=True)
    if triple1.valid and triple2.valid:
        rank1 = rank_power(cards[0].rank)
        rank2 = rank_power(cards[3].rank)

        if abs(rank2 - rank1) == 1:
            power = rank1 if rank2 > rank1 else rank2
            return HandTypeCheckResult(True, power, series_start_rank_value=power)

        if cards[3].rank == "A" and cards[0].rank == "2":
            return HandTypeCheckResult(True, 1, series_start_rank_value=1)

    separated = separate_wild_cards(cards)
    wild = separated[0]
    regular = separated[1]
    if len(regular) == 0:
        return HandTypeCheckResult(True, wild[0].power_rank,
                                   series_start_rank_value=wild[0].power_rank)

    def _is_valid_plate_with_wild_cards(reg: PokerCardList, wild_cards_available: int,
                                        start_rank_value: int) -> bool:
        wild_cards_needed = 0
        for r in range(start_rank_value, start_rank_value + 2):
            c = count_cards(reg, rank_from_value(r), None)
            if c >= 4:
                return False
            wild_cards_needed += 3 - c
        return wild_cards_needed == len(wild)

    regular.sort_by_natural_rank()
    start_rank_value = rank_power(regular.first.rank)
    end_rank_value = rank_power(regular.cards[-1].rank)
    if (end_rank_value - start_rank_value) >= 2:
        if regular.cards[-1].rank == "A" and regular.first.rank == "2":
            if _is_valid_plate_with_wild_cards(regular, len(wild), 1):
                return HandTypeCheckResult(True, 1, series_start_rank_value=1)
        return HandTypeCheckResult.invalid_result()

    if _is_valid_plate_with_wild_cards(regular, len(wild), start_rank_value):
        return HandTypeCheckResult(True, start_rank_value,
                                   series_start_rank_value=start_rank_value)

    return HandTypeCheckResult.invalid_result()


def is_plate(cards: PokerCardList) -> bool:
    return check_plate(cards).valid


def check_tube(cards: PokerCardList) -> HandTypeCheckResult:
    if len(cards) != 6:
        return HandTypeCheckResult.invalid_result()

    if cards.any(lambda c: c.is_joker):
        return HandTypeCheckResult.invalid_result()

    separated = separate_wild_cards(cards)
    wild = separated[0]
    regular = separated[1]
    regular.sort_by_natural_rank()

    if len(regular) == 0:
        return HandTypeCheckResult(True, 12, series_start_rank_value=12)

    ret = find_series(cards, min(regular[0].power, 12), 3, len(wild), 2)
    if ret.is_valid:
        power = min(ret.start_rank_value, 12)
        return HandTypeCheckResult(True, power, series_start_rank_value=power)

    ret = find_series(cards, 1, 3, len(wild), 2)
    if ret.is_valid:
        return HandTypeCheckResult(True, 1, series_start_rank_value=1)

    return HandTypeCheckResult.invalid_result()


def is_tube(cards: PokerCardList) -> bool:
    return check_tube(cards).valid


def check_straight(cards) -> HandTypeCheckResult:
    if len(cards) != 5:
        return HandTypeCheckResult.invalid_result()

    if cards.any(lambda c: c.is_joker):
        return HandTypeCheckResult.invalid_result()

    separated = separate_wild_cards(cards)
    wild = separated[0]
    regular = separated[1]
    regular.sort_by_natural_rank()

    if len(regular) == 0:
        return HandTypeCheckResult(True, 10, series_start_rank_value=10)

    ret = find_series(cards, min(regular[0].power, 10), 5, len(wild), 1)
    if ret.is_valid:
        return HandTypeCheckResult(True, ret.start_rank_value,
                                   series_start_rank_value=ret.start_rank_value)

    ret = find_series(cards, 1, 5, len(wild), 1)
    if ret.is_valid:
        return HandTypeCheckResult(True, 1, series_start_rank_value=1)

    return HandTypeCheckResult.invalid_result()


def is_straight(cards: PokerCardList) -> bool:
    return check_straight(cards).valid


def check_straight_flush(cards) -> HandTypeCheckResult:
    s = check_straight(cards)
    if s.valid:
        regular_cards = extract_regular_cards(cards)
        if regular_cards.every(lambda c: c.suit == regular_cards[0].suit):
            return HandTypeCheckResult(True, get_non_joker_bomb_power(6, s.power),
                                       series_start_rank_value=s.series_start_rank_value)
    return HandTypeCheckResult.invalid_result()


def is_straight_flush(cards) -> bool:
    return check_straight_flush(cards).valid


def check_bomb(cards: PokerCardList, number_of_decks: int = 2) -> HandTypeCheckResult:
    if len(cards) < 4:
        return HandTypeCheckResult.invalid_result()

    jokers = cards.where(lambda c: c.is_joker)
    if len(jokers) == len(cards) and len(jokers) == number_of_decks * 2:
        return HandTypeCheckResult(True, get_joker_bomb_power(number_of_decks))

    if len(jokers) > 0:
        return HandTypeCheckResult.invalid_result()

    regular_cards = extract_regular_cards(cards)

    if len(regular_cards) == 0:
        if len(cards) == 5:
            return HandTypeCheckResult(True, get_non_joker_bomb_power(6, 14))
        else:
            major = len(cards) + (0 if len(cards) <= 5 else 1)
            return HandTypeCheckResult(True, get_non_joker_bomb_power(major, rank_value_of_level_card()))

    if regular_cards.every(lambda c: c.rank == regular_cards[0].rank):
        major = len(cards) + (0 if len(cards) <= 5 else 1)
        return HandTypeCheckResult(True, get_non_joker_bomb_power(major, regular_cards[0].power_rank))

    sf = check_straight_flush(cards)
    if sf.valid:
        return HandTypeCheckResult(True, sf.power)

    return HandTypeCheckResult.invalid_result()


def is_bomb(cards: PokerCardList, number_of_decks: int = 2) -> bool:
    return check_bomb(cards, number_of_decks=number_of_decks).valid


def is_joker_bomb(cards: PokerCardList, number_of_decks: int = 2) -> bool:
    b = check_bomb(cards, number_of_decks=number_of_decks)
    if b.valid:
        return b.power == get_joker_bomb_power(number_of_decks)
    return False


# =============================================================================
# Find functions
# =============================================================================

def find_tubes(cards: PokerCardList, level_rank: str,
               find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    tubes = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    for start_rank_value in range(1, 13):
        if start_rank_value <= resolved_target_power:
            continue
        result = find_series(cards, start_rank_value, 3, wild_cards_available, 2)
        if result.is_valid:
            tubes.append(result.to_hand(level_rank))
        if not find_all and tubes:
            return [tubes[0]]
    if not find_all and tubes:
        tubes.sort(key=lambda h: h.power)
        return [tubes[0]]
    return tubes


def find_plates(cards: PokerCardList, level_rank: str,
                find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    plates = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    for start_rank_value in range(1, 14):
        if start_rank_value <= resolved_target_power:
            continue
        result = find_series(cards, start_rank_value, 2, wild_cards_available, 3)
        if result.is_valid:
            plates.append(result.to_hand(level_rank))
        if not find_all and plates:
            return [plates[0]]
    if not find_all and plates:
        plates.sort(key=lambda h: h.power)
        return [plates[0]]
    return plates


def find_straights(cards: PokerCardList, level_rank: str,
                   find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    straights = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    for start_rank_value in range(1, 11):
        if start_rank_value <= resolved_target_power:
            continue
        result = find_series(regular_cards, start_rank_value, 5, wild_cards_available, 1)
        if result.is_valid:
            straights.append(result.to_hand(level_rank))
        if not find_all and straights:
            return [straights[0]]
    if not find_all and straights:
        straights.sort(key=lambda h: h.power)
        return [straights[0]]
    return straights


def find_straight_flushes(cards: PokerCardList, level_rank: str,
                          find_all: bool = False) -> list[Hand]:
    straight_flushes = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    for start_rank_value in range(1, 11):
        for suit in NON_JOKER_SUITS:
            result = find_series(cards, start_rank_value, 5, wild_cards_available, 1, suit=suit)
            if result.is_valid:
                hand = result.to_hand(level_rank)
                check_result = check_straight_flush(hand)
                if check_result.valid:
                    straight_flushes.append(Hand(hand.cards, HandType.BOMB, power=check_result.power))
            if not find_all and straight_flushes:
                break
        if not find_all and straight_flushes:
            break
    return straight_flushes


def find_triples(cards: PokerCardList, level_rank: str,
                 find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    triples = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)

    for group in grouped:
        if group[0].power_rank <= resolved_target_power:
            continue
        if len(group) >= 3:
            triples.append(Hand(group.cards[:3], HandType.TRIPLE, power=group[0].power_rank))
        elif len(group) == 2 and not group[0].is_joker and wild_cards_available >= 1:
            triples.append(Hand(group.cards + [Card.wild_card(level_rank)],
                                HandType.TRIPLE, power=group[0].power_rank))
        elif len(group) == 1 and not group[0].is_joker and wild_cards_available >= 2:
            triples.append(Hand(group.cards + [Card.wild_card(level_rank), Card.wild_card(level_rank)],
                                HandType.TRIPLE, power=group[0].power_rank))
        if not find_all and triples:
            return [triples[0]]

    if wild_cards_available >= 3:
        triples.append(Hand([Card.wild_card(level_rank), Card.wild_card(level_rank),
                              Card.wild_card(level_rank)], HandType.TRIPLE,
                             power=rank_value_of_level_card()))

    if not find_all and triples:
        triples.sort(key=lambda h: h.power)
        return [triples[0]]
    return triples


def find_pairs(cards: PokerCardList, level_rank: str,
               find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    pairs = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)
    resolved_target_power = target_power if target_power is not None else -1

    for group in grouped:
        if group[0].power_rank <= resolved_target_power:
            continue
        if len(group) >= 2:
            pairs.append(Hand(group.cards[:2], HandType.PAIR, power=group[0].power_rank))
        elif len(group) == 1 and not group[0].is_joker and wild_cards_available >= 1 \
                and group[0].power_rank > resolved_target_power:
            pairs.append(Hand(group.cards + [Card.wild_card(level_rank)],
                              HandType.PAIR, power=group[0].power_rank))

    if wild_cards_available >= 2 and rank_value_of_level_card() > resolved_target_power:
        pairs.append(Hand([Card.wild_card(level_rank), Card.wild_card(level_rank)],
                           HandType.PAIR, power=rank_value_of_level_card()))

    if not find_all and pairs:
        pairs.sort(key=lambda h: h.power)
        return [pairs[0]]
    return pairs


def find_full_houses(cards: PokerCardList, level_rank: str,
                     find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    full_houses = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    black_jokers = cards.where(lambda c: c.rank == "BJ")
    red_jokers = cards.where(lambda c: c.rank == "RJ")

    for triple_rank_value in range(2, 18):
        if triple_rank_value == rank_value_of_level_card():
            continue
        if triple_rank_value <= resolved_target_power:
            continue

        wild_cards_used = 0
        cards_of_triple = None
        triple_rank_str = rank_from_value(triple_rank_value)

        if triple_rank_str == "BJ":
            if len(black_jokers) >= 3:
                cards_of_triple = PokerCardList.from_list(black_jokers.cards[:3])
        elif triple_rank_str == "RJ":
            if len(red_jokers) >= 3:
                cards_of_triple = PokerCardList.from_list(red_jokers.cards[:3])
        else:
            triple = find_series(regular_cards, triple_rank_value, 1, wild_cards_available, 3)
            if triple.is_valid:
                cards_of_triple = PokerCardList.from_list(triple.to_hand(level_rank).cards)
                wild_cards_used = triple.wild_cards_used

        if cards_of_triple is not None:
            remaining_cards = cards - cards_of_triple
            for pair_rank_value in range(1, 14):
                if pair_rank_value == triple_rank_value:
                    continue
                pair = find_series(remaining_cards, pair_rank_value, 1,
                                   wild_cards_available - wild_cards_used, 2)
                if pair.is_valid:
                    hand = Hand(cards_of_triple.cards + pair.to_hand(level_rank).cards,
                                HandType.FULL_HOUSE, power=triple_rank_value)
                    full_houses.append(hand)
                    if not find_all and full_houses:
                        return [full_houses[0]]

            if find_all or not full_houses:
                if len(black_jokers) >= 2 and triple_rank_value != 16:
                    hand = Hand(cards_of_triple.cards + black_jokers.cards[:2],
                                HandType.FULL_HOUSE, power=triple_rank_value)
                    full_houses.append(hand)

            if find_all or not full_houses:
                if len(red_jokers) >= 2 and triple_rank_value != 17:
                    hand = Hand(cards_of_triple.cards + red_jokers.cards[:2],
                                HandType.FULL_HOUSE, power=triple_rank_value)
                    full_houses.append(hand)

    if not find_all and full_houses:
        full_houses.sort(key=lambda h: h.power)
        return [full_houses[0]]
    return full_houses


def find_singles(cards: PokerCardList, level_rank: str,
                 find_all: bool = False, target_power: Optional[int] = None) -> list[Hand]:
    resolved_target_power = target_power if target_power is not None else -1
    hands = [Hand([card], HandType.SINGLE, power=card.power_rank)
             for card in cards if card.power_rank > resolved_target_power]
    if find_all or not hands:
        return hands
    hands.sort(key=lambda h: h.power)
    return [hands[0]] if hands else []


def find_bombs(cards: PokerCardList, level_rank: str,
               find_all: bool = False, include_straight_flush: bool = False,
               number_of_standard_decks: int = 2,
               target_power: Optional[int] = None) -> list[Hand]:
    bombs = []
    regular_cards = extract_regular_cards(cards)
    wild_cards_available = len(cards) - len(regular_cards)
    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)

    for group in grouped:
        if group[0].is_joker:
            continue
        for w in range(wild_cards_available + 1):
            if len(group) + w >= 4:
                bomb_cards = group.cards + [Card.wild_card(level_rank) for _ in range(w)]
                bomb_power = get_bomb_power(len(group) + w, group.cards[0].power_rank,
                                            number_of_standard_decks, False, False)
                bombs.append(Hand(bomb_cards, HandType.BOMB, power=bomb_power))

    black_jokers = cards.where(lambda c: c.rank == "BJ")
    red_jokers = cards.where(lambda c: c.rank == "RJ")
    if len(black_jokers) == number_of_standard_decks and len(red_jokers) == number_of_standard_decks:
        bomb_cards = ([Card.red_joker_card() for _ in range(number_of_standard_decks)] +
                       [Card.black_joker_card() for _ in range(number_of_standard_decks)])
        bombs.append(Hand(bomb_cards, HandType.BOMB, power=get_joker_bomb_power(number_of_standard_decks)))

    if include_straight_flush:
        straight_flushes = find_straight_flushes(cards, level_rank, find_all=True)
        bombs.extend(straight_flushes)

    if target_power is not None:
        bombs = [h for h in bombs if h.power > target_power]

    if not find_all and bombs:
        bombs.sort(key=lambda h: h.power)
        return [bombs[0]]
    return bombs


def find_hands(cards: PokerCardList, level_rank: str, hand_type: HandType,
               find_all: bool = False, include_straight_flush: bool = False,
               number_of_standard_decks: int = 2,
               target_power: Optional[int] = None) -> list[Hand]:
    if hand_type == HandType.SINGLE:
        return find_singles(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.PAIR:
        return find_pairs(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.TRIPLE:
        return find_triples(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.STRAIGHT:
        return find_straights(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.TUBE:
        return find_tubes(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.PLATE:
        return find_plates(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.FULL_HOUSE:
        return find_full_houses(cards, level_rank, find_all=find_all, target_power=target_power)
    elif hand_type == HandType.BOMB:
        return find_bombs(cards, level_rank, find_all=find_all,
                          include_straight_flush=include_straight_flush,
                          number_of_standard_decks=number_of_standard_decks,
                          target_power=target_power)
    return []


# =============================================================================
# Deduce hand type and can_play
# =============================================================================

def deduce_hand_type(cards, deck_count: int = 2, forced: bool = False) -> Hand:
    if not forced:
        if isinstance(cards, Hand) and not cards.is_unknown_or_invalid and cards.power >= 0:
            return cards

    def _create_new_hand(hand_or_cards, ht: HandType, p: int) -> Hand:
        if isinstance(hand_or_cards, Hand):
            hand_or_cards.type = ht
            hand_or_cards.power = p
            return hand_or_cards
        elif isinstance(hand_or_cards, PokerCardList):
            return Hand(hand_or_cards.cards, ht, power=p)
        elif isinstance(hand_or_cards, list):
            return Hand(hand_or_cards, ht, power=p)
        raise TypeError("cards must be Hand, PokerCardList, or list[Card]")

    if isinstance(cards, (PokerCardList, list)):
        card_list = PokerCardList(list(cards)) if isinstance(cards, list) else cards
    else:
        card_list = cards if isinstance(cards, PokerCardList) else PokerCardList(list(cards))

    if len(card_list) == 0:
        return _create_new_hand(cards, HandType.EMPTY, 0)

    result = check_bomb(card_list, number_of_decks=deck_count)
    if result.valid:
        return _create_new_hand(cards, HandType.BOMB, result.power)

    result = check_straight_flush(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.BOMB, result.power)

    result = check_straight(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.STRAIGHT, result.power)

    result = check_full_house(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.FULL_HOUSE, result.power)

    result = check_tube(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.TUBE, result.power)

    result = check_plate(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.PLATE, result.power)

    result = check_triple(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.TRIPLE, result.power)

    result = check_pair(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.PAIR, result.power)

    result = check_single(card_list)
    if result.valid:
        return _create_new_hand(cards, HandType.SINGLE, result.power)

    return _create_new_hand(cards, HandType.INVALID, -1)


def can_play(hand_or_cards_to_play, hand_on_table: Hand,
             allow_empty_hand: bool = False, number_of_decks: int = 2,
             forced: bool = False) -> bool:
    if hand_on_table.is_unknown_or_invalid:
        hand_on_table = deduce_hand_type(hand_on_table, deck_count=number_of_decks, forced=forced)

    if hand_on_table.is_unknown_or_invalid:
        return False

    hand_to_play = deduce_hand_type(hand_or_cards_to_play, deck_count=number_of_decks, forced=forced)
    if hand_to_play.is_unknown_or_invalid:
        return False

    if hand_to_play.type == HandType.EMPTY:
        return allow_empty_hand

    if hand_on_table.type == HandType.EMPTY:
        return True

    if hand_to_play.type == HandType.BOMB:
        return hand_to_play.power > hand_on_table.power

    if hand_on_table.type == HandType.BOMB:
        return False

    if hand_on_table.type == HandType.TUBE and hand_to_play.type == HandType.PLATE:
        check_tube_result = check_tube(hand_to_play)
        if check_tube_result.valid and check_tube_result.power > hand_on_table.power:
            return True

    if hand_on_table.type == HandType.PLATE and hand_to_play.type == HandType.TUBE:
        check_plate_result = check_plate(hand_to_play)
        if check_plate_result.valid and check_plate_result.power > hand_on_table.power:
            return True

    return hand_to_play.type == hand_on_table.type and hand_to_play.power > hand_on_table.power


# =============================================================================
# Hand rank, filtering, min/max
# =============================================================================

def rank_of_hand(hand: Hand, level_rank: str, number_of_decks: int = 2) -> Optional[str]:
    if hand.type in (HandType.SINGLE, HandType.PAIR, HandType.TRIPLE,
                      HandType.FULL_HOUSE, HandType.TUBE, HandType.PLATE):
        if hand.power == rank_value_of_level_card():
            return level_rank
        return rank_from_value(hand.power)

    if hand.type == HandType.BOMB:
        if hand.power == get_joker_bomb_power(number_of_decks):
            return "BJ"
        if len(hand.cards) == 5:
            b = check_straight(hand)
            if b.valid:
                return rank_from_value(b.power)
        regular = extract_regular_cards(hand)
        if len(regular) > 0:
            return regular[0].rank

    return None


def filter_hands(hands: list[Hand], hand_type: Optional[HandType] = None,
                 number_of_decks: int = 2, lower_bound: Optional[int] = None,
                 upper_bound: Optional[int] = None,
                 triples_to_plates: bool = True,
                 triples_and_pairs_to_full_houses: bool = True,
                 pairs_to_tubes: bool = True,
                 pair_jokers: bool = False) -> list[Hand]:
    assert all(h.type not in (HandType.UNKNOWN, HandType.INVALID) and h.power >= 0 for h in hands)

    result = []
    lb = lower_bound if lower_bound is not None else -1
    ub = upper_bound if upper_bound is not None else get_joker_bomb_power(number_of_decks)

    for hand in hands:
        if hand_type is not None and hand.type != hand_type:
            continue
        index = hand.power
        if lb < index < ub:
            result.append(hand)

    def _pairs_from_jokers() -> list[Hand]:
        joker_pairs = []
        all_cards = []
        for h in hands:
            all_cards.extend(h.cards)
        black_jokers = [c for c in all_cards if c.is_black_joker]
        if len(black_jokers) >= 2:
            joker_pairs.append(Hand(black_jokers[:2], HandType.PAIR, power=16))
        red_jokers = [c for c in all_cards if c.is_red_joker]
        if len(red_jokers) >= 2:
            joker_pairs.append(Hand(red_jokers[:2], HandType.PAIR, power=17))
        return joker_pairs

    if hand_type == HandType.PAIR and pair_jokers:
        result.extend(_pairs_from_jokers())

    if hand_type == HandType.PLATE and triples_to_plates:
        for start_rank_value in range(1, 14):
            if start_rank_value <= lb or start_rank_value >= ub:
                continue
            start_triples = [h for h in hands if h.type == HandType.TRIPLE and h.power == start_rank_value]
            if not start_triples:
                continue
            end_triples = [h for h in hands if h.type == HandType.TRIPLE and h.power == start_rank_value + 1]
            if not end_triples:
                continue
            result.append(Hand(start_triples[0].cards + end_triples[0].cards,
                                HandType.PLATE, power=start_rank_value))

    if hand_type == HandType.TUBE and pairs_to_tubes:
        for start_rank_value in range(1, 13):
            if start_rank_value <= lb or start_rank_value >= ub:
                continue
            start_pairs = [h for h in hands if h.type == HandType.PAIR and h.power == start_rank_value]
            if not start_pairs:
                continue
            middle_pairs = [h for h in hands if h.type == HandType.PAIR and h.power == start_rank_value + 1]
            if not middle_pairs:
                continue
            end_pairs = [h for h in hands if h.type == HandType.PAIR and h.power == start_rank_value + 2]
            if not end_pairs:
                continue
            result.append(Hand(start_pairs[0].cards + end_pairs[0].cards,
                                HandType.TUBE, power=start_rank_value))

    if hand_type == HandType.FULL_HOUSE and triples_and_pairs_to_full_houses:
        triples = [h for h in hands if h.type == HandType.TRIPLE]
        pairs = [h for h in hands if h.type == HandType.PAIR]
        if not pairs and pair_jokers:
            pairs = _pairs_from_jokers()

        if triples and pairs:
            min_pair = min(pairs, key=lambda h: h.power)
            for triple in triples:
                if triple.power <= lb or triple.power >= ub:
                    continue
                result.append(Hand(triple.cards + min_pair.cards,
                                    HandType.FULL_HOUSE, power=triple.power))

    return result


def min_of_hands(hands: list[Hand], hand_type: Optional[HandType] = None,
                 number_of_decks: int = 2, lower_bound: Optional[int] = None,
                 upper_bound: Optional[int] = None,
                 single_from_pairs: bool = False, single_from_triples: bool = False,
                 triples_to_plates: bool = False,
                 triples_and_pairs_to_full_houses: bool = False,
                 pairs_to_tubes: bool = False,
                 pair_jokers: bool = False) -> Optional[Hand]:
    lb = lower_bound if lower_bound is not None else -1
    ub = upper_bound if upper_bound is not None else get_joker_bomb_power(number_of_decks)

    filtered = filter_hands(hands, hand_type=hand_type, number_of_decks=number_of_decks,
                            lower_bound=lb, upper_bound=ub,
                            triples_to_plates=triples_to_plates,
                            triples_and_pairs_to_full_houses=triples_and_pairs_to_full_houses,
                            pairs_to_tubes=pairs_to_tubes,
                            pair_jokers=pair_jokers)

    if filtered:
        return min(filtered, key=lambda h: h.power)

    if hand_type == HandType.SINGLE:
        result = None

        if single_from_triples:
            triples = filter_hands(hands, hand_type=HandType.TRIPLE, number_of_decks=number_of_decks,
                                   lower_bound=lb, upper_bound=ub)
            if triples:
                result = min(triples, key=lambda h: h.power)

        if result is None and single_from_pairs:
            pairs = filter_hands(hands, hand_type=HandType.PAIR, number_of_decks=number_of_decks,
                                 lower_bound=lb, upper_bound=ub)
            if pairs:
                result = min(pairs, key=lambda h: h.power)

        if result is not None:
            return Hand(result.cards[:1], HandType.SINGLE, power=result.first.power_rank)

    if hand_type == HandType.PAIR and pair_jokers:
        joker_pairs = filter_hands(hands, hand_type=HandType.PAIR, number_of_decks=number_of_decks,
                                   lower_bound=lb, upper_bound=ub, pair_jokers=True)
        if joker_pairs:
            return min(joker_pairs, key=lambda h: h.power)

    return None


def max_of_hands(hands: list[Hand], hand_type: Optional[HandType] = None,
                 number_of_decks: int = 2, lower_bound: Optional[int] = None,
                 upper_bound: Optional[int] = None,
                 triples_to_plates: bool = False,
                 triples_and_pairs_to_full_houses: bool = False,
                 pairs_to_tubes: bool = False,
                 pair_jokers: bool = False) -> Optional[Hand]:
    lb = lower_bound if lower_bound is not None else -1
    ub = upper_bound if upper_bound is not None else get_joker_bomb_power(number_of_decks)

    filtered = filter_hands(hands, hand_type=hand_type, number_of_decks=number_of_decks,
                            lower_bound=lb, upper_bound=ub,
                            triples_to_plates=triples_to_plates,
                            triples_and_pairs_to_full_houses=triples_and_pairs_to_full_houses,
                            pairs_to_tubes=pairs_to_tubes,
                            pair_jokers=pair_jokers)

    if filtered:
        return max(filtered, key=lambda h: h.power)

    return None


def is_max_of_hand_type(hand: Hand, number_of_decks: int) -> bool:
    sw = hand.type
    if sw == HandType.SINGLE or sw == HandType.PAIR:
        return hand.power == 17
    if sw in (HandType.TRIPLE, HandType.FULL_HOUSE):
        return hand.power == rank_value_of_level_card()
    if sw == HandType.TUBE:
        return hand.power == 12
    if sw == HandType.PLATE:
        return hand.power == 13
    if sw == HandType.STRAIGHT:
        return hand.power == 10
    if sw == HandType.BOMB:
        return hand.power == get_joker_bomb_power(number_of_decks)
    return False


def is_max_bomb_power_of(cards_count: int, number_of_decks: int,
                         include_joker_bomb: bool = False) -> int:
    if cards_count < 4:
        return 0
    if cards_count == 4:
        if number_of_decks == 2 and include_joker_bomb:
            return get_joker_bomb_power(number_of_decks)
        else:
            return get_non_joker_bomb_power(4, rank_value_of_level_card())
    if cards_count == 5:
        return get_bomb_power(5, 10, number_of_decks, True, False)
    return get_non_joker_bomb_power(cards_count + 1, rank_value_of_level_card())


# =============================================================================
# Hand extraction helpers
# =============================================================================

def group_hands_by_type(hands: list[Hand]) -> dict[HandType, list[Hand]]:
    grouped = {}
    for hand in hands:
        if hand.type not in grouped:
            grouped[hand.type] = []
        grouped[hand.type].append(hand)
    return grouped


def extract_regular_single_if_possible(cards, return_max: bool = False) -> Optional[Card]:
    cards_list = list(cards)
    if len(cards_list) == 1:
        return cards_list[0]
    regular_cards = [c for c in cards_list if not c.is_wild]
    if regular_cards:
        if return_max:
            return max(regular_cards, key=lambda c: c.power_rank)
        return regular_cards[0]
    return cards_list[0] if cards_list else None


def extract_regular_pair_if_possible(cards, lower_bound: int = -1,
                                     upper_bound: Optional[int] = None,
                                     return_max: bool = False) -> Optional[Hand]:
    if upper_bound is None:
        upper_bound = 17

    regular_cards = PokerCardList([c for c in cards
                                   if not c.is_wild and lower_bound < c.power_rank < upper_bound])
    wild_cards = [c for c in cards if c.is_wild and c.power_rank > lower_bound]

    if len(regular_cards) + len(wild_cards) < 2:
        return None

    if len(regular_cards) == 0:
        return Hand([wild_cards[0], wild_cards[1]], HandType.PAIR, power=wild_cards[0].power_rank)

    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)

    if return_max:
        for group in reversed(grouped):
            if len(group) == 2:
                return Hand(group.cards, HandType.PAIR, power=group[0].power_rank)
            elif len(group) >= 2:
                return Hand(group.cards[:2], HandType.PAIR, power=group[0].power_rank)
            elif wild_cards:
                return Hand(group.cards + wild_cards[:1], HandType.PAIR, power=group[0].power_rank)

    for group in grouped:
        if len(group) == 2:
            return Hand(group.cards[:2], HandType.PAIR, power=group[0].power_rank)

    for group in grouped:
        if len(group) >= 2:
            return Hand(group.cards[:2], HandType.PAIR, power=group[0].power_rank)

    if wild_cards:
        for group in grouped:
            if len(group) == 1:
                return Hand(group.cards + wild_cards[:1], HandType.PAIR, power=group[0].power_rank)

    return None


def extract_pair_from_triple(triple: Hand, lower_bound: int = -1,
                             return_max: bool = False) -> Optional[Hand]:
    assert triple.type == HandType.TRIPLE
    return extract_regular_pair_if_possible(triple, lower_bound, None, return_max)


def extract_triples_from_plate(plate: Hand, lower_bound: int = -1,
                               return_max: bool = False) -> list[Hand]:
    assert plate.type == HandType.PLATE
    wild_cards = plate.where(lambda c: c.is_wild and c.power_rank > lower_bound)
    regular_cards = plate.where(lambda c: not c.is_wild and c.power_rank > lower_bound)

    if len(regular_cards) + len(wild_cards) < 3:
        return []

    if len(regular_cards) == 0:
        return [Hand(wild_cards.cards[:3], HandType.TRIPLE, power=wild_cards[0].power_rank)]

    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)

    triples = []
    for group in grouped:
        if len(group) == 3:
            triples.append(Hand(group.cards, HandType.TRIPLE, power=group[0].power_rank))

    if len(wild_cards) > 0:
        for group in grouped:
            if len(group) == 2:
                triples.append(Hand(group.cards + wild_cards.cards[:1],
                                    HandType.TRIPLE, power=group[0].power_rank))

    if len(wild_cards) > 1:
        for group in grouped:
            if len(group) == 1:
                triples.append(Hand(group.cards + wild_cards.cards[:2],
                                    HandType.TRIPLE, power=group[0].power_rank))

    if return_max:
        triples.sort(key=lambda h: h.power, reverse=True)

    return triples


def extract_pair_from_full_house(full_house: Hand, lower_bound: int = -1,
                                 upper_bound: Optional[int] = None,
                                 return_max: bool = False) -> Optional[Hand]:
    assert full_house.type == HandType.FULL_HOUSE
    return extract_regular_pair_if_possible(full_house, lower_bound, upper_bound, return_max)


def extract_pair_from_plate(plate: Hand, lower_bound: int = -1,
                            upper_bound: Optional[int] = None,
                            return_max: bool = False) -> Optional[Hand]:
    assert plate.type == HandType.PLATE
    return extract_regular_pair_if_possible(plate, lower_bound, upper_bound, return_max)


def extract_pair_from_tube(tube: Hand, lower_bound: int = -1,
                           upper_bound: Optional[int] = None,
                           return_max: bool = False) -> Optional[Hand]:
    assert tube.type == HandType.TUBE
    return extract_regular_pair_if_possible(tube, lower_bound, upper_bound, return_max)


def extract_triple_from_full_house(full_house: Hand, lower_bound: int = -1) -> Optional[Hand]:
    assert full_house.type == HandType.FULL_HOUSE
    wild_cards = full_house.where(lambda c: c.is_wild and c.power_rank > lower_bound)
    regular_cards = full_house.where(lambda c: not c.is_wild and c.power_rank > lower_bound)

    if len(regular_cards) + len(wild_cards) < 3:
        return None

    if len(regular_cards) == 0:
        return Hand(wild_cards.cards[:3], HandType.TRIPLE, power=wild_cards[0].power_rank)

    grouped = list(group_cards(regular_cards).values())
    grouped.sort(key=lambda g: g[0].power_rank)

    for group in grouped:
        if len(group) == 3:
            return Hand(group.cards, HandType.TRIPLE, power=group[0].power_rank)

    for group in grouped:
        if len(group) >= 3:
            return Hand(group.cards[:3], HandType.TRIPLE, power=group[0].power_rank)

    if len(wild_cards) > 0:
        for group in grouped:
            if len(group) == 2:
                return Hand(group.cards[:2] + wild_cards.cards[:1],
                            HandType.TRIPLE, power=group[0].power_rank)

    if len(wild_cards) > 1:
        for group in grouped:
            if len(group) == 1:
                return Hand(group.cards + wild_cards.cards[:2],
                            HandType.TRIPLE, power=group[0].power_rank)

    return None


def extract_full_house_from_plate(plate: Hand, lower_bound: int = -1,
                                  return_max: bool = False) -> Optional[Hand]:
    triples = extract_triples_from_plate(plate, lower_bound, return_max)
    if not triples:
        return None
    pair = extract_regular_pair_if_possible(plate - triples[0])
    if pair is None:
        return None
    return Hand(triples[0].cards + pair.cards, HandType.FULL_HOUSE, power=triples[0].power)


# =============================================================================
# canBeatXXX functions
# =============================================================================

def can_beat_single(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    if cards.is_empty:
        return False
    for c in cards:
        if c.power_rank > target_power:
            return True
    return False


def can_beat_pair(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_pairs(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_triple(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_triples(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_full_house(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_full_houses(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_straight(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_straights(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_tube(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_tubes(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_plate(cards: PokerCardList, target_power: int, level_rank: str) -> bool:
    hands = find_plates(cards, level_rank, target_power=target_power)
    return len(hands) > 0


def can_beat_bomb(cards: PokerCardList, target_power: int, level_rank: str,
                  number_of_standard_decks: int = 2) -> bool:
    hands = find_bombs(cards, level_rank,
                       include_straight_flush=True,
                       number_of_standard_decks=number_of_standard_decks,
                       target_power=target_power)
    return len(hands) > 0


def can_player_beat(cards: PokerCardList, target_hand: Hand, level_rank: str,
                    number_of_standard_decks: int = 2) -> bool:
    if cards.is_empty:
        return False

    if target_hand.type == HandType.EMPTY:
        return True

    if not target_hand.is_bomb:
        if can_beat_bomb(cards, target_hand.power, level_rank,
                         number_of_standard_decks=number_of_standard_decks):
            return True

    if target_hand.type == HandType.SINGLE:
        return can_beat_single(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.PAIR:
        return can_beat_pair(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.TRIPLE:
        return can_beat_triple(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.FULL_HOUSE:
        return can_beat_full_house(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.STRAIGHT:
        return can_beat_straight(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.TUBE:
        return can_beat_tube(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.PLATE:
        return can_beat_plate(cards, target_hand.power, level_rank)
    elif target_hand.type == HandType.BOMB:
        return can_beat_bomb(cards, target_hand.power, level_rank,
                             number_of_standard_decks=number_of_standard_decks)
    return False
