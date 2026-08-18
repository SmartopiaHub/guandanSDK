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


def test_session_start_params_round_trip() -> None:
    from guandan_bot.protocol import SessionStart

    message = SessionStart("s1", params={"strength": 25, "mode": "max"})
    parsed = SessionStart.from_dict(message.to_dict())
    assert parsed.params == {"strength": 25, "mode": "max"}


def test_session_start_omits_params_and_tolerates_missing_key() -> None:
    from guandan_bot.protocol import SessionStart

    # to_dict omits params when None (legacy payloads stay byte-compatible).
    assert "params" not in SessionStart("s1").to_dict()
    # from_dict tolerates payloads without params.
    assert SessionStart.from_dict({"session_id": "s2"}).params is None
