"""Wire models for the ``guandan-bot-v1`` protocol."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class BotMessage:
    session_id: str
    type: ClassVar[str]

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def parse(cls, value: str | bytes | dict[str, Any]) -> "BotMessage":
        data = value if isinstance(value, dict) else json.loads(value)
        if not isinstance(data, dict):
            raise ValueError("bot message must be a JSON object")
        message_type = data.get("type")
        message_class = _MESSAGE_TYPES.get(message_type)
        if message_class is None:
            raise ValueError(f"unknown bot message type: {message_type!r}")
        return message_class.from_dict(data)


@dataclass(frozen=True)
class SessionStart(BotMessage):
    deployment_id: str | None = None
    bot_definition_id: str | None = None
    player_id: str | None = None
    seat: int | None = None
    rule_set: str | None = None
    protocol_version: str | None = None
    deck_count: int | None = None
    type: ClassVar[str] = "session_start"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionStart":
        return cls(
            session_id=data["session_id"],
            deployment_id=data.get("deployment_id"),
            bot_definition_id=data.get("bot_definition_id"),
            player_id=data.get("player_id"),
            seat=data.get("seat"),
            rule_set=data.get("rule_set"),
            protocol_version=data.get("protocol_version"),
            deck_count=data.get("number_of_standard_decks"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = {"type": self.type, "session_id": self.session_id}
        optional = {
            "deployment_id": self.deployment_id,
            "bot_definition_id": self.bot_definition_id,
            "player_id": self.player_id,
            "seat": self.seat,
            "rule_set": self.rule_set,
            "protocol_version": self.protocol_version,
            "number_of_standard_decks": self.deck_count,
        }
        data.update({key: value for key, value in optional.items() if value is not None})
        return data


@dataclass(frozen=True)
class SessionStarted(BotMessage):
    accepted: bool = True
    type: ClassVar[str] = "session_started"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionStarted":
        return cls(data["session_id"], data.get("accepted", True))

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "session_id": self.session_id, "accepted": self.accepted}


@dataclass(frozen=True)
class SessionEnd(BotMessage):
    type: ClassVar[str] = "session_end"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionEnd":
        return cls(data["session_id"])

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "session_id": self.session_id}


@dataclass(frozen=True)
class SessionEnded(SessionEnd):
    type: ClassVar[str] = "session_ended"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionEnded":
        return cls(data["session_id"])


@dataclass(frozen=True)
class GameMessageEnvelope(BotMessage):
    payload: dict[str, Any]
    request_id: str | None = None
    deadline_millis: int | None = None
    type: ClassVar[str] = "game_message"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameMessageEnvelope":
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("game_message payload must be an object")
        return cls(data["session_id"], payload, data.get("request_id"), data.get("deadline_millis"))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type,
            "session_id": self.session_id,
            "payload": self.payload,
        }
        if self.request_id is not None:
            data["request_id"] = self.request_id
        if self.deadline_millis is not None:
            data["deadline_millis"] = self.deadline_millis
        return data


@dataclass(frozen=True)
class BotError(BotMessage):
    code: str
    message: str
    type: ClassVar[str] = "error"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BotError":
        return cls(data.get("session_id", ""), data.get("code", "unknown_error"), data.get("message", ""))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "code": self.code,
            "message": self.message,
        }


_MESSAGE_TYPES: dict[str, type[BotMessage]] = {
    message.type: message
    for message in (SessionStart, SessionStarted, SessionEnd, SessionEnded, GameMessageEnvelope, BotError)
}

