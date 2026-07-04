"""JSON message models compatible with Dart ``message.dart``.

The Dart package has many concrete message subclasses. This module provides a
complete set of typed Python dataclasses mirroring every message, payload, and
helper type defined in the Dart ``message.dart``, along with a factory that
dispatches raw JSON to the correct typed class.

Wire strings and JSON keys remain Dart-compatible at all times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .cards import Card, Hand, PokerCardList
from .game_room import GameRoomConfig, RoomMetadata
from .game_state import (
    GameState,
    PlayerRank,
    Round,
    RoundResult,
    TeamLevelRanks,
    TeamScores,
    TributeResult,
)
from .player import Player, PlayerTeam


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════


class RemovalReason(Enum):
    """Reason a player was removed from a game room."""

    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    KICKED = "kicked"
    UNKNOWN = "unknown"

    @classmethod
    def from_name(cls, name: str) -> "RemovalReason":
        return cls(name)


class ServerResponseCode(Enum):
    """Represents the outcome of a request processed by the server."""

    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    UNKNOWN_MESSAGE = "unknownMessage"
    EXTRA_TIME_NOT_ALLOWED = "extraTimeNotAllowed"
    NOT_IN_GAME_ROOM = "notInGameRoom"
    PLAYER_ID_NOT_FOUND = "playerIdNotFound"
    ROOM_NOT_FOUND = "roomNotFound"
    ROOM_FULL = "roomFull"
    ROOM_EXISTS = "roomExists"
    ALREADY_IN_ROOM = "alreadyInRoom"
    GAME_ALREADY_STARTED = "gameAlreadyStarted"
    INVALID_HAND = "invalidHand"
    INVALID_TRIBUTE_CARD = "invalidTributeCard"
    INVALID_RETURN_CARD = "invalidReturnCard"
    NOT_ROOM_OWNER = "notRoomOwner"
    ROUND_NOT_ENDED = "roundNotEnded"
    ALREADY_PAID_TRIBUTE = "alreadyPaidTribute"
    ALREADY_RETURNED_TRIBUTE = "alreadyReturnedTribute"
    INVALID_TOKEN = "invalidToken"
    NOT_AUTHORIZED = "notAuthorized"
    INVALID_SEAT = "invalidSeat"
    SEAT_NOT_AVAILABLE = "seatNotAvailable"

    @classmethod
    def from_name(cls, name: str) -> "ServerResponseCode":
        return cls(name)

    @classmethod
    def from_index(cls, index: int) -> "ServerResponseCode":
        """Parses a ServerResponseCode from its ordinal index."""
        return list(cls)[index]


class MessageType(Enum):
    """Message type discriminator used on the game wire protocol.

    Naming convention:
    - ``pXxxRequest`` — player-to-server request.
    - ``sXxxRequest`` — server-to-player request.
    - ``iXxx`` — informational broadcast.
    """

    # ── Player-to-server requests ───────────────────────────────────────────
    P_CREATE_ROOM_REQUEST = "pCreateRoomRequest"
    P_JOIN_ROOM_REQUEST = "pJoinRoomRequest"
    P_QUIT_ROOM_REQUEST = "pQuitRoomRequest"
    P_PAY_TRIBUTE_REQUEST = "pPayTributeRequest"
    P_PLAY_HAND_REQUEST = "pPlayHandRequest"
    P_EXTRA_TIME_REQUEST = "pExtraTimeRequest"
    P_SEAT_REQUEST = "pSeatRequest"
    P_RETURN_CARD_REQUEST = "pReturnCardRequest"
    P_START_GAME_REQUEST = "pStartGameRequest"
    P_NEW_ROUND_REQUEST = "pNewRoundRequest"

    # ── Server-to-player requests ───────────────────────────────────────────
    S_PLAY_HAND_REQUEST = "sPlayHandRequest"
    S_TRIBUTE_CARD_REQUEST = "sTributeCardRequest"
    S_RETURN_CARD_REQUEST = "sReturnCardRequest"

    # ── Informational broadcasts ────────────────────────────────────────────
    I_GAME_ROOM_CREATED = "iGameRoomCreated"
    I_PLAYER_JOINED_ROOM = "iPlayerJoinedRoom"
    I_PLAYER_QUIT_ROOM = "iPlayerQuitRoom"
    I_PLAYER_REMOVED_FROM_ROOM = "iPlayerRemovedFromRoom"
    I_ROOM_OWNER = "iRoomOwner"
    I_GAME_ROOM_CLOSED = "iGameRoomClosed"
    I_SERVER_CLOSED = "iServerClosed"
    I_PLAYER_SEAT = "iPlayerSeat"
    I_GAME_STARTED = "iGameStarted"
    I_NEW_ROUND = "iNewRound"
    I_ROUND_ENDED = "iRoundEnded"
    I_START_PLAYER = "iStartPlayer"
    I_NEW_PHASE = "iNewPhase"
    I_HAND_PLAYED = "iHandPlayed"
    I_CARDS_ON_HAND = "iCardsOnHand"
    I_TIME_OUT = "iTimeOut"
    I_PLAYER_EMPTIED_HAND = "iPlayerEmptiedHand"
    I_ROUND_RESULT = "iRoundResult"
    I_JIE_FENG = "iJieFeng"
    I_GAME_ENDED = "iGameEnded"
    I_TEAM_SCORES = "iTeamScores"
    I_TRIBUTE_CARD = "iTributeCard"
    I_TRIBUTE_RESISTANCE = "iTributeResistance"
    I_RETURN_CARD = "iReturnCard"
    I_TRIBUTE_RESULT = "iTributeResult"
    I_MORE_TIME_GRANTED = "iMoreTimeGranted"
    I_REQUEST_RESULT = "iRequestResult"
    HEARTBEAT = "heartbeat"
    AUTO_DELEGATED = "autoDelegated"

    @classmethod
    def from_name(cls, name: str) -> "MessageType":
        return cls(name)


class PayloadType(Enum):
    """Identifies the type of a MessagePayload embedded in a RequestResultMessage."""

    PREVIOUS_GAME_ROOM = "previousGameRoom"
    JOIN_ROOM_RESPONSE = "joinRoomResponse"
    PLAY_HAND_RESPONSE = "playHandResponse"
    PAY_TRIBUTE_RESPONSE = "payTributeResponse"
    RETURN_CARD_RESPONSE = "returnCardResponse"

    @classmethod
    def from_name(cls, name: str) -> "PayloadType":
        return cls(name)


# ═══════════════════════════════════════════════════════════════════════════════
# Payloads (embedded in RequestResultMessage)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MessagePayload:
    """Abstract base for message payloads embedded in RequestResultMessage.

    Subclasses are dispatched by :meth:`MessagePayload.from_json` based on the
    ``"type"`` discriminator.
    """

    type: PayloadType

    def to_json(self) -> dict[str, Any]:
        return {"type": self.type.value}

    @staticmethod
    def from_json(json: Optional[dict[str, Any]]) -> Optional["MessagePayload"]:
        """Deserializes a MessagePayload from JSON, dispatching to the correct subclass."""
        if not json:
            return None
        payload_type = PayloadType.from_name(json["type"])
        if payload_type == PayloadType.PREVIOUS_GAME_ROOM:
            return PreviousGameRoomPayload.from_json(json)
        elif payload_type == PayloadType.JOIN_ROOM_RESPONSE:
            return JoinRoomResponsePayload.from_json(json)
        elif payload_type == PayloadType.PLAY_HAND_RESPONSE:
            return PlayHandResponsePayload.from_json(json)
        elif payload_type == PayloadType.PAY_TRIBUTE_RESPONSE:
            return PayTributeResponsePayload.from_json(json)
        elif payload_type == PayloadType.RETURN_CARD_RESPONSE:
            return ReturnCardResponsePayload.from_json(json)
        return None


@dataclass
class PreviousGameRoomPayload(MessagePayload):
    """Payload carrying the player's previous game room information."""

    room_info: RoomMetadata
    type: PayloadType = field(default=PayloadType.PREVIOUS_GAME_ROOM, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["room_info"] = self.room_info.to_json()
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PreviousGameRoomPayload":
        return cls(room_info=RoomMetadata.from_json(json["room_info"]))


@dataclass
class JoinRoomResponsePayload(MessagePayload):
    """Payload for a failed join-room request, carrying room info and bot list."""

    room_info: RoomMetadata
    bots: list[Player] = field(default_factory=list)
    type: PayloadType = field(default=PayloadType.JOIN_ROOM_RESPONSE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["room_info"] = self.room_info.to_json()
        json["bots"] = [
            bot.to_json(with_cards_on_hand=False, with_played_cards=False) for bot in self.bots
        ]
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "JoinRoomResponsePayload":
        bots = [Player.from_json(b) for b in json.get("bots", [])]
        return cls(room_info=RoomMetadata.from_json(json["room_info"]), bots=bots)


@dataclass
class PlayHandResponsePayload(MessagePayload):
    """Payload for a failed play-hand request, carrying the invalid hand."""

    player_id: str = ""
    cards: PokerCardList = field(default_factory=PokerCardList)
    type: PayloadType = field(default=PayloadType.PLAY_HAND_RESPONSE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["cards"] = str(self.cards)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayHandResponsePayload":
        return cls(
            player_id=json.get("player_id", ""),
            cards=PokerCardList.from_string(json.get("cards", "")),
        )


@dataclass
class PayTributeResponsePayload(MessagePayload):
    """Payload for a failed pay-tribute request, carrying the invalid tribute card."""

    player_id: str = ""
    tribute_card: Optional[Card] = None
    type: PayloadType = field(default=PayloadType.PAY_TRIBUTE_RESPONSE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        if self.tribute_card is not None:
            json["tribute_card"] = str(self.tribute_card)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PayTributeResponsePayload":
        tribute_card = None
        if "tribute_card" in json and json["tribute_card"]:
            tribute_card = Card.parse(json["tribute_card"])
        return cls(player_id=json.get("player_id", ""), tribute_card=tribute_card)


@dataclass
class ReturnCardResponsePayload(MessagePayload):
    """Payload for a failed return-card request, carrying the invalid return card."""

    player_id: str = ""
    return_card: Optional[Card] = None
    type: PayloadType = field(default=PayloadType.RETURN_CARD_RESPONSE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        if self.return_card is not None:
            json["return_card"] = str(self.return_card)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ReturnCardResponsePayload":
        return_card = None
        if "return_card" in json and json["return_card"]:
            return_card = Card.parse(json["return_card"])
        return cls(player_id=json.get("player_id", ""), return_card=return_card)


# ═══════════════════════════════════════════════════════════════════════════════
# BotSelectionData
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BotSelectionData:
    """Specifies which bot to use for auto-delegation.

    Sent from client to server when a player enables auto-play with a specific
    bot choice. The server omits this field in broadcast messages.
    """

    type: str  # "builtin" or "deployed"
    bot_code: str
    deployment_id: Optional[str] = None
    bot_definition_id: Optional[str] = None
    base_url: Optional[str] = None
    transport_type: Optional[str] = None
    protocol_version: Optional[str] = None
    authorization_api_key: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        json: dict[str, Any] = {"type": self.type, "bot_code": self.bot_code}
        if self.deployment_id is not None:
            json["deployment_id"] = self.deployment_id
        if self.bot_definition_id is not None:
            json["bot_definition_id"] = self.bot_definition_id
        if self.base_url is not None:
            json["base_url"] = self.base_url
        if self.transport_type is not None:
            json["transport_type"] = self.transport_type
        if self.protocol_version is not None:
            json["protocol_version"] = self.protocol_version
        if self.authorization_api_key is not None:
            json["authorization_api_key"] = self.authorization_api_key
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "BotSelectionData":
        return cls(
            type=json["type"],
            bot_code=json["bot_code"],
            deployment_id=json.get("deployment_id"),
            bot_definition_id=json.get("bot_definition_id"),
            base_url=json.get("base_url"),
            transport_type=json.get("transport_type"),
            protocol_version=json.get("protocol_version"),
            authorization_api_key=json.get("authorization_api_key"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Base message classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class GameMessage:
    """Base class for all messages exchanged between client and game server."""

    type: MessageType
    message_id: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        json: dict[str, Any] = {"type": self.type.value}
        if self.message_id is not None:
            json["message_id"] = self.message_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "GameMessage":
        return cls(
            type=MessageType.from_name(json["type"]),
            message_id=json.get("message_id"),
        )


@dataclass
class GameRoomMessage(GameMessage):
    """Base class for messages scoped to a specific game room.

    Extends GameMessage with a room_id and game_id. Most game-related messages
    inherit from this class, except for RequestResultMessage (which may carry
    its own optional room_id).
    """

    room_id: str = ""
    game_id: str = ""

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["room_id"] = self.room_id
        json["game_id"] = self.game_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "GameRoomMessage":
        return cls(
            type=MessageType.from_name(json["type"]),
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
        )


@dataclass
class ServerRequestMessage(GameRoomMessage):
    """Abstract base for server-to-player request messages within a game room.

    Adds timeout, player_id, and round_id to GameRoomMessage.
    """

    player_id: str = ""
    round_id: str = ""
    timeout: Optional[int] = None  # seconds, or None if no limit

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["round_id"] = self.round_id
        if self.timeout is not None:
            json["timeout"] = self.timeout
        return json


@dataclass
class PlayerRequestMessage(GameRoomMessage):
    """Abstract base for player-to-server request messages within a game room."""

    player_id: str = ""

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        return json


# ═══════════════════════════════════════════════════════════════════════════════
# Informational broadcast messages (iXxx)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class GameRoomCreatedMessage(GameRoomMessage):
    """Broadcast to the room creator when a game room is successfully created."""

    room_info: Optional[RoomMetadata] = None
    players: list[Player] = field(default_factory=list)
    type: MessageType = field(default=MessageType.I_GAME_ROOM_CREATED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.room_info is not None:
            json["room_info"] = self.room_info.to_json()
        json["players"] = [p.to_json(with_cards_on_hand=False) for p in self.players]
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "GameRoomCreatedMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            room_info=RoomMetadata.from_json(json["room_info"]) if json.get("room_info") else None,
            players=[Player.from_json(p) for p in json.get("players", [])],
        )


@dataclass
class PlayerJoinedRoomMessage(GameRoomMessage):
    """Broadcast when a player joins a game room.

    Sent to the joining player with room_info, game_state, and reconnect_token.
    Broadcast to other players without those fields.
    """

    player: Optional[Player] = None
    replaced_player_id: Optional[str] = None
    bot_code: Optional[str] = None
    room_info: Optional[RoomMetadata] = None
    game_state: Optional[GameState] = None
    reconnect_token: Optional[str] = None
    auto_delegated: Optional[bool] = None
    type: MessageType = field(default=MessageType.I_PLAYER_JOINED_ROOM, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.player is not None:
            json["player"] = self.player.to_json(with_cards_on_hand=True)
        if self.bot_code is not None:
            json["bot_code"] = self.bot_code
        if self.replaced_player_id is not None:
            json["replaced_player_id"] = self.replaced_player_id
        if self.room_info is not None:
            json["room_info"] = self.room_info.to_json()
        if self.game_state is not None:
            json["game_state"] = self.game_state.to_json(
                include_played_cards=True,
                include_cards_on_hand_for_players=[p.id for p in self.game_state.players],
                include_player_type_info=True,
            )
        if self.reconnect_token is not None:
            json["reconnect_token"] = self.reconnect_token
        if self.auto_delegated is not None:
            json["auto_delegated"] = self.auto_delegated
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerJoinedRoomMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player=Player.from_json(json["player"]) if json.get("player") else None,
            bot_code=json.get("bot_code"),
            replaced_player_id=json.get("replaced_player_id"),
            room_info=RoomMetadata.from_json(json["room_info"]) if json.get("room_info") else None,
            game_state=GameState.from_json(json["game_state"]) if json.get("game_state") else None,
            reconnect_token=json.get("reconnect_token"),
            auto_delegated=json.get("auto_delegated"),
        )


@dataclass
class PlayerQuitRoomMessage(GameRoomMessage):
    """Broadcast when a player quits the game room.

    If the game is in progress, replacement_player identifies the bot that
    takes over the departing player's seat.
    """

    player_id: str = ""
    replacement_player: Optional[Player] = None
    type: MessageType = field(default=MessageType.I_PLAYER_QUIT_ROOM, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        if self.replacement_player is not None:
            json["replacement_player"] = self.replacement_player.to_json(with_cards_on_hand=False)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerQuitRoomMessage":
        replacement = None
        if "replacement_player" in json and json["replacement_player"] is not None:
            replacement = Player.from_json(json["replacement_player"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            replacement_player=replacement,
        )


@dataclass
class PlayerRemovedMessage(GameRoomMessage):
    """Sent to a player when they are removed from the room."""

    player_id: str = ""
    reason: Optional[RemovalReason] = None
    type: MessageType = field(default=MessageType.I_PLAYER_REMOVED_FROM_ROOM, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        if self.reason is not None:
            json["reason"] = self.reason.value
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerRemovedMessage":
        reason = None
        if json.get("reason"):
            reason = RemovalReason.from_name(json["reason"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            reason=reason,
        )


@dataclass
class RoomOwnerMessage(GameRoomMessage):
    """Broadcast when the room owner changes."""

    owner_id: str = ""
    type: MessageType = field(default=MessageType.I_ROOM_OWNER, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["owner_id"] = self.owner_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RoomOwnerMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            owner_id=json.get("owner_id", ""),
        )


@dataclass
class GameRoomClosedMessage(GameRoomMessage):
    """Broadcast when the game room is closed."""

    type: MessageType = field(default=MessageType.I_GAME_ROOM_CLOSED, init=False)

    def to_json(self) -> dict[str, Any]:
        return super().to_json()

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "GameRoomClosedMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
        )


@dataclass
class ServerClosedMessage(GameMessage):
    """Broadcast when the game server is shutting down."""

    reason: Optional[str] = None
    type: MessageType = field(default=MessageType.I_SERVER_CLOSED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.reason is not None:
            json["reason"] = self.reason
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ServerClosedMessage":
        return cls(message_id=json.get("message_id"), reason=json.get("reason"))


@dataclass
class PlayerSeatMessage(GameRoomMessage):
    """Broadcast when a player takes or changes a seat in the room."""

    player_id: str = ""
    seat: int = 0
    team: Optional[PlayerTeam] = None
    type: MessageType = field(default=MessageType.I_PLAYER_SEAT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["seat"] = self.seat
        if self.team is not None:
            json["team"] = self.team.value
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerSeatMessage":
        team = None
        if json.get("team"):
            team = PlayerTeam.from_name(json["team"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            seat=json.get("seat", 0),
            team=team,
        )


@dataclass
class NewRoundMessage(GameRoomMessage):
    """Broadcast to all players when a new round starts."""

    round_id: str = ""
    start_player_id: Optional[str] = None
    level_rank: str = "2"
    team_level_rank: Optional[TeamLevelRanks] = None
    previous_round_result: Optional[RoundResult] = None
    players: list[Player] = field(default_factory=list)
    hand: Optional[PokerCardList] = None
    type: MessageType = field(default=MessageType.I_NEW_ROUND, init=False)

    @property
    def is_first_round(self) -> bool:
        return self.previous_round_result is None

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["round_id"] = self.round_id
        if self.start_player_id is not None:
            json["start_player_id"] = self.start_player_id
        json["level_rank"] = self.level_rank
        if self.team_level_rank is not None:
            json["team_level_rank"] = self.team_level_rank.to_json()
        if self.previous_round_result is not None:
            json["previous_round_result"] = self.previous_round_result.to_json()
        json["players"] = [p.to_json(with_cards_on_hand=False) for p in self.players]
        if self.hand is not None:
            json["hand"] = str(self.hand)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "NewRoundMessage":
        players = [Player.from_json(p) for p in json.get("players", [])]
        prev_result = None
        if json.get("previous_round_result"):
            prev_result = RoundResult.from_json(json["previous_round_result"], players)
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            round_id=json.get("round_id", ""),
            start_player_id=json.get("start_player_id"),
            level_rank=json.get("level_rank", "2"),
            team_level_rank=TeamLevelRanks.from_json(json["team_level_rank"])
            if json.get("team_level_rank")
            else None,
            previous_round_result=prev_result,
            players=players,
            hand=PokerCardList.from_string(json.get("hand", ""))
            if json.get("hand")
            else None,
        )


@dataclass
class RoundEndedMessage(GameRoomMessage):
    """Broadcast when a round ends, carrying the full Round object."""

    round_id: str = ""
    round: Optional[Round] = None
    type: MessageType = field(default=MessageType.I_ROUND_ENDED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["round_id"] = self.round_id
        if self.round is not None:
            json["round"] = self.round.to_json()
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RoundEndedMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            round_id=json.get("round_id", ""),
            round=Round.from_json(json["round"]) if json.get("round") else None,
        )


@dataclass
class StartPlayerMessage(GameRoomMessage):
    """Broadcast to inform players who the start player is for a round or phase."""

    start_player_id: str = ""
    round_id: str = ""
    phase_id: str = ""
    type: MessageType = field(default=MessageType.I_START_PLAYER, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["start_player_id"] = self.start_player_id
        json["round_id"] = self.round_id
        json["phase_id"] = self.phase_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "StartPlayerMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            start_player_id=json.get("start_player_id", ""),
            round_id=json.get("round_id", ""),
            phase_id=json.get("phase_id", ""),
        )


@dataclass
class NewPhaseMessage(GameRoomMessage):
    """Broadcast when a new phase (turn cycle) starts within a round."""

    phase_id: str = ""
    start_player_id: str = ""
    type: MessageType = field(default=MessageType.I_NEW_PHASE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["phase_id"] = self.phase_id
        json["start_player_id"] = self.start_player_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "NewPhaseMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            phase_id=json.get("phase_id", ""),
            start_player_id=json.get("start_player_id", ""),
        )


@dataclass
class HandPlayedMessage(GameRoomMessage):
    """Broadcast when a player successfully plays a hand of cards."""

    player_id: str = ""
    round_id: str = ""
    phase_id: str = ""
    turn_id: str = ""
    cards: Optional[Hand] = None
    seat: int = 0
    bot_code: Optional[str] = None
    type: MessageType = field(default=MessageType.I_HAND_PLAYED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["round_id"] = self.round_id
        json["phase_id"] = self.phase_id
        json["turn_id"] = self.turn_id
        if self.cards is not None:
            json["cards"] = str(self.cards)
        json["seat"] = self.seat
        if self.bot_code is not None:
            json["bot_code"] = self.bot_code
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "HandPlayedMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            round_id=json.get("round_id", ""),
            phase_id=json.get("phase_id", ""),
            turn_id=json.get("turn_id", ""),
            cards=Hand.parse(json.get("cards", "")) if json.get("cards") else None,
            seat=json.get("seat", 0),
            bot_code=json.get("bot_code"),
        )

    def __repr__(self) -> str:
        return (
            f"HandPlayedMessage(type={self.type.value}, player_id={self.player_id}, "
            f"seat={self.seat}, game_id={self.game_id}, round_id={self.round_id}, "
            f"phase_id={self.phase_id}, turn_id={self.turn_id}, cards={self.cards})"
        )


@dataclass
class CardsOnHandMessage(GameRoomMessage):
    """Sent to a player with the remaining card counts of other players."""

    cards_on_hand: dict[str, Optional[PokerCardList]] = field(default_factory=dict)
    type: MessageType = field(default=MessageType.I_CARDS_ON_HAND, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["cards_on_hand"] = {
            k: (str(v) if v is not None else None) for k, v in self.cards_on_hand.items()
        }
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "CardsOnHandMessage":
        raw = json.get("cards_on_hand", {})
        cards_on_hand = {
            k: (PokerCardList.from_string(v) if v is not None else None)
            for k, v in raw.items()
        }
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            cards_on_hand=cards_on_hand,
        )


@dataclass
class PlayerTimeoutMessage(GameRoomMessage):
    """Sent to all players when a player times out on a server request."""

    player_id: str = ""
    request: Optional[MessageType] = None
    round_id: Optional[str] = None
    turn_id: Optional[str] = None
    type: MessageType = field(default=MessageType.I_TIME_OUT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        if self.request is not None:
            json["request"] = self.request.value
        if self.round_id is not None:
            json["round_id"] = self.round_id
        if self.turn_id is not None:
            json["turn_id"] = self.turn_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerTimeoutMessage":
        request = None
        if json.get("request"):
            request = MessageType.from_name(json["request"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            request=request,
            round_id=json.get("round_id"),
            turn_id=json.get("turn_id"),
        )


@dataclass
class PlayerEmptiedHandMessage(GameRoomMessage):
    """Broadcast when a player empties their hand (plays their last card)."""

    player_id: str = ""
    round_id: str = ""
    player_rank: Optional[PlayerRank] = None
    type: MessageType = field(default=MessageType.I_PLAYER_EMPTIED_HAND, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["round_id"] = self.round_id
        if self.player_rank is not None:
            json["player_rank"] = self.player_rank.value
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerEmptiedHandMessage":
        player_rank = None
        if json.get("player_rank"):
            player_rank = PlayerRank.from_name(json["player_rank"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            round_id=json.get("round_id", ""),
            player_rank=player_rank,
        )


@dataclass
class RoundResultMessage(GameRoomMessage):
    """Broadcast with the (potentially partial) result of a round."""

    round_result: Optional[RoundResult] = None
    is_partial: bool = False
    emptied_by_player_id: Optional[str] = None
    type: MessageType = field(default=MessageType.I_ROUND_RESULT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.round_result is not None:
            json["round_result"] = self.round_result.to_json()
        if self.emptied_by_player_id is not None:
            json["emptied_by"] = self.emptied_by_player_id
        json["is_partial"] = self.is_partial
        return json

    @classmethod
    def from_json(
        cls, json: dict[str, Any], *, players: Optional[list[Player]] = None
    ) -> "RoundResultMessage":
        round_result = None
        if json.get("round_result"):
            round_result = RoundResult.from_json(json["round_result"], players)
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            round_result=round_result,
            is_partial=json.get("is_partial", False),
            emptied_by_player_id=json.get("emptied_by"),
        )


@dataclass
class JieFengMessage(GameRoomMessage):
    """Broadcast when a player 接风 (leads next phase due to teammate emptying hand)."""

    player_id: str = ""
    phase_id: str = ""
    type: MessageType = field(default=MessageType.I_JIE_FENG, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["phase_id"] = self.phase_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "JieFengMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            phase_id=json.get("phase_id", ""),
        )


@dataclass
class TeamScoresMessage(GameRoomMessage):
    """Broadcast when team scores are updated."""

    scores: Optional[TeamScores] = None
    type: MessageType = field(default=MessageType.I_TEAM_SCORES, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.scores is not None:
            json["team_scores"] = self.scores.to_json()
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "TeamScoresMessage":
        scores = None
        if json.get("team_scores"):
            scores = TeamScores.from_json(json["team_scores"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            scores=scores,
        )


@dataclass
class TributeCardMessage(GameRoomMessage):
    """Broadcast when a tribute card (进贡) is paid by one player to another."""

    payer_id: str = ""
    winner_id: Optional[str] = None
    round_id: str = ""
    tribute: Optional[Card] = None
    type: MessageType = field(default=MessageType.I_TRIBUTE_CARD, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["payer_id"] = self.payer_id
        if self.winner_id is not None:
            json["winner_id"] = self.winner_id
        json["round_id"] = self.round_id
        if self.tribute is not None:
            json["tribute"] = str(self.tribute)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "TributeCardMessage":
        tribute = None
        if json.get("tribute"):
            tribute = Card.parse(json["tribute"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            payer_id=json.get("payer_id", ""),
            winner_id=json.get("winner_id"),
            round_id=json.get("round_id", ""),
            tribute=tribute,
        )


@dataclass
class TributeResistanceMessage(GameRoomMessage):
    """Broadcast when tribute is resisted (抗贡)."""

    round_id: str = ""
    start_player_id: str = ""
    red_joker_counts: dict[int, int] = field(default_factory=dict)
    type: MessageType = field(default=MessageType.I_TRIBUTE_RESISTANCE, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["round_id"] = self.round_id
        json["start_player_id"] = self.start_player_id
        json["red_joker_counts"] = {str(k): v for k, v in self.red_joker_counts.items()}
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "TributeResistanceMessage":
        raw = json.get("red_joker_counts", {})
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            round_id=json.get("round_id", ""),
            start_player_id=json.get("start_player_id", ""),
            red_joker_counts={int(k): v for k, v in raw.items()},
        )


@dataclass
class ReturnCardMessage(GameRoomMessage):
    """Broadcast when a card is returned (还牌) in response to receiving a tribute."""

    payer_id: str = ""
    winner_id: str = ""
    round_id: str = ""
    return_card: Optional[Card] = None
    type: MessageType = field(default=MessageType.I_RETURN_CARD, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["payer_id"] = self.payer_id
        json["winner_id"] = self.winner_id
        json["round_id"] = self.round_id
        if self.return_card is not None:
            json["return_card"] = str(self.return_card)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ReturnCardMessage":
        return_card = None
        if json.get("return_card"):
            return_card = Card.parse(json["return_card"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            payer_id=json.get("payer_id", ""),
            winner_id=json.get("winner_id", ""),
            round_id=json.get("round_id", ""),
            return_card=return_card,
        )


@dataclass
class TributeResultMessage(GameRoomMessage):
    """Broadcast when all tributes and returns for a round are complete."""

    tribute_result: Optional[TributeResult] = None
    round_id: str = ""
    type: MessageType = field(default=MessageType.I_TRIBUTE_RESULT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.tribute_result is not None:
            json["tribute_result"] = self.tribute_result.to_json()
        json["round_id"] = self.round_id
        return json

    @classmethod
    def from_json(
        cls, json: dict[str, Any], *, players: Optional[list[Player]] = None
    ) -> "TributeResultMessage":
        tribute_result = None
        if json.get("tribute_result"):
            tribute_result = TributeResult.from_json(json["tribute_result"], players)
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            tribute_result=tribute_result,
            round_id=json.get("round_id", ""),
        )


@dataclass
class MoreTimeGrantedMessage(GameRoomMessage):
    """Sent to a player when additional time is granted for their current action."""

    player_id: str = ""
    new_allocated_seconds: int = 0
    type: MessageType = field(default=MessageType.I_MORE_TIME_GRANTED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["new_allocated_seconds"] = self.new_allocated_seconds
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "MoreTimeGrantedMessage":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            new_allocated_seconds=json.get("new_allocated_seconds", 0),
        )


@dataclass
class RequestResultMessage(GameMessage):
    """Sent to a player with the result of a previous request.

    Unlike most messages, this extends GameMessage directly (not GameRoomMessage)
    so it can carry an optional room_id.
    """

    player_id: Optional[str] = None
    request: Optional[MessageType] = None
    result: ServerResponseCode = ServerResponseCode.SUCCESS
    room_id: Optional[str] = None
    payload: Optional[MessagePayload] = None
    type: MessageType = field(default=MessageType.I_REQUEST_RESULT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.player_id is not None:
            json["player_id"] = self.player_id
        if self.request is not None:
            json["request"] = self.request.value
        json["result"] = self.result.value
        if self.payload is not None:
            json["payload"] = self.payload.to_json()
        if self.room_id is not None:
            json["room_id"] = self.room_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RequestResultMessage":
        request = None
        if json.get("request"):
            request = MessageType.from_name(json["request"])
        return cls(
            message_id=json.get("message_id"),
            player_id=json.get("player_id"),
            request=request,
            result=ServerResponseCode.from_name(json.get("result", "success")),
            payload=MessagePayload.from_json(json.get("payload")),
            room_id=json.get("room_id"),
        )


@dataclass
class AutoDelegationMessage(GameRoomMessage):
    """Sent by a player to enable/disable auto-delegation (托管), and broadcast by server."""

    player_id: str = ""
    auto_delegated: bool = False
    bot_selection: Optional[BotSelectionData] = None
    type: MessageType = field(default=MessageType.AUTO_DELEGATED, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        json["auto_delegated"] = self.auto_delegated
        if self.bot_selection is not None:
            json["bot_selection"] = self.bot_selection.to_json()
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "AutoDelegationMessage":
        bot_selection = None
        if json.get("bot_selection"):
            bot_selection = BotSelectionData.from_json(json["bot_selection"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            auto_delegated=json.get("auto_delegated", False),
            bot_selection=bot_selection,
        )


@dataclass
class HeartbeatMessage(GameMessage):
    """Periodic heartbeat sent by clients to keep the WebSocket connection alive."""

    player_id: str = ""
    type: MessageType = field(default=MessageType.HEARTBEAT, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["player_id"] = self.player_id
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "HeartbeatMessage":
        return cls(message_id=json.get("message_id"), player_id=json.get("player_id", ""))


# ═══════════════════════════════════════════════════════════════════════════════
# Server-to-player request messages (sXxxRequest)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ServerPlayHandRequest(ServerRequestMessage):
    """Sent by the server to a player when it is their turn to play cards."""

    hand_on_table: Optional[Hand] = None
    seat_of_hand_on_table: Optional[int] = None
    level_rank: str = "2"
    turn_id: str = ""
    available_cards: Optional[PokerCardList] = None
    game_state_snapshot: Optional[GameState] = None
    type: MessageType = field(default=MessageType.S_PLAY_HAND_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.hand_on_table is not None:
            json["hand_on_table"] = str(self.hand_on_table)
        json["turn_id"] = self.turn_id
        if self.available_cards is not None:
            json["available_cards"] = str(self.available_cards)
        json["level_rank"] = self.level_rank
        if self.seat_of_hand_on_table is not None:
            json["seat_of_hand_on_table"] = self.seat_of_hand_on_table
        if self.game_state_snapshot is not None:
            json["game_state_snapshot"] = self.game_state_snapshot.to_json(
                include_cards_on_hand_for_players=[self.player_id],
                include_played_cards=True,
            )
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ServerPlayHandRequest":
        seat = json.get("seat_of_hand_on_table")
        if seat is not None:
            seat = int(seat)
        level_rank = json.get("level_rank", "2")
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            timeout=json.get("timeout"),
            round_id=json.get("round_id", ""),
            hand_on_table=Hand.parse(json.get("hand_on_table", ""))
            if json.get("hand_on_table")
            else None,
            seat_of_hand_on_table=seat,
            turn_id=json.get("turn_id", ""),
            level_rank=level_rank,
            available_cards=PokerCardList.from_string(
                json.get("available_cards", ""), level_rank
            )
            if "available_cards" in json
            else None,
            game_state_snapshot=GameState.from_json(json["game_state_snapshot"])
            if json.get("game_state_snapshot")
            else None,
        )


@dataclass
class ServerTributeRequest(ServerRequestMessage):
    """Sent by the server to a player requesting them to select a tribute card (进贡)."""

    available_cards: Optional[PokerCardList] = None
    type: MessageType = field(default=MessageType.S_TRIBUTE_CARD_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.available_cards is not None:
            json["available_cards"] = str(self.available_cards)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ServerTributeRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            timeout=json.get("timeout"),
            round_id=json.get("round_id", ""),
            available_cards=PokerCardList.from_string(json.get("available_cards", ""))
            if "available_cards" in json
            else None,
        )


@dataclass
class ServerReturnCardRequest(ServerRequestMessage):
    """Sent by the server to a player requesting them to return a card (还牌)."""

    available_cards: Optional[PokerCardList] = None
    type: MessageType = field(default=MessageType.S_RETURN_CARD_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.available_cards is not None:
            json["available_cards"] = str(self.available_cards)
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ServerReturnCardRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            timeout=json.get("timeout"),
            round_id=json.get("round_id", ""),
            available_cards=PokerCardList.from_string(json.get("available_cards", ""))
            if "available_cards" in json
            else None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Player-to-server request messages (pXxxRequest)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class JoinRoomRequest(PlayerRequestMessage):
    """Player-to-server request to join a game room."""

    replaced_player_id: Optional[str] = None
    display_name: Optional[str] = None
    join_ticket: Optional[str] = None
    reconnect_token: Optional[str] = None
    type: MessageType = field(default=MessageType.P_JOIN_ROOM_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.replaced_player_id is not None:
            json["replaced_player_id"] = self.replaced_player_id
        if self.display_name is not None:
            json["display_name"] = self.display_name
        if self.join_ticket is not None:
            json["join_ticket"] = self.join_ticket
        if self.reconnect_token is not None:
            json["reconnect_token"] = self.reconnect_token
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "JoinRoomRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            replaced_player_id=json.get("replaced_player_id"),
            display_name=json.get("display_name"),
            join_ticket=json.get("join_ticket"),
            reconnect_token=json.get("reconnect_token"),
        )


@dataclass
class QuitRoomRequest(PlayerRequestMessage):
    """Player-to-server request to leave the current game room."""

    type: MessageType = field(default=MessageType.P_QUIT_ROOM_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        return super().to_json()

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "QuitRoomRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
        )


@dataclass
class PlayerPlayHandRequest(PlayerRequestMessage):
    """Player-to-server request to play a hand of cards."""

    cards: Optional[PokerCardList] = None
    round_id: str = ""
    turn_id: str = ""
    bot_code: Optional[str] = None
    type: MessageType = field(default=MessageType.P_PLAY_HAND_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.cards is not None:
            json["cards"] = str(self.cards)
        json["round_id"] = self.round_id
        json["turn_id"] = self.turn_id
        if self.bot_code is not None:
            json["bot_code"] = self.bot_code
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerPlayHandRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            cards=PokerCardList.from_string(json.get("cards", "")) if "cards" in json else None,
            round_id=json.get("round_id", ""),
            turn_id=json.get("turn_id", ""),
            bot_code=json.get("bot_code"),
        )


@dataclass
class PlayerPayTributeRequest(PlayerRequestMessage):
    """Player-to-server request to pay a tribute card (进贡)."""

    tribute: Optional[Card] = None
    round_id: str = ""
    bot_code: Optional[str] = None
    type: MessageType = field(default=MessageType.P_PAY_TRIBUTE_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.tribute is not None:
            json["tribute_card"] = str(self.tribute)
        json["round_id"] = self.round_id
        if self.bot_code is not None:
            json["bot_code"] = self.bot_code
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerPayTributeRequest":
        tribute = None
        if json.get("tribute_card"):
            tribute = Card.parse(json["tribute_card"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            tribute=tribute,
            round_id=json.get("round_id", ""),
            bot_code=json.get("bot_code"),
        )


@dataclass
class PlayerReturnCardRequest(PlayerRequestMessage):
    """Player-to-server request to return a card (还牌) in response to receiving a tribute."""

    return_card: Optional[Card] = None
    round_id: str = ""
    bot_code: Optional[str] = None
    type: MessageType = field(default=MessageType.P_RETURN_CARD_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.return_card is not None:
            json["return_card"] = str(self.return_card)
        json["round_id"] = self.round_id
        if self.bot_code is not None:
            json["bot_code"] = self.bot_code
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "PlayerReturnCardRequest":
        return_card = None
        if json.get("return_card"):
            return_card = Card.parse(json["return_card"])
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            return_card=return_card,
            round_id=json.get("round_id", ""),
            bot_code=json.get("bot_code"),
        )


@dataclass
class NewRoundRequest(PlayerRequestMessage):
    """Player-to-server request to start the next round."""

    type: MessageType = field(default=MessageType.P_NEW_ROUND_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        return super().to_json()

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "NewRoundRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
        )


@dataclass
class StartGameRequest(PlayerRequestMessage):
    """Player-to-server request (from room owner) to start the game."""

    game_state_snapshot: Optional[GameState] = None
    start_player_seat: Optional[int] = None
    level_rank: Optional[str] = None
    fill_with_bots: bool = True
    type: MessageType = field(default=MessageType.P_START_GAME_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        if self.game_state_snapshot is not None:
            player_ids = [p.id for p in self.game_state_snapshot.players]
            json["game_state_snapshot"] = self.game_state_snapshot.to_json(
                include_cards_on_hand_for_players=player_ids,
                include_played_cards=True,
                include_player_type_info=True,
            )
            json["start_player_seat"] = self.start_player_seat
            json["level_rank"] = self.level_rank
            json["fill_with_bots"] = self.fill_with_bots
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "StartGameRequest":
        start_player_seat = json.get("start_player_seat")
        if start_player_seat is not None:
            start_player_seat = int(start_player_seat)
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            game_state_snapshot=GameState.from_json(json["game_state_snapshot"])
            if json.get("game_state_snapshot")
            else None,
            start_player_seat=start_player_seat,
            level_rank=json.get("level_rank"),
            fill_with_bots=json.get("fill_with_bots", True),
        )


@dataclass
class CreateRoomRequest(PlayerRequestMessage):
    """Player-to-server request to create a new game room."""

    room_name: str = ""
    room_config: Optional[GameRoomConfig] = None
    bots: Optional[dict[int, str]] = None
    type: MessageType = field(default=MessageType.P_CREATE_ROOM_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["room_name"] = self.room_name
        if self.room_config is not None:
            json["room_config"] = self.room_config.to_json()
        if self.bots is not None:
            json["bots"] = {str(seat): code for seat, code in self.bots.items()}
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "CreateRoomRequest":
        bots = None
        if json.get("bots"):
            bots = {int(k): v for k, v in json["bots"].items()}
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            room_name=json.get("room_name", ""),
            room_config=GameRoomConfig.from_json(json["room_config"])
            if json.get("room_config")
            else None,
            bots=bots,
        )


@dataclass
class ExtraTimeRequest(PlayerRequestMessage):
    """Player-to-server request for additional time on the current action."""

    round_id: str = ""
    turn_id: Optional[str] = None
    seconds: Optional[int] = None
    type: MessageType = field(default=MessageType.P_EXTRA_TIME_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["round_id"] = self.round_id
        if self.turn_id is not None:
            json["turn_id"] = self.turn_id
        if self.seconds is not None:
            json["seconds"] = self.seconds
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ExtraTimeRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            round_id=json.get("round_id", ""),
            turn_id=json.get("turn_id") if "turn_id" in json else None,
            seconds=json.get("seconds") if "seconds" in json else None,
        )


@dataclass
class SeatRequest(PlayerRequestMessage):
    """Player-to-server request to change to a different seat in the room."""

    new_seat: int = 0
    type: MessageType = field(default=MessageType.P_SEAT_REQUEST, init=False)

    def to_json(self) -> dict[str, Any]:
        json = super().to_json()
        json["new_seat"] = self.new_seat
        return json

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "SeatRequest":
        return cls(
            message_id=json.get("message_id"),
            room_id=json.get("room_id", ""),
            game_id=json.get("game_id", ""),
            player_id=json.get("player_id", ""),
            new_seat=json.get("new_seat", 0),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Factory (JSON → typed message dispatch)
# ═══════════════════════════════════════════════════════════════════════════════


class GameMessageFactory:
    """Factory matching Dart ``GameMessageFactory.fromJson`` at the wire level.

    Dispatches raw JSON to the correct typed message class based on the
    ``"type"`` discriminator field.
    """

    @staticmethod
    def from_json(data: dict[str, Any]) -> GameMessage:
        msg_type = data.get("type", "")
        try:
            mt = MessageType.from_name(msg_type)
        except ValueError:
            return GameMessage.from_json(data)

        # ── Player-to-server requests ───────────────────────────────────────
        if mt == MessageType.P_CREATE_ROOM_REQUEST:
            return CreateRoomRequest.from_json(data)
        if mt == MessageType.P_JOIN_ROOM_REQUEST:
            return JoinRoomRequest.from_json(data)
        if mt == MessageType.P_QUIT_ROOM_REQUEST:
            return QuitRoomRequest.from_json(data)
        if mt == MessageType.P_PAY_TRIBUTE_REQUEST:
            return PlayerPayTributeRequest.from_json(data)
        if mt == MessageType.P_PLAY_HAND_REQUEST:
            return PlayerPlayHandRequest.from_json(data)
        if mt == MessageType.P_EXTRA_TIME_REQUEST:
            return ExtraTimeRequest.from_json(data)
        if mt == MessageType.P_SEAT_REQUEST:
            return SeatRequest.from_json(data)
        if mt == MessageType.P_RETURN_CARD_REQUEST:
            return PlayerReturnCardRequest.from_json(data)
        if mt == MessageType.P_START_GAME_REQUEST:
            return StartGameRequest.from_json(data)
        if mt == MessageType.P_NEW_ROUND_REQUEST:
            return NewRoundRequest.from_json(data)

        # ── Server-to-player requests ───────────────────────────────────────
        if mt == MessageType.S_PLAY_HAND_REQUEST:
            return ServerPlayHandRequest.from_json(data)
        if mt == MessageType.S_TRIBUTE_CARD_REQUEST:
            return ServerTributeRequest.from_json(data)
        if mt == MessageType.S_RETURN_CARD_REQUEST:
            return ServerReturnCardRequest.from_json(data)

        # ── Informational broadcasts ────────────────────────────────────────
        if mt == MessageType.I_GAME_ROOM_CREATED:
            return GameRoomCreatedMessage.from_json(data)
        if mt == MessageType.I_PLAYER_JOINED_ROOM:
            return PlayerJoinedRoomMessage.from_json(data)
        if mt == MessageType.I_PLAYER_QUIT_ROOM:
            return PlayerQuitRoomMessage.from_json(data)
        if mt == MessageType.I_PLAYER_REMOVED_FROM_ROOM:
            return PlayerRemovedMessage.from_json(data)
        if mt == MessageType.I_ROOM_OWNER:
            return RoomOwnerMessage.from_json(data)
        if mt == MessageType.I_GAME_ROOM_CLOSED:
            return GameRoomClosedMessage.from_json(data)
        if mt == MessageType.I_SERVER_CLOSED:
            return ServerClosedMessage.from_json(data)
        if mt == MessageType.I_PLAYER_SEAT:
            return PlayerSeatMessage.from_json(data)
        if mt == MessageType.I_NEW_ROUND:
            return NewRoundMessage.from_json(data)
        if mt == MessageType.I_ROUND_ENDED:
            return RoundEndedMessage.from_json(data)
        if mt == MessageType.I_START_PLAYER:
            return StartPlayerMessage.from_json(data)
        if mt == MessageType.I_NEW_PHASE:
            return NewPhaseMessage.from_json(data)
        if mt == MessageType.I_HAND_PLAYED:
            return HandPlayedMessage.from_json(data)
        if mt == MessageType.I_CARDS_ON_HAND:
            return CardsOnHandMessage.from_json(data)
        if mt == MessageType.I_TIME_OUT:
            return PlayerTimeoutMessage.from_json(data)
        if mt == MessageType.I_PLAYER_EMPTIED_HAND:
            return PlayerEmptiedHandMessage.from_json(data)
        if mt == MessageType.I_ROUND_RESULT:
            return RoundResultMessage.from_json(data)
        if mt == MessageType.I_JIE_FENG:
            return JieFengMessage.from_json(data)
        if mt == MessageType.I_TEAM_SCORES:
            return TeamScoresMessage.from_json(data)
        if mt == MessageType.I_TRIBUTE_CARD:
            return TributeCardMessage.from_json(data)
        if mt == MessageType.I_TRIBUTE_RESISTANCE:
            return TributeResistanceMessage.from_json(data)
        if mt == MessageType.I_RETURN_CARD:
            return ReturnCardMessage.from_json(data)
        if mt == MessageType.I_TRIBUTE_RESULT:
            return TributeResultMessage.from_json(data)
        if mt == MessageType.I_MORE_TIME_GRANTED:
            return MoreTimeGrantedMessage.from_json(data)
        if mt == MessageType.I_REQUEST_RESULT:
            return RequestResultMessage.from_json(data)
        if mt == MessageType.HEARTBEAT:
            return HeartbeatMessage.from_json(data)
        if mt == MessageType.AUTO_DELEGATED:
            return AutoDelegationMessage.from_json(data)

        # Fallback: generic GameMessage preserving all fields
        return GameMessage.from_json(data)
