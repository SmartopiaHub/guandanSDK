# Third-Party Bot Development Specification

## Scope

Third-party bots are untrusted services that play one or more Guandan seats
through a registered bot deployment. The game server remains authoritative:
it validates every action, rejects stale or illegal responses, enforces
deadlines, and may replace a failed bot with a fallback player.

## Package Contracts

The canonical discovery and registration contracts are in:

```dart
import 'package:guandan_bot/guandan_bot.dart';
```

Important types:

- `BotProvider`
- `BotDefinition`
- `BotDeployment`
- `BotSession`
- `RegisterBotProviderRequest`
- `CreateBotDefinitionRequest`
- `RegisterBotDeploymentRequest`
- `BotDiscoveryResponse`

## Identity Model

A bot service is not a player. One provider can register many definitions and
many deployments. One deployment can serve many independent bot sessions.

Each game seat backed by a third-party bot has an independent session:

```text
BotProvider
  -> BotDefinition
  -> BotDeployment
  -> BotSession
  -> external bot player agent
```

The session boundary is mandatory. A deployment must not share hidden cards,
turn state, or response correlation between sessions unless the platform
explicitly sends that state for the same `session_id`.

### Identifier Conventions

All bot entity identifiers are fixed-length uppercase alpha strings:

| Entity     | Format   | Length | Prefix | Example   | Notes                              |
|-----------|---------|--------|--------|-----------|-------------------------------------|
| Provider   | Pxxxxx   | 6      | `P`    | `PABCDE`  | `P` + 5 random uppercase letters    |
| Definition | Axxxxx   | 6      | `A`    | `AAAAAA`  | Reserved for built-in bots          |
| Definition | Bxxxxx   | 6      | `B`    | `BBCDEF`  | External (third-party) bots         |
| Deployment | Dxxxxxxx | 8      | `D`    | `DABCDEFG`| `D` + 7 random uppercase letters    |

The special provider ID `SYSTEM` is reserved for the platform's built-in
provider ("Built-in Provider"), which owns the built-in definitions `AAAAAA`
(Basic Bot, `bot_code: "basicBot"`) and `AAAAAB` (Strong Bot,
`bot_code: "strongBot"`). The SYSTEM provider is always in `approved` status
and its definitions are `public` and `active`. These are automatically created
on lobby startup if they do not exist.

## Runtime Protocol Version

The first supported protocol version is `guandan-bot-v1`.

Deployments must declare the protocol versions they support in
`supported_protocol_versions`. A session is created only when a deployment and
bot definition share the selected protocol version.

## HTTP Pull Mode

HTTP deployments register:

```json
{
  "transport_type": "http"
}
```

The platform returns a one-time `deployment_management_key` and
`bot_invocation_token`.

Two keys are used during bot deployment:

| Key | Direction | Env Variable | Description |
| --- | --- | --- | --- |
| **Deployment key** | bot → server | `HTTP_BOT_DEPLOYMENT_KEY` / `WEBSOCKET_BOT_DEPLOYMENT_KEY` | The bot presents this key to the lobby / game server when registering or connecting. |
| **Bot invocation key** | server -> bot | `HTTP_BOT_INVOCATION_KEY` | Platform-issued token. The lobby uses it for deployment verification and the game server includes it as `Authorization: Bearer <key>` when calling an HTTP bot. The bot checks it to authenticate incoming requests. |

Configure `bot_invocation_token` in the bot HTTP server as the invocation key.
Runtime game servers include it as `Authorization: Bearer <bot_invocation_token>`
when calling the bot.

After the bot is configured, submit its stable base URL for verification. The
registered `base_url` must be the externally reachable base HTTPS URL of the
bot service; loopback `http://127.0.0.1:<port>` and `http://localhost:<port>`
are accepted for local development. The platform performs an authenticated
health probe before marking the deployment `healthy`.

