"""Player models compatible with Dart ``player.dart``."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .cards import Hand, HandType, PokerCardList


class PlayerTeam(Enum):
    """Teams in a Guandan game."""

    RED_TEAM = "redTeam"
    BLUE_TEAM = "blueTeam"

    @classmethod
    def from_name(cls, name: str) -> "PlayerTeam":
        return cls(name)


class PlayerPosition(Enum):
    """Position relative to an anchor player."""

    SELF = ("self", 0)
    LEFT_OPPONENT = ("leftOpponent", 3)
    TEAM_MATE = ("teamMate", 2)
    RIGHT_OPPONENT = ("rightOpponent", 1)
    OPPOSITE_OPPONENT = ("oppositeOpponent", 4)
    LEFT_TEAM_MATE = ("leftTeamMate", 4)
    RIGHT_TEAM_MATE = ("rightTeamMate", 2)

    def __init__(self, wire_name: str, value_index: int) -> None:
        self.wire_name = wire_name
        self.value_index = value_index


@dataclass
class Player:
    """A player with identity, seat, team, and optional known hand state."""

    id: str
    seat: int
    team: PlayerTeam
    display_name: Optional[str] = None
    bot_code: Optional[str] = None
    cards_on_hand: Optional[PokerCardList] = None
    played_cards: PokerCardList = field(default_factory=PokerCardList.empty)

    @property
    def name(self) -> str:
        return self.display_name or self.id

    @property
    def is_human_player(self) -> bool:
        return self.bot_code is None

    @property
    def is_ai_player(self) -> bool:
        return not self.is_human_player

    @property
    def has_at_least_one_card(self) -> bool:
        return self.card_count_on_hand > 0

    @property
    def card_count_on_hand(self) -> int:
        if self.cards_on_hand is not None:
            return len(self.cards_on_hand)
        return 27 - len(self.played_cards)

    def to_json(
        self,
        with_cards_on_hand: bool = True,
        with_played_cards: bool = True,
        with_player_type: bool = False,
    ) -> dict[str, Any]:
        """Serialize using Dart-compatible JSON keys."""
        data: dict[str, Any] = {
            "player_id": self.id,
            "seat": self.seat,
            "team": self.team.value,
        }
        if self.display_name is not None:
            data["display_name"] = self.display_name
        if self.bot_code is not None:
            data["bot_model"] = self.bot_code
        if with_player_type:
            data["is_human"] = self.is_human_player
            if self.bot_code is not None:
                data["bot_model"] = self.bot_code
        if with_played_cards:
            data["played_cards"] = str(self.played_cards)
        if with_cards_on_hand and self.cards_on_hand is not None:
            data["cards_on_hand"] = str(self.cards_on_hand)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Player":
        """Create a player from Dart-compatible JSON."""
        player = cls(
            id=cls.read_id(data),
            seat=cls.read_seat(data),
            team=cls.read_team(data),
            display_name=cls.read_display_name(data),
            bot_code=cls.read_bot_code(data),
            cards_on_hand=cls.read_cards_on_hand(data),
        )
        player.played_cards = cls.read_played_cards(data)
        return player

    @staticmethod
    def read_id(data: dict[str, Any]) -> str:
        return data["player_id"]

    @staticmethod
    def read_seat(data: dict[str, Any]) -> int:
        return data["seat"]

    @staticmethod
    def read_display_name(data: dict[str, Any]) -> Optional[str]:
        if "display_name" in data:
            return data.get("display_name")
        profile = data.get("profile")
        return profile.get("nickname") if isinstance(profile, dict) else None

    @staticmethod
    def read_bot_code(data: dict[str, Any]) -> Optional[str]:
        if "bot_model" in data:
            return data.get("bot_model")
        profile = data.get("profile")
        if isinstance(profile, dict) and "bot_model" in profile:
            return profile.get("bot_model")
        if "is_human" in data:
            return "basicBot" if data.get("is_human") is False else None
        return None

    @staticmethod
    def read_team(data: dict[str, Any]) -> PlayerTeam:
        return PlayerTeam.from_name(data["team"])

    @staticmethod
    def read_cards_on_hand(data: dict[str, Any]) -> Optional[PokerCardList]:
        cards = data.get("cards_on_hand")
        return None if cards is None else PokerCardList.from_string(cards)

    @staticmethod
    def read_played_cards(data: dict[str, Any]) -> PokerCardList:
        cards = data.get("played_cards")
        return PokerCardList.empty() if cards is None else PokerCardList.from_string(cards)

    def has_cards(self, hand_or_cards: Any) -> bool:
        """Return whether the known hand contains all requested cards."""
        if self.cards_on_hand is None:
            return False
        cards = hand_or_cards.cards if isinstance(hand_or_cards, PokerCardList) else hand_or_cards
        return self.cards_on_hand.has_cards(cards)

    def play(self, hand: Hand) -> None:
        """Remove played cards from hand and add them to played cards."""
        if self.cards_on_hand is not None and len(self.cards_on_hand) > 0:
            self.cards_on_hand.remove_cards(hand.cards)
        self.played_cards.add_all(hand.cards)

    def reset_hands(self) -> None:
        """Forget current hand and clear played cards."""
        self.cards_on_hand = PokerCardList.empty()
        self.played_cards.clear()

    def set_cards_on_hand(self, hand: PokerCardList) -> None:
        """Set the player's hand."""
        self.cards_on_hand = hand if isinstance(hand, Hand) else Hand(hand.cards, HandType.UNKNOWN)

    def deep_copy_with(self, id: Optional[str] = None) -> "Player":
        """Deep-copy the player, optionally replacing the id."""
        return self.deep_copy(self, new_id=id or self.id)

    @classmethod
    def deep_copy(
        cls,
        player: "Player",
        new_id: Optional[str] = None,
        with_played_cards: bool = True,
        with_cards_on_hand: bool = True,
    ) -> "Player":
        """Deep-copy a player, matching Dart ``Player.deepCopy``."""
        return cls(
            id=new_id or player.id,
            seat=player.seat,
            team=player.team,
            display_name=player.display_name,
            bot_code=player.bot_code,
            cards_on_hand=PokerCardList.from_list(player.cards_on_hand.cards)
            if with_cards_on_hand and player.cards_on_hand
            else None,
            played_cards=PokerCardList.from_list(player.played_cards.cards) if with_played_cards else PokerCardList.empty(),
        )

    @classmethod
    def copy(cls, player: "Player", new_id: Optional[str] = None) -> "Player":
        """Shallow-copy a player, matching Dart ``Player.copy``."""
        return cls(
            id=new_id or player.id,
            seat=player.seat,
            team=player.team,
            display_name=player.display_name,
            bot_code=player.bot_code,
            cards_on_hand=player.cards_on_hand,
            played_cards=player.played_cards,
        )


