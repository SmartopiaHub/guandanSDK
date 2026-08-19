import 'package:guandan_core/guandan_core.dart';
import 'package:guandan_hand_splitter/guandan_hand_splitter.dart';
import 'package:test/test.dart';

void main() {
  group('MinHandsSplitter wildcard preservation', () {
    // Regression: the shared mutable wildConfig in calculateMinHandsImp could
    // retain increments from a sub-optimal branch, so a hand with a single
    // wildcard could report more wildcards than it actually contained.
    test('single-wildcard hand never reports more than one wildcard', () {
      final level = CardRank.two;
      final hand = PokerCardList.fromString(
          'JH 2H* 2S* KC 2C* 7S 3H 4S JH JD 3H QH 6D 9D 8C 5S QD 7C KS '
          'AC 3C AD JC 8D 5C 5D 9H');
      final wildcards = hand.cards.where((c) => c.isWildCard).length;
      expect(wildcards, 1);

      final result = MinHandsSplitter(level, 4).split(hand);
      final shown = result.$1
          .expand((h) => h.cards)
          .where((c) => c.isWildCard)
          .length;
      expect(shown, 1, reason: 'reported hands must not invent wildcards');
    });

    test('wildcard count is preserved for random hands with wildcards', () {
      final level = CardRank.two;
      var checked = 0;
      for (var trial = 0; trial < 2000 && checked < 200; trial++) {
        final deck = PokerCardList.createDeck(level, requiredPlayers: 4);
        deck.shuffle();
        final hand = PokerCardList.from(deck.cards.take(27));
        final wildcards = hand.cards.where((c) => c.isWildCard).length;
        if (wildcards == 0) continue;
        checked++;

        final result = MinHandsSplitter(level, 4).split(hand);
        final shown = result.$1
            .expand((h) => h.cards)
            .where((c) => c.isWildCard)
            .length;
        expect(shown, wildcards,
            reason: 'trial $trial hand: ${hand.cards.map((c) => c.toString()).join(' ')}');
      }
    });
  });
}
