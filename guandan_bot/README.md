# Guandan Bot

A standalone Dart package for building and running Guandan (掼蛋) card-playing bots. Connects to the Guandan game server via WebSocket or HTTP using the `guandan-bot-v1` protocol.

## Architecture

This package provides two bot transport modes, both backed by the same `BasicBot` AI:

| Mode | Direction | When to use |
|---|---|---|
| **WebSocket** | Bot connects to game server | Bot runs as a client; simple, persistent connection |
| **HTTP** | Game server calls bot | Bot runs as a server behind a proxy/tunnel; platform-discoverable |

Both modes speak the same `guandan-bot-v1` protocol — JSON-encoded `BotMessage` envelopes over their respective transports.

## Quick Start — WebSocket Bot

### 1. Prerequisites

- Dart SDK ≥ 3.6.0
- Access to a running Guandan game server (e.g. `wss://engine.zhiquguandan.com`)
- A **deployment key** issued by the platform

### 2. Obtain a deployment key

A **deployment key** authenticates your bot to the game server. You get one by deploying a WebSocket bot through the [智趣掼蛋 Developer Center](https://www.zhiquguandan.com):

1. Go to [www.zhiquguandan.com](https://www.zhiquguandan.com) and log in as a developer.
2. Navigate to the **Developer Center**.
3. Create a new **WebSocket bot deployment**. The platform will generate a **deployment key** for you — copy it and keep it secure.
4. Take note of the **game server URL**: `wss://engine.zhiquguandan.com`.

> **Note:** The deployment key is a secret. It is sent as `Authorization: Bearer <key>` in the WebSocket handshake. Do not commit it to version control — the `config/config.yaml` file is gitignored for this reason.

### 3. Configure

Copy the example config and fill in your values:

```bash
cd guandan_bot
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` — the minimal setup for WebSocket:

```yaml
websocket_bot:
  game_server_url: "wss://engine.zhiquguandan.com"
  deployment_key: "your-deployment-key-here"
```

All config values can also be set via environment variables (see [Configuration Reference](#configuration-reference) below).

### 4. Run

```bash
dart run bin/websocket_test_bot.dart
```

The bot will:
1. Load config from environment → `config.yaml` → interactive prompts (in priority order)
2. Print the resolved configuration
3. Connect to `{game_server_url}/bot-gateway/v1` with `Authorization: Bearer <deployment_key>`
4. Wait for the game server to send `SessionStartMessage` — it then spawns a `BasicBot` AI instance
5. Auto-reconnect on connection loss (3-second delay)

Press `Ctrl+C` to gracefully disconnect and exit.

### 5. What happens during a game

When the game server sends a request, the bot responds:

| Server sends | Bot does |
|---|---|
| `ServerPlayHandRequest` | Calls `BasicBot.getCardsToPlay()` — finds the smallest legal hand that beats the table |
| `ServerTributeRequest` | Calls `BasicBot.tribute()` — gives the strongest non-wild card |
| `ServerReturnCardRequest` | Calls `BasicBot.returnCard()` — returns the weakest card |
| Other game messages | Updates internal state (hand, round info, played cards) — no reply |

All message traffic is logged to stdout with timestamps, direction, type, and size.

## Quick Start — HTTP Bot

The HTTP bot runs as a **server** that the game server calls:

```bash
dart run bin/http_test_bot.dart
```

Configure the `http_bot:` section in `config/config.yaml`. The HTTP bot can also **auto-register** itself with the lobby server if you provide `provider_id`, `definition_ids`, and `lobby` config.

## Configuration Reference

Config is resolved in this priority order:

```
environment variables  >  config.yaml  >  interactive console prompt
```

If a value is found at a higher priority, the lower ones are skipped. An empty/missing value falls through to the next level.

### `websocket_bot:` section

| Key | Env Variable | Default | Description |
|---|---|---|---|
| `game_server_url` | `GAME_SERVER_URL` | *(prompted)* | WebSocket URL of the game server, e.g. `wss://engine.zhiquguandan.com` |
| `deployment_key` | `WEBSOCKET_BOT_DEPLOYMENT_KEY` | *(prompted)* | Deployment key the bot sends as `Authorization: Bearer <key>` in the WebSocket handshake |

### `http_bot:` section

| Key | Env Variable | Default | Description |
|---|---|---|---|
| `host` | `HTTP_BOT_HOST` | `127.0.0.1` | Network address the HTTP server binds to |
| `port` | `HTTP_BOT_PORT` | `10001` | Port the HTTP server listens on (`0` = OS-assigned) |
| `deployment_key` | `HTTP_BOT_DEPLOYMENT_KEY` | *(prompted)* | Deployment key presented to the lobby/game server during registration |
| `invocation_key` | `HTTP_BOT_INVOCATION_KEY` | *(optional)* | Bot invocation token that the bot checks on incoming requests (`Authorization: Bearer <key>`). Leave empty to accept all requests. |
| `public_base_url` | `HTTP_BOT_PUBLIC_BASE_URL` | *(optional)* | Publicly-reachable URL when behind a reverse proxy or tunnel (differs from bind address) |
| `provider_id` | `BOT_PROVIDER_ID` | *(optional)* | Bot provider ID — required for auto-registration |
| `definition_ids` | `BOT_DEFINITION_IDS` (comma-separated) or `BOT_DEFINITION_ID` | `[]` | Bot definition IDs this deployment supports |
| `protocol_versions` | `BOT_PROTOCOL_VERSIONS` | `["guandan-bot-v1"]` | Supported protocol versions |
| `max_concurrent_sessions` | `BOT_MAX_CONCURRENT_SESSIONS` | `10` | Maximum concurrent bot sessions |
| `region` | `BOT_REGION` | *(optional)* | Geographic region label |

### `lobby:` section (optional — for HTTP bot auto-registration)

| Key | Env Variable | Default | Description |
|---|---|---|---|
| `url` | `LOBBY_URL` | `http://127.0.0.1:8686` | Lobby server base URL |
| `access_token` | `LOBBY_ACCESS_TOKEN` or `DEVELOPER_ACCESS_TOKEN` | *(optional)* | Developer access token for lobby API authentication |

### Environment-only overrides

To run without a config file, set the env variables directly:

```bash
export GAME_SERVER_URL="wss://engine.zhiquguandan.com"
export WEBSOCKET_BOT_DEPLOYMENT_KEY="your-key"
dart run bin/websocket_test_bot.dart
```

## Writing Your Own Bot

### Extend `BotPlayer`

The abstract class `BotPlayer` (in `lib/src/bot.dart`) is the base for all bot AIs. Override the related methods.

Your bot receives informational messages (new round, cards played, tribute results) via `receiveMessage()`, and you may update internal state. The `basic_bot.dart` implementation is a good starting reference — it's a simple rule-based bot with random exploration.


## Project Structure

```
guandan_bot/
├── bin/
│   ├── websocket_test_bot.dart    # WebSocket bot entry point
│   └── http_test_bot.dart         # HTTP bot entry point
├── lib/
│   ├── guandan_bot.dart           # Library barrel (exports all public symbols)
│   └── src/
│       ├── bot.dart               # Abstract BotPlayer base class
│       ├── basic_bot.dart         # BasicBot — simple rule-based AI
│       ├── http_test_bot.dart     # HttpTestBot — HTTP server implementation
│       ├── websocket_test_bot.dart # WebSocketTestBot — WebSocket client implementation
│       ├── message_formatter.dart  # Human-readable message logging
│       └── contracts/
│           ├── bot_protocol_contract.dart  # Bot protocol message types
│           ├── bot_registry_contract.dart  # Registration/discovery API types
│           └── bot_test_message.dart       # Test framework message types
├── test/
│   ├── websocket_test_bot_test.dart
│   ├── http_test_bot_test.dart
│   └── bot_registry_contract_test.dart
├── config/
│   ├── config.yaml.example        # Tracked config template (safe to commit)
│   └── config.yaml                # Your actual config (gitignored — contains secrets)
├── pubspec.yaml
└── analysis_options.yaml
```

## Dependencies

| Package | Purpose |
|---|---|
| `guandan_core` | Game model: `Card`, `PlayHand`, `Player`, `GameMessage` hierarchy, rules |
| `guandan_hand_splitter` | Hand analysis: `findPlates`, `findBombs`, `findTriples`, chain finders |
| `http` | HTTP client for lobby registration calls |
| `logging` | Structured logging |
| `yaml` | Config file parsing |

## Protocol

The bot protocol is defined in `lib/src/contracts/bot_protocol_contract.dart`. Top-level message types:

- `SessionStartMessage` / `SessionStartedMessage` — session lifecycle
- `SessionEndMessage` / `SessionEndedMessage` — session teardown
- `GameMessageEnvelope` — wraps a game payload with `sessionId`, `requestId`, and `deadlineMillis`
- `ErrorMessage` — protocol-level errors

Game payloads include `ServerPlayHandRequest`, `ServerTributeRequest`, `ServerReturnCardRequest` (server → bot) and their `Player*` reply counterparts (bot → server), plus informational messages like `NewRoundMessage`, `HandPlayedMessage`, `TributeResultMessage`, and `RoundResultMessage`.

## Testing

```bash
dart test
```

Tests cover WebSocket bot session lifecycle, HTTP bot endpoints and auth, and registration contract serialization.
