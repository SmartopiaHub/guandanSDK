"""Python-specific behavior tests beyond the Dart parity suite."""

from __future__ import annotations

from dataclasses import replace

from guandan_core.cards import Card, PokerCardList
from guandan_core.game_room import GameRoomConfig
from guandan_core.player import Player, PlayerTeam


def test_card_is_hashable_for_sets_and_dicts() -> None:
    card = Card.parse("AS")
    assert {card: "ace"}[Card("A", "S", False)] == "ace"
    assert len({card, Card.parse("AS")}) == 1


def test_card_list_cards_property_returns_copy() -> None:
    cards = PokerCardList.from_string("AS KH")
    snapshot = cards.cards
    snapshot.pop()
    assert len(cards) == 2


def test_card_list_supports_python_iteration_and_membership() -> None:
    cards = PokerCardList.from_string("AS KH")
    assert [str(card) for card in cards] == ["AS", "KH"]
    assert Card.parse("AS") in cards


def test_dataclass_replace_for_room_config() -> None:
    config = GameRoomConfig(required_players=4, room_tier=1)
    updated = replace(config, room_tier=2)
    assert config.room_tier == 1
    assert updated.room_tier == 2


def test_deep_copy_is_independent_but_shallow_copy_shares_card_lists() -> None:
    original = Player("p1", 1, PlayerTeam.RED_TEAM, cards_on_hand=PokerCardList.from_string("AS KH"))
    deep = Player.deep_copy(original)
    shallow = Player.copy(original)

    original.cards_on_hand.remove_card(Card.parse("AS"))
    assert deep.cards_on_hand.has_card(Card.parse("AS"))
    assert not shallow.cards_on_hand.has_card(Card.parse("AS"))
