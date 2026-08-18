from __future__ import annotations

import json

import pytest

from guandan_bot import (
    BasicBot,
    Bot,
    BotApplication,
    BotMessage,
    GameMessageEnvelope,
    HttpBotServer,
    InvalidBotDecision,
    Participant,
    PlayRequest,
    ReturnCardRequest,
    SessionEnd,
    SessionStart,
    TestGameConfig,
    TributeRequest,
)
from guandan_core import Card, Hand, HandType
from guandan_core.hand_validator import detect_hand
from py_guandan.http import HttpResponseError, http_client


class ThreeMethodBot(Bot):
    def play_hand(self, request: PlayRequest) -> Hand:
        card = min(request.cards, key=lambda item: item.power_rank)
        return Hand([card], HandType.SINGLE, card.power_rank)

    def tribute_card(self, request: TributeRequest) -> Card:
        return max(request.cards, key=lambda item: item.power_rank)

    def return_card(self, request: ReturnCardRequest) -> Card:
        return min(request.cards, key=lambda item: item.power_rank)


def start(application: BotApplication):
    response = application.handle(SessionStart("s1", player_id="p1", seat=1, deck_count=2))
    assert response is not None and response.to_dict()["accepted"] is True


def test_protocol_round_trip() -> None:
    original = GameMessageEnvelope("session", {"type": "iGameStarted", "game_id": "g"}, "request")
    assert BotMessage.parse(original.to_json()) == original


def test_application_dispatches_all_three_decisions() -> None:
    application = BotApplication(ThreeMethodBot, bot_code="example")
    start(application)
    common = {"room_id": "r", "game_id": "g", "player_id": "p1", "round_id": "R1"}

    play = application.handle(GameMessageEnvelope("s1", {
        "type": "sPlayHandRequest", **common, "turn_id": "T1", "available_cards": "3H 4D", "hand_on_table": "empty-0 :", "level_rank": "2",
    }, "play-request"))
    assert play.to_dict()["request_id"] == "play-request"
    assert play.to_dict()["payload"] == {
        "type": "pPlayHandRequest", **common, "bot_code": "example", "cards": "3H", "turn_id": "T1",
    }

    tribute = application.handle(GameMessageEnvelope("s1", {"type": "sTributeCardRequest", **common, "available_cards": "3H RJ"}, "tribute-request"))
    assert tribute.to_dict()["payload"]["tribute_card"] == "RJ"

    returned = application.handle(GameMessageEnvelope("s1", {"type": "sReturnCardRequest", **common, "available_cards": "3H 9D"}, "return-request"))
    assert returned.to_dict()["payload"]["return_card"] == "3H"


def test_broadcast_for_another_player_has_no_response() -> None:
    application = BotApplication(ThreeMethodBot)
    start(application)
    message = GameMessageEnvelope("s1", {"type": "sPlayHandRequest", "available_cards": ""})
    assert application.handle(message) is None


def test_invalid_decision_is_reported_early() -> None:
    class Cheater(ThreeMethodBot):
        def return_card(self, request: ReturnCardRequest) -> Card:
            return Card.parse("RJ")

    application = BotApplication(Cheater)
    start(application)
    with pytest.raises(InvalidBotDecision, match="not in your hand"):
        application.handle(GameMessageEnvelope("s1", {
            "type": "sReturnCardRequest", "available_cards": "3H", "round_id": "R1",
        }))


@pytest.mark.parametrize(
    ("cards", "expected_type", "expected_power"),
    [
        ("2D* 2S*", HandType.PAIR, 15),
        ("2D* 2S* 2C*", HandType.TRIPLE, 15),
        ("2D* 2S* 2C* 2D*", HandType.BOMB, 415),
    ],
)
def test_level_rank_groups_use_promoted_power(
    cards: str,
    expected_type: HandType,
    expected_power: int,
) -> None:
    detected = detect_hand(
        [Card.parse(value, "2") for value in cards.split()],
        level_rank="2",
    )
    assert detected == (expected_type, expected_power)


def test_basic_bot_can_beat_ace_pair_with_level_pair() -> None:
    application = BotApplication(
        lambda: BasicBot(randomize_leads=False),
        bot_code="basic",
    )
    start(application)
    response = application.handle(
        GameMessageEnvelope(
            "s1",
            {
                "type": "sPlayHandRequest",
                "room_id": "r",
                "game_id": "g",
                "player_id": "p1",
                "round_id": "R1",
                "turn_id": "T1",
                "available_cards": "2D* 2S*",
                "hand_on_table": "pair-14 : AH AS",
                "level_rank": "2",
            },
            "play-request",
        )
    )
    assert response is not None
    assert response.to_dict()["payload"]["cards"] == "2D* 2S*"


def test_informational_messages_update_hand_and_reach_hook() -> None:
    seen = []

    class Observer(ThreeMethodBot):
        def on_message(self, message):
            seen.append(message.type.value)

    application = BotApplication(Observer)
    start(application)
    application.handle(GameMessageEnvelope("s1", {"type": "iNewRound", "hand": "3H 4D", "level_rank": "2"}))
    bot = application._sessions["s1"].bot
    assert str(bot.cards_on_hand) == "3H 4D"
    assert seen == ["iNewRound"]
    application.handle(SessionEnd("s1"))
    assert application.session_count == 0


def test_http_transport_lifecycle_and_auth() -> None:
    application = BotApplication(ThreeMethodBot)
    with HttpBotServer(application, invocation_key="secret") as server:
        payload = SessionStart("http-session", player_id="p1", seat=1).to_json().encode()
        sessions_url = f"{server.base_url}/sessions"
        with pytest.raises(HttpResponseError) as error:
            http_client.request_json(
                "POST",
                sessions_url,
                body=json.loads(payload),
            )
        assert error.value.status_code == 401

        response = http_client.request_json(
            "POST",
            sessions_url,
            body=json.loads(payload),
            headers={"Authorization": "Bearer secret"},
        )
        assert response["accepted"] is True
        assert application.session_count == 1

        response = http_client.request_json(
            "DELETE",
            f"{sessions_url}/http-session",
            headers={"X-Api-Key": "secret"},
        )
        assert response["type"] == "session_ended"
        assert application.session_count == 0


def test_game_configuration_matches_benchmark_payload() -> None:
    config = TestGameConfig(
        lobby_url="https://example.test",
        api_key="key",
        participants=(
            Participant.deployed(1, "deployment", bot_definition_id="definition"),
            Participant.builtin(2, "basicBot"),
            Participant.builtin(3),
            Participant.builtin(4),
        ),
        num_rounds=2,
    )
    payload = config.payload()
    assert payload["rule_set"] == "guandan-standard-v1"
    assert payload["options"]["auto_start"] is True
    assert payload["options"]["num_rounds"] == 2
    assert payload["participants"][0]["type"] == "external_bot"


def test_game_configuration_requires_four_seats() -> None:
    with pytest.raises(ValueError, match="exactly seats"):
        TestGameConfig("url", "key", (Participant.builtin(1),))


def test_application_forwards_session_params_to_bot() -> None:
    application = BotApplication(ThreeMethodBot, bot_code="example")
    response = application.handle(
        SessionStart("s2", player_id="p1", seat=1, params={"strength": 25})
    )
    assert response is not None and response.to_dict()["accepted"] is True
    session = application._sessions["s2"]
    assert session.bot.parameters == {"strength": 25}


def test_application_leaves_parameters_none_without_params() -> None:
    application = BotApplication(ThreeMethodBot, bot_code="example")
    application.handle(SessionStart("s3", player_id="p1", seat=2))
    assert application._sessions["s3"].bot.parameters is None
