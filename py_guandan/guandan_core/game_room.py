"""Room configuration models compatible with Dart ``game_room.dart``."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


@dataclass
class TimingConfig:
    """Per-action time limits in seconds.

    ``None`` means the corresponding action is unlimited. Duration-returning
    Dart getters are represented as ``datetime.timedelta`` instances in Python.
    """

    play_time_limit: Optional[int] = None
    tribute_time_limit: Optional[int] = None
    return_time_limit: Optional[int] = None
    sort_time_limit: Optional[int] = None
    opening_time_limit: Optional[int] = None
    delegated_action_delay: Optional[int] = 4

    extra_time = timedelta(seconds=60)

    @property
    def is_timed(self) -> bool:
        """Whether any action time limit is configured."""
        return any(
            value is not None
            for value in (
                self.play_time_limit,
                self.tribute_time_limit,
                self.return_time_limit,
                self.sort_time_limit,
                self.opening_time_limit,
            )
        )

    def copy_with(self, **changes: Any) -> "TimingConfig":
        """Return a copy with selected fields replaced."""
        return replace(self, **{k: v for k, v in changes.items() if v is not None})

    def to_json(self) -> dict[str, Any]:
        """Serialize using Dart-compatible JSON keys."""
        return {
            "play_time_limit": self.play_time_limit,
            "tribute_time_limit": self.tribute_time_limit,
            "return_time_limit": self.return_time_limit,
            "sort_time_limit": self.sort_time_limit,
            "opening_time_limit": self.opening_time_limit,
            "delegated_action_delay": self.delegated_action_delay,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TimingConfig":
        """Create a timing config from Dart-compatible JSON."""
        return cls(
            play_time_limit=data.get("play_time_limit"),
            tribute_time_limit=data.get("tribute_time_limit"),
            return_time_limit=data.get("return_time_limit"),
            sort_time_limit=data.get("sort_time_limit"),
            opening_time_limit=data.get("opening_time_limit"),
            delegated_action_delay=data.get("delegated_action_delay", 4),
        )


class PresetTimingMode(Enum):
    """Predefined room timing presets."""

    FAST_PACED = "fastPaced"
    RELAXED = "relaxed"
    NO_LIMIT = "noLimit"


def create_preset_timing_config(timing_mode: PresetTimingMode) -> TimingConfig:
    """Create a ``TimingConfig`` from a preset."""
    if timing_mode is PresetTimingMode.NO_LIMIT:
        return TimingConfig()
    if timing_mode is PresetTimingMode.FAST_PACED:
        return TimingConfig(play_time_limit=30, tribute_time_limit=60, return_time_limit=90, opening_time_limit=120)
    return TimingConfig(play_time_limit=99, tribute_time_limit=99, return_time_limit=99)


@dataclass
class GameRoomConfig:
    """Immutable-ish gameplay configuration for a room."""

    required_players: int
    ace_passing_enabled: bool = True
    room_tier: int = 0
    tribute_enabled: bool = True
    banker_first_when_no_tribute: bool = True
    allow_extra_time: bool = True
    password: Optional[str] = None
    timing_config: Optional[TimingConfig] = None
    use_bot_nicknames: bool = True
    expose_bot_code: bool = True
    broadcast_player_leave: bool = False

    @classmethod
    def four_players(cls) -> "GameRoomConfig":
        """Create the default four-player room config."""
        return cls(required_players=4)

    @property
    def effective_timing_config(self) -> TimingConfig:
        """Return explicit timing config or the Dart default relaxed preset."""
        return self.timing_config or create_preset_timing_config(PresetTimingMode.RELAXED)

    @property
    def is_timed(self) -> bool:
        return self.effective_timing_config.is_timed

    @property
    def extra_time(self) -> Optional[timedelta]:
        return TimingConfig.extra_time if self.allow_extra_time else None

    def copy_with(self, **changes: Any) -> "GameRoomConfig":
        """Return a copy with selected fields replaced."""
        return replace(self, **{k: v for k, v in changes.items() if v is not None})

    def to_json(self) -> dict[str, Any]:
        """Serialize using Dart-compatible JSON keys."""
        return {
            "required_players": self.required_players,
            "room_tier": self.room_tier,
            "ace_plus_enabled": self.ace_passing_enabled,
            "password": self.password,
            "allow_extra_time": self.allow_extra_time,
            "tribute_enabled": self.tribute_enabled,
            "banker_first_when_no_tribute": self.banker_first_when_no_tribute,
            "use_bot_nicknames": self.use_bot_nicknames,
            "expose_bot_code": self.expose_bot_code,
            "broadcast_player_leave": self.broadcast_player_leave,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "GameRoomConfig":
        """Create a config from Dart-compatible JSON."""
        return cls(
            required_players=data["required_players"],
            room_tier=data.get("room_tier", 0),
            ace_passing_enabled=data.get("ace_plus_enabled", True),
            tribute_enabled=data.get("tribute_enabled", True),
            allow_extra_time=data.get("allow_extra_time", True),
            banker_first_when_no_tribute=data.get("banker_first_when_no_tribute", True),
            password=data.get("password"),
            use_bot_nicknames=data.get("use_bot_nicknames", True),
            expose_bot_code=data.get("expose_bot_code", True),
            broadcast_player_leave=data.get("broadcast_player_leave", False),
        )


@dataclass
class RoomMetadata:
    """Room identity and configuration metadata."""

    room_id: str
    creator_id: str
    creation_time: datetime
    owner_id: Optional[str]
    config: GameRoomConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = GameRoomConfig.four_players()

    @property
    def password(self) -> Optional[str]:
        return self.config.password

    def copy_with(self, **changes: Any) -> "RoomMetadata":
        """Return a copy with selected fields replaced."""
        return replace(self, **{k: v for k, v in changes.items() if v is not None})

    def to_json(self) -> dict[str, Any]:
        """Serialize using Dart-compatible JSON keys."""
        return {
            "room_id": self.room_id,
            "creator_id": self.creator_id,
            "creation_time": self.creation_time.isoformat(),
            "room_owner_id": self.owner_id,
            "config": self.config.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RoomMetadata":
        """Create room metadata from Dart-compatible JSON."""
        return cls(
            room_id=data["room_id"],
            creator_id=data["creator_id"],
            creation_time=datetime.fromisoformat(data["creation_time"]),
            owner_id=data.get("room_owner_id"),
            config=GameRoomConfig.from_json(data["config"]),
        )
