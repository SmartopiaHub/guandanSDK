import benchmark

VALID_API_KEY = "sk-zq-abc12345_01234567890123456789012345678901"


def test_api_request_uses_central_http_client(monkeypatch) -> None:
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"ok": True}

    monkeypatch.setattr(benchmark.http_client, "request_json", request_json)

    result = benchmark.api_request(
        "POST",
        "http://127.0.0.1:8686/api/auth/login",
        body={"account": "user", "password": "password"},
    )

    assert result == {"ok": True}
    assert requests[0][0:2] == (
        "POST",
        "http://127.0.0.1:8686/api/auth/login",
    )


def _config_yaml(tmp_path) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(
        f"""
developer_api_key: {VALID_API_KEY}
lobby_url: https://lobby.example
name: Interactive run
num_rounds: 2
total_timeout: 600
heartbeat_timeout: 60
bots:
  seat_1: {{type: builtin, bot_code: strongBot}}
  seat_2: {{type: builtin, bot_code: strongBot}}
  seat_3: {{type: builtin, bot_code: strongBot}}
  seat_4: {{type: builtin, bot_code: strongBot}}
""",
        encoding="utf-8",
    )
    return str(path)


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


def test_interactive_flow_reaches_create_benchmark(
    monkeypatch, tmp_path
) -> None:
    """The interactive benchmark.py flow creates the benchmark with the
    DEV_API_KEY from .env and the config file's name."""
    calls: dict = {}
    monitor_calls: dict = {}

    def fake_create_benchmark(**kwargs):
        calls.update(kwargs)
        return {
            "benchmark_id": "BENCH0001",
            "benchmark_name": "Interactive run",
            "status": "starting",
            "test_game_id": "tg",
            "game_id": "game-1",
            "room_id": "game-1",
            "runtime": _runtime(),
        }

    def fake_monitor(**kwargs):
        monitor_calls.update(kwargs)
        return {"termination": "test_completed", "events": [], "error": None}

    # .env provides the API key + config file + lobby URL, so no prompts
    # and no login/key-creation round-trips happen.
    monkeypatch.setattr(
        benchmark,
        "_load_dotenv",
        lambda: {
            "DEV_API_KEY": VALID_API_KEY,
            "CONFIG_FILE": _config_yaml(tmp_path),
            "LOBBY_SERVER_URL": "https://lobby.example",
        },
    )
    monkeypatch.setattr(benchmark, "check_lobby_reachable", lambda *a, **k: None)
    monkeypatch.setattr(benchmark, "check_game_server_reachable", lambda *a, **k: None)
    monkeypatch.setattr(benchmark, "discover_deployments", lambda *a, **k: [])
    monkeypatch.setattr(
        benchmark,
        "build_participants",
        lambda *a, **k: [
            {"seat": 1, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
        ],
    )
    monkeypatch.setattr(benchmark, "create_benchmark", fake_create_benchmark)
    monkeypatch.setattr(benchmark, "monitor_events", fake_monitor)
    monkeypatch.setattr(benchmark, "print_report", lambda *a, **k: None)

    exit_code = benchmark.main()

    assert exit_code == 0
    assert calls["api_key"] == VALID_API_KEY
    assert calls["name"] == "Interactive run"
    assert calls["num_rounds"] == 2
    # The monitor still consumes the runtime shape unchanged.
    assert monitor_calls["events_url"] == _runtime()["events_url"]
    assert monitor_calls["access_token"] == "runtime-token"
