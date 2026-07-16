# py_guandan

Python bot-development
SDK compatible with the `guandan-bot-v1` protocol of zhiquguandan.com.

The package provides Python-native models and rule helpers for:

- cards, card lists, hands, hand detection, and hand comparison
- rule search helpers such as `find_pairs`, `find_bombs`, and `can_player_beat`
- player, room configuration, room metadata, and message serialization models
- game state, round, phase, turn, tribute, and score/rank models
- bot-facing validation helpers


## Prerequisites

| Requirement | Notes |
|---|---|
| **Python** | CPython 3.10 or newer with `pip`; using a virtual environment is recommended. |
| **Base dependency** | `requests>=2`, installed automatically with `py-guandan`. |
| **WebSocket bots** | Install `py-guandan[websocket]` for `websockets>=11`. |
| **Async HTTP bots** | Install `py-guandan[async-http]` for `aiohttp>=3.9`. |
| **Benchmark runner** | Install `py-guandan[benchmark]` for `PyYAML>=6`. |
| **Development/tests** | Install `py-guandan[dev]` for pytest and all optional runtime dependencies. The Dart SDK is only needed for the optional cross-language parity test. |
| **Platform credentials** | Not required for core rules or local tests. Deployment and test-game automation require a scoped developer API key; a running WebSocket bot also needs its deployment key. |

For a development checkout:

```sh
cd py_guandan
python3 -m venv .venv  # ensure python3 is version 3.10 or newer
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

## Obtaining an API Key

Developer API keys are needed only for lobby automation such as bot deployment
and benchmark/test-game creation. Obtain one through the **Developer Center**
at [zhiquguandan.com](https://www.zhiquguandan.com):

1. Sign in to [https://www.zhiquguandan.com](https://www.zhiquguandan.com)
   with your developer account.
2. Open the **Developer Center** (top-right menu → Developer Center).
3. Navigate to **API Keys** and create a key.
4. Select only the scopes needed: `bots:manage` and `bots:read` for deployment,
   or `test_games:create` and `test_games:read` for benchmarks.
5. Copy the generated `sk-zq-*` key immediately; its secret is shown only once.
6. Store it as `.env` `BOT_DEPLOY_API_KEY` or `DEV_API_KEY`, or as the YAML
   `developer_api_key` used by the benchmark module. Do not commit the secret.

### Programmatic key creation and management

Key lifecycle operations require a human developer access token obtained from
`POST /api/auth/login`; a developer API key cannot create or manage other
keys. The following example uses the HTTP client included in this package:

```python
from py_guandan.http import http_client

lobby_url = "https://www.zhiquguandan.com"

# Log in and obtain the human developer access token.
login = http_client.request_json(
    "POST",
    f"{lobby_url}/api/auth/login",
    body={"account": "developer@example.com", "password": "your-password"},
)
access_token = login["tokens"]["accessToken"]["token"]
headers = {"Authorization": f"Bearer {access_token}"}

# Create a least-privilege benchmark key. The secret is returned only here.
created = http_client.request_json(
    "POST",
    f"{lobby_url}/api/v1/developer/keys",
    headers=headers,
    body={
        "name": "benchmark",
        "environment": "test",
        "scopes": ["test_games:create", "test_games:read"],
        "expires_in_days": 30,
    },
)
key_id = created["key_id"]
api_key = created["api_key"]

# List key metadata; full secrets aren't included.
keys = http_client.request_json(
    "GET",
    f"{lobby_url}/api/v1/developer/keys",
    headers=headers,
)["keys"]

# Rotate a key. Save rotated["api_key"] immediately; the old secret is invalid.
rotated = http_client.request_json(
    "POST",
    f"{lobby_url}/api/v1/developer/keys/{key_id}/rotate",
    headers=headers,
)