def next_seat(seat: int, max_players: int) -> int:
    """Return the next 1-based seat number."""
    seat = (seat + 1) % max_players
    return max_players if seat == 0 else seat


def next_player(
    current_player: Player,
    players: list[Player],
    team_mate_only: bool,
    nonempty_hand_only: bool,
) -> Optional[Player]:
    """Return the next player matching the requested criteria."""
    for i in range(len(players) - 1):
        seat = next_seat(current_player.seat + i, len(players))
        player = next(p for p in players if p.seat == seat)
        if team_mate_only and player.team != current_player.team:
            continue
        if nonempty_hand_only and not player.has_at_least_one_card:
            continue
        return player
    return None


def get_player_position(anchor_player: Player, player: Player, number_of_players: int) -> PlayerPosition:
    """Return ``player``'s relative position from ``anchor_player``."""
    relative_position = (player.seat - anchor_player.seat + number_of_players) % number_of_players
    if number_of_players == 4:
        return {
            0: PlayerPosition.SELF,
            1: PlayerPosition.RIGHT_OPPONENT,
            2: PlayerPosition.TEAM_MATE,
            3: PlayerPosition.LEFT_OPPONENT,
        }[relative_position]
    if number_of_players == 6:
        return {
            0: PlayerPosition.SELF,
            1: PlayerPosition.RIGHT_OPPONENT,
            2: PlayerPosition.RIGHT_TEAM_MATE,
            3: PlayerPosition.OPPOSITE_OPPONENT,
            4: PlayerPosition.LEFT_TEAM_MATE,
            5: PlayerPosition.LEFT_OPPONENT,
        }[relative_position]
    raise ValueError("Invalid number of players or player positions")
