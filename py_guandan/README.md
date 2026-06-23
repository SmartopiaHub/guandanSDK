# py_guandan

Python port of the Dart `guandan_core` package.

The package provides Python-native models and rule helpers for:

- cards, card lists, hands, hand detection, and hand comparison
- rule search helpers such as `find_pairs`, `find_bombs`, and `can_player_beat`
- player, room configuration, room metadata, and message serialization models
- game state, round, phase, turn, tribute, and score/rank models
- bot-facing validation helpers

The implementation intentionally keeps wire-format strings and JSON keys compatible
with `guandan_core` while using Python dataclasses, enums, snake_case function names,
and in-file docstrings.

## Development

Run the Python package tests:

```sh
cd py_guandan
python -m pytest
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
