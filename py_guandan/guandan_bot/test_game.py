"""Small client for launching automated games through the lobby API."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Participant:
    seat: int
    type: str
    bot_code: str | None = None
    deployment_id: str | None = None
    bot_definition_id: str | None = None
    deployment_key: str | None = None

    @classmethod
    def builtin(cls, seat: int, bot_code: str = "strongBot") -> "Participant":
        return cls(seat, "internal_bot", bot_code=bot_code)

    @classmethod
    def deployed(
        cls,
        seat: int,
        deployment_id: str,
        *,
        bot_definition_id: str | None = None,
        deployment_key: str | None = None,
    ) -> "Participant":
        return cls(seat, "external_bot", deployment_id=deployment_id, bot_definition_id=bot_definition_id, deployment_key=deployment_key)

    def to_dict(self) -> dict[str, Any]:
        values = {
            "seat": self.seat,
            "type": self.type,
            "bot_code": self.bot_code,
            "deployment_id": self.deployment_id,
            "bot_definition_id": self.bot_definition_id,
            "deployment_key": self.deployment_key,
        }
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True)
class TestGameConfig:
    __test__ = False

    lobby_url: str
    api_key: str
    participants: tuple[Participant, ...]
    num_rounds: int = 1
    num_series: int = 1
    rule_set: str = "guandan-standard-v1"
    record_replay: bool = True
    expires_in_seconds: int = 3600
    timeout: float = 15.0

    def __post_init__(self) -> None:
        seats = sorted(participant.seat for participant in self.participants)
        if seats != [1, 2, 3, 4]:
            raise ValueError("participants must contain exactly seats 1, 2, 3, and 4")
        if self.num_rounds < 1 or self.num_series < 1:
            raise ValueError("num_rounds and num_series must be positive")

    def payload(self) -> dict[str, Any]:
        return {
            "rule_set": self.rule_set,
            "participants": [participant.to_dict() for participant in sorted(self.participants, key=lambda item: item.seat)],
            "options": {
                "auto_start": True,
                "record_replay": self.record_replay,
                "expires_in_seconds": self.expires_in_seconds,
                "num_rounds": self.num_rounds,
                "num_series": self.num_series,
            },
        }


class TestGameError(RuntimeError):
    pass


@dataclass(frozen=True)
class TestGame:
    """A created game plus URLs/tokens used to observe or cancel it."""

    __test__ = False

    data: dict[str, Any] = field(repr=False)

    @property
    def test_game_id(self) -> str:
        return self.data.get("test_game_id", "")

    @property
    def game_id(self) -> str:
        return self.data.get("game_id", "")

    @property
    def status(self) -> str:
        return self.data.get("status", "")

    @property
    def runtime(self) -> dict[str, Any]:
        return self.data.get("runtime", {})

    @classmethod
    def start(cls, config: TestGameConfig) -> "TestGame":
        """Create and auto-start a game using the same API as ``benchmark.py``."""
        url = f"{config.lobby_url.rstrip('/')}/api/v1/test-games"
        request = Request(
            url,
            data=json.dumps(config.payload()).encode(),
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Idempotency-Key": str(uuid.uuid4()),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=config.timeout) as response:
                data = json.load(response)
        except HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise TestGameError(f"test game creation failed: HTTP {exc.code}: {body}") from exc
        except OSError as exc:
            raise TestGameError(f"test game creation failed: {exc}") from exc
        return cls(data)

    def cancel(self, *, timeout: float = 10.0) -> None:
        url = self.runtime.get("cancel_url")
        token = self.runtime.get("access_token")
        if not url or not token:
            raise TestGameError("game response has no cancel_url or access_token")
        request = Request(url, headers={"Authorization": f"Bearer {token}"}, method="POST")
        try:
            with urlopen(request, timeout=timeout):
                return
        except OSError as exc:
            raise TestGameError(f"test game cancellation failed: {exc}") from exc
