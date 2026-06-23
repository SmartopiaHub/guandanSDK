"""Python copy of player-related tests from Dart ``guandan_core/test``."""

from __future__ import annotations

from guandan_core.cards import Card, Hand, HandType, PokerCardList
from guandan_core.player import Player, PlayerTeam, next_player, next_seat


def test_player_to_json_and_from_json() -> None:
    player = Player("Player 1", 1, PlayerTeam.RED_TEAM)
    restored = Player.from_json(player.to_json())
    assert restored.id == player.id
    assert restored.seat == player.seat
    assert restored.team == player.team
    assert restored.name == player.name


def test_player_has_cards() -> None:
    player = Player("1", 1, PlayerTeam.RED_TEAM)
    card1 = Card.parse("AS")
    card2 = Card.parse("KH")
    player.set_cards_on_hand(PokerCardList([card1, card2]))
    assert player.has_cards([card1])
    assert player.has_cards([card2])
    assert not player.has_cards([Card.parse("QH")])
    assert not player.has_cards([card1, card1])


def test_player_has_at_least_one_card_and_card_count() -> None:
    player = Player("1", 1, PlayerTeam.RED_TEAM)
    player.set_cards_on_hand(Hand.empty_hand())
    assert not player.has_at_least_one_card

    player.cards_on_hand.add_all([Card.parse("QH")])
    assert player.has_at_least_one_card

    player.set_cards_on_hand(Hand([Card.parse("QH") for _ in range(25)], HandType.UNKNOWN))
    assert player.card_count_on_hand == 25
    player.cards_on_hand.add_all([Card.parse("QH")])
    assert player.card_count_on_hand == 26


def test_player_play_and_reset() -> None:
    player = Player("1", 1, PlayerTeam.RED_TEAM)
    card1 = Card.parse("QH")
    card2 = Card.parse("AH")
    player.set_cards_on_hand(PokerCardList([card1, card2]))

    player.play(Hand([card1], HandType.SINGLE))
    assert not player.cards_on_hand.has_cards([card1])
    assert player.played_cards.has_cards([card1])

    player.reset_hands()
    assert player.cards_on_hand.length == 0
    assert player.played_cards.length == 0


def test_next_seat_calculation() -> None:
    assert next_seat(1, 4) == 2
    assert next_seat(2, 4) == 3
    assert next_seat(3, 4) == 4
    assert next_seat(4, 4) == 1
    assert next_seat(3, 6) == 4
    assert next_seat(6, 6) == 1


def test_next_player_returns_correct_player() -> None:
    player1 = Player("1", 1, PlayerTeam.RED_TEAM, cards_on_hand=Hand.empty_hand())
    player2 = Player("2", 2, PlayerTeam.BLUE_TEAM, cards_on_hand=Hand.empty_hand())
    player3 = Player("3", 3, PlayerTeam.RED_TEAM, cards_on_hand=Hand.empty_hand())
    player4 = Player("4", 4, PlayerTeam.BLUE_TEAM, cards_on_hand=Hand.empty_hand())
    players = [player1, player2, player3, player4]

    assert next_player(player1, players, False, False).id == player2.id
    assert next_player(player2, players, False, False).id == player3.id
    assert next_player(player3, players, False, False).id == player4.id
    assert next_player(player4, players, False, False).id == player1.id
    assert next_player(player1, players, True, False).id == player3.id
    assert next_player(player2, players, True, False).id == player4.id
    assert next_player(player3, players, True, False).id == player1.id
    assert next_player(player4, players, True, False).id == player2.id
    assert next_player(player1, players, False, True) is None


def test_player_profile_refactor_constructor_and_json() -> None:
    player = Player("p1", 1, PlayerTeam.RED_TEAM, display_name="Alice", bot_code="strongBot")
    assert player.name == "Alice"
    assert not player.is_human_player
    assert player.is_ai_player

    human = Player("p1", 1, PlayerTeam.RED_TEAM, display_name="Human")
    assert human.is_human_player
    assert not human.is_ai_player
    assert human.bot_code is None

    fallback = Player("player-uuid", 1, PlayerTeam.RED_TEAM)
    assert fallback.name == "player-uuid"

    player = Player("p1", 1, PlayerTeam.RED_TEAM, display_name="TestPlayer", bot_code="basicBot")
    player.played_cards.add_all([Card.parse("AH"), Card.parse("AS")])
    data = player.to_json(with_cards_on_hand=False, with_played_cards=True)
    assert data["player_id"] == "p1"
    assert data["seat"] == 1
    assert data["display_name"] == "TestPlayer"
    assert data["bot_model"] == "basicBot"
    assert "profile" not in data
    restored = Player.from_json(data)
    assert restored.display_name == "TestPlayer"
    assert restored.bot_code == "basicBot"
    assert not restored.is_human_player


def test_player_backward_compat_and_copy_helpers() -> None:
    old_json = {
        "player_id": "p1",
        "seat": 1,
        "team": "redTeam",
        "profile": {"nickname": "OldPlayer", "bot_model": "legacyBot"},
        "played_cards": "",
    }
    player = Player.from_json(old_json)
    assert player.display_name == "OldPlayer"
    assert player.bot_code == "legacyBot"

    original = Player("p1", 1, PlayerTeam.RED_TEAM, display_name="Original", bot_code="testBot")
    deep_copy = Player.deep_copy(original)
    assert deep_copy.display_name == "Original"
    assert deep_copy.bot_code == "testBot"
    assert not deep_copy.is_human_player

    new_id_copy = Player.deep_copy(original, new_id="p2")
    assert new_id_copy.id == "p2"
    assert new_id_copy.display_name == "Original"

    shallow = Player.copy(original)
    assert shallow.display_name == "Original"
    assert shallow.bot_code == "testBot"
