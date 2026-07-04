from guandan_bot.protocol import BotMessage, GameMessageEnvelope
from guandan_core import NewPhaseMessage, ServerPlayHandRequest


def test_protocol_parses_typed_game_payload() -> None:
    message = BotMessage.parse({
        "type": "game_message",
        "session_id": "s1",
        "payload": {"type": "sPlayHandRequest", "turn_id": "t1"},
    })

    assert isinstance(message, GameMessageEnvelope)
    assert isinstance(message.payload, ServerPlayHandRequest)
    assert message.payload.turn_id == "t1"


def test_protocol_round_trips_empty_available_cards() -> None:
    raw = {
        "type": "game_message",
        "session_id": "s1",
        "payload": {"type": "sPlayHandRequest", "available_cards": ""},
    }

    payload = BotMessage.parse(raw).to_dict()["payload"]
    assert payload["available_cards"] == ""


def test_protocol_types_informational_game_payloads() -> None:
    message = BotMessage.parse({
        "type": "game_message",
        "session_id": "s1",
        "payload": {"type": "iNewPhase", "phase_id": "phase-1"},
    })

    assert isinstance(message.payload, NewPhaseMessage)
