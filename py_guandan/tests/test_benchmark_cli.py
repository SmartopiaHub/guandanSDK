from benchmark import _resolve_lobby_url
from guandan_benchmark.config import load_config


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
