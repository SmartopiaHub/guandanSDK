# py_guandan

Python port of the Dart `guandan_core` package, with a Python bot-development
SDK compatible with the `guandan-bot-v1` protocol.

The package provides Python-native models and rule helpers for:

- cards, card lists, hands, hand detection, and hand comparison
- rule search helpers such as `find_pairs`, `find_bombs`, and `can_player_beat`
- player, room configuration, room metadata, and message serialization models
- game state, round, phase, turn, tribute, and score/rank models
- bot-facing validation helpers

The implementation intentionally keeps wire-format strings and JSON keys compatible
with `guandan_core` while using Python dataclasses, enums, snake_case function names,
and in-file docstrings.

## Build a bot

Install the package with WebSocket support:

```sh
cd py_guandan
python3 -m pip install -e '.[websocket]'
```

A developer bot only needs three decisions. Each request includes an immutable
copy of the available cards and the relevant game metadata:

```python
from guandan_bot import Bot, PlayRequest, ReturnCardRequest, TributeRequest
from guandan_core import Card, Hand, HandType

class MyBot(Bot):
    def play_hand(self, request: PlayRequest) -> Hand:
        if not request.hand_on_table.is_empty:
            return Hand.empty_hand()  # pass
        card = request.cards[0]
        return Hand([card], HandType.SINGLE, card.power_rank)

    def tribute_card(self, request: TributeRequest) -> Card:
        return max(request.cards, key=lambda card: card.power_rank)

    def return_card(self, request: ReturnCardRequest) -> Card:
        return min(request.cards, key=lambda card: card.power_rank)
```

The SDK validates every returned decision before putting it on the wire.
`Bot.context` exposes the assigned player, seat, team, rule set, and deck count;
`Bot.cards_on_hand` is maintained for convenience. Override `on_message()` only
if the strategy needs to observe other game events.

### Run as a WebSocket bot

```python
from guandan_bot import BotApplication, run_websocket_bot

run_websocket_bot(
    BotApplication(MyBot),
    game_server_url="wss://engine.zhiquguandan.com",
    deployment_key="your-deployment-key",
)
```

The deployment key is sent as a bearer token to `/bot-gateway/v1`. The client
reconnects after connection loss. See
[`examples/minimal_bot.py`](examples/minimal_bot.py) for a runnable bot.

### Run as an HTTP bot

```python
from guandan_bot import BotApplication, HttpBotServer

HttpBotServer(
    BotApplication(MyBot),
    host="0.0.0.0",
    port=10001,
    invocation_key="secret-from-the-platform",
).start()
```

The server implements `POST /sessions`,
`POST /sessions/{session_id}/messages`, `DELETE /sessions/{session_id}`, and
`GET /health`. The invocation key is accepted through either `Authorization:
Bearer ...` or `X-Api-Key`.

## Start an automated game

`TestGame.start()` uses the same lobby API and payload as `benchmark.py`:

```python
from guandan_bot import Participant, TestGame, TestGameConfig

game = TestGame.start(TestGameConfig(
    lobby_url="https://www.zhiquguandan.com",
    api_key="your-developer-automation-key",
    participants=(
        Participant.deployed(1, "your-deployment-id"),
        Participant.builtin(2, "strongBot"),
        Participant.builtin(3, "strongBot"),
        Participant.builtin(4, "basicBot"),
    ),
    num_rounds=2,
))

print(game.test_game_id, game.status)
print(game.runtime["events_url"])
```

All four seats must be configured. Start a WebSocket bot before creating a game
that references its deployment. `game.runtime` contains the event/status/cancel
URLs and access token; `game.cancel()` cancels the game. See
[`examples/start_test_game.py`](examples/start_test_game.py).

## SDK modules

- `guandan_bot.Bot`: the three-method strategy interface
- `guandan_bot.BotApplication`: sessions, state updates, validation, protocol dispatch
- `guandan_bot.WebSocketBot` and `HttpBotServer`: transport adapters
- `guandan_bot.TestGame`: automated game launcher
- `guandan_bot.BasicBot`: a small rule-based reference implementation
- `guandan_bot.protocol`: typed `guandan-bot-v1` envelopes

## Development

Run the Python package tests:

```sh
cd py_guandan
python3 -m pytest
```

The test suite includes Python copies of the Dart `guandan_core/test` files:
card/hand tests, utility and find/can-beat tests, player tests, message tests,
and game-state tests. Python-only tests cover language-specific behavior such
as hashability, dataclass copying, iteration, membership, and mutable-list
copy boundaries.

Run the bot tests against the shared core:

```sh
cd py_bot
PYTHONPATH=../py_guandan:. python -m pytest
```

Some tests cross-check the Python behavior with a small Dart runner compiled against
`../guandan_core`.