For local development, enter a URL that is reachable from the lobby server
process. If the bot binds to `0.0.0.0`, use a real client address such as
`http://127.0.0.1:10001` when the lobby runs on the same host, or
`http://host.docker.internal:10001` when the lobby runs in Docker on macOS.
The verifier also normalizes common local inputs such as `localhost` and
`0.0.0.0` to reachable loopback candidates.

The bot must answer:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Report bot readiness under bot invocation token auth. |

Health response:

```json
{
  "status": "ok"
}
```

During verification the platform sends both
`Authorization: Bearer <bot_invocation_token>` and
`X-Api-Key: <bot_invocation_token>` so bots can support either header.

Only verified healthy HTTP deployments are routed to runtime game servers.
Once healthy, the game server calls endpoints relative to `base_url`:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/sessions` | Create a logical bot session with a `session_start` BotMessage. |
| `POST` | `/sessions/{session_id}/messages` | Deliver game-message BotMessage envelopes and receive action responses. |
| `DELETE` | `/sessions/{session_id}` | End a bot session. |

All requests must include:

```http
Content-Type: application/json
X-Guandan-Bot-Protocol: guandan-bot-v1
X-Guandan-Request-Id: <unique request id>
```

Action request envelopes also include:

```http
X-Guandan-Deadline-Millis: <unix epoch millis>
```

### Local `HttpTestBot` deployment

The `guandan_bot` package includes a development HTTP bot:

```bash
cd guandan_bot
HTTP_BOT_PORT=10001 HTTP_BOT_INVOCATION_KEY=<bot-invocation-token> \
  dart run bin/http_test_bot.dart
