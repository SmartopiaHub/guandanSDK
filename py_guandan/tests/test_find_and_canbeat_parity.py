"""Comprehensive tests for findXXX and canBeatXXX methods ported from guandan_core.

Covers find_and_canbeat_test.dart tests.
"""

import pytest
from guandan_core.cards import (
    Card,
    Hand,
    HandType,
    PokerCardList,
    rank_value_of_level_card,
    rank_power,
    LEVEL_CARD_VALUE,
)
from guandan_core.utility import (
    find_series,
    find_tubes,
    find_plates,
    find_straights,
    find_straight_flushes,
    find_triples,
    find_pairs,
    find_full_houses,
    find_singles,
    find_bombs,
    find_hands,
    can_beat_single,
    can_beat_pair,
    can_beat_triple,
    can_beat_full_house,
    can_beat_straight,
    can_beat_tube,
    can_beat_plate,
    can_beat_bomb,
    can_player_beat,
    get_joker_bomb_power,
    get_non_joker_bomb_power,
    cards_from_string,
)


# Helper
def c(s: str) -> PokerCardList:
    return PokerCardList.parse(s)


# ============================================================================
# findSeries
# ============================================================================
class TestFindSeries:
    def test_valid_straight_5_1_0(self):
        cards = c("AH 2S 3D 4C 5H 9D KS")
        result = find_series(cards, 1, 5, 0, 1)
        assert result.is_valid is True
        assert result.series_length == 5
        assert result.wild_cards_used == 0
        assert result.start_rank_value == 1
        assert len(result.series) == 5

    def test_valid_with_wild_filling_gap(self):
        cards = c("AH 3S 4D 5C 2H*")
        result = find_series(cards, 1, 5, 1, 1)
        assert result.is_valid is True
        assert result.wild_cards_used == 1
        assert len(result.series) == 4

    def test_invalid_not_enough_wilds(self):
        cards = c("AH 3S 5D 6C 7H")
        result = find_series(cards, 1, 5, 1, 1)
        assert result.is_valid is False

    def test_valid_2_wilds_fill_2_gaps(self):
        cards = c("AH 4S 5D 3H* 2H*")
        result = find_series(cards, 1, 5, 2, 1)
        assert result.is_valid is True
        assert result.wild_cards_used == 2

    def test_valid_with_suit_filter(self):
        cards = c("AH 2H 3H 4H 5H 2S 3D")
        result = find_series(cards, 1, 5, 0, 1, suit="H")
        assert result.is_valid is True
        assert len(result.series) == 5
        for card in result.series:
            assert card.suit == "H"

    def test_invalid_with_suit_filter(self):
        cards = c("AH 2H 3H 4D 5S")
        result = find_series(cards, 1, 5, 0, 1, suit="H")
        assert result.is_valid is False

    def test_valid_suit_filter_wild_fills(self):
        cards = c("AH 2H 3H 4D 5H 2H*")
        result = find_series(cards, 1, 5, 1, 1, suit="H")
        assert result.is_valid is True
        assert result.wild_cards_used == 1

    def test_start_rank_14_series_length_1(self):
        cards = c("AH")
        result = find_series(cards, 14, 1, 0, 1)
        assert result.is_valid is True
        assert len(result.series) == 1

    def test_count_2_pairs(self):
        cards = c("AH AS 2D 2C 9H KD")
        result = find_series(cards, 1, 2, 0, 2)
        assert result.is_valid is True
        assert len(result.series) == 4
        assert result.series_length == 2

    def test_count_2_needs_wild(self):
        cards = c("AH 2S 2D 3H*")
        result = find_series(cards, 1, 2, 1, 2)
        assert result.is_valid is True
        assert result.wild_cards_used == 1

    def test_count_3_plate_triples(self):
        cards = c("AH AS AD 2H 2S 2D 9D")
        result = find_series(cards, 1, 2, 0, 3)
        assert result.is_valid is True
        assert len(result.series) == 6
        assert result.series_length == 2

    def test_count_3_needs_wilds(self):
        cards = c("AH AS 2S 2D 3H* 4H*")
        result = find_series(cards, 1, 2, 2, 3)
        assert result.is_valid is True
        assert result.wild_cards_used == 2
        assert len(result.series) == 4

    def test_count_3_not_enough_wilds(self):
        # Cards: 1 A, 2 twos, 3 wilds needed but only 2 available
        cards = c("AH 2S 2D 3H* 4H*")
        result = find_series(cards, 1, 2, 2, 3)
        assert result.is_valid is False


