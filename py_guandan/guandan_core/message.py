"""JSON message models compatible with Dart ``message.dart``.

The Dart package has many concrete message subclasses. Python keeps a small
factory plus generic dataclass that preserves all payload fields, while the
core discriminators and response/payload enums are explicit and type-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .game_room import RoomMetadata
from .game_state import GameState
from .player import Player


class RemovalReason(Enum):
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    KICKED = "kicked"
    UNKNOWN = "unknown"

    @classmethod
    def from_name(cls, name: str) -> "RemovalReason":
        return cls(name)


class ServerResponseCode(Enum):
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


class MessageType(Enum):
    """Message type discriminator used on the game wire protocol."""

    P_CREATE_ROOM_REQUEST = "pCreateRoomRequest"
    P_JOIN_ROOM_REQUEST = "pJoinRoomRequest"
    P_QUIT_ROOM_REQUEST = "pQuitRoomRequest"
    P_PAY_TRIBUTE_REQUEST = "pPayTributeRequest"
    P_PLAY_HAND_REQUEST = "pPlayHandRequest"
    P_MORE_TIME_REQUEST = "pMoreTimeRequest"
    P_SEAT_REQUEST = "pSeatRequest"
    P_RETURN_CARD_REQUEST = "pReturnCardRequest"
    P_START_GAME_REQUEST = "pStartGameRequest"
    P_NEW_ROUND_REQUEST = "pNewRoundRequest"
    S_PLAY_HAND_REQUEST = "sPlayHandRequest"
    S_TRIBUTE_CARD_REQUEST = "sTributeCardRequest"
    S_RETURN_CARD_REQUEST = "sReturnCardRequest"
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
    PREVIOUS_GAME_ROOM = "previousGameRoom"
    JOIN_ROOM_RESPONSE = "joinRoomResponse"
    PLAY_HAND_RESPONSE = "playHandResponse"
    PAY_TRIBUTE_RESPONSE = "payTributeResponse"
    RETURN_CARD_RESPONSE = "returnCardResponse"

    @classmethod
    def from_name(cls, name: str) -> "PayloadType":
        return cls(name)


@dataclass
class MessagePayload:
    """Generic request-result payload preserving Dart wire fields."""

    type: PayloadType
    fields: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"type": self.type.value, **self.fields}

    @classmethod
    def from_json(cls, data: Optional[dict[str, Any]]) -> Optional["MessagePayload"]:
        if not data:
            return None
        payload_type = PayloadType.from_name(data["type"])
        fields = dict(data)
        fields.pop("type", None)
        return cls(payload_type, fields)


@dataclass
class GameMessage:
    """Generic game message preserving all Dart JSON fields."""

    type: MessageType
    fields: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"type": self.type.value, **self.fields}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "GameMessage":
        msg_type = MessageType.from_name(data["type"])
        fields = dict(data)
        fields.pop("type", None)
        if isinstance(fields.get("payload"), dict):
            payload = MessagePayload.from_json(fields["payload"])
            fields["payload"] = payload.to_json() if payload is not None else None
        return cls(msg_type, fields)


class GameMessageFactory:
    """Factory matching Dart ``GameMessageFactory.fromJson`` at the wire level."""

    @staticmethod
    def from_json(data: dict[str, Any]) -> GameMessage:
        if data.get("type") == MessageType.I_PLAYER_JOINED_ROOM.value:
            return PlayerJoinedRoomMessage.from_json(data)
        return GameMessage.from_json(data)


@dataclass
class PlayerJoinedRoomMessage(GameMessage):
    """Message broadcast when a player joins a room."""

    player: Player = None  # type: ignore[assignment]
    room_id: str = ""
    game_id: str = ""
    message_id: Optional[str] = None
    replaced_player_id: Optional[str] = None
    bot_code: Optional[str] = None
    room_info: Optional[RoomMetadata] = None
    game_state: Optional[GameState] = None
    reconnect_token: Optional[str] = None
    auto_delegated: Optional[bool] = None

    def __init__(
        self,
        *,
        player: Player,
        room_id: str,
        game_id: str,
        message_id: Optional[str] = None,
        replaced_player_id: Optional[str] = None,
        bot_code: Optional[str] = None,
        room_info: Optional[RoomMetadata] = None,
        game_state: Optional[GameState] = None,
        reconnect_token: Optional[str] = None,
        auto_delegated: Optional[bool] = None,
    ) -> None:
        super().__init__(MessageType.I_PLAYER_JOINED_ROOM, {})
        self.player = player
        self.room_id = room_id
        self.game_id = game_id
        self.message_id = message_id
        self.replaced_player_id = replaced_player_id
        self.bot_code = bot_code
        self.room_info = room_info
        self.game_state = game_state
        self.reconnect_token = reconnect_token
        self.auto_delegated = auto_delegated

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type.value,
            "message_id": self.message_id,
            "room_id": self.room_id,
            "game_id": self.game_id,
            "player": self.player.to_json(with_cards_on_hand=True),
        }
        if self.bot_code is not None:
            data["bot_code"] = self.bot_code
        if self.replaced_player_id is not None:
            data["replaced_player_id"] = self.replaced_player_id
        if self.room_info is not None:
            data["room_info"] = self.room_info.to_json()
        if self.game_state is not None:
            data["game_state"] = self.game_state.to_json(
                include_played_cards=True,
                include_cards_on_hand_for_players=[p.id for p in self.game_state.players],
                include_player_type_info=True,
            )
        if self.reconnect_token is not None:
            data["reconnect_token"] = self.reconnect_token
        if self.auto_delegated is not None:
            data["auto_delegated"] = self.auto_delegated
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PlayerJoinedRoomMessage":
        return cls(
            message_id=data.get("message_id"),
            player=Player.from_json(data["player"]),
            room_id=data["room_id"],
            game_id=data["game_id"],
            bot_code=data.get("bot_code"),
            replaced_player_id=data.get("replaced_player_id"),
            room_info=RoomMetadata.from_json(data["room_info"]) if data.get("room_info") else None,
            game_state=GameState.from_json(data["game_state"]) if data.get("game_state") else None,
            reconnect_token=data.get("reconnect_token"),
            auto_delegated=data.get("auto_delegated"),
        )