```

`HTTP_BOT_API_KEY` is still accepted as a legacy alias for
`HTTP_BOT_INVOCATION_KEY`.

This starts an HTTP server and prints its base URL. For the normal two-step
flow, first create the HTTP deployment in Developer Center, copy the returned
`bot_invocation_token`, start or restart the bot with that token, then verify
the stable base URL in Developer Center.

For local tooling, the test bot can still register a deployment in the same
process. This creates the pending deployment and prints the platform-issued
tokens; configure the returned `bot_invocation_token` in the bot before URL
verification:

```bash
cd guandan_bot
HTTP_BOT_PORT=10001 \
HTTP_BOT_PUBLIC_BASE_URL=http://127.0.0.1:10001 \
LOBBY_URL=http://127.0.0.1:8686 \
DEVELOPER_ACCESS_TOKEN=<developer-access-token> \
BOT_PROVIDER_ID=<provider-id> \
BOT_DEFINITION_ID=<definition-id> \
dart run bin/http_test_bot.dart
```

`HTTP_BOT_PUBLIC_BASE_URL` is optional when the bind URL is the same URL the
game server can call. It should be set when binding to `0.0.0.0`, running
behind a reverse proxy, or publishing through a tunnel.

## WebSocket Push Mode

WebSocket deployments register without a `base_url`:

```json
{
  "transport_type": "websocket"
}
```

The bot is the WebSocket client. It connects to the assigned game server's
`/bot-gateway/v1` endpoint with its one-time deployment management key:

```http
Authorization: Bearer <deployment-management-key>
X-Guandan-Bot-Protocol: guandan-bot-v1
```

Messages use a flat top-level envelope. There is no nested `envelope` field:

```json
{
  "type": "game_message",
  "session_id": "bot_session_01",
  "request_id": "req_01",
  "deadline_millis": 1780502400000,
  "payload": {
    "type": "sPlayHandRequest",
    "room_id": "room_01",
    "game_id": "game_01",
    "round_id": "R1",
    "turn_id": "R1_P1_T1",
    "hand_on_table": "pair-14 : AH AS",
    "level_rank": "2",
    "available_cards": "2D* 2S* 3H"
  }
}
```

Responses must echo `request_id` and `session_id`.

## Session Creation

HTTP bots receive this object in `POST /sessions`; WebSocket bots receive the
same object as a text frame:

```json
{
  "type": "session_start",
  "session_id": "bot_session_01",
  "bot_definition_id": "bot_definition_01",
  "deployment_id": "DABCDEFG",
  "player_id": "player_03",
  "seat": 3,
  "rule_set": "classic",
  "protocol_version": "guandan-bot-v1",
  "number_of_standard_decks": 2
}
```

Successful response:

```json
{
  "type": "session_started",
  "session_id": "bot_session_01",
  "accepted": true
}
```

## Action Responses

Play response:

```json
{
  "type": "game_message",
  "session_id": "bot_session_01",
  "request_id": "req_01",
  "payload": {
    "type": "pPlayHandRequest",
    "room_id": "room_01",
    "game_id": "game_01",
    "player_id": "player_03",
    "round_id": "R1",
    "turn_id": "R1_P1_T1",
    "cards": "2D* 2S*"
  }
}
```

Tribute response:

```json
{
  "type": "game_message",
  "session_id": "bot_session_01",
  "request_id": "req_02",
  "payload": {
    "type": "pPayTributeRequest",
    "room_id": "room_01",
    "game_id": "game_01",
    "player_id": "player_03",
    "round_id": "R1",
    "tribute_card": "AS"
  }
}
```

Return-card response:

```json
{
  "type": "game_message",
  "session_id": "bot_session_01",
  "request_id": "req_03",
  "payload": {
    "type": "pReturnCardRequest",
    "room_id": "room_01",
    "game_id": "game_01",
    "player_id": "player_03",
    "round_id": "R1",
    "return_card": "3C"
  }
}
```

The card string format is the same format accepted by `PokerCard.fromString`
and `PokerCardList.fromString` in `guandan_core`.

## Game State on Join

When a bot joins a game that is already in progress (e.g., replacing a
disconnected player or backfilling after a crash), the platform sends a
`PlayerJoinedRoomMessage` (`iPlayerJoinedRoom`) with a non-null `game_state`
field. This field contains the **complete current game state** as visible to
the joining bot:

- `players` — all players with `cards_on_hand` populated only for the bot's
  own player entry (other players' cards are not disclosed).
- `rounds` — all completed and in-progress rounds.
- `current_level_rank`, `number_of_standard_decks` — deck configuration.
- `team_level_rank`, `team_scores` — current team standings.

The bot **must** use this snapshot to initialize its internal state before
responding to any action requests. A `reconnect_token` is also included for
potential reconnection.

See the [Bot Development Guide](bot_development_guideline.md#iplayerjoinedroom--a-player-joined-the-room)
for the full message schema.

## Required Bot Behavior

Bots must:

- Reply before the deadline.
- Echo the request id exactly once.
- Keep state isolated by `session_id`.
- Return only legal cards from the bot player's visible hand.
- Treat all platform messages as authoritative.
- Handle duplicate delivery idempotently.
- Handle `PlayerJoinedRoomMessage` with non-null `game_state` to initialize
  internal state when joining an in-progress game.

Bots must not:

- Infer or use hidden cards from other seats.
- Return a response for an old turn after a newer request has arrived.
- Share private session state across games.
- Depend on undocumented message fields.

### Broadcast vs Targeted Requests

Play requests (`sPlayHandRequest`), tribute requests (`sTributeCardRequest`),
and return-card requests (`sReturnCardRequest`) are **broadcast** by the game
server to every player in the room. However, only the **targeted player** (the
player whose turn it is to act) receives non-empty `available_cards` in the
request payload. For all other players, the `available_cards` field is empty.

Bots MUST check whether `available_cards` is non-empty before responding to
these request types. If `available_cards` is empty or null, the bot is an
observer for that message and should not respond.

## Failure Handling

The platform may ignore or replace a bot when:

- The deployment is unavailable.
- A request times out.
- The response is malformed.
- The action is illegal.
- A duplicate or stale `request_id` is returned.

Fallback behavior is platform-owned and may change without notice.
