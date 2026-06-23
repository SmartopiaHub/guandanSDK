"""Unit tests for non-rule Python core models."""

from __future__ import annotations

from datetime import datetime

from guandan_core.game_room import GameRoomConfig, RoomMetadata, TimingConfig
from guandan_core.game_state import GameState, Phase, Round, RoundResult, Turn
from guandan_core.message import GameMessageFactory, MessageType
from guandan_core.player import Player, PlayerTeam, get_player_position, next_seat
from guandan_core.cards import Hand


def test_player_json_round_trip_and_card_counts() -> None:
    player = Player.from_json(
        {
            "player_id": "p1",
            "seat": 1,
            "team": "redTeam",
            "display_name": "Ada",
            "bot_model": "basicBot",
            "cards_on_hand": "3H 3D",
            "played_cards": "4S",
        }
    )

    assert player.name == "Ada"
    assert player.is_ai_player
    assert player.card_count_on_hand == 2
    assert player.to_json()["cards_on_hand"] == "3H 3D"


def test_room_metadata_json_round_trip() -> None:
    metadata = RoomMetadata(
        "room-1",
        "creator",
        datetime.fromisoformat("2026-06-23T12:00:00"),
        "owner",
        config=GameRoomConfig(
            required_players=4,
            timing_config=TimingConfig(play_time_limit=30),
            password="secret",
        ),
    )

    parsed = RoomMetadata.from_json(metadata.to_json())
    assert parsed.room_id == "room-1"
    assert parsed.password == "secret"
    assert parsed.config.required_players == 4


def test_generic_message_factory_preserves_fields() -> None:
    message = GameMessageFactory.from_json(
        {
            "type": "sPlayHandRequest",
            "message_id": "m1",
            "hand_on_table": "single-3 : 3H",
        }
    )

    assert message.type is MessageType.S_PLAY_HAND_REQUEST
    assert message.to_json()["hand_on_table"] == "single-3 : 3H"


def test_position_helpers() -> None:
    p1 = Player("p1", 1, PlayerTeam.RED_TEAM)
    p3 = Player("p3", 3, PlayerTeam.RED_TEAM)

    assert next_seat(4, 4) == 1
    assert get_player_position(p1, p3, 4).wire_name == "teamMate"


def test_game_state_round_trip() -> None:
    players = [
        Player("p1", 1, PlayerTeam.RED_TEAM),
        Player("p2", 2, PlayerTeam.BLUE_TEAM),
        Player("p3", 3, PlayerTeam.RED_TEAM),
        Player("p4", 4, PlayerTeam.BLUE_TEAM),
    ]
    turn = Turn(players[0], Hand.parse("single-3 : 3H"), "R1_P1_T1")
    phase = Phase(players[0], "R1_P1", [turn])
    round_obj = Round(players, "R1", start_player=players[0], phases=[phase])
    round_obj.round_result = RoundResult(round_id="R1", level_rank="2")
    state = GameState(id="game-1", players=players, rounds=[round_obj])

    parsed = GameState.from_json(state.to_json(current_round_only=False))
    assert parsed.id == "game-1"
    assert parsed.current_round is not None
    assert parsed.current_round.current_phase.hand_on_table.power == 3
