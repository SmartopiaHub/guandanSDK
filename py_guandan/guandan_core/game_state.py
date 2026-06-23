"""Game-state models compatible with Dart ``game_state.dart``.

This module ports the exported state containers and JSON shapes from the Dart
core. It focuses on deterministic model behavior, round/phase bookkeeping, and
wire-compatible serialization; advanced server orchestration remains in the
Dart game server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from .cards import Card, Hand, PokerCardList, rank_from_value, rank_power
from .player import Player, PlayerPosition, PlayerTeam, next_player
from .utility import can_play as can_play_cards


def is_end_of_round(players: list[Player]) -> bool:
    """Return whether all players with cards belong to one or zero teams."""
    teams_with_cards = {player.team for player in players if player.has_at_least_one_card}
    return len(teams_with_cards) <= 1


def get_player_by_id(players: list[Player], player_id: str) -> Player:
    """Return the player with ``player_id`` or raise ``ValueError``."""
    try:
        return next(player for player in players if player.id == player_id)
    except StopIteration as exc:
        raise ValueError(f"Player with ID {player_id} not found") from exc


class PlayerRank(Enum):
    """Rank of a player in a round result."""

    BANKER = "banker"
    FOLLOWER = "follower"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH = "fifth"
    DWELLER = "dweller"

    @classmethod
    def from_name(cls, name: str) -> "PlayerRank":
        return cls(name)


@dataclass
class TeamScores:
    """Cumulative scores for red and blue teams."""

    red_team_score: int = 0
    blue_team_score: int = 0

    def get_score(self, team: PlayerTeam) -> int:
        return self.red_team_score if team is PlayerTeam.RED_TEAM else self.blue_team_score

    def add_score(self, team: PlayerTeam, score: int) -> None:
        if team is PlayerTeam.RED_TEAM:
            self.red_team_score += score
        else:
            self.blue_team_score += score

    def increase_score(self, team: PlayerTeam) -> None:
        self.add_score(team, 1)

    def to_json(self) -> dict[str, int]:
        return {"redTeam": self.red_team_score, "blueTeam": self.blue_team_score}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TeamScores":
        return cls(red_team_score=data.get("redTeam", 0), blue_team_score=data.get("blueTeam", 0))


@dataclass
class TeamLevelRanks:
    """Current level rank for each team."""

    red_team_level_rank: str = "2"
    blue_team_level_rank: str = "2"

    def get_level_rank(self, team: PlayerTeam) -> str:
        return self.red_team_level_rank if team is PlayerTeam.RED_TEAM else self.blue_team_level_rank

    def set_level_rank(self, team: PlayerTeam, level_rank: str) -> None:
        if team is PlayerTeam.RED_TEAM:
            self.red_team_level_rank = level_rank
        else:
            self.blue_team_level_rank = level_rank

    def to_json(self) -> dict[str, str]:
        return {"redTeam": self.red_team_level_rank, "blueTeam": self.blue_team_level_rank}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TeamLevelRanks":
        return cls(red_team_level_rank=data.get("redTeam", "2"), blue_team_level_rank=data.get("blueTeam", "2"))


@dataclass(eq=False)
class Turn:
    """One player action, including passes."""

    player: Player
    played_hand: Hand
    id: str
    played_time: datetime = field(default_factory=datetime.now)
    bot_code: Optional[str] = None

    @property
    def is_passed(self) -> bool:
        return self.played_hand.is_empty

    def to_json(self) -> dict[str, Any]:
        return {
            "turn_id": self.id,
            "player_id": self.player.id,
            "played_hand": self.played_hand.to_json(),
            "played_time": self.played_time.isoformat(),
            "bot_code": self.bot_code,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: list[Player]) -> "Turn":
        return cls(
            player=get_player_by_id(players, data["player_id"]),
            played_hand=Hand.from_json(data["played_hand"]),
            id=data["turn_id"],
            played_time=datetime.fromisoformat(data["played_time"]),
            bot_code=data.get("bot_code"),
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Turn) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class Phase:
    """A phase starts with one player and contains a sequence of turns."""

    start_player: Player
    id: str = field(default_factory=lambda: str(uuid4()))
    turns: list[Turn] = field(default_factory=list)

    @property
    def is_start_of_phase(self) -> bool:
        return not self.turns

    @property
    def last_turn(self) -> Optional[Turn]:
        return self.turns[-1] if self.turns else None

    @property
    def last_non_pass_turn(self) -> Optional[Turn]:
        return next((turn for turn in reversed(self.turns) if not turn.is_passed), None)

    @property
    def hand_on_table(self) -> Hand:
        return self.last_non_pass_turn.played_hand if self.last_non_pass_turn else Hand.empty_hand()

    def create_turn_id(self) -> str:
        return f"{self.id}_T{len(self.turns) + 1}"

    def append_turn(self, player: Player, cards_played: Hand, bot_code: Optional[str] = None) -> None:
        self.turns.append(Turn(player, cards_played, self.create_turn_id(), bot_code=bot_code or player.bot_code))

    def update_start_player(self, player: Player) -> None:
        self.start_player = player

    def is_end_of_phase(self, players: list[Player]) -> bool:
        if not self.turns:
            return False
        if is_end_of_round(players):
            return True
        last_non_pass = self.last_non_pass_turn
        if last_non_pass is None:
            return False
        index = self.turns.index(last_non_pass)
        players_passed = {turn.player.id for turn in self.turns[index + 1 :] if turn.is_passed}
        return all(
            player.id == last_non_pass.player.id
            or not player.has_at_least_one_card
            or player.id in players_passed
            for player in players
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "phase_id": self.id,
            "start_player_id": self.start_player.id,
            "turns": [turn.to_json() for turn in self.turns],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: list[Player]) -> "Phase":
        phase = cls(start_player=get_player_by_id(players, data["start_player_id"]), id=data["phase_id"])
        phase.turns = [Turn.from_json(turn, players) for turn in data.get("turns", [])]
        return phase


@dataclass
class RoundResult:
    """Outcome of a round."""

    banker: Optional[Player] = None
    follower: Optional[Player] = None
    third: Optional[Player] = None
    fourth: Optional[Player] = None
    fifth: Optional[Player] = None
    dwellers: list[Player] = field(default_factory=list)
    level_rank: Optional[str] = None
    ace_passing_tries_of_blue_team: Optional[int] = None
    ace_passing_tries_of_red_team: Optional[int] = None
    round_id: Optional[str] = None
    team_of_level_rank: Optional[PlayerTeam] = None

    @property
    def team_of_banker(self) -> Optional[PlayerTeam]:
        return self.banker.team if self.banker else None

    def get_rank_of_player(self, player_id: str) -> Optional[PlayerRank]:
        if self.banker and self.banker.id == player_id:
            return PlayerRank.BANKER
        if self.follower and self.follower.id == player_id:
            return PlayerRank.FOLLOWER
        if self.third and self.third.id == player_id:
            return PlayerRank.THIRD
        if self.fourth and self.fourth.id == player_id:
            return PlayerRank.FOURTH
        if self.fifth and self.fifth.id == player_id:
            return PlayerRank.FIFTH
        if any(player.id == player_id for player in self.dwellers):
            return PlayerRank.DWELLER
        return None

    def get_ace_passing_tries(self, team: Optional[PlayerTeam]) -> Optional[int]:
        if team is None:
            return None
        return self.ace_passing_tries_of_red_team if team is PlayerTeam.RED_TEAM else self.ace_passing_tries_of_blue_team

    def set_ace_passing_tries(self, team: PlayerTeam, tries: Optional[int]) -> None:
        if team is PlayerTeam.RED_TEAM:
            self.ace_passing_tries_of_red_team = tries
        else:
            self.ace_passing_tries_of_blue_team = tries

    def increase_ace_passing_tries(self, team: PlayerTeam) -> None:
        current = self.get_ace_passing_tries(team) or 0
        self.set_ace_passing_tries(team, current + 1)

    @property
    def is_ace_passed(self) -> Optional[bool]:
        if self.level_rank != "A" or not self.is_valid_and_complete():
            return None
        banker_team = self.banker.team  # type: ignore[union-attr]
        return banker_team == self.team_of_level_rank and not any(player.team == banker_team for player in self.dwellers)

    @property
    def players_to_pay_tribute(self) -> list[Player]:
        if not self.is_valid_and_complete():
            raise ValueError("Cannot deduce tribute info from an invalid or incomplete round result.")
        return self.dwellers

    @property
    def players_to_receive_tribute(self) -> list[Player]:
        if not self.is_valid_and_complete():
            raise ValueError("Cannot deduce tribute info from an invalid or incomplete round result.")
        return [self.banker, self.follower] if self.banker.team == self.follower.team else [self.banker]  # type: ignore[list-item,union-attr]

    def record_player_finished(self, player: Player) -> None:
        if self.banker is None:
            self.banker = player
        elif self.follower is None:
            self.follower = player
        elif self.banker.team == self.follower.team:
            self.dwellers.append(player)
        else:
            self.third = player

    def is_valid_and_complete(self) -> bool:
        if self.banker is None or self.follower is None:
            return False
        if self.banker.team == self.follower.team:
            return self.third is None and len(self.dwellers) == 2
        return self.third is not None and len(self.dwellers) == 1

    def to_json(self) -> dict[str, Any]:
        def player_json(player: Optional[Player]) -> Optional[dict[str, Any]]:
            return player.to_json(with_cards_on_hand=False, with_played_cards=False) if player else None

        return {
            "banker_id": self.banker.id if self.banker else None,
            "banker": player_json(self.banker),
            "follower_id": self.follower.id if self.follower else None,
            "follower": player_json(self.follower),
            "third_id": self.third.id if self.third else None,
            "third": player_json(self.third),
            "fourth_id": self.fourth.id if self.fourth else None,
            "fourth": player_json(self.fourth),
            "fifth_id": self.fifth.id if self.fifth else None,
            "fifth": player_json(self.fifth),
            "dwellers_id": [player.id for player in self.dwellers],
            "dwellers": [player_json(player) for player in self.dwellers],
            "round_id": self.round_id,
            "ace_passing_tries_redteam": self.ace_passing_tries_of_red_team,
            "ace_passing_tries_blueteam": self.ace_passing_tries_of_blue_team,
            "level_rank": self.level_rank,
            "team_of_level_rank": self.team_of_level_rank.value if self.team_of_level_rank else None,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: Optional[list[Player]] = None) -> "RoundResult":
        def read_player(key: str, id_key: str) -> Optional[Player]:
            if data.get(key) is None:
                return None
            return get_player_by_id(players, data[id_key]) if players is not None else Player.from_json(data[key])

        dwellers = (
            [get_player_by_id(players, player_id) for player_id in data.get("dwellers_id", [])]
            if players is not None
            else [Player.from_json(player) for player in data.get("dwellers", [])]
        )
        team_name = data.get("team_of_level_rank")
        return cls(
            banker=read_player("banker", "banker_id"),
            follower=read_player("follower", "follower_id"),
            third=read_player("third", "third_id"),
            fourth=read_player("fourth", "fourth_id"),
            fifth=read_player("fifth", "fifth_id"),
            dwellers=dwellers,
            round_id=data.get("round_id"),
            ace_passing_tries_of_red_team=data.get("ace_passing_tries_redteam"),
            ace_passing_tries_of_blue_team=data.get("ace_passing_tries_blueteam"),
            level_rank=data.get("level_rank"),
            team_of_level_rank=PlayerTeam.from_name(team_name) if team_name else None,
        )


@dataclass
class Tribute:
    """A tribute exchange between two players."""

    payer: Player
    winner: Optional[Player] = None
    tribute_card: Optional[Card] = None
    return_card: Optional[Card] = None
    payer_bot_code: Optional[str] = None
    winner_bot_code: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        return {
            "payer_id": self.payer.id,
            "payer": self.payer.to_json(with_cards_on_hand=False, with_played_cards=False),
            "receiver_id": self.winner.id if self.winner else None,
            "winner": self.winner.to_json(with_cards_on_hand=False, with_played_cards=False) if self.winner else None,
            "tribute_card": str(self.tribute_card) if self.tribute_card else None,
            "return_card": str(self.return_card) if self.return_card else None,
            "payer_bot_code": self.payer_bot_code,
            "winner_bot_code": self.winner_bot_code,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: Optional[list[Player]] = None) -> "Tribute":
        payer = get_player_by_id(players, data["payer_id"]) if players is not None else Player.from_json(data["payer"])
        winner = None
        if data.get("receiver_id") is not None:
            winner = get_player_by_id(players, data["receiver_id"]) if players is not None else Player.from_json(data["winner"])
        return cls(
            payer=payer,
            winner=winner,
            tribute_card=Card.parse(data["tribute_card"]) if data.get("tribute_card") else None,
            return_card=Card.parse(data["return_card"]) if data.get("return_card") else None,
            payer_bot_code=data.get("payer_bot_code"),
            winner_bot_code=data.get("winner_bot_code"),
        )


@dataclass
class TributeResult:
    """Result of the tribute stage."""

    is_resisted: bool = False
    tributes: list[Tribute] = field(default_factory=list)
    red_jokers: dict[int, int] = field(default_factory=dict)

    def add_tribute(self, tribute: Tribute) -> bool:
        if self.is_resisted or any(t.payer.id == tribute.payer.id for t in self.tributes):
            return False
        self.tributes.append(tribute)
        return True

    def to_json(self) -> dict[str, Any]:
        return {
            "tributes": [tribute.to_json() for tribute in self.tributes],
            "is_resisted": self.is_resisted,
            "red_jokers": {str(key): value for key, value in self.red_jokers.items()},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: Optional[list[Player]] = None) -> "TributeResult":
        return cls(
            is_resisted=data.get("is_resisted", False),
            tributes=[Tribute.from_json(item, players) for item in data.get("tributes", [])],
            red_jokers={int(key): value for key, value in data.get("red_jokers", {}).items()},
        )


@dataclass
class Round:
    """A round consisting of phases and turns."""

    players: list[Player]
    id: str
    level_rank: str = "2"
    previous_round_result: Optional[RoundResult] = None
    start_player: Optional[Player] = None
    creation_time: datetime = field(default_factory=datetime.now)
    tribute_enabled: bool = True
    phases: list[Phase] = field(default_factory=list)
    round_result: RoundResult = None  # type: ignore[assignment]
    tribute_result: TributeResult = field(default_factory=TributeResult)
    hands_at_start: dict[str, list[Card]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.round_result is None:
            self.round_result = RoundResult(
                round_id=self.id,
                level_rank=self.level_rank,
                team_of_level_rank=self.previous_round_result.banker.team if self.previous_round_result and self.previous_round_result.banker else None,
            )

    @property
    def has_phase(self) -> bool:
        return bool(self.phases)

    @property
    def current_phase(self) -> Phase:
        if not self.phases:
            if self.start_player is None:
                raise ValueError("No phase in the round and start player is not set.")
            self.new_phase(self.start_player)
        return self.phases[-1]

    @property
    def has_ended(self) -> bool:
        return is_end_of_round(self.players)

    @property
    def is_tribute_stage_completed(self) -> bool:
        if not self.tribute_enabled or self.previous_round_result is None or self.tribute_result.is_resisted:
            return True
        if self.phases and self.phases[-1].turns:
            return True
        required = len(self.previous_round_result.players_to_pay_tribute)
        return len(self.tribute_result.tributes) == required and all(t.return_card is not None for t in self.tribute_result.tributes)

    @property
    def ready_to_play(self) -> bool:
        return self.is_tribute_stage_completed and self.start_player is not None and all(player.card_count_on_hand == 27 for player in self.players)

    @property
    def is_at_start_of_round(self) -> bool:
        return not self.phases or (len(self.phases) == 1 and self.current_phase.is_start_of_phase)

    @property
    def current_turn_id(self) -> Optional[str]:
        try:
            return self.current_phase.create_turn_id()
        except ValueError:
            return None

    @property
    def last_turn(self) -> Optional[Turn]:
        if not self.phases or (len(self.phases) == 1 and self.current_phase.is_start_of_phase):
            return None
        return self.current_phase.last_turn or self.phases[-2].last_turn

    def create_phase_id(self) -> str:
        return f"{self.id}_P{len(self.phases) + 1}"

    def new_phase(self, start_player: Player, phase_id: Optional[str] = None) -> None:
        self.phases.append(Phase(start_player, phase_id or self.create_phase_id()))

    def update_start_player(self, start_player: Player) -> None:
        if not self.is_at_start_of_round:
            raise ValueError("Cannot update the start player in the middle of a round.")
        self.start_player = start_player
        self.current_phase.update_start_player(start_player)

    def to_json(self, with_cards_on_hand: bool = True, with_played_cards: bool = True) -> dict[str, Any]:
        return {
            "round_id": self.id,
            "creation_time": self.creation_time.isoformat(),
            "start_player_id": self.start_player.id if self.start_player else None,
            "players": [player.to_json(with_cards_on_hand=with_cards_on_hand, with_played_cards=with_played_cards) for player in self.players],
            "level_rank": self.level_rank,
            "round_result": self.round_result.to_json(),
            "previous_round_result": self.previous_round_result.to_json() if self.previous_round_result else None,
            "tribute_result": self.tribute_result.to_json(),
            "hands_at_start": {pid: str(PokerCardList(cards)) for pid, cards in self.hands_at_start.items()},
            "phases": [phase.to_json() for phase in self.phases],
            "tribute_enabled": self.tribute_enabled,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], players: Optional[list[Player]] = None) -> "Round":
        players = players or [Player.from_json(player) for player in data.get("players", [])]
        start_player = get_player_by_id(players, data["start_player_id"]) if data.get("start_player_id") else None
        previous = RoundResult.from_json(data["previous_round_result"], players) if data.get("previous_round_result") else None
        round_obj = cls(
            players=players,
            id=data["round_id"],
            level_rank=data.get("level_rank", "2"),
            previous_round_result=previous,
            start_player=start_player,
            creation_time=datetime.fromisoformat(data["creation_time"]),
            tribute_enabled=data.get("tribute_enabled", True),
        )
        round_obj.phases = [Phase.from_json(item, players) for item in data.get("phases", [])]
        round_obj.round_result = RoundResult.from_json(data["round_result"], players)
        round_obj.tribute_result = TributeResult.from_json(data.get("tribute_result", {}), players)
        round_obj.hands_at_start = {
            pid: PokerCardList.from_string(cards).cards for pid, cards in data.get("hands_at_start", {}).items()
        }
        return round_obj


@dataclass
class RoundSeries:
    """A consecutive series of rounds."""

    start_round_id: str
    end_round_id: Optional[str] = None
    winner_team: Optional[PlayerTeam] = None

    def to_json(self) -> dict[str, Any]:
        return {
            "start_round_id": self.start_round_id,
            "end_round_id": self.end_round_id,
            "winner_team": self.winner_team.value if self.winner_team else None,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RoundSeries":
        winner = data.get("winner_team")
        return cls(data["start_round_id"], end_round_id=data.get("end_round_id"), winner_team=PlayerTeam.from_name(winner) if winner else None)


@dataclass
class GameState:
    """Top-level game state."""

    id: str = ""
    required_players: int = 4
    players: list[Player] = field(default_factory=list)
    team_level_rank: TeamLevelRanks = field(default_factory=TeamLevelRanks)
    team_scores: TeamScores = field(default_factory=TeamScores)
    rounds: list[Round] = field(default_factory=list)
    series: list[RoundSeries] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.required_players != 4:
            raise ValueError("Currently, only 4 players are supported.")

    @property
    def current_round(self) -> Optional[Round]:
        return self.rounds[-1] if self.rounds else None

    @property
    def has_game_started(self) -> bool:
        return self.current_round is not None

    @property
    def current_level_rank(self) -> str:
        return self.current_round.level_rank if self.current_round else "2"

    @property
    def deck_count(self) -> int:
        return round(self.required_players / 2)

    def has_player(self, player_id: str) -> bool:
        return any(player.id == player_id for player in self.players)

    def add_player(self, player: Player) -> None:
        if not self.has_player(player.id):
            self.players.append(player)
            self.players.sort(key=lambda p: p.seat)

    def add_players(self, players: list[Player]) -> None:
        for player in players:
            self.add_player(player)

    def get_player_by_id(self, player_id: str) -> Player:
        return get_player_by_id(self.players, player_id)

    def assign_team(self, seat: int) -> PlayerTeam:
        return PlayerTeam.RED_TEAM if seat % 2 == 1 else PlayerTeam.BLUE_TEAM

    def set_seat(self, player_id: str, seat: int) -> bool:
        if self.current_round or not self.has_player(player_id) or any(p.seat == seat and p.id != player_id for p in self.players):
            return False
        player = self.get_player_by_id(player_id)
        player.seat = seat
        player.team = self.assign_team(seat)
        self.players.sort(key=lambda p: p.seat)
        return True

    @property
    def current_player_to_play(self) -> Optional[Player]:
        try:
            if self.current_round is None or self.current_round.has_ended:
                return None
            phase = self.current_round.current_phase
            if phase.is_end_of_phase(self.players):
                return next_player(phase.last_non_pass_turn.player, self.players, False, True) if phase.last_non_pass_turn else None
            if phase.is_start_of_phase:
                return phase.start_player
            return next_player(phase.last_turn.player, self.players, False, True) if phase.last_turn else None
        except Exception:
            return None

    def new_round(
        self,
        start_player: Optional[Player] = None,
        previous_round_result: Optional[RoundResult] = None,
        round_id: Optional[str] = None,
        level_rank: Optional[str] = None,
        tribute_enabled: bool = True,
    ) -> None:
        round_obj = Round(
            self.players,
            round_id or self.create_round_id(),
            level_rank or "2",
            previous_round_result=previous_round_result,
            start_player=start_player,
            tribute_enabled=tribute_enabled,
        )
        self.rounds.append(round_obj)
        for player in self.players:
            player.cards_on_hand = None
            player.played_cards.clear()

    def create_round_id(self, previous_round_id: Optional[str] = None) -> str:
        previous_round_id = previous_round_id or (self.rounds[-1].id if self.rounds else None)
        if previous_round_id:
            try:
                return f"R{int(previous_round_id[1:]) + 1}"
            except ValueError:
                return "R1"
        return f"R{len(self.rounds) + 1}"

    def can_pass(self) -> bool:
        return self.current_round is not None and not self.current_round.current_phase.is_start_of_phase

    def play_cards(self, player: Player, cards_to_play: Hand, bot_code: Optional[str] = None) -> None:
        if self.current_round is None:
            raise ValueError("No current round.")
        player.play(cards_to_play)
        self.current_round.current_phase.append_turn(player, cards_to_play, bot_code=bot_code)

    def can_play(self, cards_to_play: PokerCardList, player_id: str) -> bool:
        player = self.get_player_by_id(player_id)
        if player.id != (self.current_player_to_play.id if self.current_player_to_play else None):
            return False
        if cards_to_play.is_empty:
            return self.can_pass()
        if not player.has_cards(cards_to_play):
            return False
        return can_play_cards(cards_to_play, self.current_round.current_phase.hand_on_table, number_of_decks=self.deck_count, forced=True)  # type: ignore[union-attr]

    def get_player_by_seat(self, seat: int) -> Player:
        return next(player for player in self.players if player.seat == seat)

    def get_player_by_position(self, anchor_player: Player, position: PlayerPosition) -> Player:
        seat = (anchor_player.seat + position.value_index) % len(self.players)
        return self.get_player_by_seat(len(self.players) if seat == 0 else seat)

    def to_json(
        self,
        include_cards_on_hand_for_players: Optional[list[str]] = None,
        include_played_cards: bool = False,
        current_round_only: bool = True,
        include_player_type_info: bool = False,
    ) -> dict[str, Any]:
        rounds = self.rounds[-1:] if current_round_only and self.rounds else self.rounds
        player_json = []
        for player in self.players:
            data = player.to_json(
                with_cards_on_hand=include_cards_on_hand_for_players is not None and player.id in include_cards_on_hand_for_players,
                with_played_cards=include_played_cards,
                with_player_type=include_player_type_info,
            )
            if not include_player_type_info:
                data["is_human"] = True
                data.pop("bot_code", None)
            player_json.append(data)
        return {
            "game_id": self.id,
            "required_players": self.required_players,
            "players": player_json,
            "team_level_rank": self.team_level_rank.to_json(),
            "team_scores": self.team_scores.to_json(),
            "series": [] if current_round_only else [item.to_json() for item in self.series],
            "rounds": [round_obj.to_json(with_cards_on_hand=False, with_played_cards=False) for round_obj in rounds],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "GameState":
        players = [Player.from_json(player) for player in data.get("players", [])]
        state = cls(id=data.get("game_id", ""), required_players=data.get("required_players", 4))
        state.add_players(players)
        state.team_level_rank = TeamLevelRanks.from_json(data.get("team_level_rank", {}))
        state.team_scores = TeamScores.from_json(data.get("team_scores", {}))
        state.series = [RoundSeries.from_json(item) for item in data.get("series", [])]
        state.rounds = [Round.from_json(item, players=state.players) for item in data.get("rounds", [])]
        return state
