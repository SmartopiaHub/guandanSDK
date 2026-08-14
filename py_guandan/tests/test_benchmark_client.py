import json

from py_guandan.http import GuandanHttpClient
from guandan_benchmark import client as benchmark_client


def test_benchmark_http_session_ignores_proxies_for_loopback_only() -> None:
    client = GuandanHttpClient()
    assert client.session_for("http://127.0.0.1:8686").trust_env is False
    assert client.session_for("http://localhost:9001").trust_env is False
    assert client.session_for("https://example.com").trust_env is True
    client.close()


# ---------------------------------------------------------------------------
# build_bots
# ---------------------------------------------------------------------------
def test_build_bots_maps_builtin_participants_to_builtin_entries() -> None:
    participants = [
        {"seat": 1, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 2, "type": "internal_bot", "bot_code": "basicBot"},
        {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 4, "type": "internal_bot", "bot_code": "basicBot"},
    ]
    bots = benchmark_client.build_bots(participants)

    assert set(bots.keys()) == {"seat_1", "seat_2", "seat_3", "seat_4"}
    assert bots["seat_1"] == {"type": "builtin", "bot_code": "strongBot"}
    assert bots["seat_2"]["bot_code"] == "basicBot"
    # No deployment_key for builtin entries.
    assert "deployment_key" not in bots["seat_1"]


def test_build_bots_maps_external_participants_with_deployment_key() -> None:
    participants = [
        {
            "seat": 1,
            "type": "external_bot",
            "deployment_id": "dep-123",
            "deployment_key": "secret-key",
        },
        {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
    ]
    bots = benchmark_client.build_bots(participants)

    assert bots["seat_1"] == {
        "type": "deployed",
        "deployment_id": "dep-123",
        "deployment_key": "secret-key",
    }


def test_build_bots_omits_deployment_key_when_absent() -> None:
    participants = [
        {"seat": 1, "type": "external_bot", "deployment_id": "dep-123"},
        {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
    ]
    bots = benchmark_client.build_bots(participants)

    assert bots["seat_1"] == {"type": "deployed", "deployment_id": "dep-123"}


# ---------------------------------------------------------------------------
# create_benchmark
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, status_code: int, body: dict, text: str = ""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._body = body
        self.text = text if text else json.dumps(body)

    def json(self):
        return self._body


def _participants() -> list[dict]:
    return [
        {"seat": 1, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
    ]


def _runtime() -> dict:
    return {
        "runtime_server_id": "server-1",
        "base_url": "http://game-1.example",
        "events_url": "http://game-1.example/api/v1/test-games/tg/events",
        "status_url": "http://game-1.example/api/v1/test-games/tg",
        "cancel_url": "http://game-1.example/api/v1/test-games/tg/cancel",
        "replay_url": "http://game-1.example/api/v1/test-games/tg/replay",
        "access_token": "runtime-token",
        "expires_in_seconds": 3600,
    }


def _ok_response() -> _FakeResponse:
    return _FakeResponse(
        201,
        {
            "benchmark_id": "BENCH0001",
            "benchmark_name": "My run",
            "status": "starting",
            "test_game_id": "tg",
            "game_id": "game-1",
            "room_id": "game-1",
            "runtime": _runtime(),
        },
    )


def test_create_benchmark_posts_to_benchmark_endpoint_with_auth_headers(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return _ok_response()

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    result = benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=_participants(),
        num_rounds=2,
    )

    assert result is not None
    assert captured["url"] == "https://lobby.example/api/benchmarks"
    headers = captured["headers"]
    assert headers["Authorization"] == "Bearer sk-zq-test"
    assert headers["Content-Type"] == "application/json"
    assert "Idempotency-Key" in headers
    assert headers["Idempotency-Key"] != ""


def test_create_benchmark_body_shape(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _ok_response()

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=_participants(),
        num_rounds=4,
        num_series=2,
        name="Nightly regression",
        total_timeout=600,
        heartbeat_timeout=30,
    )

    body = captured["json"]
    assert body["name"] == "Nightly regression"
    assert body["num_rounds"] == 4
    assert body["num_series"] == 2
    assert body["total_timeout"] == 600
    assert body["heartbeat_timeout"] == 30
    assert set(body["bots"].keys()) == {"seat_1", "seat_2", "seat_3", "seat_4"}
    assert body["bots"]["seat_1"] == {"type": "builtin", "bot_code": "strongBot"}


def test_create_benchmark_omits_name_when_empty(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _ok_response()

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=_participants(),
        num_rounds=2,
        name="",
    )

    assert "name" not in captured["json"]


def test_create_benchmark_passes_deployment_key_through(monkeypatch) -> None:
    captured: dict = {}
    participants = [
        {
            "seat": 1,
            "type": "external_bot",
            "deployment_id": "dep-123",
            "deployment_key": "private-key",
        },
        {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
        {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
    ]

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _ok_response()

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=participants,
        num_rounds=2,
    )

    assert captured["json"]["bots"]["seat_1"] == {
        "type": "deployed",
        "deployment_id": "dep-123",
        "deployment_key": "private-key",
    }


def test_create_benchmark_parses_response_with_runtime_shape(monkeypatch) -> None:
    def fake_post(url, **kwargs):
        return _ok_response()

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    result = benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=_participants(),
        num_rounds=2,
    )

    assert result["benchmark_id"] == "BENCH0001"
    assert result["benchmark_name"] == "My run"
    assert result["status"] == "starting"
    assert result["test_game_id"] == "tg"
    # The runtime shape is identical to create_test_game so the SSE monitor
    # can consume it unchanged.
    assert result["runtime"]["events_url"].endswith("/events")
    assert result["runtime"]["access_token"] == "runtime-token"
    assert result["runtime"]["cancel_url"].endswith("/cancel")


def test_create_benchmark_returns_none_on_failure(monkeypatch) -> None:
    def fake_post(url, **kwargs):
        return _FakeResponse(
            409,
            {"code": "benchmark_limit_reached", "message": "limit reached"},
        )

    monkeypatch.setattr(benchmark_client, "_post", fake_post)

    result = benchmark_client.create_benchmark(
        lobby_url="https://lobby.example",
        api_key="sk-zq-test",
        participants=_participants(),
        num_rounds=2,
    )

    assert result is None
