from __future__ import annotations

import json
import threading
import time

import yaml

from guandan_bot import GameMessageEnvelope, SessionStart
from py_guandan.http import http_client
from proxy_bot import ProxyBotApplication, ProxyHttpServer


def test_proxy_round_trip_and_state() -> None:
    app = ProxyBotApplication(action_timeout=2)
    assert app.handle(SessionStart("s1", player_id="p1", seat=1)).accepted
    app.handle(
        GameMessageEnvelope(
            "s1",
            {
                "type": "iNewRound",
                "room_id": "r",
                "game_id": "g",
                "round_id": "R1",
                "level_rank": "2",
                "hand": "3H 3D 4S",
                "players": [
                    {"player_id": "p1", "seat": 1, "team": "redTeam"},
                    {"player_id": "p2", "seat": 2, "team": "blueTeam"},
                ],
            },
        )
    )
    result = {}

    def request() -> None:
        result["response"] = app.handle(
            GameMessageEnvelope(
                "s1",
                {
                    "type": "sPlayHandRequest",
                    "room_id": "r",
                    "game_id": "g",
                    "player_id": "p1",
                    "round_id": "R1",
                    "turn_id": "T1",
                    "available_cards": "3H 3D 4S",
                    "hand_on_table": "empty-0 :",
                    "level_rank": "2",
                },
                "req1",
            )
        )

    thread = threading.Thread(target=request)
    thread.start()
    for _ in range(100):
        if app.requests(game_id="g")["pending"]:
            break
        time.sleep(0.01)
    app.submit_action("3H 3D", game_id="g")
    thread.join(timeout=2)
    assert result["response"].to_dict()["payload"]["cards"] == "3H 3D"
    state = app.states(session_id="s1")
    assert state["round"]["initial_cards"] == "3H 3D 4S"


def test_public_http_api_needs_no_auth() -> None:
    app = ProxyBotApplication()
    app.handle(SessionStart("s1", player_id="p1", seat=1))
    server = ProxyHttpServer(app, host="127.0.0.1", port=0, invocation_key="secret")
    server.start(background=True)
    try:
        request_response = http_client.request("GET", f"{server.base_url}/request")
        assert request_response.json()[0]["session_id"] == "s1"
        response = http_client.request("GET", f"{server.base_url}/state")
        assert yaml.safe_load(response.text)[0]["session_id"] == "s1"
        help_response = http_client.request("GET", f"{server.base_url}/help")
        assert "POST /action" in help_response.text
        session = http_client.request_json(
            "POST",
            f"{server.base_url}/sessions",
            body=json.loads(SessionStart("s2:test", player_id="p2", seat=2).to_json()),
            headers={"Authorization": "Bearer secret"},
        )
        assert session["accepted"]
        response = http_client.request(
            "POST",
            f"{server.base_url}/sessions/s2%3Atest/messages",
            json={
                "type": "game_message",
                "session_id": "s2:test",
                "payload": {"type": "iGameStarted", "game_id": "g2"},
            },
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 204
    finally:
        server.close()