# Choose soft revocation or permanent deletion when the key is no longer needed.
http_client.request_json(
    "POST",
    f"{lobby_url}/api/v1/developer/keys/{key_id}/revoke",
    headers=headers,
)
# http_client.request_json(
#     "DELETE",
#     f"{lobby_url}/api/v1/developer/keys/{key_id}",
#     headers=headers,
# )
```

See [Developer API key management](#developer-api-key-management) for endpoint
semantics, credential distinctions, and CLI key-retention behavior.


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

## Deploy a bot with `deploy_bot.py`

`deploy_bot.py` is the interactive deployment-registration wizard. It creates
or reuses the lobby-side provider and bot definition, registers an HTTP or
WebSocket deployment, and prints the credentials returned at creation time.
Run it from `py_guandan` so it reads and, when requested, updates
`py_guandan/.env`:

```sh
cd py_guandan
python3 deploy_bot.py
```

The script resolves configuration from the current working directory's `.env`:

```dotenv
LOBBY_SERVER_URL=http://localhost:8686
USERNAME=developer@example.com
PASSWORD=your-password

# Optional reusable key. deploy_bot.py prefers BOT_DEPLOY_API_KEY.
BOT_DEPLOY_API_KEY=sk-zq-...

# Legacy/general fallback when BOT_DEPLOY_API_KEY is absent.
# DEV_API_KEY=sk-zq-...
```

The interactive flow is:

1. Resolve `LOBBY_SERVER_URL`, prompting with `http://localhost:8686` as the default.
2. Use `BOT_DEPLOY_API_KEY`, or fall back to `DEV_API_KEY`. If neither exists,
   log in with `USERNAME` and `PASSWORD` from `.env` (prompting for missing
   values), then offer to create a key with `bots:manage` and `bots:read`.
3. List owned bot providers. Select one by number or enter `n` to create one
   with a display name and contact email.
4. List that provider's bot definitions. Select one or enter `n` to create one
   with a display name, unique bot code, and version.
5. Choose HTTP or WebSocket transport and set the maximum concurrent sessions
   (default `10`). HTTP also requires the bot's public base URL.
6. Create the deployment. For HTTP, the wizard then asks the lobby to verify
   the base URL by probing the bot's `/health` endpoint.

A configured API key is checked before use. If it lacks the bot scopes,
`deploy_bot.py` can log in and create a compatible replacement only when
`USERNAME` and `PASSWORD` are present in `.env`; otherwise it stops with an
actionable error.

The deployment management key and, for HTTP, the bot invocation token are
shown only in the creation response. Store them immediately. A WebSocket bot
uses the deployment key when connecting to `/bot-gateway/v1`; an HTTP bot must
configure the invocation token in its server. These deployment credentials are
not developer API keys and are not written to `.env` by this wizard.

When the wizard creates a developer API key, saving it as
`BOT_DEPLOY_API_KEY` is the default. If you decline to save it, the wizard asks
whether to delete it after the run; no response for 10 seconds selects deletion.
The created provider, definition, and deployment remain registered regardless
of that key-cleanup choice.

## Benchmark runner

The `guandan_benchmark` module is a fully automated test harness that creates a
configurable bot match-up, monitors the SSE event stream in real time, and
reports per-round scores and win rates.  It wraps `TestGame.start()` (see below)
with live monitoring, heartbeat tracking, and a summary report.

### Interactive `benchmark.py` runner

The repository-level convenience script adds credential setup and sensible
built-in match defaults around the benchmark library:

```sh
cd py_guandan
python3 benchmark.py
```

