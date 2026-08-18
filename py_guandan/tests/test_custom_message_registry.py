"""Extension (custom) message type support — mirror of the Dart
``CustomMessageRegistry`` / ``MessageType.custom`` behavior."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from guandan_core.message import (
    GameMessage,
    GameMessageFactory,
    GameRoomMessage,
    MessageType,
    register_custom_type,
)


@dataclass
class ExtensionMessage(GameRoomMessage):
    """A sample extension message following the documented recipe:
    ``type=MessageType.CUSTOM``, an own wire-type subtype, a from_json
    factory registered in the registry."""

    payload: str = ""
    type: MessageType = field(default=MessageType.CUSTOM, init=False)

    @property
    def wire_type(self) -> str:
        return self.WIRE_TYPE

    WIRE_TYPE = "iTestExtension"

    @classmethod
    def from_json(cls, data: dict) -> "ExtensionMessage":
        return cls(
            room_id=data.get("room_id", ""),
            game_id=data.get("game_id", ""),
            message_id=data.get("message_id"),
            payload=data.get("payload", ""),
        )


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    register_custom_type(ExtensionMessage.WIRE_TYPE, ExtensionMessage.from_json)
    yield


def test_custom_enum_member_exists() -> None:
    assert MessageType.CUSTOM.value == "custom"


def test_from_name_resolves_builtins_and_falls_back_to_custom() -> None:
    assert MessageType.from_name("heartbeat") == MessageType.HEARTBEAT
    assert MessageType.from_name("iTestExtension") == MessageType.CUSTOM
    assert MessageType.from_name("nonsense") == MessageType.CUSTOM


def test_registered_custom_type_dispatches_through_factory() -> None:
    parsed = GameMessageFactory.from_json(
        {
            "type": "iTestExtension",
            "message_id": "m1",
            "room_id": "r1",
            "game_id": "g1",
            "payload": "hello",
        }
    )
    assert isinstance(parsed, ExtensionMessage)
    assert parsed.room_id == "r1"
    assert parsed.game_id == "g1"
    assert parsed.payload == "hello"
    assert parsed.message_id == "m1"


def test_custom_type_round_trips_through_factory() -> None:
    original = ExtensionMessage(
        room_id="r1", game_id="g1", message_id="m2", payload="round-trip"
    )
    restored = GameMessageFactory.from_json(original.to_json())
    assert restored.to_json() == original.to_json()


def test_custom_type_emits_own_subtype_on_the_wire() -> None:
    msg = ExtensionMessage(room_id="r1", game_id="g1", payload="hello")
    assert msg.type == MessageType.CUSTOM
    assert msg.wire_type == "iTestExtension"
    assert msg.to_json()["type"] == "iTestExtension"


def test_unknown_unregistered_type_falls_back_to_generic() -> None:
    parsed = GameMessageFactory.from_json({"type": "iUnknownType"})
    assert isinstance(parsed, GameMessage)
    assert parsed.type == MessageType.CUSTOM


def test_builtin_types_still_dispatch_unchanged() -> None:
    parsed = GameMessageFactory.from_json(
        {"type": "heartbeat", "player_id": "p1", "message_id": None}
    )
    assert isinstance(parsed, GameMessage)
    assert parsed.type == MessageType.HEARTBEAT


def test_register_rejects_builtin_collision() -> None:
    with pytest.raises(ValueError, match="collides with a built-in MessageType"):
        register_custom_type("heartbeat", ExtensionMessage.from_json)


def test_re_register_is_idempotent() -> None:
    register_custom_type(ExtensionMessage.WIRE_TYPE, ExtensionMessage.from_json)
    parsed = GameMessageFactory.from_json({"type": "iTestExtension"})
    assert isinstance(parsed, ExtensionMessage)
