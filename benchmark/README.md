# Guandan Bot Benchmark Runner

Fully automated test-runner for the Guandan bot platform.  Creates a test
game with configurable bot line-ups, monitors the SSE event stream, and
reports per-round scores and win-rates.

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python** | 3.8+ with `pip` |
| **Python packages** | `requests`, `PyYAML` (`pip install requests pyyaml`) |
| **API key** | A developer automation key with scope `test_games:create` |

### Obtaining an API Key

You need a developer automation key to run the benchmark.  Get one through the
**Developer Center** at [zhiquguandan.com](https://www.zhiquguandan.com):

1. Sign in to [https://www.zhiquguandan.com](https://www.zhiquguandan.com)
   with your developer account.
2. Open the **Developer Center** (top-right menu → Developer Center).
3. Navigate to **API Keys** → **Create Automation Key**.
4. Fill in the form
5. Click **Create**.  Copy the generated key — it looks like
   `gdk_test_kid_<8-chars>.<32-chars>`.
6. Paste it into `config.yaml` as the `auto_test_api_key` value.

## Quick Start

```bash
# 1. Install dependencies
pip install requests pyyaml

# 2. Edit config.yaml with your lobby URL, API key, and bot preferences
cp config.yaml.example config.yaml   # if an example exists
vim config.yaml

# 3. Run 2 rounds (or whatever num_rounds is set to in config.yaml)
python3 benchmark.py

# Or override the round count and enable verbose output
python3 benchmark.py --num-rounds 10 --verbose

# Or use a different config file
python3 benchmark.py --config my-bot-matchup.yaml
```

## Configuration File (`config.yaml`)

All settings come from the YAML config file — there are **no built-in
defaults**.  The script exits with an error if any required field is missing.

### `auto_test_api_key` (required)

The developer automation API key used to authenticate with the lobby.

```yaml
auto_test_api_key: gdk_test_kid_6REIcePa.TPS7ezvWFxirqMMXCwNNwrjZIDgD7oNX
```

Format: `gdk_test_kid_<key-id>.<char-secret>`

### `lobby_url` (required)

Base URL of the lobby server. Do not change it unless you are running your own lobby server.

```yaml
lobby_url: https://www.zhiquguandan.com
```

### `num_rounds` (required)

Number of rounds the test game will run before automatically completing.
Can be overridden at runtime with `--num-rounds N`.

```yaml
num_rounds: 2
```

### `total_timeout` (required)

Maximum number of seconds to wait for the entire test game to finish.
If the game does not complete within this window the script exits with a
timeout warning.  Can be overridden with `--timeout SECONDS`.

```yaml
total_timeout: 6000
```

### `heartbeat_timeout` (required)

If no SSE event (including heartbeats) is received within this many
seconds, the script disconnects and reports a heartbeat-timeout error.

```yaml
heartbeat_timeout: 1200
```

### `bots` (required)

Per-seat bot assignments for all four seats.  Each key must be `seat_1`
through `seat_4`.

**Seat layout (standard 4-player Guandan):**

```
  seat 1 ↔ seat 3  →  Red team
  seat 2 ↔ seat 4  →  Blue team
```

#### Built-in bot

Uses a platform-provided bot.  Valid `bot_code` values are `basicBot` and
`strongBot`.

```yaml
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

#### Deployed (third-party) bot

Uses an externally registered bot deployment.  If `deployment_id` is
omitted the script auto-discovers a healthy deployment from the lobby.

```yaml
bots:
  seat_1:
    type: deployed
    deployment_id: DXXXXXXX  
  seat_2:
    type: builtin
    bot_code: basicBot
  seat_3:
    type: deployed
    deployment_id: DXXXXXXX
  seat_4:
    type: builtin
    bot_code: basicBot
```

> **Note:** When using deployed bots, make sure the referenced deployments are registered and healthy.

## CLI Reference

```
python3 benchmark.py [OPTIONS]
```

| Flag | Description |
|---|---|
| `--config PATH` | Path to YAML config file (default: `./config.yaml`) |
| `--num-rounds N` | Override `num_rounds` from the config file |
| `--timeout N` | Override `total_timeout` from the config file |
| `--verbose` | Print every agent message (default: only round start/end) |
| `--external-only` | Require deployed bots; exit if none are healthy |
| `--internal-only` | Force all seats to use built-in bots, ignoring any `deployed` entries |

## Output

### Non-verbose mode (default)

Prints one line per round start and one per round end, plus a round-completion
summary:

```
▶ Round R1  level=2  teamLR=(R:2 B:2)  start=seat1
◀ Round R1  first=S1(red) | second=S3(red) | fourth=S2(blue)
🏁 Round 1/10 completed (series 0/1)
   Score: Red 3 – Blue 0  (winner: red)
```

When all rounds finish a scoreboard is printed:

```
TEST COMPLETED
  Red  wins: 9/10  score: 26
  Blue wins: 1/10  score: 1
  Per-round results:
    Round  1: R3–B0    winner=red   [first: red | second: red | ...]
    ...
```

### Verbose mode (`--verbose`)

Prints every `agent.message` SSE event with full detail (card hands,
tribute exchanges, timeouts, etc.).

### Final report

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
    Blue         1/10       1

    Per-round:
    Round  Red    Blue   Winner    Rankings
    ------ ------ ------ --------  ------------------------------
    1      3      0      red       first: red | second: red | ...
    ...
========================================================================
```

## Scoring

The team whose player finishes **first** (banker / 头游) wins the round.
Points are awarded as follows:

| Winning team holds | Losing team holds | Winner | Loser |
|---|---|---|---|
| 1st + 2nd (double-down / 双下) | 3rd + 4th | +3 | −3 |
| 1st + 3rd | 2nd + 4th | +2 | −2 |
| 1st + 4th | 2nd + 3rd | +1 | −1 |

The win-rate is reported as `x/y` where `x` is rounds won and `y` is the
total number of requested rounds.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Config file not found` | `--config` points to a missing file, or `config.yaml` is not in the `benchmark/` directory |
| `auto_test_api_key is missing` | Add the key to `config.yaml` |
| `bots: missing seat(s): seat_2, seat_4` | Every seat (1–4) must have a bot entry |
| `Test game creation failed: HTTP 401` | API key is invalid or expired — re-create it |
| `Test game creation failed: HTTP 503` | No healthy game server is registered with the lobby |
| `SSE connection failed` | Game server is unreachable — check the `events_url` in the response |
| `heartbeat timeout` | Game server stopped sending events; increase `heartbeat_timeout` or check server health |
| `Game did not complete within Ns` | Increase `total_timeout` or reduce `num_rounds` |
