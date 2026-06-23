"""Python copy of ``guandan_core/test/game_state_test.dart``."""

from __future__ import annotations

import json

import pytest

from guandan_core.cards import Hand
from guandan_core.game_state import GameState
from guandan_core.player import Player, PlayerTeam
from guandan_core.utility import deduce_hand_type


def _state() -> tuple[GameState, Player, Player, Player, Player]:
    player1 = Player("Player 1", 1, PlayerTeam.RED_TEAM, display_name="alex")
    player2 = Player("Player 2", 2, PlayerTeam.BLUE_TEAM, display_name="alex")
    player3 = Player("Player 3", 3, PlayerTeam.RED_TEAM, display_name="alex")
    player4 = Player("Player 4", 4, PlayerTeam.BLUE_TEAM, display_name="alex")
    game_state = GameState()
    game_state.add_players([player1, player2, player3, player4])
    return game_state, player1, player2, player3, player4


@pytest.mark.xfail(reason="Upstream Dart test expects 'bob' although fixture displayName is 'alex'.")
def test_get_player_literal_upstream_expectation() -> None:
    game_state, _, _, _, _ = _state()
    assert len(game_state.players) == 4
    assert game_state.get_player_by_seat(1).name == "alex"
    assert game_state.get_player_by_id("Player 2").name == "bob"


def test_new_round() -> None:
    game_state, player1, *_ = _state()
    game_state.new_round(start_player=player1)
    assert game_state.current_round.id == "R1"
    assert game_state.current_round.start_player.id == player1.id


def test_play_cards() -> None:
    game_state, player1, *_ = _state()
    game_state.new_round(start_player=player1)
    player1.set_cards_on_hand(Hand.parse("3D 3S"))
    hand = Hand.parse("3D 3S")
    game_state.play_cards(player1, hand)
    assert len(game_state.current_round.current_phase.turns) == 1
    assert game_state.current_round.current_phase.turns[0].player.id == player1.id
    assert game_state.current_round.current_phase.turns[0].played_hand == hand


def test_can_pass() -> None:
    game_state, player1, player2, *_ = _state()
    game_state.new_round(start_player=player1)
    player1.set_cards_on_hand(Hand.parse("3D 3S"))
    player2.set_cards_on_hand(Hand.parse("4D 4S"))
    assert game_state.can_pass() is False
    game_state.play_cards(player1, Hand.parse("3D 3S"))
    assert game_state.can_pass() is True


def test_can_play() -> None:
    game_state, player1, player2, player3, player4 = _state()
    game_state.new_round(start_player=player1)
    player1.set_cards_on_hand(Hand.parse("3D 3S 3D 2H* 2S*"))
    player2.set_cards_on_hand(Hand.empty_hand())
    player4.set_cards_on_hand(Hand.parse("AD AS"))
    player3.set_cards_on_hand(Hand.parse("4D 4S RJ RJ"))

    hand1 = deduce_hand_type(Hand.parse("3D 3S"))
    assert game_state.can_play(hand1, player1.id) is True

    hand2 = deduce_hand_type(Hand.parse("2H* 2S*"))
    game_state.play_cards(player1, hand2)
    assert game_state.current_player_to_play.id == player3.id
    assert game_state.can_play(Hand.parse("4D 4S"), player1.id) is False
    assert game_state.can_play(Hand.parse("4D 4S"), player2.id) is False
    assert game_state.can_play(Hand.parse("4D 4S 4S"), player3.id) is False
    assert game_state.can_play(Hand.parse("4D 4S"), player3.id) is False
    assert game_state.can_play(Hand.parse("RJ RJ"), player3.id) is True


def test_current_player_to_play() -> None:
    game_state, player1, *_ = _state()
    game_state.new_round(start_player=player1)
    assert game_state.current_player_to_play.id == player1.id


def test_save_game_state_equivalent_round_trip(tmp_path) -> None:
    game_state, player1, player2, player3, player4 = _state()
    game_state.new_round(start_player=player1)
    player1.set_cards_on_hand(Hand.parse("3D 3S 3D 2H* 2S*"))
    player2.set_cards_on_hand(Hand.parse("4D 4S"))
    player3.set_cards_on_hand(Hand.parse("4D 4S RJ RJ"))
    player4.set_cards_on_hand(Hand.parse("AD AS"))
    game_state.play_cards(player1, Hand.parse("3D 3S"))
    game_state.play_cards(player2, Hand.parse("4D 4S"))
    game_state.play_cards(player3, Hand.parse("4D 4S"))
    game_state.play_cards(player4, Hand.parse("AD AS"))

    path = tmp_path / "game_state.json"
    path.write_text(json.dumps(game_state.to_json(current_round_only=False)), encoding="utf-8")
    restored = GameState.from_json(json.loads(path.read_text(encoding="utf-8")))
    assert restored.current_round.last_turn.player.id == player4.id
