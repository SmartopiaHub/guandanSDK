from demo import _load_dotenv, _resolve_demo_inputs


def test_demo_reads_inputs_from_dotenv_without_prompting(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        """
LOBBY_SERVER_URL=https://lobby.example/
USERNAME=developer@example.com
PASSWORD="secret value"
GAME_SERVER_URL=wss://game.example/
""",
        encoding="utf-8",
    )

    def unexpected_prompt(_: str) -> str:
        raise AssertionError("complete .env configuration should not prompt")

    values = _resolve_demo_inputs(
        _load_dotenv(str(env_path)),
        process_env={},
        prompt=unexpected_prompt,
    )

    assert values == (
        "https://lobby.example",
        "developer@example.com",
        "secret value",
        "wss://game.example",
    )


def test_demo_prompts_for_missing_required_inputs() -> None:
    answers = iter(("", "developer", "secret"))

    values = _resolve_demo_inputs(
        {},
        process_env={},
        prompt=lambda _: next(answers),
    )

    assert values == (
        "http://localhost:8686",
        "developer",
        "secret",
        "ws://127.0.0.1:9001",
    )


def test_process_game_server_url_overrides_dotenv() -> None:
    values = _resolve_demo_inputs(
        {
            "LOBBY_SERVER_URL": "https://lobby.example",
            "USERNAME": "developer",
            "PASSWORD": "secret",
            "GAME_SERVER_URL": "wss://dotenv.example",
        },
        process_env={"GAME_SERVER_URL": "wss://process.example"},
    )

    assert values[3] == "wss://process.example"