# ============================================================================
# findTubes
# ============================================================================
class TestFindTubes:
    def test_single_tube(self):
        cards = c("AH AS 2D 2C 3D 3C 9H KD")
        tubes = find_tubes(cards, "2")
        assert len(tubes) == 1
        assert tubes[0].type == HandType.TUBE
        assert tubes[0].power == 1

    def test_multiple_tubes_find_all(self):
        cards = c("AH AS 2D 2C 3D 3C 3H 3S 4H 4S 5H 5S KD")
        tubes = find_tubes(cards, "2", find_all=True)
        assert any(t.power == 1 for t in tubes)
        assert any(t.power == 3 for t in tubes)

    def test_no_tube(self):
        cards = c("AH KS QD JC TH 9S 8H")
        tubes = find_tubes(cards, "2")
        assert tubes == []

    def test_target_power_filter(self):
        cards = c("AH AS 2D 2C 3D 3C TH TS JD JC QD QC")
        tubes = find_tubes(cards, "2", find_all=True, target_power=1)
        assert len(tubes) == 1
        assert tubes[0].power == 10

    def test_target_power_filters_all(self):
        cards = c("AH AS 2D 2C 3D 3C")
        tubes = find_tubes(cards, "2", target_power=10)
        assert tubes == []

    def test_tube_with_1_wild(self):
        cards = c("AH 2S 2D 3S 3D KH*")
        tubes = find_tubes(cards, "2")
        assert len(tubes) == 1
        assert tubes[0].type == HandType.TUBE
        assert tubes[0].power == 1

    def test_tube_with_2_wilds_not_enough(self):
        cards = c("AH 2S 3D KH* QH*")
        tubes = find_tubes(cards, "2")
        assert tubes == []

    def test_tube_with_3_wilds(self):
        cards = c("AH 2S 3D KH* QH* JH*")
        tubes = find_tubes(cards, "2")
        assert len(tubes) == 1
        assert tubes[0].type == HandType.TUBE

    def test_tube_a23_power_1(self):
        cards = c("AH AS 2D 2C 3D 3C QH QS KD KC")
        tubes = find_tubes(cards, "2")
        assert len(tubes) == 1
        assert tubes[0].power == 1


# ============================================================================
# findPlates
# ============================================================================
class TestFindPlates:
    def test_single_plate(self):
        cards = c("AH AS AD 2H 2S 2D 9D")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].type == HandType.PLATE
        assert plates[0].power == 1

    def test_multiple_plates(self):
        cards = c("AH AS AD 2H 2S 2D QH QS QD KH KS KD 4H 5S")
        plates = find_plates(cards, "2", find_all=True)
        assert len(plates) == 3
        assert any(p.power == 1 for p in plates)
        assert any(p.power == 12 for p in plates)
        assert any(p.power == 13 for p in plates)

    def test_no_plate(self):
        cards = c("AH KS QD JC TH 9S 8H 7S")
        plates = find_plates(cards, "2")
        assert plates == []

    def test_target_power_filter(self):
        cards = c("AH AS AD 2H 2S 2D QH QS QD KH KS KD")
        plates = find_plates(cards, "2", find_all=True, target_power=1)
        assert len(plates) == 2
        assert any(p.power == 12 for p in plates)
        assert any(p.power == 13 for p in plates)

    def test_target_power_filters_all(self):
        cards = c("AH AS AD 2H 2S 2D")
        plates = find_plates(cards, "2", target_power=10)
        assert plates == []

    def test_plate_with_1_wild(self):
        cards = c("AH AS 2H 2S 2D KH*")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].type == HandType.PLATE

    def test_plate_with_2_wilds(self):
        cards = c("AH 2H 2S 2D KH* QH*")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].type == HandType.PLATE

    def test_lowest_power_plate(self):
        cards = c("AH AS AD 2H 2S 2D 3H 3S 3D 4H 4S 4D")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].power == 1

    def test_plate_boundary_ka(self):
        cards = c("KH KS KD AH AS AD")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].power == 13


# ============================================================================
# findStraights
# ============================================================================
class TestFindStraights:
    def test_valid_straight_a2345(self):
        cards = c("AH 2S 3D 4C 5H 9D KS")
        straights = find_straights(cards, "2")
        assert len(straights) == 1
        assert straights[0].type == HandType.STRAIGHT
        assert straights[0].power == 1

    def test_multiple_straights(self):
        cards = c("AH 2S 3D 4C 5H 3H 4S 5D 6C 7H TS JD QH KH AD")
        straights = find_straights(cards, "2", find_all=True)
        assert len(straights) >= 3

    def test_no_straight(self):
        cards = c("AH 3S 5D 7C 9H")
        straights = find_straights(cards, "2")
        assert straights == []

    def test_straight_with_1_wild(self):
        cards = c("AH 2S 4D 5C KH*")
        straights = find_straights(cards, "2")
        assert len(straights) == 1
        assert straights[0].type == HandType.STRAIGHT

    def test_straight_with_2_wilds(self):
        cards = c("AH 3S 5D KH* QH*")
        straights = find_straights(cards, "2")
        assert len(straights) == 1
        assert straights[0].type == HandType.STRAIGHT

    def test_target_power_filter(self):
        cards = c("AH 2S 3D 4C 5H 6H 7S 8D 9C TH")
        straights = find_straights(cards, "2", find_all=True, target_power=1)
        assert len(straights) == 5

    def test_target_power_filters_all(self):
        cards = c("AH 2S 3D 4C 5H")
        straights = find_straights(cards, "2", target_power=5)
        assert straights == []

    def test_straight_10jqka(self):
        cards = c("TH JS QD KC AH 3S")
        straights = find_straights(cards, "2")
        assert len(straights) == 1
        assert straights[0].power == 10

    def test_wild_cards_extracted(self):
        cards = c("AH 2S 3D 4C KH*")
        straights = find_straights(cards, "2")
        assert len(straights) == 1


