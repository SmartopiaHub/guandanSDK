"""Python copy of ``guandan_core/test/poker_card_test.dart``."""

from __future__ import annotations

from guandan_core.cards import Card, Hand, HandType, PokerCardList
from guandan_core.utility import cards_from_string, cards_to_string, find_series


def test_should_create_a_card_instance() -> None:
    card = Card("A", "S", False)
    assert card.rank == "A"
    assert card.suit == "S"
    assert card.is_level is False


def test_should_identify_a_joker_card() -> None:
    assert Card.red_joker_card().is_joker is True
    assert Card.black_joker_card().is_joker is True


def test_should_identify_a_wild_card() -> None:
    assert Card("2", "H", True).is_wild is True


def test_should_create_a_card_from_string() -> None:
    card = Card.parse("AS")
    assert card == Card("A", "S", False)
    assert Card.parse("RJ") == Card.red_joker_card()
    assert Card.parse("BJ") == Card.black_joker_card()


def test_cards_with_same_rank_and_suit_should_be_equal() -> None:
    assert Card("A", "S", False) == Card("A", "S", False)


def test_cards_with_different_rank_should_not_be_equal() -> None:
    assert Card("A", "S", False) != Card("K", "S", False)


def test_cards_comparison() -> None:
    card_a = Card("A", "S", False)
    card_k = Card("K", "S", False)
    card_q_level = Card("Q", "S", True)
    assert card_a > card_k
    assert card_k < card_a
    assert card_a < card_q_level
    assert card_q_level < Card.black_joker_card()
    assert Card.red_joker_card() > Card.black_joker_card()
    assert not (Card.red_joker_card() < Card.red_joker_card())


def test_should_convert_string_to_list_of_cards() -> None:
    cards = cards_from_string("AS KH RJ")
    assert len(cards) == 3
    assert cards[0] == Card("A", "S", False)
    assert cards[1] == Card("K", "H", False)
    assert cards[2] == Card.red_joker_card()


def test_should_convert_list_of_cards_to_string() -> None:
    cards = [Card("A", "S", False), Card("K", "H", False)]
    assert cards_to_string(cards) == "AS KH"


def test_should_find_a_valid_series() -> None:
    cards = PokerCardList.from_string("3S 4S 5S 6S 7S 8S 8S 9S 9H TS TD JS QS KS AH 2D RJ BJ")
    result = find_series(cards, 3, 5, 0, 1)
    assert result.is_valid is True
    assert len(result.series) == 5
    result = find_series(cards, 1, 5, 0, 1)
    assert result.is_valid is True
    assert len(result.series) == 5
    assert result.to_hand("A").type == HandType.STRAIGHT
    result = find_series(cards, 8, 3, 0, 2)
    assert result.is_valid is True
    assert len(result.series) == 6


def test_should_find_a_valid_series_with_wild_cards() -> None:
    cards = PokerCardList.from_string("3S 4S 5S 6S AH 5S 6S")
    result = find_series(cards, 2, 5, 1, 1)
    assert result.is_valid is True
    hand = result.to_hand("A")
    assert hand.type == HandType.BOMB
    assert len(hand.cards) == 5
    assert hand.power == 603

    result = find_series(cards, 4, 3, 1, 2)
    assert result.is_valid is True
    hand = result.to_hand("A")
    assert hand.type == HandType.TUBE
    assert len(hand.cards) == 6
    assert hand.power == 4


def test_should_not_find_an_invalid_series() -> None:
    cards = PokerCardList.from_string("3S 4S 5S 6S 8S 8S 9S TS TS JS JS QS QS KS")
    assert find_series(cards, 3, 5, 0, 1).is_valid is False
    assert find_series(cards, 10, 5, 0, 1).is_valid is False
    assert find_series(cards, 8, 3, 0, 2).is_valid is False


def test_should_return_unknown_hand_from_string() -> None:
    hand_str = "unknown : 9S QC KH 3D 9C 6H 5C AD 3S 6S 3C KS JH BJ JH AC AH QS 2C* TC 4S 4C 5H 4S 2C* 7S QD"
    hand = Hand.parse(hand_str)
    assert hand.type == HandType.UNKNOWN


def test_should_add_two_card_lists_together() -> None:
    combined = PokerCardList.from_string("AS KH") + PokerCardList.from_string("2D 3C")
    assert len(combined) == 4
    assert combined.has_cards(PokerCardList.from_string("AS KH 2D 3C").cards)


def test_should_subtract_card_lists() -> None:
    result = PokerCardList.from_string("AS KH 2D 3C") - PokerCardList.from_string("2D 3C")
    assert len(result) == 2
    assert result.has_cards(PokerCardList.from_string("AS KH").cards)


def test_card_list_membership_helpers() -> None:
    cards = PokerCardList.from_string("AS KH 2D 3C")
    assert cards.has_card(Card("A", "S", False))
    assert cards.has_cards(PokerCardList.from_string("AS KH").cards)


def test_should_shuffle_card_list() -> None:
    cards = PokerCardList.from_string("AS KH 2D 3C")
    cards.shuffle()
    assert len(cards) == 4


def test_should_sort_card_list_by_power_rank() -> None:
    cards = PokerCardList.from_string("AS KH 2D* 3C")
    cards.sort_by_power_rank()
    assert cards.cards[0] == Card.parse("3C")
    assert cards.cards[-1] == Card.parse("2D*")


def test_should_sort_card_list_by_natural_rank() -> None:
    cards = PokerCardList.from_string("AS KH 2D 3C")
    cards.sort_by_natural_rank()
    assert cards.cards[0] == Card("2", "D", False)
    assert cards.cards[-1] == Card("A", "S", False)


def test_mutating_card_list_helpers() -> None:
    cards = PokerCardList.from_string("AS KH 2D 3C")
    cards.remove_last()
    assert len(cards) == 3
    assert cards.has_cards(PokerCardList.from_string("AS KH 2D").cards)

    sublist = PokerCardList.from_string("AS KH 2D 3C").sublist(1, 3)
    assert len(sublist) == 2
    assert sublist.has_cards(PokerCardList.from_string("KH 2D").cards)

    assert PokerCardList.from_string("AS KH 2D 3C").index_of(Card("K", "H", False)) == 1
    assert PokerCardList.from_string("AS KH 2D 3C").count(lambda card: card.suit == "H") == 1


def test_should_remove_multiple_cards() -> None:
    cards = PokerCardList.from_string("AS KH KH 3C")
    cards.remove_cards(PokerCardList.from_string("KH KH").cards)
    assert len(cards) == 2
    assert cards.has_cards(PokerCardList.from_string("AS 3C").cards)

    cards = PokerCardList.from_string("AS KH KH 3C")
    cards.remove_cards(PokerCardList.from_string("KH").cards)
    assert len(cards) == 3
    assert cards.has_cards(PokerCardList.from_string("AS KH 3C").cards)
