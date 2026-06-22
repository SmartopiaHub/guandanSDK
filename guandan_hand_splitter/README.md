# guandan_hand_splitter

Shared abstractions for splitting a Guandan hand into multiple candidate hands.

## Features

- Defines a reusable `HandSplitter` abstract class.
- Provides `HandSplitContext` helpers derived from `GameState` and `Round`.
- Keeps the package independent from concrete splitting strategies.

## Usage

```dart
class MySplitter extends HandSplitter {
  @override
  List<Hand> split(
    PokerCardList cards, {
    HandSplitContext? context,
  }) {
    return <Hand>[];
  }

  @override
  List<List<Hand>> splitAll(
    PokerCardList cards, {
    HandSplitContext? context,
  }) {
    return <List<Hand>>[];
  }
}
```

## Acknowledgement

This package is based on https://github.com/Bobgy/poker-guandan-strategy. The original code is licensed under the MIT License.