It reads `.env` from the current working directory. Set `CONFIG_FILE` there to
load a YAML configuration; otherwise it displays a two-round built-in-bot
match and asks for confirmation, automatically accepting after 60 seconds.
`LOBBY_SERVER_URL` is taken from `.env`, then the YAML config, or finally an
interactive prompt. `DEV_API_KEY` from `.env` takes precedence over the YAML
key. If neither is available, the script logs in with `.env` `USERNAME` and
`PASSWORD` or prompts for them, then walks through temporary-key creation and
retention as described under [Developer API key management](#developer-api-key-management).

After creating the test game, the runner checks lobby and game-server health,
streams SSE events, prints the final report, and cancels the game during
cleanup if it did not reach a terminal state.

### Install

```sh
cd py_guandan
python3 -m pip install -e '.[benchmark]'
```

This pulls in `PyYAML`; the core package already includes `requests` for its
shared HTTP transport.

### Configuration

Copy the example config and edit it:

```sh
cp guandan_benchmark/config.yaml.example config.yaml
```

The config file drives everything — there are no built-in defaults:

```yaml
developer_api_key: sk-zq-xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
lobby_url: https://www.zhiquguandan.com
num_rounds: 2
total_timeout: 6000
heartbeat_timeout: 1200

bots:
  seat_1:
    type: builtin
    bot_code: strongBot
  seat_2:
    type: builtin
    bot_code: basicBot
  seat_3:
    type: builtin
    bot_code: strongBot
  seat_4:
    type: builtin
    bot_code: basicBot
```

Seats 1 & 3 are the red team, seats 2 & 4 are blue.  Use `type: deployed` with a
`deployment_id` to test your own bot against built-in opponents:

```yaml
bots:
  seat_1:
    type: deployed
    deployment_id: DXXXXXXXX
  seat_2:
    type: builtin
    bot_code: strongBot
  seat_3:
    type: builtin
    bot_code: basicBot
  seat_4:
    type: builtin
    bot_code: strongBot
```

### CLI

```sh
# Run with the default config
python -m guandan_benchmark

# Override rounds and enable full output
python -m guandan_benchmark --num-rounds 10 --verbose

# Use a custom config, force internal-only bots
python -m guandan_benchmark --config my-matchup.yaml --internal-only

# Require deployed bots (fail if none are healthy)
python -m guandan_benchmark --external-only

# Override the timeout
python -m guandan_benchmark --timeout 3600
```

| Flag | Description |
|---|---|
| `--config PATH` | Path to YAML config file |
| `--num-rounds N` | Override `num_rounds` from config |
| `--timeout N` | Override `total_timeout` from config |
| `--verbose` | Print every agent message (default: only round start/end) |
| `--external-only` | Require deployed bots; exit if none are healthy |
| `--internal-only` | Force all seats to use built-in bots |

### Library

```python
from guandan_benchmark import (
    GameTracker,
    load_config,
    create_test_game,
    monitor_events,
    print_report,
)

# Load and validate config
config = load_config("config.yaml")

# Create a test game (uses the same API as TestGame.start())
game = create_test_game(
    lobby_url=config["lobby_url"],
    api_key=config["api_key"],
    participants=build_participants(
        config["bot_configs"], [],
        lobby_url=config["lobby_url"],
        api_key=config["api_key"],
    ),
    num_rounds=config["num_rounds"],
)

# Monitor the SSE event stream with a score tracker
tracker = GameTracker(total_rounds=config["num_rounds"])
result = monitor_events(
    events_url=game["runtime"]["events_url"],
    access_token=game["runtime"]["access_token"],
    timeout_s=config["total_timeout"],
    heartbeat_timeout=config["heartbeat_timeout"],
    verbose=True,
    tracker=tracker,
)

# Print the final scoreboard
print(tracker.red_win_rate, tracker.blue_win_rate)
for d in tracker.round_details:
    print(f"Round {d['round']}: {d['winner']}  Red {d['red_pts']} – Blue {d['blue_pts']}")
```

### Output

#### Non-verbose mode (default)

Non-verbose mode prints one line per round start and one per round end, plus a
round-completion summary:

```
▶ Round R1  level=2  teamLR=(R:2 B:2)  start=seat1
◀ Round R1  first=S1(red) | second=S3(red) | dwellers=S2(blue),S4(blue)
🏁 Round 1/10 completed (series 0/1)
   Score: Red 3 – Blue -3  (winner: red)
```

When all rounds finish, a scoreboard is printed:

```
TEST COMPLETED
  Red  wins: 9/10  score: 26
  Blue wins: 1/10  score: -26
  Per-round results:
    Round  1: R3–B-3   winner=red   [first: red | second: red | ...]
    ...
```

#### Verbose mode (`--verbose`)

Verbose mode prints every `agent.message` SSE event, including card hands,
tribute exchanges, and timeouts.

#### Final report

A summary report is always printed at the end:

```
========================================================================
  GUANDAN AUTO-TEST REPORT
========================================================================
  Lobby URL:     http://127.0.0.1:8686
  Participants:
    Seat 1: internal_bot     bot_code=strongBot
    ...

  Scoreboard:
    Team         Wins       Score
    ------------ ---------- ----------
    Red          9/10       26
    Blue         1/10       -26

    Per-round:
    Round  Red    Blue   Winner    Rankings
    ------ ------ ------ --------  ------------------------------
    1      3      -3     red       first: red | second: red | ...
    ...
========================================================================
```

### Scoring

The team whose player finishes **first** (banker / 头游) wins the round.
Points are awarded from the finishing positions held by each team:

| Winning team holds | Losing team holds | Winner | Loser |
|---|---|---:|---:|
| 1st + 2nd (double-down / 双下) | 3rd + 4th | +3 | −3 |
| 1st + 3rd | 2nd + 4th | +2 | −2 |
| 1st + 4th | 2nd + 3rd | +1 | −1 |

Win rates use `x/y`, where `x` is the number of rounds won and `y` is the
total number of requested rounds.

### Troubleshooting

| Symptom | Likely cause or action |
|---|---|
| `Config file not found` | `BENCHMARK_CONFIG_FILE` or `--config` points to a missing YAML file. |
| `developer_api_key is missing` | Set `.env` `DEV_API_KEY`, add `developer_api_key` to YAML, or provide `.env` `USERNAME` and `PASSWORD` so the interactive runner can create a temporary key. |
| `bots: missing seat(s): seat_2, seat_4` | Configure every seat from 1 through 4. |
| `Test game creation failed: HTTP 401` | The developer API key is invalid, expired, or lacks the required test-game scopes. |
| `Test game creation failed: HTTP 503` | No healthy game server is registered with the lobby. |
| `SSE connection failed` | The game server is unreachable; inspect the returned `events_url` and server health. |
| `heartbeat timeout` | The game server stopped sending events; check its health or increase `heartbeat_timeout`. |
| `Game did not complete within Ns` | Increase `total_timeout` or reduce `num_rounds`. |

## Run the end-to-end `demo.py`

`demo.py` exercises the complete temporary WebSocket-bot path: developer
login, API-key creation, bot registration, gateway connection, a one-round
test game, event monitoring, and cleanup.

```sh
cd py_guandan
python3 demo.py
```

The demo reads `.env` from the current working directory. Configure
`LOBBY_SERVER_URL`, `USERNAME`, `PASSWORD`, and optionally
`GAME_SERVER_URL`; it prompts only for a missing lobby URL, username,
or password. The game-server URL defaults to `ws://127.0.0.1:9001`. A
`GAME_SERVER_URL` value in the process environment overrides `.env`.

The demo creates an all-scopes developer API key, reuses the first existing
provider or creates a demo provider, creates a uniquely named bot definition
and WebSocket deployment, starts a local `BasicBot`, and tests it against three
built-in bots. On exit it cancels an unfinished game, closes the bot, deletes
the temporary deployment, and hard-deletes the temporary API key. The bot
definition—and a provider if the demo had to create one—remain registered.

## Start an automated game

`TestGame.start()` uses the same lobby API and payload as the benchmark:

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
- `guandan_bot.AsyncWebSocketBotClient` and `AsyncHttpBotServer`: generic
  async transports for stateful or LLM-backed handlers
- `guandan_bot.TestGame`: automated game launcher
- `guandan_bot.BasicBot`: a small rule-based reference implementation
- `guandan_bot.protocol`: immutable transport envelopes with typed game
  payloads from `guandan_core.message`
- `guandan_benchmark`: fully automated test harness with SSE monitoring, scoring, and reporting
- `py_guandan.http`: centralized HTTP transport; loopback traffic bypasses
  system proxies while remote traffic preserves normal proxy behavior

Protocol parsing types both the transport envelope and its nested game message:

```python
from guandan_bot.protocol import BotMessage, GameMessageEnvelope
from guandan_core import ServerPlayHandRequest

message = BotMessage.parse(raw_json)
if (
    isinstance(message, GameMessageEnvelope)
    and isinstance(message.payload, ServerPlayHandRequest)
):
    print(message.payload.available_cards)
```

## Developer API key management

Developer API keys authenticate automation against the lobby. They are
different from the short-lived human access token returned by login, the
deployment management key used by a WebSocket bot, the HTTP bot invocation
token, and a test game's runtime access token.

### Lifecycle

1. **Log in.** Send the developer account's username and password to
   `POST /api/auth/login`. The returned human access token authorizes key
   management; a developer API key cannot manage its own lifecycle.
2. **Create a scoped key.** Send the human access token to
   `POST /api/v1/developer/keys`, choosing only the scopes needed by the task.
   `deploy_bot.py` requests `bots:manage` and `bots:read`; `benchmark.py`
   requests `test_games:create` and `test_games:read`; `demo.py` requests all
   four because it deploys a bot and starts a test game.
3. **Capture the secret once.** Creation returns a `key_id` and a full
   `sk-zq-*` API key. The lobby stores a hash and never returns the secret from
   list operations, so a lost secret must be rotated or replaced.
4. **Use or persist it.** Send the API key as `Authorization: Bearer ...`.
   Reusable CLI keys can be stored in `.env`; `py_guandan/.env` is ignored by
   this repository, but it still contains plaintext credentials and must not be
   shared.
5. **Rotate, revoke, or delete it.** Rotation keeps the public key ID but
   returns a new one-time secret and invalidates the old secret. Revocation
   retains an audit record with `status: revoked`. Deletion permanently removes
   the record. These operations require the human developer session/access
   token and ownership of the key.

The unified key-management endpoints are:

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/developer/keys` | Create a scoped key; returns the full secret once |
| `GET` | `/api/v1/developer/keys` | List owned key metadata; never returns secrets |
| `POST` | `/api/v1/developer/keys/{keyId}/rotate` | Replace the secret while retaining the key ID |
| `POST` | `/api/v1/developer/keys/{keyId}/revoke` | Soft-delete: invalidate the key and retain its record |
| `DELETE` | `/api/v1/developer/keys/{keyId}` | Hard-delete: invalidate the key and remove its record |

The legacy `/api/v1/developer/keys/automation-test` paths remain aliases during
the migration window. New code should use the unified paths above.

### CLI script behavior

All `.env` references below mean the file in the process's current working
directory.

| Script | Credential input and prompts | Key created | End-of-run behavior |
|---|---|---|---|
| `deploy_bot.py` | Prefers `.env` `BOT_DEPLOY_API_KEY`, then `DEV_API_KEY`; otherwise uses `.env` `USERNAME`/`PASSWORD` or prompts | `bots:manage`, `bots:read` | Offers to save as `BOT_DEPLOY_API_KEY`. If not saved, asks whether to hard-delete it and defaults to deletion after 10 seconds. Existing keys are never deleted. |
| `benchmark.py` | Prefers `.env` `DEV_API_KEY`, then the configured YAML key; otherwise uses `.env` `USERNAME`/`PASSWORD` or prompts | `test_games:create`, `test_games:read` | Offers to save as `DEV_API_KEY`. If not saved, asks whether to hard-delete it and defaults to deletion after 10 seconds. It also cancels an unfinished test game. Existing keys are never deleted. |
| `demo.py` | Uses `.env` `LOBBY_SERVER_URL`, `USERNAME`, `PASSWORD`, and `GAME_SERVER_URL`, prompting for missing lobby/login values. A process `GAME_SERVER_URL` overrides `.env`. | All four bot and test-game scopes | Always hard-deletes its temporary key, closes the WebSocket bot, deletes its temporary deployment, and cancels an unfinished game. A provider created by the demo and its newly created bot definition are left registered. |

For `deploy_bot.py` and `benchmark.py`, accepting the save prompt makes the key
persistent and suppresses automatic deletion. Declining both saving and
deletion leaves a live key on the server without recording its secret locally;
copy the printed secret immediately or later rotate/delete the key by ID.
