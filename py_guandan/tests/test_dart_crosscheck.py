"""Cross-check selected Python core behavior against Dart ``guandan_core``."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from guandan_core.cards import Hand, PokerCardList
from guandan_core.utility import can_play, deduce_hand_type


ROOT = Path(__file__).resolve().parents[2]


def _dart_eval(cases: list[dict]) -> list[dict]:
    """Run a tiny Dart program that evaluates cases with guandan_core."""
    source = """
import 'dart:convert';
import 'dart:io';
import 'package:guandan_core/guandan_core.dart';

void main() {
  final cases = jsonDecode(stdin.readLineSync()!) as List<dynamic>;
  final out = <Map<String, dynamic>>[];
  for (final c in cases) {
    final op = c['op'] as String;
    if (op == 'deduce') {
      final hand = deduceHandType(PokerCardList.fromString(c['cards'] as String));
      out.add({'type': hand.type.name, 'power': hand.power, 'text': hand.toString()});
    } else if (op == 'canPlay') {
      final hand = PokerCardList.fromString(c['cards'] as String);
      final table = Hand.fromString(c['table'] as String);
      out.add({'value': canPlay(hand, table, allowEmptyHand: c['allowEmpty'] as bool? ?? false)});
    }
  }
  print(jsonEncode(out));
}
"""
    with TemporaryDirectory() as tmp_dir:
        runner = Path(tmp_dir) / "dart_crosscheck_runner.dart"
        runner.write_text(source, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["dart", "--packages=.dart_tool/package_config.json", str(runner)],
                input=json.dumps(cases) + "\n",
                cwd=ROOT / "guandan_core",
                text=True,
                capture_output=True,
                check=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            pytest.skip(f"Dart cross-check unavailable: {exc}")
        return json.loads(proc.stdout)


@pytest.mark.parametrize(
    "cards",
    [
        "",
        "3H",
        "3H 3D",
        "3H 3D 3C",
        "3H 3D 3C 4S 4D",
        "AH 2S 3D 4C 5H",
        "AH AS 2D 2C 3D 3C",
        "AH AS AD 2H 2S 2D",
        "7H 7D 7C 7S",
        "TH JH QH KH AH",
        "BJ RJ BJ RJ",
    ],
)
def test_deduce_hand_type_matches_dart(cards: str) -> None:
    dart = _dart_eval([{"op": "deduce", "cards": cards}])[0]
    py = deduce_hand_type(PokerCardList.from_string(cards), forced=True)
    assert py.type.value == dart["type"]
    assert py.power == dart["power"]


@pytest.mark.parametrize(
    ("cards", "table", "allow_empty"),
    [
        ("4H", "single-3 : 3H", False),
        ("3D", "single-3 : 3H", False),
        ("", "single-3 : 3H", True),
        ("7H 7D 7C 7S", "straight-1 : AH 2S 3D 4C 5H", False),
        ("8H 8D", "pair-7 : 7H 7D", False),
        ("8H 8D", "bomb-407 : 7H 7D 7C 7S", False),
    ],
)
def test_can_play_matches_dart(cards: str, table: str, allow_empty: bool) -> None:
    dart = _dart_eval([{"op": "canPlay", "cards": cards, "table": table, "allowEmpty": allow_empty}])[0]
    py = can_play(PokerCardList.from_string(cards), Hand.parse(table), allow_empty_hand=allow_empty, forced=True)
    assert py is dart["value"]
