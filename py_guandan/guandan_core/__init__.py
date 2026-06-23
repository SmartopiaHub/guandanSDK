"""Python implementation of the Guandan core model and rules.

The package mirrors the public behavior of the Dart ``guandan_core`` package
while exposing idiomatic Python dataclasses, enums, and snake_case helpers.
Wire strings and JSON keys remain Dart-compatible.
"""

from .cards import Card, Hand, HandType, PokerCardList, parse_hand_on_table
from .game_room import GameRoomConfig, PresetTimingMode, RoomMetadata, TimingConfig
from .game_state import (
    GameState,
    Phase,
    PlayerRank,
    Round,
    RoundResult,
    RoundSeries,
    TeamLevelRanks,
    TeamScores,
    Tribute,
    TributeResult,
    Turn,
)
from .hand_validator import detect_hand, validate_play, validate_return_card, validate_tribute_card
from .message import (
    GameMessage,
    GameMessageFactory,
    MessageType,
    PayloadType,
    PlayerJoinedRoomMessage,
    RemovalReason,
    ServerResponseCode,
)
from .player import Player, PlayerPosition, PlayerTeam, get_player_position, next_player, next_seat

__all__ = [
    "Card",
    "Hand",
    "HandType",
    "PokerCardList",
    "parse_hand_on_table",
    "GameRoomConfig",
    "PresetTimingMode",
    "RoomMetadata",
    "TimingConfig",
    "GameState",
    "Phase",
    "PlayerRank",
    "Round",
    "RoundResult",
    "RoundSeries",
    "TeamLevelRanks",
    "TeamScores",
    "Tribute",
    "TributeResult",
    "Turn",
    "detect_hand",
    "validate_play",
    "validate_return_card",
    "validate_tribute_card",
    "GameMessage",
    "GameMessageFactory",
    "MessageType",
    "PayloadType",
    "PlayerJoinedRoomMessage",
    "RemovalReason",
    "ServerResponseCode",
    "Player",
    "PlayerPosition",
    "PlayerTeam",
    "get_player_position",
    "next_player",
    "next_seat",
]
