# Guandan Bot Development Guide

This document describes everything a third-party developer needs to build and
deploy a bot for the Guandan (掼蛋) card game platform.  Bots communicate with
the platform using a standard JSON protocol over **HTTP** or **WebSocket**.

---

## Table of Contents

1. [Overview](#overview)
2. [Team and Player](#team-and-player)
3. [Game State Structure](#game-state-structure)
4. [Card, Hand & Deck Encoding](#card-hand--deck-encoding)
5. [Bot Protocol Messages](#bot-protocol-messages)
6. [Building an HTTP Bot](#building-an-http-bot)
7. [Building a WebSocket Bot](#building-a-websocket-bot)
8. [Game Messages (Payload Reference)](#game-messages-payload-reference)
9. [Deploying Your Bot](#deploying-your-bot)
10. [Testing Your Bot](#testing-your-bot)
11. [Health Checks & Monitoring](#health-checks--monitoring)
12. [Key & Token Reference](#key--token-reference)
13. [Quick-Start Checklist](#quick-start-checklist)

---

## Overview

```
┌──────────────┐     game message       ┌──────────────────┐
│  Game Server │ ─────────────────────→ │  Your Bot        │
│  (platform)  │ ←───────────────────── │  (HTTP or WS)    │
└──────────────┘     game message       └──────────────────┘
```

The game server sends your bot **game messages** wrapped in a protocol
envelope.  Your bot responds with action messages (play cards, pay tribute,
etc.) wrapped in the same envelope.

### Transport Options

| Transport   | How it works |
|-------------|-------------|
| **HTTP**    | The platform POSTs JSON messages to your bot's HTTP endpoints. Your bot responds with JSON. |
| **WebSocket** | Your bot connects to the platform's bot gateway (`wss://<game-server>/bot-gateway/v1`) and exchanges JSON frames. |

### Protocol Version

The current protocol version is **`guandan-bot-v1`**.  All bots must declare
support for this version during registration.

---

## Team and Player

### Teams

Every game has exactly **two teams**:

| Team | JSON value | Seats |
|------|-----------|-------|
| **Red Team** | `"redTeam"` | 1, 3 |
| **Blue Team** | `"blueTeam"` | 2, 4 |

The seat-to-team mapping is deterministic: odd seats are red, even seats are
blue.  Teammates sit opposite each other across the table.

### Players

Each player is identified by a unique **player ID** and assigned a **seat**
(1–4).  In the `session_start` message, your bot receives both:

```json
{
  "player_id": "bot_player_01",
  "seat": 1
}
```

A player's full JSON representation (as seen in `iNewRound.players` or
`game_state_snapshot`) looks like:

```json
{
  "id": "player_01",
  "seat": 1,
  "team": "redTeam",
  "name": "Alice",
  "is_human": true,
  "cards_on_hand": "3H 4D 5C 6S ...",
  "played_cards": "pair-7 : 7H 7D",
  "profile": {
    "nickname": "Alice",
    "bot_model": null
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique player identifier. |
| `seat` | int | Seat number (1–4). |
| `team` | string | `"redTeam"` or `"blueTeam"`. |
| `name` | string | Display name (falls back to `id` if no nickname). |
| `is_human` | bool | `true` for human players, `false` for bots. |
| `cards_on_hand` | string | Space-separated card list (present only when the server includes private information for this player). |
| `played_cards` | string | Cards this player has played in the current round. |
| `profile.nickname` | string | Player's chosen display name. |
| `profile.bot_model` | string | If this player is a bot, the bot's model identifier. `null` for humans. |

> **For bot developers:** Your bot is an AI player, so `is_human` will be
> `false` and `profile.bot_model` will be set to your bot's model string.

### Player Ranks (Round Result)

When a round ends, each player is assigned a rank based on the order they
emptied their hand:

| Rank | JSON value | Chinese | Description |
|------|-----------|---------|-------------|
| 1st | `banker` | 上游 | First to empty hand |
| 2nd | `follower` | 二游 | Second to empty hand |
| 3rd | `third` | 三游 | Third to empty hand |
| 4th | `dweller` | 下游 | Last player with cards (there can be two dwellers from the same team) |

### Player Position (Relative)

Player positions are defined relative to a given player:

| Position | Applies to |
|----------|-----------|
| `self` | The reference player |
| `leftOpponent` | Player to the left (next in turn order) |
| `teamMate` | Partner (opposite seat) |
| `rightOpponent` | Player to the right |

In a 4-player game, the turn order goes: seat 1 → seat 2 → seat 3 → seat 4 → seat 1...

---

## Game State Structure

The game is organized as a strict hierarchy:

```
Game
└── Series (optional sets of rounds; used for 过A tracking)
└── Round (一局)
    └── Phase (一圈)
        └── Turn (一次出牌，含不出)
```

### Game

A **game** is the top-level container, identified by a `game_id` (a UUID v4
generated when the game instance is created). The `game_id` is distinct from the
`room_id` — a room may persist across multiple games, while each game receives
its own unique identifier. The `GameState` object tracks teams, scores, rounds,
and series:

```json
{
  "game_id": "game_12345",
  "required_number_of_players": 4,
  "team_level_rank": { "redTeam": "2", "blueTeam": "3" },
  "team_scores": { "redTeam": 5, "blueTeam": 2 },
  "series": [
    { "start_round_id": "R1", "end_round_id": "R2", "winner_team": "redTeam" }
  ],
  "rounds": [ /* Round objects */ ],
  "players": [ /* Player objects */ ]
}
```

The `game_state_snapshot` optionally included in `sPlayHandRequest` messages
contains this structure, but with only the current round and without
opponents' hidden cards.

### Series

A **series** (not to be confused with game "series" or tournament rounds)
tracks the 过A (passing Ace) mechanic.  Each series starts with a round and
ends when the team holding the Ace level either successfully passes it or is
demoted:

```json
{
  "start_round_id": "R1",
  "end_round_id": "R5",
  "winner_team": "redTeam"
}
```

| Field | Description |
|-------|-------------|
| `start_round_id` | The round that started this series. |
| `end_round_id` | The round that ended this series (`null` if in progress). |
| `winner_team` | `"redTeam"` or `"blueTeam"`; `null` if the series has not ended. |

Each time a series concludes, the winning team's score increments by 1.

### Round (一局)

A **round** is a complete deal and play through to when one team empties all
cards.  Rounds are identified by IDs like `"R1"`, `"R2"`, `"R3"`, etc.

```json
{
  "round_id": "R1",
  "level_rank": "2",
  "start_player_id": "player_01",
  "tribute_enabled": true,
  "creation_time": "2025-01-01T00:00:00.000Z",
  "phases": [ /* Phase objects */ ],
  "round_result": { /* RoundResult */ },
  "previous_round_result": null,
  "tribute_result": { /* TributeResult */ },
  "hands_at_start": {
    "player_01": "3H 4D 5C ...",
    "player_02": "6S 7H 9D ...",
    "player_03": "TC JS QH ...",
    "player_04": "KD AS BJ ..."
  },
  "players": [ /* Player objects */ ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `round_id` | string | Round identifier, format `"R" + number`. |
| `level_rank` | string | The level rank for this round (e.g. `"2"`, `"A"`). |
| `start_player_id` | string | Player who starts the round (after tribute). `null` during tribute. |
| `tribute_enabled` | bool | Whether tribute/anti-tribute is enabled. |
| `phases` | array | Ordered list of phases in this round. |
| `round_result` | object | The result of this round (see below). |
| `previous_round_result` | object | Result of the previous round; `null` for the first round. |

#### RoundResult

```json
{
  "banker": { "player_id": "player_01", "team": "redTeam" },
  "follower": { "player_id": "player_03", "team": "redTeam" },
  "dwellers": [{ "player_id": "player_02", "team": "blueTeam" }],
  "level_rank": "2",
  "team_of_level_rank": "redTeam",
  "a_plus_tries_of_red_team": null,
  "a_plus_tries_of_blue_team": null
}
```

| Field | Description |
|-------|-------------|
| `banker` | First to empty hand (上游). |
| `follower` | Second to empty hand (二游). |
| `third` | Third to empty hand (三游), for 6-player games. |
| `fourth` | Fourth to empty hand (四游), for 6-player games. |
| `dwellers` | Array of players who finished last (下游). In 4-player mode, this has one entry. |
| `level_rank` | Level rank of this round. |
| `team_of_level_rank` | The team whose level rank was being played. |

### Phase (一圈)

A **phase** is a sequence of turns where players respond to the lead hand.
A phase starts when a player leads (plays first) and ends when all other
players still holding cards have passed or when all players from one team
have emptied their hands.  Phase IDs use the format `"R1_P1"` (round 1,
phase 1).

```json
{
  "phase_id": "R1_P1",
  "start_player_id": "player_01",
  "turns": [ /* Turn objects */ ]
}
```

A new phase begins when:
- The starting player leads (hand on table is empty at the time)
- After a player plays and all other players pass — a new phase starts with
  that player as the leader
- After 接风 (JieFeng): when a player's teammate empties their hand, the
  partner inherits the lead for the next phase

### Turn (一次出牌)

A **turn** represents one player's action: either playing a hand of cards or
passing.  Turn IDs use the format `"R1_P1_T3"` (round 1, phase 1, turn 3).

```json
{
  "turn_id": "R1_P1_T3",
  "player_id": "player_02",
  "played_hand": {
    "type": "pair",
    "power": 7,
    "cards": "7H 7D"
  },
  "played_time": "2025-01-01T00:05:00.000Z",
  "bot_model": "StrongBot"
}
```

A **pass** turn has an empty `played_hand`:

```json
{
  "turn_id": "R1_P1_T4",
  "player_id": "player_03",
  "played_hand": { "type": "empty", "power": 0, "cards": "" },
  "played_time": "2025-01-01T00:05:02.000Z"
}
```

### ID Format Summary

| Level | ID Format | Example | Scope |
|-------|-----------|---------|-------|
| Round | `R{n}` | `R1`, `R2` | Unique within a game |
| Phase | `R{n}_P{m}` | `R1_P1`, `R2_P3` | Unique within a round |
| Turn | `R{n}_P{m}_T{k}` | `R1_P1_T1`, `R2_P3_T4` | Unique within a game |

### Tribute Stage

Before the first phase of each round (except the first round), there is a
**tribute stage** (进贡/还贡):

1. The dwellers from the previous round must pay tribute to the bankers.
2. Each dweller sends their highest card to the corresponding banker.
3. The banker returns a card (anti-tribute / 还贡) to the dweller.
4. If each team has one dweller, it's a single tribute (单贡).
5. If both dwellers are on the same team, it's a double tribute (双贡).
6. If both teams have equal red joker counts, tribute is **resisted** (抗贡)
   — no tribute cards are paid.

The `tribute_result` field in the round shows the tribute state:

```json
{
  "tributes": [
    {
      "payer_id": "player_03",
      "payer": { "id": "player_03" },
      "receiver_id": "player_01",
      "winner": { "id": "player_01" },
      "tribute_card": "RJ",
      "return_card": "3D"
    }
  ],
  "is_resisted": false,
  "red_jokers": { "1": 2, "2": 1, "3": 0, "4": 1 }
}
```

Your bot handles tribute via `sTributeCardRequest` (when it must pay tribute)
and `sReturnCardRequest` (when it must return a card after receiving tribute).

### Turn Order

The turn order is clockwise by seat: **seat 1 → seat 2 → seat 3 → seat 4 →
seat 1** (repeating).  Within a phase, turns cycle through players who still
have cards; players who have emptied their hand are skipped.

### Game Progression

```
Game Start
  │
  ▼
Round 1 (level=2, no tribute)
  ├── Phase 1
  │     ├── Turn: player leads
  │     ├── Turn: next player plays or passes
  │     └── ... until phase ends
  ├── Phase 2 ...
  └── Round ends → RoundResult computed → scores updated
  │
  ▼
Round 2 (level updated from RoundResult)
  ├── Tribute stage (if applicable)
  ├── Phase 1 ...
  └── ...
  │
  ▼
...continue until target series/rounds completed
```

---

## Card, Hand & Deck Encoding

### Individual Cards

Each card is encoded as a **2–3 character string**:

```
<rank><suit>[<level-marker>]
```

| Component | Encoding |
|-----------|----------|
| **Rank**  | `2`–`9`, `T` (10), `J`, `Q`, `K`, `A`, `BJ` (black joker), `RJ` (red joker) |
| **Suit**  | `H` (hearts ♥), `D` (diamonds ♦), `C` (clubs ♣), `S` (spades ♠) |
| **Level marker** | `*` suffix means the card is the current **level card** (级牌) |

**Examples:**

| String | Meaning |
|--------|---------|
| `3H`   | 3 of Hearts |
| `TD`   | 10 of Diamonds |
| `AS`   | Ace of Spades |
| `2C*`  | 2 of Clubs (level card) |
| `BJ`   | Black Joker (小王) |
| `RJ`   | Red Joker (大王) |

> **Note:** Jokers have no suit character.  Hearts that are also the level
> card are **wild cards** (逢人配).

### Card Lists

Multiple cards are space-separated:

```
3H 3D 3C 5S 5H
```

### Hands (with type information)

A **hand** (played set of cards) has type, power, and the card list:

```
<type>-<power> : <card-list>
```

**Hand types and their structure:**

| Type | Name (Chinese) | Valid size(s) | Example |
|------|-------|------|---------|
| `single` | 单张 | 1 card | `single-3 : 3H` |
| `pair` | 对子 | 2 cards | `pair-4 : 4H 4D` |
| `triple` | 三不带 | 3 cards | `triple-5 : 5H 5D 5C` |
| `fullHouse` | 三带一对 | 5 cards | `fullHouse-5 : 5H 5D 5C 3S 3C` |
| `straight` | 顺子 | 5 cards | `straight-7 : 3H 4D 5C 6S 7H` |
| `tube` | 木板（三连对） | 6 cards | `tube-5 : 3H 3D 4C 4S 5H 5D` |
| `plate` | 钢板 | 6 cards | `plate-6 : 4H 4D 4C 5S 5H 5C` |
| `bomb` | 炸弹 | 4+ cards | `bomb-5 : 5H 5D 5C 5S` |
| `empty` | 不出 / 过 | 0 cards | `empty-0 :` |

The **power** value is used to compare hands of the same type.  Higher power
beats lower power.  Bombs beat all non-bomb types.

### Decks

The standard game uses **2 decks** of 54 cards each (108 cards total), as
specified by `number_of_standard_decks`.  Level cards are promoted: all cards
of the current level rank become level cards, and all ♥ cards of the level
rank become wild cards (逢人配).

---

## Bot Protocol Messages

Every message between the platform and your bot is a **JSON object** with a
`type` field identifying the message kind.

### Message Envelope Types

```
BotMessage
├── SessionStart    (type: "session_start")
├── SessionStarted  (type: "session_started")
├── SessionEnd      (type: "session_end")
├── SessionEnded    (type: "session_ended")
├── GameMessage     (type: "game_message")
└── Error           (type: "error")
```

---

### Session Lifecycle

#### `session_start` — Platform → Bot

The game server initiates a bot session.  For HTTP bots, this is the **first**
request the platform makes to your `/sessions` endpoint.

```json
{
  "type": "session_start",
  "session_id": "sess_abc123",
  "deployment_id": "dep_xyz789",
  "player_id": "bot_player_01",
  "seat": 1,
  "rule_set": "classic",
  "protocol_version": "guandan-bot-v1",
  "number_of_standard_decks": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | **Required.** Unique session identifier. |
| `deployment_id` | string | Deployment ID this session belongs to. |
| `player_id` | string | Player ID assigned to this bot. |
| `seat` | int | Seat number (1–4). Seats 1,3 = red team; 2,4 = blue team. |
| `rule_set` | string | Rule set name, e.g. `"classic"`. |
| `protocol_version` | string | Always `"guandan-bot-v1"`. |
| `number_of_standard_decks` | int | Number of standard 54-card decks (usually 2). |

> **WebSocket bots** receive a minimal `session_start` first (only
> `session_id`, `deployment_id`, `protocol_version`), followed by a full one
> once the outbound agent provisions the session.

#### `session_started` — Bot → Platform

Your bot must respond to accept (or decline) the session.

```json
{
  "type": "session_started",
  "session_id": "sess_abc123",
  "accepted": true
}
```

#### `session_end` — Platform → Bot

The game server ends the session (game over, player left, or error).

```json
{
  "type": "session_end",
  "session_id": "sess_abc123"
}
```

#### `session_ended` — Bot → Platform

Your bot acknowledges session termination.

```json
{
  "type": "session_ended",
  "session_id": "sess_abc123"
}
```

---

### `game_message` — Platform ↔ Bot (bidirectional)

This is the **primary message type** during gameplay.  It wraps a
[GameMessage](#game-messages-payload-reference) payload.

```json
{
  "type": "game_message",
  "session_id": "sess_abc123",
  "request_id": "req_001",
  "deadline_millis": 1718000000000,
  "payload": {
    "type": "sPlayHandRequest",
    "player_id": "bot_player_01",
    "room_id": "room_xyz",
    "round_id": "R1",
    "turn_id": "R1_P1_T3",
    "hand_on_table": "pair-7 : 7H 7D",
    "seat_of_hand_on_table": 2,
    "level_rank": "2",
    "available_cards": "3H 4D 5C ..."
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"game_message"`. |
| `session_id` | string | Session identifier. |
| `request_id` | string | **Request/response correlation ID.** Your bot MUST echo this back in its response so the platform can match it.  Absent for informational messages. |
| `deadline_millis` | int | Optional deadline for the response (Unix ms). |
| `payload` | object | A [GameMessage](#game-messages-payload-reference) object. |

> **Critical rule:** When responding to a `game_message` that has a
> `request_id`, your bot's response MUST include the **same** `request_id`.

#### Response with action

```json
{
  "type": "game_message",
  "session_id": "sess_abc123",
  "request_id": "req_001",
  "payload": {
    "type": "pPlayHandRequest",
    "player_id": "bot_player_01",
    "room_id": "room_xyz",
    "cards": "8H 8D 8C 8S",
    "round_id": "R1",
    "turn_id": "R1_P1_T3"
  }
}
```

#### Informational message (no response needed)

For informational messages (those starting with `i`), your bot does not need
to respond.  Return HTTP `204 No Content` or simply omit a WebSocket frame.

---

### `error` — Platform ↔ Bot (bidirectional)

```json
{
  "type": "error",
  "session_id": "sess_abc123",
  "code": "unknown_session",
  "message": "Bot session has not been started."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable error code. |
| `message` | string | Human-readable error description. |

Common error codes: `unauthorized`, `unknown_session`, `invalid_bot_message`,
`session_id_mismatch`, `unsupported_message_type`.

---

## Building an HTTP Bot

An HTTP bot exposes REST endpoints that the game server calls.  Your bot is a
**server** — the platform is the **client**.

### Endpoint Specification

Your bot MUST implement these endpoints:

#### `POST /sessions`

Called to start a new bot session.  The body is a
[`session_start`](#sessionstart--platform--bot) message.

**Response:** A [`session_started`](#sessionstarted--bot--platform) message.

#### `POST /sessions/{session_id}/messages`

Called for each game message during the session.  The body is a
[`game_message`](#gamemessage--platform--bot-bidirectional) message.

The `session_id` in the URL path MUST match the `session_id` in the JSON body.

**Response:** A [`game_message`](#gamemessage--platform--bot-bidirectional)
with the bot's action, or HTTP `204 No Content` for informational messages.

#### `DELETE /sessions/{session_id}`

Called to end a session.  The body is a
[`session_end`](#sessionend--platform--bot) message.

**Response:** A [`session_ended`](#sessionended--bot--platform) message.

#### `GET /health` (recommended)

Optional health check endpoint.  Return `{"status": "ok"}` with HTTP 200.

### Authentication (Server → Bot)

If you provided an `authorization_api_key` during deployment registration, the
platform will send it in every request:

- `Authorization: Bearer <your-api-key>`
- Or `X-Api-Key: <your-api-key>`

Your bot SHOULD validate this header on every request.

### Content Types

- All requests and responses use `Content-Type: application/json`.
- Responses with no body use HTTP `204 No Content`.

### Broadcast vs Targeted Messages

Play requests (`sPlayHandRequest`), tribute requests (`sTributeCardRequest`),
and return-card requests (`sReturnCardRequest`) are **broadcast** by the game
server to every player in the room. Only the **targeted player** (the player
whose turn it is to act) receives non-empty `available_cards` in the payload.
For all other players, the `available_cards` field is empty.

> **Important:** Your bot MUST check whether `available_cards` is non-empty
> before responding to these request types. If it is empty, the bot is an
> observer for that message and should not respond.

### Minimal HTTP Bot Example (Python)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
sessions = {}

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/sessions", methods=["POST"])
def create_session():
    msg = request.get_json()
    sid = msg["session_id"]
    seat = msg.get("seat", 1)
    sessions[sid] = {"cards": [], "seat": seat, "player_id": msg.get("player_id")}
    return jsonify({"type": "session_started", "session_id": sid, "accepted": True})

@app.route("/sessions/<sid>/messages", methods=["POST"])
def handle_message(sid):
    msg = request.get_json()
    payload = msg["payload"]
    msg_type = payload["type"]

    if msg_type == "sPlayHandRequest":
        # Play requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return "", 204  # Not my turn — skip
        cards = cards_str.split()
        response_cards = compute_play(cards, payload["hand_on_table"], payload["level_rank"])
        return jsonify({
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pPlayHandRequest",
                "player_id": sessions[sid]["player_id"],
                "room_id": payload["room_id"],
                "cards": response_cards,
                "round_id": payload["round_id"],
                "turn_id": payload["turn_id"]
            }
        })

    elif msg_type == "sTributeCardRequest":
        # Tribute requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return "", 204  # Not my turn — skip
        cards = cards_str.split()
        tribute = select_tribute(cards)
        return jsonify({
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pPayTributeRequest",
                "player_id": sessions[sid]["player_id"],
                "room_id": payload["room_id"],
                "tribute_card": tribute,
                "round_id": payload["round_id"]
            }
        })

    elif msg_type == "sReturnCardRequest":
        # Return-card requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return "", 204  # Not my turn — skip
        cards = cards_str.split()
        return_card = select_return(cards)
        return jsonify({
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pReturnCardRequest",
                "player_id": sessions[sid]["player_id"],
                "room_id": payload["room_id"],
                "return_card": return_card,
                "round_id": payload["round_id"]
            }
        })

    # Informational message — no response needed
    return "", 204

@app.route("/sessions/<sid>", methods=["DELETE"])
def end_session(sid):
    sessions.pop(sid, None)
    return jsonify({"type": "session_ended", "session_id": sid})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

---

## Building a WebSocket Bot

A WebSocket bot connects to the platform's bot gateway and maintains a
persistent connection.  Your bot is the **client** — the platform is the
**server**.

### Connection

Connect to:

```
wss://<game-server-host>/bot-gateway/v1
```

**Required headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <your-deployment-key>` |
| `X-Guandan-Bot-Protocol` | `guandan-bot-v1` |

> The **deployment key** is returned once when you register your deployment
> (see [Deploying Your Bot](#deploying-your-bot)).  Store it securely.

### Message Flow

After connecting, the platform sends JSON text frames.  Your bot responds
with JSON text frames on the same socket.

```
Platform                              Bot
   │                                    │
   │ ── session_start ────────────────→ │
   │ ←─ session_started ─────────────── │
   │                                    │
   │ ── game_message (play hand?) ────→ │
   │ ←─ game_message (cards to play) ── │
   │                                    │
   │ ── game_message (info) ──────────→ │
   │   (no response needed)             │
   │                                    │
   │ ── session_end ──────────────────→ │
   │ ←─ session_ended ───────────────── │
   │                                    │
   │ ── close ────────────────────────→ │
```

### Reconnection

The platform may close the connection at any time (game server restart,
deployment rotation, etc.).  Your bot SHOULD implement exponential backoff
reconnection.  A new `session_start` will be sent after reconnection.

### Minimal WebSocket Bot Example (Python)

```python
import asyncio
import json
import websockets

DEPLOYMENT_KEY = "your-deployment-key-here"
GAME_SERVER_URL = "wss://game-server.example.com"

async def bot():
    uri = f"{GAME_SERVER_URL}/bot-gateway/v1"
    async with websockets.connect(uri, extra_headers={
        "Authorization": f"Bearer {DEPLOYMENT_KEY}",
        "X-Guandan-Bot-Protocol": "guandan-bot-v1",
    }) as ws:
        sessions = {}
        async for raw in ws:
            msg = json.loads(raw)
            msg_type = msg["type"]

            if msg_type == "session_start":
                sid = msg["session_id"]
                sessions[sid] = {
                    "player_id": msg.get("player_id"),
                    "seat": msg.get("seat", 1),
                    "cards": [],
                }
                await ws.send(json.dumps({
                    "type": "session_started",
                    "session_id": sid,
                    "accepted": True,
                }))

            elif msg_type == "game_message":
                response = handle_game_message(msg, sessions)
                if response:
                    await ws.send(json.dumps(response))

            elif msg_type == "session_end":
                sid = msg["session_id"]
                sessions.pop(sid, None)
                await ws.send(json.dumps({
                    "type": "session_ended",
                    "session_id": sid,
                }))

def handle_game_message(msg, sessions):
    sid = msg["session_id"]
    payload = msg["payload"]
    msg_type = payload["type"]
    bot_state = sessions.get(sid)
    if not bot_state:
        return None

    if msg_type == "sPlayHandRequest":
        # Play requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return None  # Not my turn — skip
        cards = cards_str.split()
        response_cards = compute_play(cards, payload["hand_on_table"], payload["level_rank"])
        return {
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pPlayHandRequest",
                "player_id": bot_state["player_id"],
                "room_id": payload["room_id"],
                "cards": response_cards,
                "round_id": payload["round_id"],
                "turn_id": payload["turn_id"],
            },
        }

    elif msg_type == "sTributeCardRequest":
        # Tribute requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return None  # Not my turn — skip
        cards = cards_str.split()
        tribute = cards[0] if cards else "RJ"
        return {
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pPayTributeRequest",
                "player_id": bot_state["player_id"],
                "room_id": payload["room_id"],
                "tribute_card": tribute,
                "round_id": payload["round_id"],
            },
        }

    elif msg_type == "sReturnCardRequest":
        # Return-card requests are broadcast; only the targeted player has cards.
        cards_str = payload.get("available_cards", "")
        if not cards_str:
            return None  # Not my turn — skip
        cards = cards_str.split()
        return_card = cards[-1] if cards else "3H"
        return {
            "type": "game_message",
            "session_id": sid,
            "request_id": msg.get("request_id"),
            "payload": {
                "type": "pReturnCardRequest",
                "player_id": bot_state["player_id"],
                "room_id": payload["room_id"],
                "return_card": return_card,
                "round_id": payload["round_id"],
            },
        }

    # Informational message — no response
    return None

asyncio.run(bot())
```

---

## Game Messages (Payload Reference)

All game messages are sent inside a `game_message` envelope's `payload` field.
The `payload.type` field determines the specific message.

### Messages Requiring a Response (Server → Bot)

#### `sPlayHandRequest` — Play cards

The server requests your bot to play a hand of cards.

```json
{
  "type": "sPlayHandRequest",
  "message_id": "msg_001",
  "room_id": "room_xyz",
  "player_id": "bot_player_01",
  "timeout": 30,
  "hand_on_table": "pair-7 : 7H 7D",
  "seat_of_hand_on_table": 2,
  "level_rank": "2",
  "turn_id": "R1_P1_T3",
  "round_id": "R1",
  "available_cards": "3H 4D 5C 6S 7H 9D TC JS QH KD AS BJ RJ ...",
  "game_state_snapshot": { /* see GameState definition */ }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hand_on_table` | string | The hand currently on the table. `"empty-0 :"` at the start of a phase (you must lead). |
| `seat_of_hand_on_table` | int | Seat of the player who played the current hand. `null` at the start of a phase or after you played. |
| `level_rank` | string | Current level rank (e.g. `"2"`, `"A"`). |
| `available_cards` | string | Space-separated list of cards currently in the bot's hand. |
| `turn_id` | string | Unique turn identifier. |
| `round_id` | string | Unique round identifier. |
| `game_state_snapshot` | object | Optional full game state snapshot. |

**Response:** [`pPlayHandRequest`](#pplayhandrequest--bot--server)

> If you cannot or do not want to play, respond with an empty hand:
> `"cards": ""` or `"cards": "empty-0 :"`.  If you want to pass when there is a
> hand on the table (others haven't all passed yet), also respond with empty
> cards.

#### `sTributeCardRequest` — Pay tribute

The server requests your bot to pay a tribute card (进贡).

```json
{
  "type": "sTributeCardRequest",
  "message_id": "msg_002",
  "room_id": "room_xyz",
  "player_id": "bot_player_01",
  "round_id": "R1",
  "available_cards": "3H 4D 5C ..."
}
```

**Response:** [`pPayTributeRequest`](#ppaytriberequest--bot--server)

#### `sReturnCardRequest` — Return a card (anti-tribute)

The server requests your bot to return a card to the tribute payer (还贡).

```json
{
  "type": "sReturnCardRequest",
  "message_id": "msg_003",
  "room_id": "room_xyz",
  "player_id": "bot_player_01",
  "round_id": "R1",
  "available_cards": "3H 4D 5C ..."
}
```

**Response:** [`pReturnCardRequest`](#preturncardrequest--bot--server)

---

### Action Messages (Bot → Server)

#### `pPlayHandRequest` — Play cards response

```json
{
  "type": "pPlayHandRequest",
  "player_id": "bot_player_01",
  "room_id": "room_xyz",
  "cards": "8H 8D 8C 8S",
  "round_id": "R1",
  "turn_id": "R1_P1_T3",
  "bot_model": "MyBot-v1"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `cards` | string | Space-separated cards to play, or `""` / `"empty-0 :"` to pass. |
| `round_id` | string | MUST match the round_id from the request. |
| `turn_id` | string | MUST match the turn_id from the request. |
| `bot_model` | string | Optional. Your bot's model identifier. |

#### `pPayTributeRequest` — Tribute response

```json
{
  "type": "pPayTributeRequest",
  "player_id": "bot_player_01",
  "room_id": "room_xyz",
  "tribute_card": "RJ",
  "round_id": "R1",
  "bot_model": "MyBot-v1"
}
```

#### `pReturnCardRequest` — Return card response

```json
{
  "type": "pReturnCardRequest",
  "player_id": "bot_player_01",
  "room_id": "room_xyz",
  "return_card": "3H",
  "round_id": "R1",
  "bot_model": "MyBot-v1"
}
```

---

### Informational Messages (Server → Bot, No Response Required)

These are sent to keep your bot informed of game state.  Your bot does not
need to respond — return `204` (HTTP) or nothing (WebSocket).

#### `iNewRound` — New round started

```json
{
  "type": "iNewRound",
  "room_id": "room_xyz",
  "round_id": "R1",
  "start_player_id": "player_01",
  "level_rank": "2",
  "team_level_rank": { "redTeam": "2", "blueTeam": "3" },
  "previous_round_result": { /* RoundResult, null for first round */ },
  "players": [
    { "id": "player_01", "seat": 1, "team": "redTeam", "name": "Alice" },
    { "id": "player_02", "seat": 2, "team": "blueTeam", "name": "Bob" },
    { "id": "player_03", "seat": 3, "team": "redTeam", "name": "Carol" },
    { "id": "player_04", "seat": 4, "team": "blueTeam", "name": "Dave" }
  ],
  "hand": "3H 4D 5C 6S 7H 9D TC JS QH KD AS BJ RJ ..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hand` | string | The bot's initial hand for this round. |
| `level_rank` | string | The level rank for this round. |
| `team_level_rank` | object | Current level ranks for each team. |
| `players` | array | All players with IDs, seats, names, and teams. |

#### `iNewPhase` — New phase started

```json
{
  "type": "iNewPhase",
  "room_id": "room_xyz",
  "phase_id": "P1",
  "start_player_id": "player_01"
}
```

#### `iStartPlayer` — Designated start player

```json
{
  "type": "iStartPlayer",
  "room_id": "room_xyz",
  "start_player_id": "player_01",
  "round_id": "R1",
  "phase_id": "P1"
}
```

#### `iHandPlayed` — A player played cards

```json
{
  "type": "iHandPlayed",
  "room_id": "room_xyz",
  "player_id": "player_02",
  "round_id": "R1",
  "phase_id": "P1",
  "turn_id": "R1_P1_T3",
  "cards": "pair-7 : 7H 7D",
  "seat": 2,
  "bot_model": "StrongBot"
}
```

#### `iTributeCard` — A tribute was paid

```json
{
  "type": "iTributeCard",
  "room_id": "room_xyz",
  "payer_id": "player_03",
  "winner_id": "player_01",
  "round_id": "R2",
  "tribute": "RJ"
}
```

#### `iReturnCard` — A card was returned (anti-tribute)

```json
{
  "type": "iReturnCard",
  "room_id": "room_xyz",
  "payer_id": "player_01",
  "winner_id": "player_03",
  "round_id": "R2",
  "return_card": "3D"
}
```

#### `iTributeResult` — All tributes resolved

```json
{
  "type": "iTributeResult",
  "room_id": "room_xyz",
  "round_id": "R2",
  "tribute_result": {
    "tributes": [
      { "payer": { "id": "player_03" }, "winner": { "id": "player_01" }, "card": "RJ" },
      { "payer": { "id": "player_04" }, "winner": { "id": "player_02" }, "card": "BJ" }
    ],
    "is_resisted": false
  }
}
```

#### `iTributeResistance` — Tribute was resisted (抗贡)

```json
{
  "type": "iTributeResistance",
  "room_id": "room_xyz",
  "round_id": "R2",
  "start_player_id": "player_01",
  "red_joker_counts": { "1": 2, "2": 1, "3": 0, "4": 1 }
}
```

#### `iPlayerEmptiedCards` — A player played their last card

```json
{
  "type": "iPlayerEmptiedCards",
  "room_id": "room_xyz",
  "player_id": "player_01",
  "round_id": "R1",
  "player_rank": "banker"
}
```

`player_rank` values: `banker` (1st/上游), `follower` (2nd/二游), `third`
(3rd/三游), `dweller` (4th/下游).

#### `iRoundResult` — Round result (partial or final)

```json
{
  "type": "iRoundResult",
  "room_id": "room_xyz",
  "round_result": {
    "banker": { "id": "player_01", "team": "redTeam" },
    "follower": { "id": "player_03", "team": "redTeam" },
    "dwellers": [{ "id": "player_02", "team": "blueTeam" }]
  },
  "is_partial": false,
  "emptied_by": "player_03"
}
```

#### `iRoundEnded` — Round ended

```json
{
  "type": "iRoundEnded",
  "room_id": "room_xyz",
  "round_id": "R1",
  "round": { /* Full round data */ }
}
```

#### `iTeamScores` — Team scores updated

```json
{
  "type": "iTeamScores",
  "room_id": "room_xyz",
  "team_scores": { "redTeam": 5, "blueTeam": 2 }
}
```

#### `iCardsOnHand` — Cards remaining for each player

```json
{
  "type": "iCardsOnHand",
  "room_id": "room_xyz",
  "cards_on_hand": {
    "player_01": "3H 4D",
    "player_02": "5C 6S 7H 9D TC",
    "player_03": null,
    "player_04": "JS QH KD"
  }
}
```

#### `iPlayerJoinedRoom` — A player joined the room

Broadcast when a player (human or bot) joins the game room. The message sent
to the **joining player** differs from the one broadcast to existing players.

**Sent to the joining player** (includes `roomInfo`, `gameState`, and
`reconnectToken`):

```json
{
  "type": "iPlayerJoinedRoom",
  "room_id": "room_xyz",
  "player": { "id": "bot_player_01", "seat": 1, "name": "MyBot", "team": "redTeam" },
  "bot_model": "MyBot-v1",
  "profile": { "bot_model": "MyBot-v1" },
  "room_info": {
    "room_id": "room_xyz",
    "room_code": "AB12CD",
    "name": "Test Room",
    "config": { "max_players": 4, "rule_set": "classic" }
  },
  "game_state": {
    "game_id": "room_xyz",
    "team_level_rank": { "redTeam": "2", "blueTeam": "3" },
    "team_scores": { "redTeam": 5, "blueTeam": 2 },
    "current_level_rank": "2",
    "number_of_standard_decks": 2,
    "players": [
      {
        "id": "bot_player_01",
        "seat": 1,
        "team": "redTeam",
        "cards_on_hand": "3H 4D 5C 6S ...",
        "played_cards": null
      }
    ],
    "rounds": [ /* Round objects */ ]
  },
  "reconnect_token": "<crypto-secure-one-time-token>"
}
```

**Broadcast to existing players** (only minimal fields):

```json
{
  "type": "iPlayerJoinedRoom",
  "room_id": "room_xyz",
  "player": { "id": "bot_player_01", "seat": 1, "name": "MyBot", "team": "redTeam" },
  "bot_model": "MyBot-v1",
  "profile": { "bot_model": "MyBot-v1" }
}
```

> **For bot developers:** When your bot receives `iPlayerJoinedRoom` and
> `game_state` is **not null**, it means the bot is joining an already-running
> game (e.g., replacing a disconnected player or joining mid-game). The
> `game_state` field contains the **complete current game state** with all
> information available to the intended player:
>
> - `players` — all players in the game, with `cards_on_hand` populated **only
>   for the joining bot's own player entry** (other players' `cards_on_hand`
>   will be `null`).
> - `rounds` — all completed and in-progress rounds.
> - `current_level_rank` and `number_of_standard_decks` — the current level
>   rank and deck configuration.
> - `team_level_rank` and `team_scores` — current team standings.
>
> Your bot should use this snapshot to initialize its internal game state
> before making any decisions. Store the `reconnect_token` for potential
> reconnection scenarios.

#### `iPlayerQuitRoom` — A player left the room

```json
{
  "type": "iPlayerQuitRoom",
  "room_id": "room_xyz",
  "player_id": "player_02"
}
```

#### `iGameRoomCreated` — Room created

```json
{
  "type": "iGameRoomCreated",
  "room_id": "room_xyz",
  "room_info": { "room_id": "room_xyz", "room_code": "AB12CD", "name": "My Room", "config": { /* ... */ } },
  "players": [ /* ... */ ]
}
```

#### `iGameRoomClosed` — Room closed

```json
{ "type": "iGameRoomClosed", "room_id": "room_xyz" }
```

#### `iPlayerSeat` — Player seat/team assignment

```json
{ "type": "iPlayerSeat", "room_id": "room_xyz", "player_id": "player_01", "seat": 1, "team": "redTeam" }
```

#### `iJieFeng` — 接风 (player inherits the lead)

```json
{ "type": "iJieFeng", "room_id": "room_xyz", "player_id": "player_03", "phase_id": "P3" }
```

#### `iRequestResult` — Result of a previous request

```json
{
  "type": "iRequestResult",
  "player_id": "bot_player_01",
  "request": "pPlayHandRequest",
  "result": "success"
}
```

Common `result` values: `success`, `invalidHand`, `invalidRequest`, `notInGameRoom`.

#### `iTimeOut` — A player timed out

```json
{
  "type": "iTimeOut",
  "room_id": "room_xyz",
  "player_id": "player_02",
  "request": "sPlayHandRequest",
  "round_id": "R1",
  "turn_id": "R1_P1_T3"
}
```

#### `iMoreTimeGranted` — More time granted

```json
{
  "type": "iMoreTimeGranted",
  "room_id": "room_xyz",
  "player_id": "player_02",
  "new_allocated_seconds": 30
}
```

#### `iServerClosed` — Server shutting down

```json
{ "type": "iServerClosed", "reason": "maintenance" }
```

#### `chat` — Chat message

```json
{
  "type": "chat",
  "room_id": "room_xyz",
  "message": {
    "senderId": "player_01",
    "message": "Good luck!",
    "timestamp": "2025-01-01T00:00:00.000Z",
    "roomId": "room_xyz",
    "mediaType": "MediaType.text"
  }
}
```

#### `heartbeat` — Connection keep-alive

```json
{ "type": "heartbeat", "player_id": "player_01" }
```

#### `autoDelegated` — Auto-delegation toggle

```json
{ "type": "autoDelegated", "room_id": "room_xyz", "player_id": "player_01", "auto_delegated": true }
```

---

## Deploying Your Bot

Deployment is a three-step process via the Lobby REST API.

### Step 1: Register a Provider

```
POST /api/bots/providers
Authorization: Bearer <your-access-token>
Content-Type: application/json

{
  "display_name": "My Bot Company",
  "contact_email": "bots@example.com"
}
```

**Response 201:**
```json
{
  "provider": {
    "provider_id": "prov_abc123",
    "display_name": "My Bot Company",
    "status": "pending",
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z"
  }
}
```

> Provider registration requires approval from the platform administrator
> before definitions and deployments can be created.  The `status` field
> must be `"approved"`.

### Step 2: Create a Bot Definition

```
POST /api/bots/definitions
Authorization: Bearer <your-access-token>
Content-Type: application/json

{
  "provider_id": "prov_abc123",
  "display_name": "My Guandan Bot",
  "version": "1.0.0",
  "description": "A state-of-the-art Guandan bot using MCTS.",
  "bot_code": "my_bot",
  "supported_rule_sets": ["classic"],
  "supported_protocol_versions": ["guandan-bot-v1"],
  "visibility": "private"
}
```

| Field | Description |
|-------|-------------|
| `provider_id` | Your provider ID from Step 1. |
| `display_name` | Human-readable bot name. |
| `version` | Semantic version string. |
| `bot_code` | Short machine-readable code. The full **bot model** becomes `{provider_id}-{bot_code}-{version}`. |
| `supported_rule_sets` | List of rule sets, e.g. `["classic"]`. |
| `supported_protocol_versions` | Must include `"guandan-bot-v1"`. |
| `visibility` | `"private"`, `"unlisted"`, or `"public"`. |

**Response 201:**
```json
{
  "definition": {
    "bot_definition_id": "def_xyz789",
    "provider_id": "prov_abc123",
    "display_name": "My Guandan Bot",
    "version": "1.0.0",
    "bot_code": "my_bot",
    "status": "draft",
    "created_at": "2025-01-01T00:00:00.000Z"
  }
}
```

### Step 3: Register a Deployment

```
POST /api/bots/deployments
Authorization: Bearer <your-access-token>
Content-Type: application/json

{
  "provider_id": "prov_abc123",
  "transport_type": "http",
  "base_url": "https://my-bot.example.com",
  "supported_bot_definition_ids": ["def_xyz789"],
  "supported_protocol_versions": ["guandan-bot-v1"],
  "max_concurrent_sessions": 10,
  "region": "us-east"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `transport_type` | string | `"http"` or `"websocket"`. |
| `base_url` | string | **HTTP bots only.** Your bot's base URL. |
| `supported_bot_definition_ids` | array | Bot definition IDs this deployment serves. |
| `supported_protocol_versions` | array | Must include `"guandan-bot-v1"`. |
| `max_concurrent_sessions` | int | Max simultaneous game sessions. |
| `region` | string | Optional deployment region. |
| `authorization_api_key` | string | **HTTP bots optional.** If provided, the platform includes this in `Authorization: Bearer` headers when calling your bot. **The platform now issues invocation tokens and returns them in the response — prefer using that.** |

**Response 201 (SAVE THESE VALUES — they are only returned once):**
```json
{
  "deployment": {
    "deployment_id": "dep_123abc",
    "transport_type": "http",
    "base_url": "https://my-bot.example.com",
    "status": "pending_verification"
  },
  "deployment_management_key": "dpmk_xxxx...",
  "bot_invocation_token": "gdk_bot_xxxx..."
}
```

| Field | Purpose |
|-------|---------|
| `deployment_management_key` | Used to manage this deployment (verify, health check, delete). **Store securely.** |
| `bot_invocation_token` | The platform uses this token when calling your HTTP bot. Your bot should validate it. |

### Verifying a Deployment

After registration, verify your deployment's base URL is reachable:

```
POST /api/bots/deployments/{deployment_id}/verify
Authorization: Bearer <your-access-token>
Content-Type: application/json

{ "base_url": "https://my-bot.example.com" }
```

### Deployment Lifecycle

```
pending_verification → healthy → (active)
                              → degraded
                              → unavailable
                              → disabled
```

---

## Testing Your Bot

### Option 1: Using `auto_test.py` (Recommended)

The platform includes an automated test runner in `benchmark/auto_test.py`.

**Prerequisites:**
- Python 3.8+
- `pip install requests pyyaml`

**Configuration (`benchmark/config.yaml`):**

```yaml
auto_test_api_key: "gdk_test_kid_xxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
lobby_url: "http://localhost:8686"
num_rounds: 10
sse_timeout_s: 120
heartbeat_timeout_s: 45

bots:
  seat_1:
    type: builtin
    bot_code: strongBot
  seat_2:
    type: deployed
    deployment_id: "dep_123abc"
    deployment_key: "dpmk_xxxx..."
  seat_3:
    type: builtin
    bot_code: strongBot
  seat_4:
    type: deployed
    deployment_id: "dep_456def"
```

Each seat can use:
- `type: builtin` with `bot_code: "basicBot"` or `"strongBot"` (internal bots)
- `type: deployed` with `deployment_id` and optional `deployment_key` (your bot)

**Running:**

```bash
# 10 rounds with mixed bots
python3 benchmark/auto_test.py --num-rounds 10

# Verbose mode (print all agent messages)
python3 benchmark/auto_test.py --num-rounds 5 --verbose

# External bots only
python3 benchmark/auto_test.py --external-only
```

The test script:
1. Checks lobby health
2. Discovers available bot deployments
3. Creates a test game with the specified bot assignments
4. Subscribes to SSE events and monitors the game
5. Prints a detailed report with round-by-round scores

### Option 2: Using the Dart Test Bots

The `guandan_bot` package includes reference implementations:

- `HttpTestBot` — A minimal HTTP bot server.
- `WebSocketTestBot` — A minimal WebSocket bot client.

See `guandan_bot/test/` for integration tests that demonstrate the protocol.

### Option 3: Manual cURL Testing (HTTP Bots)

```bash
# Start a session
curl -X POST http://your-bot:8080/sessions \
  -H "Content-Type: application/json" \
  -d '{"type":"session_start","session_id":"test_001","player_id":"p1","seat":1}'

# Send a play-hand request
curl -X POST http://your-bot:8080/sessions/test_001/messages \
  -H "Content-Type: application/json" \
  -d '{
    "type":"game_message",
    "session_id":"test_001",
    "request_id":"req_001",
    "payload":{
      "type":"sPlayHandRequest",
      "player_id":"p1",
      "room_id":"room_001",
      "round_id":"R1",
      "turn_id":"R1_P1_T1",
      "hand_on_table":"empty-0 :",
      "level_rank":"2",
      "available_cards":"3H 4D 5C 6S 7H 9D TC JS QH KD AS BJ RJ"
    }
  }'

# End the session
curl -X DELETE http://your-bot:8080/sessions/test_001 \
  -H "Content-Type: application/json" \
  -d '{"type":"session_end","session_id":"test_001"}'
```

---

## Health Checks & Monitoring

### For HTTP Bots

The platform periodically verifies HTTP bots are reachable:

1. **Endpoint verification** (`POST /api/bots/deployments/{id}/verify`): The
   lobby sends a verification request to your `base_url`.

2. **Health polling** (`GET /api/bots/deployments/{id}/health`): Returns the
   current connection status of your deployment from the game server's
   perspective.

Your bot SHOULD implement `GET /health` returning `{"status": "ok"}`.

### For WebSocket Bots

The game server monitors the WebSocket connection:

- If the bot disconnects, the deployment status changes to `degraded` or
  `unavailable`.
- If the bot reconnects within the grace period, status returns to `healthy`.
- The game server reports connection/disconnection events to the lobby.

### Deployment Health Response

```json
{
  "deployment_id": "dep_123abc",
  "connected": true,
  "game_server_id": "gs_001",
  "checked_at": "2025-01-01T00:00:00.000Z"
}
```

---

## Key & Token Reference

| Key / Token | Who issues it | Who uses it | Purpose |
|-------------|-------------|-------------|---------|
| **Access Token** | Lobby (login) | You (developer) | Authenticate API calls to the lobby |
| **Deployment Management Key** | Lobby (deployment creation) | You (developer) | Manage your deployment (verify, health check, delete) |
| **Bot Invocation Token** | Lobby (deployment creation) | Platform → Your HTTP bot | The platform authenticates to your HTTP bot |
| **Deployment Key** | Same as deployment management key | Your WS bot → Platform | Your WebSocket bot authenticates to the platform gateway |

### Important Security Notes

1. **Deployment management keys and bot invocation tokens are only returned
   ONCE** — when you create the deployment.  Store them securely.

2. **HTTP bots** should validate the `Authorization: Bearer <token>` or
   `X-Api-Key: <token>` header on incoming requests.  The token is the
   `bot_invocation_token` returned during deployment registration.

3. **WebSocket bots** send their deployment key as the `Authorization: Bearer`
   header when connecting to the gateway.  The platform validates it.

4. Keys use the `gdk_` prefix convention (Guandan Developer Key).

---

## Quick-Start Checklist

1. [ ] **Implement** your bot logic (card evaluation, hand selection, etc.)
2. [ ] **Choose transport:** HTTP (server) or WebSocket (client)
3. [ ] **Implement** the three required session endpoints (HTTP) or WebSocket
   message handling
4. [ ] **Implement** `sPlayHandRequest` handling (the core gameplay request)
5. [ ] **Implement** `sTributeCardRequest` and `sReturnCardRequest` handling
6. [ ] **Handle** informational messages gracefully (no response required)
7. [ ] **Register** a Provider via `POST /api/bots/providers`
8. [ ] **Create** a Definition via `POST /api/bots/definitions`
9. [ ] **Register** a Deployment via `POST /api/bots/deployments`
10. [ ] **Save** the `deployment_management_key` and `bot_invocation_token`
11. [ ] **Verify** your deployment via `POST
    /api/bots/deployments/{id}/verify`
12. [ ] **Test** with `auto_test.py` using a mix of builtin and deployed bots
13. [ ] **Monitor** your deployment health
