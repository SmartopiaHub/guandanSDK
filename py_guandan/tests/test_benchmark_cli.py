from benchmark import _resolve_lobby_url
from guandan_benchmark import runner
from guandan_benchmark.config import load_config, validate_api_key_format

VALID_API_KEY = "sk-zq-abc12345_01234567890123456789012345678901"


def test_validate_api_key_format_accepts_server_generated_key() -> None:
    # The lobby generates sk-zq-{8-alphanumeric-keyId}_{secret}.
    assert validate_api_key_format(VALID_API_KEY) is None


def test_validate_api_key_format_rejects_bad_key_id() -> None:
    assert (
        validate_api_key_format(
            "sk-zq-abc_01234567890123456789012345678901"
        )
        is not None
    )


def test_validate_api_key_format_rejects_short_secret() -> None:
    assert (
        validate_api_key_format("sk-zq-abc12345_short")
        is not None
    )


def _config_yaml(tmp_path, name: str = "From config", num_rounds: int = 3) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(
        f"""
developer_api_key: {VALID_API_KEY}
lobby_url: https://lobby.example
name: {name}
num_rounds: {num_rounds}
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


def _fake_game(benchmark_id: str = "BENCH0001") -> dict:
    return {
        "benchmark_id": benchmark_id,
        "benchmark_name": "From config",
        "status": "starting",
        "test_game_id": "tg",
        "game_id": "game-1",
        "room_id": "game-1",
        "runtime": _runtime(),
    }


def _patch_runner(monkeypatch):
    """Stub out the runner's I/O so main() drives create_benchmark only."""
    calls: dict = {}
    monitor_calls: dict = {}

    def fake_create_benchmark(**kwargs):
        calls.update(kwargs)
        return _fake_game()

    def fake_monitor(**kwargs):
        monitor_calls.update(kwargs)
        return {"termination": "test_completed", "events": [], "error": None}

    monkeypatch.setattr(runner, "check_lobby_reachable", lambda *a, **k: None)
    monkeypatch.setattr(runner, "check_game_server_reachable", lambda *a, **k: None)
    monkeypatch.setattr(runner, "discover_deployments", lambda *a, **k: [])
    monkeypatch.setattr(
        runner,
        "build_participants",
        lambda *a, **k: [
            {"seat": 1, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 2, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 3, "type": "internal_bot", "bot_code": "strongBot"},
            {"seat": 4, "type": "internal_bot", "bot_code": "strongBot"},
        ],
    )
    monkeypatch.setattr(runner, "create_benchmark", fake_create_benchmark)
    monkeypatch.setattr(runner, "monitor_events", fake_monitor)
    monkeypatch.setattr(runner, "print_report", lambda *a, **k: None)
    return calls, monitor_calls


def test_runner_calls_create_benchmark_with_config_values(
    monkeypatch, tmp_path
) -> None:
    calls, monitor_calls = _patch_runner(monkeypatch)

    exit_code = runner.main(["--config", _config_yaml(tmp_path)])

    assert exit_code == 0
    assert calls["api_key"] == VALID_API_KEY
    assert calls["lobby_url"] == "https://lobby.example"
    assert calls["name"] == "From config"
    assert calls["num_rounds"] == 3
    assert calls["total_timeout"] == 600
    assert calls["heartbeat_timeout"] == 60
    # The SSE monitor still consumes the runtime shape from the response.
    assert monitor_calls["events_url"] == _runtime()["events_url"]
    assert monitor_calls["access_token"] == "runtime-token"


def test_runner_cli_overrides_reach_create_benchmark(
    monkeypatch, tmp_path
) -> None:
    calls, _ = _patch_runner(monkeypatch)

    exit_code = runner.main(
        ["--config", _config_yaml(tmp_path), "--num-rounds", "5", "--timeout", "120"]
    )

    assert exit_code == 0
    assert calls["num_rounds"] == 5
    assert calls["total_timeout"] == 120


def test_runner_reports_failure_when_benchmark_creation_fails(
    monkeypatch, tmp_path
) -> None:
    calls, _ = _patch_runner(monkeypatch)

    def failing(**kwargs):
        calls.update(kwargs)
        return None

    monkeypatch.setattr(runner, "create_benchmark", failing)

    exit_code = runner.main(["--config", _config_yaml(tmp_path)])

    assert exit_code == 1


def test_env_lobby_url_overrides_yaml() -> None:
    assert _resolve_lobby_url(
        {"LOBBY_SERVER_URL": "https://env.example/"},
        "https://yaml.example",
    ) == "https://env.example"


def test_yaml_lobby_url_is_used_without_env_override() -> None:
    assert _resolve_lobby_url({}, "https://yaml.example/") == "https://yaml.example"


def test_lobby_url_prompts_when_env_and_yaml_are_empty() -> None:
    assert _resolve_lobby_url({}, "", prompt=lambda _: "") == "http://localhost:8686"


def test_yaml_lobby_url_is_optional_when_env_will_supply_it(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
num_rounds: 1
total_timeout: 60
heartbeat_timeout: 30
bots:
  seat_1: {type: builtin, bot_code: basicBot}
  seat_2: {type: builtin, bot_code: basicBot}
  seat_3: {type: builtin, bot_code: basicBot}
  seat_4: {type: builtin, bot_code: basicBot}
""",
        encoding="utf-8",
    )

    config = load_config(
        str(config_path),
        require_api_key=False,
        require_lobby_url=False,
    )

    assert config["lobby_url"] == ""
