# Guandan SDK

The public SDK for developing [Guandan](https://www.zhiquguandan.com) (掼蛋) bots
and integrating with the Guandan game platform.

Guandan is a 4-player Chinese card game played with two decks. The platform hosts
games between human players and AI bots, with an HTTP/WebSocket bot API that lets
you build and deploy your own bots.

## Packages

| Package | Language | Description |
|---|---|---|
| [guandan_core](guandan_core/) | Dart | Core game logic — card types, hand evaluation, rules, and scoring |
| [guandan_bot](guandan_bot/) | Dart | Bot framework — agent types, tactics engine, and bot SDK for building AI players |
| [guandan_hand_splitter](guandan_hand_splitter/) | Dart | Hand-analysis utilities — splits a 27-card hand into valid playable combinations |
| [py_guandan](py_guandan/) | Python | Python port of `guandan_core` for Python-based bot development |

## Benchmark

The [benchmark](benchmark/) directory contains a scripted test runner for
automated bot evaluation:

```bash
cd benchmark
pip install requests pyyaml
python3 benchmark.py --config config.yaml
```
It creates a test game via the Lobby REST API, monitors the SSE event stream,
and reports per-round scores and win-rates. See the
benchmark README for setup instructions and how to obtain
an API key.