# ============================================================================
# findStraightFlushes
# ============================================================================
class TestFindStraightFlushes:
    def test_real_straight_flush(self):
        cards = c("AH 2H 3H 4H 5H 9D KS")
        sf = find_straight_flushes(cards, "2")
        assert len(sf) == 1
        assert sf[0].type == HandType.BOMB
        assert sf[0].power > 0

    def test_straight_flush_with_wild(self):
        cards = c("AH 2H 4H 5H KH* 9D")
        sf = find_straight_flushes(cards, "2")
        assert len(sf) == 1
        assert sf[0].type == HandType.BOMB

    def test_no_straight_flush(self):
        cards = c("AH 2S 3D 4C 5H")
        sf = find_straight_flushes(cards, "2")
        assert sf == []

    def test_straight_not_flush(self):
        cards = c("AH 2S 3H 4D 5H")
        sf = find_straight_flushes(cards, "2")
        assert sf == []

    def test_multiple_straight_flushes(self):
        cards = c("AH 2H 3H 4H 5H 3S 4S 5S 6S 7S 9D KC")
        sf = find_straight_flushes(cards, "2", find_all=True)
        assert len(sf) == 2

    def test_find_all_false(self):
        cards = c("AH 2H 3H 4H 5H 3S 4S 5S 6S 7S")
        sf = find_straight_flushes(cards, "2")
        assert len(sf) == 1


# ============================================================================
# findTriples
# ============================================================================
class TestFindTriples:
    def test_triple_from_3_regular(self):
        cards = c("AH AS AD 2H 3S 4D 5C")
        triples = find_triples(cards, "2")
        assert len(triples) == 1
        assert triples[0].type == HandType.TRIPLE
        assert triples[0].power == rank_power("A")

    def test_triple_2_regular_1_wild(self):
        cards = c("AH AS 2H* 3D 4C 5H")
        triples = find_triples(cards, "2")
        assert len(triples) == 1
        assert triples[0].type == HandType.TRIPLE
        assert any(c.is_wild for c in triples[0].cards)

    def test_triple_1_regular_2_wilds(self):
        cards = c("AH 2H* 3H* 4S 5D")
        triples = find_triples(cards, "2")
        assert len(triples) == 1
        assert triples[0].type == HandType.TRIPLE

    def test_pure_wild_triple(self):
        cards = c("2H* 3H* 4H*")
        triples = find_triples(cards, "2")
        assert len(triples) == 1
        assert triples[0].type == HandType.TRIPLE
        assert triples[0].power == rank_value_of_level_card()

    def test_multiple_triples(self):
        cards = c("AH AS AD KH KS KD 2H* 3D 4C")
        triples = find_triples(cards, "2", find_all=True)
        assert len(triples) >= 2

    def test_target_power_filter(self):
        cards = c("AH AS AD KH KS KD")
        triples = find_triples(cards, "2", find_all=True, target_power=13)
        assert len(triples) == 1
        assert triples[0].power == 14

    def test_target_power_filters_all(self):
        cards = c("AH AS AD")
        triples = find_triples(cards, "2", target_power=14)
        assert triples == []

    def test_lowest_power_triple(self):
        cards = c("3H 3S 3D KH KS KD AH AS AD")
        triples = find_triples(cards, "2")
        assert len(triples) == 1
        assert triples[0].power == 3

    def test_no_triples(self):
        cards = c("AH KS QD JC")
        triples = find_triples(cards, "2")
        assert triples == []


# ============================================================================
# findPairs
# ============================================================================
class TestFindPairs:
    def test_pair_from_2_regular(self):
        cards = c("AH AS 2H 3S 4D 5C")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].type == HandType.PAIR

    def test_pair_1_regular_1_wild(self):
        cards = c("AH 2H* 3S 4D 5C")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].type == HandType.PAIR

    def test_pure_wild_pair_only_wilds(self):
        cards = c("2H* 3H*")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].type == HandType.PAIR
        assert pairs[0].power == rank_value_of_level_card()

    def test_pure_wild_pair_in_find_all(self):
        cards = c("2H* 3H* 4S 5D")
        pairs = find_pairs(cards, "2", find_all=True)
        has_pure = any(
            all(c.is_wild for c in p.cards) for p in pairs
        )
        assert has_pure is True

    def test_multiple_pairs(self):
        cards = c("AH AS KH KS 2H* 3H* 4D 5C")
        pairs = find_pairs(cards, "2", find_all=True)
        assert len(pairs) == 5

    def test_target_power_filter(self):
        cards = c("AH AS KH KS")
        pairs = find_pairs(cards, "2", find_all=True, target_power=13)
        assert len(pairs) == 1
        assert pairs[0].power == 14

    def test_target_power_filters_all(self):
        cards = c("AH AS")
        pairs = find_pairs(cards, "2", target_power=14)
        assert pairs == []

    def test_lowest_power_pair(self):
        cards = c("3H 3S KH KS AH AS")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].power == 3

    def test_wild_pair_filtered_by_target(self):
        cards = c("2H* 3H*")
        pairs = find_pairs(cards, "2", target_power=rank_value_of_level_card())
        assert pairs == []

    def test_pair_of_jokers(self):
        cards = c("BJ BJ")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].type == HandType.PAIR
        assert pairs[0].power == 16


