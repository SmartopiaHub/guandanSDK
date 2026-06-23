"""Python copy of ``player_joined_room_message_test.dart``."""

from __future__ import annotations

from guandan_core.message import PlayerJoinedRoomMessage
from guandan_core.player import Player, PlayerTeam


def test_joining_snapshot_round_trips_auto_delegation_state() -> None:
    message = PlayerJoinedRoomMessage(
        player=Player("player-1", 1, PlayerTeam.RED_TEAM),
        room_id="room-1",
        game_id="game-1",
        auto_delegated=True,
    )

    decoded = PlayerJoinedRoomMessage.from_json(message.to_json())
    assert decoded.auto_delegated is True