# ============================================================================
# findFullHouses
# ============================================================================
class TestFindFullHouses:
    def test_regular_triple_pair(self):
        cards = c("AH AS AD KH KS 3D 4C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE
        assert fh[0].power == 14

    def test_triple_with_wild_pair(self):
        cards = c("AH AS KH KS 2H* 3D 4C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE

    def test_regular_triple_wild_pair(self):
        cards = c("AH AS AD KH 2H* 3D 4C")
        fh = find_full_houses(cards, "2")
        assert len(fh) >= 1
        assert fh[0].type == HandType.FULL_HOUSE

    def test_lowest_power(self):
        cards = c("3H 3S 3D 4H 4S AH AS AD KH KS")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1

    def test_multiple_full_houses(self):
        cards = c("AH AS AD KH KS KD QH QS JD JC")
        fh = find_full_houses(cards, "2", find_all=True)
        assert len(fh) >= 2

    def test_no_full_house(self):
        cards = c("AH KS QD JC TH")
        fh = find_full_houses(cards, "2")
        assert fh == []

    def test_target_power_filter(self):
        cards = c("AH AS AD KH KS")
        fh = find_full_houses(cards, "2", find_all=True, target_power=2)
        assert len(fh) >= 1
        assert any(h.power == 14 for h in fh)

    def test_target_power_filters_all(self):
        cards = c("AH AS AD KH KS")
        fh = find_full_houses(cards, "2", target_power=14)
        assert fh == []

    def test_black_joker_triple(self):
        cards = c("BJ BJ BJ KH KS 2D 3C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE
        assert fh[0].power == 16

    def test_red_joker_triple(self):
        cards = c("RJ RJ RJ KH KS 2D 3C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE
        assert fh[0].power == 17

    def test_regular_triple_black_joker_pair(self):
        cards = c("AH AS AD BJ BJ 3D 4C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE
        assert fh[0].power == 14

    def test_regular_triple_red_joker_pair(self):
        cards = c("AH AS AD RJ RJ 3D 4C")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE
        assert fh[0].power == 14

    def test_black_joker_triple_pair_same_rank(self):
        cards = c("BJ BJ BJ BJ BJ")
        fh = find_full_houses(cards, "2")
        assert fh == []


# ============================================================================
# findSingles
# ============================================================================
class TestFindSingles:
    def test_all_cards_as_singles(self):
        cards = c("AH 2S 3D 4C 5H")
        singles = find_singles(cards, "2", find_all=True)
        assert len(singles) == 5
        for s in singles:
            assert s.type == HandType.SINGLE

    def test_lowest_single(self):
        cards = c("KH 2S AH 3D 4C")
        singles = find_singles(cards, "2")
        assert len(singles) == 1
        assert singles[0].power == 2

    def test_target_power_filter(self):
        cards = c("AH 2S 3D KH")
        singles = find_singles(cards, "2", find_all=True, target_power=10)
        assert len(singles) == 2

    def test_target_power_filters_all(self):
        cards = c("AH 2S 3D")
        singles = find_singles(cards, "2", target_power=14)
        assert singles == []

    def test_empty_cards(self):
        singles = find_singles(PokerCardList.empty(), "2")
        assert singles == []


# ============================================================================
# findBombs
# ============================================================================
class TestFindBombs:
    def test_4_of_a_kind(self):
        cards = c("AH AS AD AC 3D 5H")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert bombs[0].type == HandType.BOMB
        assert len(bombs[0].cards) == 4

    def test_3_plus_1_wild(self):
        cards = c("AH AS AD 2H* 3D 5H")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert bombs[0].type == HandType.BOMB

    def test_5_of_a_kind_with_wilds(self):
        cards = c("AH AS AD AC 2H* 3D 5H")
        bombs = find_bombs(cards, "2", find_all=True)
        assert any(len(b.cards) >= 4 for b in bombs)

    def test_joker_bomb(self):
        cards = c("BJ BJ RJ RJ AH 3S")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert bombs[0].type == HandType.BOMB
        assert bombs[0].power == get_joker_bomb_power(2)

    def test_incorrect_joker_count(self):
        cards = c("BJ RJ RJ")
        bombs = find_bombs(cards, "2")
        assert not any(b.power == get_joker_bomb_power(2) for b in bombs)

    def test_include_straight_flush(self):
        cards = c("AH 2H 3H 4H 5H 9S KD")
        bombs = find_bombs(cards, "2", include_straight_flush=True)
        assert any(c.suit == "H" for b in bombs for c in b.cards)

    def test_no_straight_flush_when_false(self):
        cards = c("AH 2H 3H 4H 5H")
        bombs = find_bombs(cards, "2", include_straight_flush=False)
        assert bombs == []

    def test_multiple_bombs(self):
        cards = c("AH AS AD AC KH KS KD KC BJ BJ RJ RJ")
        bombs = find_bombs(cards, "2", find_all=True)
        assert len(bombs) == 3

    def test_target_power_filter(self):
        cards = c("AH AS AD AC KH KS KD KC")
        bombs = find_bombs(cards, "2", find_all=True, target_power=get_non_joker_bomb_power(4, 13))
        assert len(bombs) == 1

    def test_target_power_filters_all(self):
        cards = c("AH AS AD AC")
        bomb = find_bombs(cards, "2")
        bombs = find_bombs(cards, "2", target_power=bomb[0].power)
        assert bombs == []

    def test_no_bombs(self):
        cards = c("AH KS QD JC")
        bombs = find_bombs(cards, "2")
        assert bombs == []

    def test_lowest_power_bomb(self):
        cards = c("3H 3S 3D 3C AH AS AD AC")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1

    def test_2_plus_2_wilds(self):
        cards = c("AH AS 2H* 3H* 4D 5C")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert bombs[0].type == HandType.BOMB
        assert len([c for c in bombs[0].cards if c.is_wild]) == 2

    def test_number_of_decks_joker_bomb(self):
        cards = c("BJ BJ RJ RJ")
        bombs2 = find_bombs(cards, "2", number_of_standard_decks=2)
        assert any(b.power == get_joker_bomb_power(2) for b in bombs2)

        bombs3 = find_bombs(cards, "2", number_of_standard_decks=3)
        assert not any(b.power == get_joker_bomb_power(3) for b in bombs3)


# ============================================================================
# findHands (dispatcher)
# ============================================================================
class TestFindHands:
    def test_dispatches_single(self):
        cards = c("AH 2S 3D")
        hands = find_hands(cards, "2", HandType.SINGLE)
        assert len(hands) == 1
        assert hands[0].type == HandType.SINGLE

    def test_dispatches_pair(self):
        cards = c("AH AS 2H*")
        hands = find_hands(cards, "2", HandType.PAIR)
        assert len(hands) == 1
        assert hands[0].type == HandType.PAIR

    def test_dispatches_triple(self):
        cards = c("AH AS AD")
        hands = find_hands(cards, "2", HandType.TRIPLE)
        assert len(hands) == 1
        assert hands[0].type == HandType.TRIPLE

    def test_dispatches_straight(self):
        cards = c("AH 2S 3D 4C 5H")
        hands = find_hands(cards, "2", HandType.STRAIGHT)
        assert len(hands) == 1
        assert hands[0].type == HandType.STRAIGHT

    def test_dispatches_tube(self):
        cards = c("AH AS 2D 2C 3D 3C")
        hands = find_hands(cards, "2", HandType.TUBE)
        assert len(hands) == 1
        assert hands[0].type == HandType.TUBE

    def test_dispatches_plate(self):
        cards = c("AH AS AD 2H 2S 2D")
        hands = find_hands(cards, "2", HandType.PLATE)
        assert len(hands) == 1
        assert hands[0].type == HandType.PLATE

    def test_dispatches_full_house(self):
        cards = c("AH AS AD KH KS")
        hands = find_hands(cards, "2", HandType.FULL_HOUSE)
        assert len(hands) == 1
        assert hands[0].type == HandType.FULL_HOUSE

    def test_dispatches_bomb(self):
        cards = c("AH AS AD AC")
        hands = find_hands(cards, "2", HandType.BOMB)
        assert len(hands) == 1
        assert hands[0].type == HandType.BOMB

    def test_passes_through_find_all_and_target(self):
        cards = c("AH AS AD KH KS KD")
        hands = find_hands(cards, "2", HandType.TRIPLE, find_all=True, target_power=13)
        assert len(hands) == 1
        assert hands[0].power == 14

    def test_unknown_type(self):
        cards = c("AH 2S")
        hands = find_hands(cards, "2", HandType.UNKNOWN)
        assert hands == []


# ============================================================================
# canBeatSingle
# ============================================================================
class TestCanBeatSingle:
    def test_can_beat_higher(self):
        cards = c("AH 2S 3D")
        assert can_beat_single(cards, 10, "2") is True

    def test_cannot_beat(self):
        cards = c("2S 3D 4C")
        assert can_beat_single(cards, 10, "2") is False

    def test_wild_card_power_15(self):
        cards = c("2H* 3S 4D")
        assert can_beat_single(cards, 14, "2") is True

    def test_jokers_beat_high(self):
        cards = c("BJ RJ")
        assert can_beat_single(cards, 15, "2") is True

    def test_empty_false(self):
        assert can_beat_single(PokerCardList.empty(), 5, "2") is False

    def test_equal_power_false(self):
        cards = c("AH")
        assert can_beat_single(cards, 14, "2") is False


# ============================================================================
# canBeatPair
# ============================================================================
class TestCanBeatPair:
    def test_can_beat_regular_pair(self):
        cards = c("AH AS 2D 3C")
        assert can_beat_pair(cards, 10, "2") is True

    def test_cannot_beat(self):
        cards = c("3S 3D 4C 5H")
        assert can_beat_pair(cards, 10, "2") is False

    def test_wild_assisted_pair(self):
        cards = c("AH 2H* 4C 5H")
        assert can_beat_pair(cards, 13, "2") is True

    def test_pure_wild_pair(self):
        cards = c("2H* 3H* 4C 5H")
        assert can_beat_pair(cards, 14, "2") is True

    def test_target_exceeds_wild_pair(self):
        cards = c("2H* 3H*")
        assert can_beat_pair(cards, rank_value_of_level_card(), "2") is False

    def test_empty_false(self):
        assert can_beat_pair(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatTriple
# ============================================================================
class TestCanBeatTriple:
    def test_can_beat_regular(self):
        cards = c("AH AS AD 2D 3C")
        assert can_beat_triple(cards, 10, "2") is True

    def test_cannot_beat(self):
        cards = c("3S 3D 3C 4H 5S")
        assert can_beat_triple(cards, 10, "2") is False

    def test_wild_assisted_triple(self):
        cards = c("AH AS 2H* 4C 5H")
        assert can_beat_triple(cards, 13, "2") is True

    def test_2_wilds_1_regular(self):
        cards = c("AH 2H* 3H* 4C 5H")
        assert can_beat_triple(cards, 13, "2") is True

    def test_pure_wild_triple(self):
        cards = c("2H* 3H* 4H*")
        assert can_beat_triple(cards, 10, "2") is True

    def test_pure_wild_triple_always_added(self):
        cards = c("2H* 3H* 4H*")
        assert can_beat_triple(cards, rank_value_of_level_card(), "2") is True

    def test_empty_false(self):
        assert can_beat_triple(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatFullHouse
# ============================================================================
class TestCanBeatFullHouse:
    def test_can_beat_regular(self):
        cards = c("AH AS AD KH KS 2D 3C")
        assert can_beat_full_house(cards, 10, "2") is True

    def test_cannot_beat(self):
        cards = c("3S 3D 3C 4H 4S")
        assert can_beat_full_house(cards, 10, "2") is False

    def test_wild_in_triple(self):
        cards = c("AH AS KH KS 2H*")
        assert can_beat_full_house(cards, 10, "2") is True

    def test_joker_triple(self):
        cards = c("BJ BJ BJ KH KS")
        assert can_beat_full_house(cards, 14, "2") is True

    def test_target_exceeds_joker_triple(self):
        cards = c("BJ BJ BJ KH KS")
        assert can_beat_full_house(cards, 16, "2") is False

    def test_empty_false(self):
        assert can_beat_full_house(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatStraight
# ============================================================================
class TestCanBeatStraight:
    def test_can_beat_regular(self):
        cards = c("6H 7S 8D 9C TH AH 2S")
        assert can_beat_straight(cards, 5, "2") is True

    def test_cannot_beat(self):
        cards = c("AH 2S 3D 4C 5H")
        assert can_beat_straight(cards, 5, "2") is False

    def test_wild_assisted(self):
        cards = c("6H 7S 8D 9C 2H* KH")
        assert can_beat_straight(cards, 5, "2") is True

    def test_target_power_10_max(self):
        cards = c("TH JS QD KC AH")
        assert can_beat_straight(cards, 10, "2") is False

    def test_empty_false(self):
        assert can_beat_straight(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatTube
# ============================================================================
class TestCanBeatTube:
    def test_can_beat(self):
        cards = c("AH AS 2D 2C 3D 3C TH TS JD JC QD QC")
        assert can_beat_tube(cards, 5, "2") is True

    def test_cannot_beat(self):
        cards = c("AH AS 2D 2C 3D 3C")
        assert can_beat_tube(cards, 5, "2") is False

    def test_higher_start_rank(self):
        cards = c("TH TS JD JC QD QC")
        assert can_beat_tube(cards, 9, "2") is True

    def test_target_10(self):
        cards = c("TH TS JD JC QD QC")
        assert can_beat_tube(cards, 10, "2") is False  # 10 <= 10 → skipped

    def test_empty_false(self):
        assert can_beat_tube(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatPlate
# ============================================================================
class TestCanBeatPlate:
    def test_can_beat(self):
        cards = c("AH AS AD 2H 2S 2D")
        assert can_beat_plate(cards, 0, "2") is True

    def test_cannot_beat(self):
        cards = c("AH AS AD 2H 2S 2D")
        assert can_beat_plate(cards, 1, "2") is False

    def test_higher_plate(self):
        cards = c("QH QS QD KH KS KD")
        assert can_beat_plate(cards, 10, "2") is True

    def test_target_13_max(self):
        cards = c("KH KS KD AH AS AD")
        assert can_beat_plate(cards, 13, "2") is False

    def test_empty_false(self):
        assert can_beat_plate(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canBeatBomb
# ============================================================================
class TestCanBeatBomb:
    def test_can_beat_4_of_a_kind(self):
        cards = c("AH AS AD AC 2D 3C")
        assert can_beat_bomb(cards, 400, "2") is True

    def test_cannot_beat(self):
        cards = c("AH AS AD AC")
        bombs = find_bombs(cards, "2")
        assert can_beat_bomb(cards, bombs[0].power, "2") is False

    def test_joker_bomb_beats_regular(self):
        cards = c("BJ BJ RJ RJ AH")
        regular_bomb = find_bombs(c("AH AS AD AC"), "2")
        assert can_beat_bomb(cards, regular_bomb[0].power, "2") is True

    def test_straight_flush_bomb(self):
        cards = c("AH 2H 3H 4H 5H")
        target_bombs = find_bombs(c("KH KS KD KC"), "2")
        assert can_beat_bomb(cards, target_bombs[0].power, "2") is True

    def test_wild_assisted_bomb(self):
        cards = c("AH AS AD 2H* 3D 4C")
        assert can_beat_bomb(cards, 400, "2") is True

    def test_no_bomb(self):
        cards = c("AH KS QD JC")
        assert can_beat_bomb(cards, 100, "2") is False

    def test_empty_false(self):
        assert can_beat_bomb(PokerCardList.empty(), 5, "2") is False


# ============================================================================
# canPlayerBeat
# ============================================================================
class TestCanPlayerBeat:
    def test_empty_cards(self):
        hand = Hand(cards=[Card("2", "S", False)], type=HandType.SINGLE, power=2)
        assert can_player_beat(PokerCardList.empty(), hand, "2") is False

    def test_lead_empty_target(self):
        cards = c("AH 2S 3D")
        assert can_player_beat(cards, Hand.empty_hand(), "2") is True

    def test_bomb_vs_nonbomb(self):
        cards = c("AH AS AD AC 2D 3C")
        target = Hand(cards=cards_from_string("KH"), type=HandType.SINGLE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_type_match_higher_wins(self):
        cards = c("AH 2S 3D 4C")
        target = Hand(cards=cards_from_string("KH"), type=HandType.SINGLE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_pair_higher_wins(self):
        cards = c("AH AS 2D 3C")
        target = Hand(cards=cards_from_string("KH KS"), type=HandType.PAIR, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_pair_lower_loses(self):
        cards = c("3S 3D 4C 5H")
        target = Hand(cards=cards_from_string("AH AS"), type=HandType.PAIR, power=14)
        assert can_player_beat(cards, target, "2") is False

    def test_triple_higher_wins(self):
        cards = c("AH AS AD 2D 3C")
        target = Hand(cards=cards_from_string("KH KS KD"), type=HandType.TRIPLE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_triple_lower_loses(self):
        cards = c("3S 3D 3C 4C 5H")
        target = Hand(cards=cards_from_string("AH AS AD"), type=HandType.TRIPLE, power=14)
        assert can_player_beat(cards, target, "2") is False

    def test_full_house_higher_wins(self):
        cards = c("AH AS AD KH KS")
        target = Hand(cards=cards_from_string("3H 3S 3D 2H 2S"), type=HandType.FULL_HOUSE, power=3)
        assert can_player_beat(cards, target, "2") is True

    def test_straight_higher_wins(self):
        cards = c("6H 7S 8D 9C TH")
        target = Hand(cards=cards_from_string("AH 2S 3D 4C 5H"), type=HandType.STRAIGHT, power=1)
        assert can_player_beat(cards, target, "2") is True

    def test_tube_higher_wins(self):
        cards = c("TH TS JD JC QD QC")
        target = Hand(cards=cards_from_string("AH AS 2D 2C 3D 3C"), type=HandType.TUBE, power=1)
        assert can_player_beat(cards, target, "2") is True

    def test_plate_higher_wins(self):
        cards = c("QH QS QD KH KS KD")
        target = Hand(cards=cards_from_string("AH AS AD 2H 2S 2D"), type=HandType.PLATE, power=1)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_vs_nonbomb_always_wins(self):
        cards = c("AH AS AD AC 2D")
        target = Hand(cards=cards_from_string("KH"), type=HandType.SINGLE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_vs_higher_bomb_loses(self):
        cards = c("AH AS AD AC")
        target = Hand(cards_from_string("BJ BJ RJ RJ"), HandType.BOMB,
                      power=get_joker_bomb_power(2))
        assert can_player_beat(cards, target, "2") is False

    def test_bomb_vs_lower_bomb_wins(self):
        cards = c("BJ BJ RJ RJ AH AS AD AC")
        target = Hand(cards_from_string("KH KS KD KC"), HandType.BOMB,
                      power=get_non_joker_bomb_power(4, 13))
        assert can_player_beat(cards, target, "2") is True

    def test_target_unknown(self):
        cards = c("AH 2S 3D")
        target = Hand.unknown_hand(cards_from_string("KH"))
        assert can_player_beat(cards, target, "2") is False

    def test_wild_single(self):
        cards = c("2H* 3S 4D")
        target = Hand(cards=cards_from_string("KH"), type=HandType.SINGLE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_target_no_bomb_available(self):
        cards = c("AH AS KH KS")
        target = Hand(cards_from_string("3H 3S 3D 3C"), HandType.BOMB,
                      power=get_non_joker_bomb_power(4, 3))
        assert can_player_beat(cards, target, "2") is False

    def test_bomb_beats_straight(self):
        cards = c("7C TS 3S 6D 7S 2D* 7D TC 2H* QS 5C JS KS JC "
                  "8S 9S TH 3C KC JD 3C 8C AS TC 9C AC 3D")
        target = Hand(cards=cards_from_string("5D 6C 7D 8D 9H"), type=HandType.STRAIGHT, power=5)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_beats_tube(self):
        cards = c("AH AS AD AC KS QD")
        target = Hand(cards=cards_from_string("TH TS JD JC QD QC"), type=HandType.TUBE, power=10)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_beats_plate(self):
        cards = c("AH AS AD AC KS QD")
        target = Hand(cards=cards_from_string("QH QS QD KH KS KD"), type=HandType.PLATE, power=12)
        assert can_player_beat(cards, target, "2") is True

    def test_bomb_beats_full_house(self):
        cards = c("AH AS AD AC KS QD")
        target = Hand(cards=cards_from_string("KH KS KD QH QS"), type=HandType.FULL_HOUSE, power=13)
        assert can_player_beat(cards, target, "2") is True

    def test_wild_assisted_bomb_beats_nonbomb_3plus1(self):
        cards = c("TS TH TD 2H* 3C 4D 5H")
        target = Hand(cards=cards_from_string("5D 6C 7D 8D 9H"), type=HandType.STRAIGHT, power=5)
        assert can_player_beat(cards, target, "2") is True

    def test_wild_assisted_bomb_beats_nonbomb_2plus2(self):
        cards = c("TS TH 2H* 3H* 4D 5H")
        target = Hand(cards=cards_from_string("5D 6C 7D 8D 9H"), type=HandType.STRAIGHT, power=5)
        assert can_player_beat(cards, target, "2") is True

    def test_wild_assisted_bomb_3_plus_wild_vs_straight(self):
        cards = c("9D 7D 7S KS JC AC 9H 3H TS JH JS 3S 2S* KC "
                  "2H* 3C 6D 6D 4H AS QD 8D 7S AD TH TD KC")
        target = Hand(cards=cards_from_string("5D 6C 7D 8D 9H"), type=HandType.STRAIGHT, power=5)
        assert can_player_beat(cards, target, "2") is True

    def test_no_wild_assisted_bomb(self):
        cards = c("TS TH TD 3C 4D 5H 6S 7C")
        target = Hand(cards=cards_from_string("5D 6C 7D 8D 9H"), type=HandType.STRAIGHT, power=5)
        assert can_player_beat(cards, target, "2") is False


# ============================================================================
# Wild card count variations
# ============================================================================
class TestWildCardVariations:
    def test_0_wilds_pairs(self):
        cards = c("AH AS KH KS")
        pairs = find_pairs(cards, "2", find_all=True)
        assert len(pairs) == 2
        assert all(not c.is_wild for p in pairs for c in p.cards)

    def test_1_wild_triple(self):
        cards = c("AH AS 2H* 3D 4C")
        triples = find_triples(cards, "2", find_all=True)
        has_wild = any(
            any(c.is_wild for c in t.cards) and t.power != rank_value_of_level_card()
            for t in triples
        )
        assert has_wild is True

    def test_2_wilds_triple(self):
        cards = c("AH 2H* 3H* 4D 5C")
        triples = find_triples(cards, "2", find_all=True)
        has_double_wild = any(
            len([c for c in t.cards if c.is_wild]) >= 2 and t.power != rank_value_of_level_card()
            for t in triples
        )
        assert has_double_wild is True

    def test_0_wilds_bomb_needs_4(self):
        cards = c("AH AS AD KH KS")
        bombs = find_bombs(cards, "2")
        assert bombs == []

    def test_1_wild_bomb_from_3_plus_wild(self):
        cards = c("AH AS AD 2H* 3D 4C")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert any(c.is_wild for c in bombs[0].cards)

    def test_2_wilds_bomb_from_2_plus_2(self):
        cards = c("AH AS 2H* 3H* 4D 5C")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert len([c for c in bombs[0].cards if c.is_wild]) == 2


# ============================================================================
# Joker card handling
# ============================================================================
class TestJokerHandling:
    def test_find_pairs_joker_pairs(self):
        cards = c("BJ BJ KH KS")
        pairs = find_pairs(cards, "2")
        assert len(pairs) == 1
        assert pairs[0].power == 13  # K=13 is lower than BJ=16

    def test_find_full_houses_joker_triple(self):
        cards = c("BJ BJ BJ KH KS")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE

    def test_find_full_houses_joker_pair(self):
        cards = c("AH AS AD BJ BJ")
        fh = find_full_houses(cards, "2")
        assert len(fh) == 1
        assert fh[0].type == HandType.FULL_HOUSE

    def test_find_bombs_joker_bomb(self):
        cards = c("BJ BJ RJ RJ")
        bombs = find_bombs(cards, "2")
        assert len(bombs) == 1
        assert bombs[0].power == get_joker_bomb_power(2)

    def test_find_bombs_jokers_mixed(self):
        cards = c("BJ AH AS AD")
        bombs = find_bombs(cards, "2")
        has_mixed = any(
            any(c.is_joker for c in b.cards) and any(not c.is_joker for c in b.cards)
            for b in bombs
        )
        assert has_mixed is False

    def test_can_beat_single_jokers(self):
        cards = c("BJ RJ")
        assert can_beat_single(cards, 15, "2") is True


# ============================================================================
# Edge cases and boundaries
# ============================================================================
class TestEdgeCases:
    def test_find_series_10jqka(self):
        cards = c("TH JS QD KC AH")
        result = find_series(cards, 10, 5, 0, 1)
        assert result.is_valid is True

    def test_find_tubes_qka(self):
        cards = c("QH QS KD KC AH AS")
        tubes = find_tubes(cards, "2")
        assert len(tubes) == 1
        assert tubes[0].power == 12

    def test_find_plates_ka(self):
        cards = c("KH KS KD AH AS AD")
        plates = find_plates(cards, "2")
        assert len(plates) == 1
        assert plates[0].power == 13

    def test_find_straights_10jqka(self):
        cards = c("TH JS QD KC AH")
        straights = find_straights(cards, "2")
        assert len(straights) == 1
        assert straights[0].power == 10

    def test_find_singles_lowest(self):
        cards = c("KH 2S AH BJ RJ")
        singles = find_singles(cards, "2")
        assert len(singles) == 1
        assert singles[0].power == 2

    def test_lead_empty_target_always_true(self):
        cards = c("2S")
        assert can_player_beat(cards, Hand.empty_hand(), "2") is True

    def test_empty_cards_empty_target(self):
        assert can_player_beat(PokerCardList.empty(), Hand.empty_hand(), "2") is False
