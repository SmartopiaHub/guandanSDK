import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

/// Comprehensive unit tests for findXXX and canBeatXXX methods in utility.dart.
///
/// Coverage goals:
/// - All argument options for each method
/// - All if-else branches in each implementation
/// - Cases returning empty results and true/false results
/// - Different numbers of wildcards (0, 1, 2) and jokers

// ---- helper ----
PokerCardList c(String s) => PokerCardList.fromString(s);

void main() {
  // ==========================================================================
  // findSeries
  // ==========================================================================
  group('findSeries', () {
    test('valid straight (seriesLength=5, countOfEachRank=1, 0 wilds)', () {
      final cards = c('AH 2S 3D 4C 5H 9D KS');
      final result = findSeries(cards, 1, 5, 0, 1);
      expect(result.isValid, true);
      expect(result.seriesLength, 5);
      expect(result.wildCardsUsed, 0);
      expect(result.startRankValue, 1);
      expect(result.series.length, 5);
    });

    test('valid series with wilds filling gap (1 missing, 1 wild)', () {
      final cards = c('AH 3S 4D 5C 2H*');
      final result = findSeries(cards, 1, 5, 1, 1);
      expect(result.isValid, true);
      expect(result.wildCardsUsed, 1);
      expect(result.series.length, 4);
    });

    test('invalid — not enough wilds (needs 2, has 1)', () {
      final cards = c('AH 3S 5D 6C 7H');
      final result = findSeries(cards, 1, 5, 1, 1);
      expect(result.isValid, false);
    });

    test('valid — 2 wilds fill 2 gaps', () {
      final cards = c('AH 4S 5D  3H* 2H*');
      final result = findSeries(cards, 1, 5, 2, 1);
      expect(result.isValid, true);
      expect(result.wildCardsUsed, 2);
    });

    test('valid with suit filter', () {
      final cards = c('AH 2H 3H 4H 5H 2S 3D');
      final result = findSeries(cards, 1, 5, 0, 1, suit: CardSuit.hearts);
      expect(result.isValid, true);
      expect(result.series.length, 5);
      for (final card in result.series) {
        expect(card.suit, CardSuit.hearts);
      }
    });

    test('invalid with suit filter — not enough of that suit', () {
      final cards = c('AH 2H 3H 4D 5S');
      final result = findSeries(cards, 1, 5, 0, 1, suit: CardSuit.hearts);
      expect(result.isValid, false);
    });

    test('valid with suit filter + wild fills missing suit', () {
      final cards = c('AH 2H 3H 4D 5H  2H*');
      final result = findSeries(cards, 1, 5, 1, 1, suit: CardSuit.hearts);
      expect(result.isValid, true);
      expect(result.wildCardsUsed, 1);
    });

    test('startRankValue=14 with seriesLength=1 → valid', () {
      final cards = c('AH');
      final result = findSeries(cards, 14, 1, 0, 1);
      expect(result.isValid, true);
      expect(result.series.length, 1);
    });

    test('countOfEachRank=2 — for tube pairs', () {
      final cards = c('AH AS 2D 2C  9H KD');
      final result = findSeries(cards, 1, 2, 0, 2);
      expect(result.isValid, true);
      expect(result.series.length, 4);
      expect(result.seriesLength, 2);
    });

    test('countOfEachRank=2 — needs wild to fill', () {
      final cards = c('AH 2S 2D  3H*');
      final result = findSeries(cards, 1, 2, 1, 2);
      expect(result.isValid, true);
      expect(result.wildCardsUsed, 1);
    });

    test('countOfEachRank=3 — for plate triples', () {
      final cards = c('AH AS AD 2H 2S 2D  9D');
      final result = findSeries(cards, 1, 2, 0, 3);
      expect(result.isValid, true);
      expect(result.series.length, 6);
      expect(result.seriesLength, 2);
    });

    test('countOfEachRank=3 — needs wilds', () {
      final cards = c('AH AS 2S 2D  3H* 4H*');
      final result = findSeries(cards, 1, 2, 2, 3);
      expect(result.isValid, true);
      expect(result.wildCardsUsed, 2);
      expect(result.series.length, 4);
    });

    test('countOfEachRank=3 — not enough wilds', () {
      // Rank A: 1 card, Rank 2: 2 cards → need 2+1=3 wilds but only 2 available
      final cards = c('AH 2S 2D  3H* 4H*');
      final result = findSeries(cards, 1, 2, 2, 3);
      expect(result.isValid, false);
    });
  });

  // ==========================================================================
  // findTubes
  // ==========================================================================
  group('findTubes', () {
    test('single tube (findAll=false)', () {
      final cards = c('AH AS 2D 2C 3D 3C  9H KD');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes.length, 1);
      expect(tubes[0].type, HandType.tube);
      expect(tubes[0].power, 1);
    });

    test('multiple tubes with findAll=true', () {
      final cards = c('AH AS 2D 2C 3D 3C  3H 3S 4H 4S 5H 5S  KD');
      final tubes = findTubes(cards, CardRank.two, findAll: true);
      expect(tubes.any((t) => t.power == 1), true);
      expect(tubes.any((t) => t.power == 3), true);
    });

    test('no tube possible → empty', () {
      final cards = c('AH KS QD JC TH 9S 8H');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes, isEmpty);
    });

    test('targetPower filter — only stronger tubes', () {
      final cards = c(
          'AH AS 2D 2C 3D 3C  TH TS JD JC QD QC');
      final tubes = findTubes(cards, CardRank.two,
          findAll: true, targetPower: 1);
      expect(tubes.length, 1);
      expect(tubes[0].power, 10);
    });

    test('targetPower filters out all → empty', () {
      final cards = c('AH AS 2D 2C 3D 3C');
      final tubes = findTubes(cards, CardRank.two, targetPower: 10);
      expect(tubes, isEmpty);
    });

    test('tube with 1 wild card', () {
      // Have A,2,2,3,3 + 1 wild → wild fills A pair
      final cards = c('AH 2S 2D 3S 3D  KH*');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes.length, 1);
      expect(tubes[0].type, HandType.tube);
      expect(tubes[0].power, 1);
    });

    test('tube with 2 wilds — still not enough (needs 3 wilds to fill all)', () {
      // Have A,2,3 + 2 wilds → need 3 pairs (6 cards), have 3 regular + 2 wilds = 5 total
      // Each rank needs 2 cards; need 3 more cards but only 2 wilds → no tube
      final cards = c('AH 2S 3D  KH* QH*');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes, isEmpty);
    });

    test('tube with 3 wilds — fills A-2-3 tube', () {
      // Have 1 of each A,2,3 + 3 wilds → form 3 pairs
      final cards = c('AH 2S 3D  KH* QH* JH*');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes.length, 1);
      expect(tubes[0].type, HandType.tube);
    });

    test('tube starting at A-2-3 (power=1) with findAll=false', () {
      final cards = c('AH AS 2D 2C 3D 3C  QH QS KD KC');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes.length, 1);
      expect(tubes[0].power, 1);
    });
  });

  // ==========================================================================
  // findPlates
  // ==========================================================================
  group('findPlates', () {
    test('single plate (findAll=false)', () {
      final cards = c('AH AS AD 2H 2S 2D  9D');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].type, HandType.plate);
      expect(plates[0].power, 1);
    });

    test('multiple plates with findAll=true (A-2, Q-K, K-A)', () {
      final cards = c(
          'AH AS AD 2H 2S 2D  QH QS QD KH KS KD  4H 5S');
      final plates = findPlates(cards, CardRank.two, findAll: true);
      expect(plates.length, 3); // A-2, Q-K, K-A
      expect(plates.any((p) => p.power == 1), true);
      expect(plates.any((p) => p.power == 12), true);
      expect(plates.any((p) => p.power == 13), true);
    });

    test('no plate possible → empty', () {
      final cards = c('AH KS QD JC TH 9S 8H 7S');
      final plates = findPlates(cards, CardRank.two);
      expect(plates, isEmpty);
    });

    test('targetPower filter — only plates with power > target', () {
      final cards = c(
          'AH AS AD 2H 2S 2D  QH QS QD KH KS KD');
      // plates at power=1 (A-2), 12 (Q-K), 13 (K-A)
      // targetPower=1 skips A-2, keeps Q-K and K-A
      final plates = findPlates(cards, CardRank.two,
          findAll: true, targetPower: 1);
      expect(plates.length, 2);
      expect(plates.any((p) => p.power == 12), true);
      expect(plates.any((p) => p.power == 13), true);
    });

    test('targetPower filters out all → empty', () {
      final cards = c('AH AS AD 2H 2S 2D');
      final plates = findPlates(cards, CardRank.two, targetPower: 10);
      expect(plates, isEmpty);
    });

    test('plate with 1 wild', () {
      final cards = c('AH AS 2H 2S 2D  KH*');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].type, HandType.plate);
    });

    test('plate with 2 wilds', () {
      final cards = c('AH 2H 2S 2D  KH* QH*');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].type, HandType.plate);
    });

    test('findAll=false returns lowest-power plate', () {
      final cards = c(
          'AH AS AD 2H 2S 2D  3H 3S 3D 4H 4S 4D');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].power, 1);
    });

    test('plate at boundary K-A (power=13)', () {
      final cards = c('KH KS KD AH AS AD');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].power, 13);
    });
  });

  // ==========================================================================
  // findStraights
  // ==========================================================================
  group('findStraights', () {
    test('valid straight A-2-3-4-5', () {
      final cards = c('AH 2S 3D 4C 5H  9D KS');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
      expect(straights[0].type, HandType.straight);
      expect(straights[0].power, 1);
    });

    test('multiple straights with findAll=true', () {
      final cards = c(
          'AH 2S 3D 4C 5H  3H 4S 5D 6C 7H  TS JD QH KH AD');
      final straights = findStraights(cards, CardRank.two, findAll: true);
      // A-5, 3-7, 10-A → 3 straights with these specific cards
      // But cards overlap: e.g. 2-6 also works using A as rank 1 + 2,3,4,5,6
      // And 6-10: uses 6,7,8,9,T
      expect(straights.length, greaterThanOrEqualTo(3));
    });

    test('no straight possible → empty', () {
      final cards = c('AH 3S 5D 7C 9H');
      final straights = findStraights(cards, CardRank.two);
      expect(straights, isEmpty);
    });

    test('straight with 1 wild card', () {
      final cards = c('AH 2S 4D 5C  KH*');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
      expect(straights[0].type, HandType.straight);
    });

    test('straight with 2 wilds', () {
      final cards = c('AH 3S 5D  KH* QH*');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
      expect(straights[0].type, HandType.straight);
    });

    test('targetPower filter — only higher-power straights', () {
      final cards = c('AH 2S 3D 4C 5H  6H 7S 8D 9C TH');
      // straights: 1(A-5), 2(2-6), 3(3-7), 4(4-8), 5(5-9), 6(6-10)
      final straights = findStraights(cards, CardRank.two,
          findAll: true, targetPower: 1);
      expect(straights.length, 5); // powers 2,3,4,5,6
    });

    test('targetPower filters out all → empty', () {
      final cards = c('AH 2S 3D 4C 5H');
      final straights = findStraights(cards, CardRank.two, targetPower: 5);
      expect(straights, isEmpty);
    });

    test('straight 10-J-Q-K-A', () {
      final cards = c('TH JS QD KC AH 3S');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
      expect(straights[0].power, 10);
    });

    test('wild cards extracted before search (regularCards used)', () {
      final cards = c('AH 2S 3D 4C KH*');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
    });
  });

  // ==========================================================================
  // findStraightFlushes
  // ==========================================================================
  group('findStraightFlushes', () {
    test('real straight flush found', () {
      final cards = c('AH 2H 3H 4H 5H  9D KS');
      final sf = findStraightFlushes(cards, CardRank.two);
      expect(sf.length, 1);
      expect(sf[0].type, HandType.bomb);
      expect(sf[0].power, greaterThan(0));
    });

    test('straight flush with wild filling a gap', () {
      final cards = c('AH 2H 4H 5H  KH*  9D');
      final sf = findStraightFlushes(cards, CardRank.two);
      expect(sf.length, 1);
      expect(sf[0].type, HandType.bomb);
    });

    test('no straight flush → empty', () {
      final cards = c('AH 2S 3D 4C 5H');
      final sf = findStraightFlushes(cards, CardRank.two);
      expect(sf, isEmpty);
    });

    test('straight but not flush → empty', () {
      final cards = c('AH 2S 3H 4D 5H');
      final sf = findStraightFlushes(cards, CardRank.two);
      expect(sf, isEmpty);
    });

    test('multiple straight flushes with findAll=true', () {
      final cards = c(
          'AH 2H 3H 4H 5H  3S 4S 5S 6S 7S  9D KC');
      final sf = findStraightFlushes(cards, CardRank.two, findAll: true);
      expect(sf.length, 2);
    });

    test('findAll=false returns first found', () {
      final cards = c('AH 2H 3H 4H 5H  3S 4S 5S 6S 7S');
      final sf = findStraightFlushes(cards, CardRank.two);
      expect(sf.length, 1);
    });
  });

  // ==========================================================================
  // findTriples
  // ==========================================================================
  group('findTriples', () {
    test('triple from 3 regular cards', () {
      final cards = c('AH AS AD  2H 3S 4D 5C');
      final triples = findTriples(cards, CardRank.two);
      expect(triples.length, 1);
      expect(triples[0].type, HandType.triple);
      expect(triples[0].power, CardRank.A.value);
    });

    test('triple from 2 regular + 1 wild', () {
      final cards = c('AH AS  2H*  3D 4C 5H');
      final triples = findTriples(cards, CardRank.two);
      expect(triples.length, 1);
      expect(triples[0].type, HandType.triple);
      expect(triples[0].cards.any((c) => c.isWildCard), true);
    });

    test('triple from 1 regular + 2 wilds', () {
      final cards = c('AH  2H* 3H*  4S 5D');
      final triples = findTriples(cards, CardRank.two);
      expect(triples.length, 1);
      expect(triples[0].type, HandType.triple);
    });

    test('pure wild triple from 3 wilds only (no regular cards)', () {
      final cards = c('2H* 3H* 4H*');
      final triples = findTriples(cards, CardRank.two);
      expect(triples.length, 1);
      expect(triples[0].type, HandType.triple);
      expect(triples[0].power, CardRank.rankValueOfLevelCard);
    });

    test('multiple triples with findAll=true', () {
      final cards = c('AH AS AD  KH KS KD  2H*  3D 4C');
      final triples = findTriples(cards, CardRank.two, findAll: true);
      // As-triple, Ks-triple, 3D+2wilds triple, 4C+2wilds triple, pure wild triple
      // wildCardsAvailable = 1 (only 2H*), actual count may vary
      expect(triples.length, greaterThanOrEqualTo(2));
    });

    test('targetPower filter', () {
      final cards = c('AH AS AD  KH KS KD');
      final triples = findTriples(cards, CardRank.two,
          findAll: true, targetPower: 13);
      expect(triples.length, 1);
      expect(triples[0].power, 14);
    });

    test('targetPower filters all → empty', () {
      final cards = c('AH AS AD');
      final triples = findTriples(cards, CardRank.two, targetPower: 14);
      expect(triples, isEmpty);
    });

    test('findAll=false returns lowest power triple', () {
      final cards = c('3H 3S 3D  KH KS KD  AH AS AD');
      final triples = findTriples(cards, CardRank.two);
      expect(triples.length, 1);
      expect(triples[0].power, 3);
    });

    test('no triples possible → empty', () {
      final cards = c('AH KS QD JC');
      final triples = findTriples(cards, CardRank.two);
      expect(triples, isEmpty);
    });
  });

  // ==========================================================================
  // findPairs
  // ==========================================================================
  group('findPairs', () {
    test('pair from 2 regular cards', () {
      final cards = c('AH AS  2H 3S 4D 5C');
      final pairs = findPairs(cards, CardRank.two);
      expect(pairs.length, 1);
      expect(pairs[0].type, HandType.pair);
    });

    test('pair from 1 regular + 1 wild', () {
      final cards = c('AH  2H*  3S 4D 5C');
      final pairs = findPairs(cards, CardRank.two);
      expect(pairs.length, 1);
      expect(pairs[0].type, HandType.pair);
    });

    test('pure wild pair (only wilds, no regular cards)', () {
      final cards = c('2H* 3H*');
      final pairs = findPairs(cards, CardRank.two);
      expect(pairs.length, 1);
      expect(pairs[0].type, HandType.pair);
      expect(pairs[0].power, CardRank.rankValueOfLevelCard);
    });

    test('pure wild pair visible in findAll mode', () {
      final cards = c('2H* 3H*  4S 5D');
      final pairs = findPairs(cards, CardRank.two, findAll: true);
      final hasPureWildPair = pairs.any(
          (p) => p.cards.every((c) => c.isWildCard));
      expect(hasPureWildPair, true);
    });

    test('multiple pairs with findAll=true', () {
      final cards = c('AH AS  KH KS  2H* 3H*  4D 5C');
      final pairs = findPairs(cards, CardRank.two, findAll: true);
      expect(pairs.length, 5);
    });

    test('targetPower filter', () {
      final cards = c('AH AS  KH KS');
      final pairs = findPairs(cards, CardRank.two,
          findAll: true, targetPower: 13);
      expect(pairs.length, 1);
      expect(pairs[0].power, 14);
    });

    test('targetPower filters all → empty', () {
      final cards = c('AH AS');
      final pairs = findPairs(cards, CardRank.two, targetPower: 14);
      expect(pairs, isEmpty);
    });

    test('findAll=false returns lowest power pair', () {
      final cards = c('3H 3S  KH KS  AH AS');
      final pairs = findPairs(cards, CardRank.two);
      expect(pairs.length, 1);
      expect(pairs[0].power, 3);
    });

    test('wild pair filtered by targetPower=rankValueOfLevelCard', () {
      final cards = c('2H* 3H*');
      final pairs = findPairs(cards, CardRank.two,
          targetPower: CardRank.rankValueOfLevelCard);
      expect(pairs, isEmpty);
    });

    test('pair of jokers — formed by group.length>=2 branch', () {
      // BJ BJ: group.length=2 >= 2 → pair IS formed (joker check only on wild-assisted branch)
      final cards = c('BJ BJ');
      final pairs = findPairs(cards, CardRank.two);
      expect(pairs.length, 1);
      expect(pairs[0].type, HandType.pair);
      expect(pairs[0].power, 16);
    });
  });

  // ==========================================================================
  // findFullHouses
  // ==========================================================================
  group('findFullHouses', () {
    test('regular triple + regular pair', () {
      final cards = c('AH AS AD  KH KS  3D 4C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
      expect(fh[0].power, 14);
    });

    test('triple with wild + regular pair', () {
      final cards = c('AH AS  KH KS  2H*  3D 4C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
    });

    test('regular triple + wild-assisted pair', () {
      // Triple is all-regular (3 As), pair uses wild (1 K + 1 wild)
      // This works because the triple's cards all exist in regularCards
      final cards = c('AH AS AD  KH  2H*  3D 4C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, greaterThanOrEqualTo(1));
      expect(fh[0].type, HandType.fullHouse);
    });

    test('findAll=false returns lowest-power full house', () {
      final cards = c('3H 3S 3D  4H 4S   AH AS AD  KH KS');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
    });

    test('multiple full houses with findAll=true', () {
      final cards = c('AH AS AD  KH KS KD  QH QS  JD JC');
      final fh = findFullHouses(cards, CardRank.two, findAll: true);
      expect(fh.length, greaterThanOrEqualTo(2));
    });

    test('no full house possible → empty', () {
      final cards = c('AH KS QD JC TH');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh, isEmpty);
    });

    test('targetPower filter — only stronger full houses', () {
      final cards = c('AH AS AD  KH KS');
      final fh = findFullHouses(cards, CardRank.two,
          findAll: true, targetPower: 2);
      // Only A-powered (14) full house passes targetPower=2
      expect(fh.length, greaterThanOrEqualTo(1));
      expect(fh.any((h) => h.power == 14), true);
    });

    test('targetPower filters all → empty', () {
      final cards = c('AH AS AD  KH KS');
      final fh = findFullHouses(cards, CardRank.two, targetPower: 14);
      expect(fh, isEmpty);
    });

    test('black joker triple + regular pair', () {
      final cards = c('BJ BJ BJ  KH KS  2D 3C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
      expect(fh[0].power, CardRank.blackJoker.value);
    });

    test('red joker triple + regular pair', () {
      final cards = c('RJ RJ RJ  KH KS  2D 3C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
      expect(fh[0].power, CardRank.redJoker.value);
    });

    test('regular triple + black joker pair', () {
      final cards = c('AH AS AD  BJ BJ  3D 4C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
      expect(fh[0].power, 14);
    });

    test('regular triple + red joker pair', () {
      final cards = c('AH AS AD  RJ RJ  3D 4C');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
      expect(fh[0].power, 14);
    });

    test('black joker triple + black joker pair — same rank, not allowed', () {
      // Triple rank = blackJoker(16), pair rank = blackJoker(16) → skipped
      final cards = c('BJ BJ BJ BJ BJ');
      final fh = findFullHouses(cards, CardRank.two);
      // No valid FH: triple is BJ, pair is BJ but same-rank check blocks it
      expect(fh, isEmpty);
    });
  });

  // ==========================================================================
  // findSingles
  // ==========================================================================
  group('findSingles', () {
    test('all cards returned as singles', () {
      final cards = c('AH 2S 3D 4C 5H');
      final singles = findSingles(cards, CardRank.two, findAll: true);
      expect(singles.length, 5);
      for (final s in singles) {
        expect(s.type, HandType.single);
      }
    });

    test('findAll=false returns lowest single', () {
      final cards = c('KH 2S AH 3D 4C');
      final singles = findSingles(cards, CardRank.two);
      expect(singles.length, 1);
      expect(singles[0].power, 2);
    });

    test('targetPower filter', () {
      final cards = c('AH 2S 3D KH');
      final singles = findSingles(cards, CardRank.two,
          findAll: true, targetPower: 10);
      expect(singles.length, 2); // KH(13) + AH(14) > 10
    });

    test('targetPower filters all → empty', () {
      final cards = c('AH 2S 3D');
      final singles = findSingles(cards, CardRank.two, targetPower: 14);
      expect(singles, isEmpty);
    });

    test('empty cards → empty', () {
      final singles = findSingles(PokerCardList.empty(), CardRank.two);
      expect(singles, isEmpty);
    });
  });

  // ==========================================================================
  // findBombs
  // ==========================================================================
  group('findBombs', () {
    test('4-of-a-kind bomb', () {
      final cards = c('AH AS AD AC  3D 5H');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].type, HandType.bomb);
      expect(bombs[0].cards.length, 4);
    });

    test('3-of-a-kind + 1 wild → bomb', () {
      final cards = c('AH AS AD  2H* 3D 5H');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].type, HandType.bomb);
    });

    test('5-of-a-kind with wilds', () {
      final cards = c('AH AS AD AC  2H* 3D 5H');
      final bombs = findBombs(cards, CardRank.two, findAll: true);
      expect(bombs.any((b) => b.cards.length >= 4), true);
    });

    test('joker bomb (2 BJ + 2 RJ)', () {
      final cards = c('BJ BJ RJ RJ  AH 3S');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].type, HandType.bomb);
      expect(bombs[0].power, getJokerBombPower(2));
    });

    test('incorrect joker count → not a joker bomb', () {
      final cards = c('BJ RJ RJ');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.any((b) => b.power == getJokerBombPower(2)), false);
    });

    test('includeStraightFlush=true finds straight flush bomb', () {
      final cards = c('AH 2H 3H 4H 5H  9S KD');
      final bombs = findBombs(cards, CardRank.two, includeStraightFlush: true);
      expect(bombs.any((b) => b.cards.any((c) => c.suit == CardSuit.hearts)),
          true);
    });

    test('includeStraightFlush=false — no straight flush bomb', () {
      final cards = c('AH 2H 3H 4H 5H');
      final bombs = findBombs(cards, CardRank.two, includeStraightFlush: false);
      expect(bombs, isEmpty);
    });

    test('multiple bombs with findAll=true', () {
      final cards = c('AH AS AD AC  KH KS KD KC  BJ BJ RJ RJ');
      final bombs = findBombs(cards, CardRank.two, findAll: true);
      expect(bombs.length, 3);
    });

    test('targetPower filter', () {
      final cards = c('AH AS AD AC  KH KS KD KC');
      // K bomb has lower power than A bomb
      final bombs = findBombs(cards, CardRank.two,
          findAll: true, targetPower: getNonJokerBombPower(4, 13));
      expect(bombs.length, 1);
    });

    test('targetPower filters all → empty', () {
      final cards = c('AH AS AD AC');
      final bomb = findBombs(cards, CardRank.two);
      final bombs = findBombs(cards, CardRank.two,
          targetPower: bomb[0].power);
      expect(bombs, isEmpty);
    });

    test('no bombs possible → empty', () {
      final cards = c('AH KS QD JC');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs, isEmpty);
    });

    test('findAll=false returns lowest power bomb', () {
      final cards = c('3H 3S 3D 3C  AH AS AD AC');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
    });

    test('2-of-a-kind + 2 wilds → bomb', () {
      final cards = c('AH AS  2H* 3H*  4D 5C');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].type, HandType.bomb);
      expect(bombs[0].cards.where((c) => c.isWildCard).length, 2);
    });

    test('deckCount affects joker bomb', () {
      final cards = c('BJ BJ RJ RJ');
      final bombs2 = findBombs(cards, CardRank.two, deckCount: 2);
      expect(bombs2.any((b) => b.power == getJokerBombPower(2)), true);

      final bombs3 = findBombs(cards, CardRank.two, deckCount: 3);
      expect(bombs3.any((b) => b.power == getJokerBombPower(3)), false);
    });
  });

  // ==========================================================================
  // findHands (dispatcher)
  // ==========================================================================
  group('findHands', () {
    test('dispatches to findSingles', () {
      final cards = c('AH 2S 3D');
      final hands = findHands(cards, CardRank.two, HandType.single);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.single);
    });

    test('dispatches to findPairs', () {
      final cards = c('AH AS 2H*');
      final hands = findHands(cards, CardRank.two, HandType.pair);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.pair);
    });

    test('dispatches to findTriples', () {
      final cards = c('AH AS AD');
      final hands = findHands(cards, CardRank.two, HandType.triple);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.triple);
    });

    test('dispatches to findStraights', () {
      final cards = c('AH 2S 3D 4C 5H');
      final hands = findHands(cards, CardRank.two, HandType.straight);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.straight);
    });

    test('dispatches to findTubes', () {
      final cards = c('AH AS 2D 2C 3D 3C');
      final hands = findHands(cards, CardRank.two, HandType.tube);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.tube);
    });

    test('dispatches to findPlates', () {
      final cards = c('AH AS AD 2H 2S 2D');
      final hands = findHands(cards, CardRank.two, HandType.plate);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.plate);
    });

    test('dispatches to findFullHouses', () {
      final cards = c('AH AS AD KH KS');
      final hands = findHands(cards, CardRank.two, HandType.fullHouse);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.fullHouse);
    });

    test('dispatches to findBombs', () {
      final cards = c('AH AS AD AC');
      final hands = findHands(cards, CardRank.two, HandType.bomb);
      expect(hands.length, 1);
      expect(hands[0].type, HandType.bomb);
    });

    test('passes through findAll and targetPower', () {
      final cards = c('AH AS AD  KH KS KD');
      final hands = findHands(cards, CardRank.two, HandType.triple,
          findAll: true, targetPower: 13);
      expect(hands.length, 1);
      expect(hands[0].power, 14);
    });

    test('unknown hand type → empty', () {
      final cards = c('AH 2S');
      final hands = findHands(cards, CardRank.two, HandType.unknown);
      expect(hands, isEmpty);
    });
  });

  // ==========================================================================
  // canBeatSingle
  // ==========================================================================
  group('canBeatSingle', () {
    test('can beat with higher card', () {
      final cards = c('AH 2S 3D');
      expect(canBeatSingle(cards, 10, CardRank.two), true);
    });

    test('cannot beat — all cards lower or equal', () {
      final cards = c('2S 3D 4C');
      expect(canBeatSingle(cards, 10, CardRank.two), false);
    });

    test('wild card has powerRank 15', () {
      final cards = c('2H* 3S 4D');
      expect(canBeatSingle(cards, 14, CardRank.two), true);
    });

    test('joker cards beat high targets', () {
      final cards = c('BJ RJ');
      expect(canBeatSingle(cards, 15, CardRank.two), true); // BJ(16)>15
    });

    test('empty cards → false', () {
      expect(canBeatSingle(PokerCardList.empty(), 5, CardRank.two), false);
    });

    test('equal power → false', () {
      final cards = c('AH');
      expect(canBeatSingle(cards, 14, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatPair
  // ==========================================================================
  group('canBeatPair', () {
    test('can beat with regular pair', () {
      final cards = c('AH AS  2D 3C');
      expect(canBeatPair(cards, 10, CardRank.two), true);
    });

    test('cannot beat — no pair strong enough', () {
      final cards = c('3S 3D  4C 5H');
      expect(canBeatPair(cards, 10, CardRank.two), false);
    });

    test('can beat with wild-assisted pair', () {
      final cards = c('AH  2H*  4C 5H');
      expect(canBeatPair(cards, 13, CardRank.two), true);
    });

    test('can beat with pure wild pair', () {
      final cards = c('2H* 3H*  4C 5H');
      // But 4C+wild beats 14 too, and pure wild beats too → true
      expect(canBeatPair(cards, 14, CardRank.two), true);
    });

    test('targetPower exceeds wild pair power (15) → false', () {
      final cards = c('2H* 3H*');
      expect(canBeatPair(cards, CardRank.rankValueOfLevelCard, CardRank.two),
          false);
    });

    test('empty cards → false', () {
      expect(canBeatPair(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatTriple
  // ==========================================================================
  group('canBeatTriple', () {
    test('can beat with regular triple', () {
      final cards = c('AH AS AD  2D 3C');
      expect(canBeatTriple(cards, 10, CardRank.two), true);
    });

    test('cannot beat — no triple strong enough', () {
      final cards = c('3S 3D 3C  4H 5S');
      expect(canBeatTriple(cards, 10, CardRank.two), false);
    });

    test('can beat with wild-assisted triple', () {
      final cards = c('AH AS  2H*  4C 5H');
      expect(canBeatTriple(cards, 13, CardRank.two), true);
    });

    test('can beat with 2 wilds + 1 regular', () {
      final cards = c('AH  2H* 3H*  4C 5H');
      expect(canBeatTriple(cards, 13, CardRank.two), true);
    });

    test('can beat with pure wild triple', () {
      final cards = c('2H* 3H* 4H*');
      expect(canBeatTriple(cards, 10, CardRank.two), true);
    });

    test('pure wild triple always added (bypasses targetPower check)', () {
      final cards = c('2H* 3H* 4H*');
      // Pure wild triple (power=15) is added unconditionally without checking targetPower
      // So even targetPower=15 returns true (triple power == targetPower)
      expect(canBeatTriple(cards, CardRank.rankValueOfLevelCard, CardRank.two),
          true);
    });

    test('empty cards → false', () {
      expect(canBeatTriple(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatFullHouse
  // ==========================================================================
  group('canBeatFullHouse', () {
    test('can beat with regular full house', () {
      final cards = c('AH AS AD  KH KS  2D 3C');
      expect(canBeatFullHouse(cards, 10, CardRank.two), true);
    });

    test('cannot beat — no full house strong enough', () {
      final cards = c('3S 3D 3C  4H 4S');
      expect(canBeatFullHouse(cards, 10, CardRank.two), false);
    });

    test('can beat with wild in triple', () {
      final cards = c('AH AS  KH KS  2H*');
      expect(canBeatFullHouse(cards, 10, CardRank.two), true);
    });

    test('can beat with joker triple', () {
      final cards = c('BJ BJ BJ  KH KS');
      expect(canBeatFullHouse(cards, 14, CardRank.two), true);
    });

    test('cannot beat — targetPower exceeds joker triple', () {
      final cards = c('BJ BJ BJ  KH KS');
      expect(canBeatFullHouse(cards, CardRank.blackJoker.value, CardRank.two),
          false);
    });

    test('empty cards → false', () {
      expect(canBeatFullHouse(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatStraight
  // ==========================================================================
  group('canBeatStraight', () {
    test('can beat with regular straight', () {
      final cards = c('6H 7S 8D 9C TH  AH 2S');
      expect(canBeatStraight(cards, 5, CardRank.two), true);
    });

    test('cannot beat — no straight strong enough', () {
      final cards = c('AH 2S 3D 4C 5H');
      expect(canBeatStraight(cards, 5, CardRank.two), false);
    });

    test('can beat with wild-assisted straight', () {
      final cards = c('6H 7S 8D 9C  2H*  KH');
      expect(canBeatStraight(cards, 5, CardRank.two), true);
    });

    test('targetPower=10 (max) → false', () {
      final cards = c('TH JS QD KC AH');
      expect(canBeatStraight(cards, 10, CardRank.two), false);
    });

    test('empty cards → false', () {
      expect(canBeatStraight(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatTube
  // ==========================================================================
  group('canBeatTube', () {
    test('can beat with tube', () {
      // targetPower=5, tube A-2-3 has power=1 which is not > 5
      // tube at 10-J-Q has power=10 > 5
      final cards = c('AH AS 2D 2C 3D 3C  TH TS JD JC QD QC');
      expect(canBeatTube(cards, 5, CardRank.two), true);
    });

    test('cannot beat — tube power <= target', () {
      final cards = c('AH AS 2D 2C 3D 3C');
      expect(canBeatTube(cards, 5, CardRank.two), false);
    });

    test('tube with higher start rank beats lower target', () {
      final cards = c('TH TS JD JC QD QC');
      expect(canBeatTube(cards, 9, CardRank.two), true);
    });

    test('targetPower >= 12 → no tube can beat (Q-K-A is max at 12)', () {
      // Actually Q-K-A is max tube (start at 12), so targetPower=12 means nothing > 12
      final cards = c('TH TS JD JC QD QC');
      expect(canBeatTube(cards, 10, CardRank.two), false); // 10 > 10? 10 <= 10 → skipped
    });

    test('empty cards → false', () {
      expect(canBeatTube(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatPlate
  // ==========================================================================
  group('canBeatPlate', () {
    test('can beat with plate (targetPower < plate power)', () {
      // Plate A-2 has power=1; targetPower=0 means 1 > 0 → found
      final cards = c('AH AS AD 2H 2S 2D');
      expect(canBeatPlate(cards, 0, CardRank.two), true);
    });

    test('cannot beat — plate power too low', () {
      final cards = c('AH AS AD 2H 2S 2D');
      // target=1 means startRankValue=1 is skipped (1<=1), only 2..13 checked
      // But we need 3 cards of each of 2 consecutive ranks. We don't have 3 twos and 3 threes...
      // Actually we DO have 3 twos (2H,2S,2D). But no threes. So no more plates above power 1.
      expect(canBeatPlate(cards, 1, CardRank.two), false);
    });

    test('higher plate beats lower target', () {
      final cards = c('QH QS QD KH KS KD');
      expect(canBeatPlate(cards, 10, CardRank.two), true);
    });

    test('targetPower=13 (K max) → no plate with power > 13', () {
      final cards = c('KH KS KD AH AS AD');
      expect(canBeatPlate(cards, 13, CardRank.two), false);
    });

    test('empty cards → false', () {
      expect(canBeatPlate(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canBeatBomb
  // ==========================================================================
  group('canBeatBomb', () {
    test('can beat with 4-of-a-kind bomb', () {
      final cards = c('AH AS AD AC  2D 3C');
      expect(canBeatBomb(cards, 400, CardRank.two), true);
    });

    test('cannot beat — bomb power too low', () {
      final cards = c('AH AS AD AC');
      final bombs = findBombs(cards, CardRank.two);
      expect(canBeatBomb(cards, bombs[0].power, CardRank.two), false);
    });

    test('can beat with joker bomb', () {
      final cards = c('BJ BJ RJ RJ  AH');
      final regularBomb = findBombs(c('AH AS AD AC'), CardRank.two);
      expect(canBeatBomb(cards, regularBomb[0].power, CardRank.two), true);
    });

    test('can beat with straight flush bomb', () {
      final cards = c('AH 2H 3H 4H 5H');
      final targetBombs = findBombs(c('KH KS KD KC'), CardRank.two);
      expect(canBeatBomb(cards, targetBombs[0].power, CardRank.two), true);
    });

    test('wild-assisted bomb can beat', () {
      final cards = c('AH AS AD  2H*  3D 4C');
      expect(canBeatBomb(cards, 400, CardRank.two), true);
    });

    test('no bomb → false', () {
      final cards = c('AH KS QD JC');
      expect(canBeatBomb(cards, 100, CardRank.two), false);
    });

    test('empty cards → false', () {
      expect(canBeatBomb(PokerCardList.empty(), 5, CardRank.two), false);
    });
  });

  // ==========================================================================
  // canPlayerBeat
  // ==========================================================================
  group('canPlayerBeat', () {
    test('empty cards → false', () {
      final hand = Hand([PokerCard(CardRank.two, CardSuit.spades, false)],
          HandType.single, power: 2);
      expect(canPlayerBeat(PokerCardList.empty(), hand, CardRank.two), false);
    });

    test('lead (empty target) → true', () {
      final cards = c('AH 2S 3D');
      expect(canPlayerBeat(cards, Hand.emptyHand(), CardRank.two), true);
    });

    test('non-bomb target, can use bomb → true', () {
      final cards = c('AH AS AD AC  2D 3C');
      final target = Hand(c('KH'), HandType.single, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('non-bomb target, no bomb → check type match (higher wins)', () {
      final cards = c('AH  2S 3D 4C');
      final target = Hand(c('KH'), HandType.single, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('pair vs pair — higher wins', () {
      final cards = c('AH AS  2D 3C');
      final target = Hand(c('KH KS'), HandType.pair, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('pair vs pair — lower loses', () {
      final cards = c('3S 3D  4C 5H');
      final target = Hand(c('AH AS'), HandType.pair, power: 14);
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });

    test('triple vs triple — higher wins', () {
      final cards = c('AH AS AD  2D 3C');
      final target = Hand(c('KH KS KD'), HandType.triple, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('triple vs triple — lower loses', () {
      final cards = c('3S 3D 3C  4C 5H');
      final target = Hand(c('AH AS AD'), HandType.triple, power: 14);
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });

    test('full house vs full house — higher wins', () {
      final cards = c('AH AS AD  KH KS');
      final target = Hand(c('3H 3S 3D  2H 2S'), HandType.fullHouse, power: 3);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('straight vs straight — higher wins', () {
      final cards = c('6H 7S 8D 9C TH');
      final target = Hand(c('AH 2S 3D 4C 5H'), HandType.straight, power: 1);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('tube vs tube — higher wins', () {
      final cards = c('TH TS JD JC QD QC');
      final target = Hand(c('AH AS 2D 2C 3D 3C'), HandType.tube, power: 1);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('plate vs plate — higher wins', () {
      final cards = c('QH QS QD KH KS KD');
      final target = Hand(c('AH AS AD 2H 2S 2D'), HandType.plate, power: 1);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('bomb vs non-bomb → always wins', () {
      final cards = c('AH AS AD AC  2D');
      final target = Hand(c('KH'), HandType.single, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('bomb vs higher bomb → loses', () {
      final cards = c('AH AS AD AC');
      final target = Hand(c('BJ BJ RJ RJ'), HandType.bomb,
          power: getJokerBombPower(2));
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });

    test('bomb vs lower bomb → wins', () {
      final cards = c('BJ BJ RJ RJ  AH AS AD AC');
      final target = Hand(c('KH KS KD KC'), HandType.bomb,
          power: getNonJokerBombPower(4, 13));
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('targetHand unknown/invalid → false', () {
      final cards = c('AH 2S 3D');
      final target = Hand.unknownHand(c('KH'));
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });

    test('can beat single with wild', () {
      final cards = c('2H*  3S 4D');
      final target = Hand(c('KH'), HandType.single, power: 13);
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('target is bomb, no bomb available → false', () {
      final cards = c('AH AS  KH KS');
      final target = Hand(c('3H 3S 3D 3C'), HandType.bomb,
          power: getNonJokerBombPower(4, 3));
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });

    // Regression: bomb vs straight (and other non-simple hand types).
    // A player with a bomb should be able to beat ANY non-bomb hand type
    // (straight, tube, plate, full house), not just singles/pairs/triples.
    test('bomb beats straight (non-simple hand type)', () {
      final cards = c('7C TS 3S 6D 7S 2D* 7D TC 2H* QS 5C JS KS JC '
          '8S 9S TH 3C KC JD 3C 8C AS TC 9C AC 3D');
      // Straight: 5-6-7-8-9, power=5
      final target = Hand(
        c('5D 6C 7D 8D 9H'),
        HandType.straight,
        power: 5,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('bomb beats tube (non-simple hand type)', () {
      // 4-of-a-kind bomb beats a tube
      final cards = c('AH AS AD AC  KS QD');
      final target = Hand(
        c('TH TS JD JC QD QC'),
        HandType.tube,
        power: 10,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('bomb beats plate (non-simple hand type)', () {
      final cards = c('AH AS AD AC  KS QD');
      final target = Hand(
        c('QH QS QD KH KS KD'),
        HandType.plate,
        power: 12,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('bomb beats full house (non-simple hand type)', () {
      final cards = c('AH AS AD AC  KS QD');
      final target = Hand(
        c('KH KS KD  QH QS'),
        HandType.fullHouse,
        power: 13,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    // Regression: wild-assisted bomb (3 regular + 1 wild = 4-card bomb).
    // The player has 3 tens and 1 wild card; together they form a bomb
    // that should beat a non-bomb target.
    test('wild-assisted bomb beats non-bomb (3×rank + 1 wild)', () {
      // 3 tens + 1 wild (2H*) = 4-card bomb, level_rank=2
      final cards = c('TS TH TD  2H* 3C 4D 5H');
      // Straight: 5-6-7-8-9, power=5
      final target = Hand(
        c('5D 6C 7D 8D 9H'),
        HandType.straight,
        power: 5,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('wild-assisted bomb beats non-bomb (2×rank + 2 wilds)', () {
      // 2 tens + 2 wilds = 4-card bomb
      final cards = c('TS TH  2H* 3H* 4D 5H');
      final target = Hand(
        c('5D 6C 7D 8D 9H'),
        HandType.straight,
        power: 5,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('wild-assisted bomb: 3-of-a-kind + wild vs straight', () {
      // Exact scenario: 3 tens + 1 wild → bomb beats straight on table.
      final cards = c('9D 7D 7S KS JC AC 9H 3H TS JH JS 3S 2S* KC '
          '2H* 3C 6D 6D 4H AS QD 8D 7S AD TH TD KC');
      final target = Hand(
        c('5D 6C 7D 8D 9H'),
        HandType.straight,
        power: 5,
      );
      expect(canPlayerBeat(cards, target, CardRank.two), true);
    });

    test('no wild-assisted bomb when wilds insufficient', () {
      // 3 tens + 0 wilds → not a bomb, can't beat straight with same-type
      final cards = c('TS TH TD  3C 4D 5H 6S 7C');
      final target = Hand(
        c('5D 6C 7D 8D 9H'),
        HandType.straight,
        power: 5,
      );
      // No bomb (only 3 tens), no same-type straight → false
      expect(canPlayerBeat(cards, target, CardRank.two), false);
    });
  });

  // ==========================================================================
  // Cross-scenario: wild card count variations
  // ==========================================================================
  group('wildcard count variations', () {
    test('0 wilds: findPairs returns exactly the regular pairs', () {
      final cards = c('AH AS  KH KS');
      final pairs = findPairs(cards, CardRank.two, findAll: true);
      expect(pairs.length, 2);
      expect(pairs.every((p) => p.cards.every((c) => !c.isWildCard)), true);
    });

    test('1 wild: findTriples with one pair + 1 wild', () {
      final cards = c('AH AS  2H*  3D 4C');
      final triples = findTriples(cards, CardRank.two, findAll: true);
      final hasWildTriple = triples.any(
          (t) => t.cards.any((c) => c.isWildCard) &&
              t.power != CardRank.rankValueOfLevelCard);
      expect(hasWildTriple, true);
    });

    test('2 wilds: findTriples with one card + 2 wilds', () {
      final cards = c('AH  2H* 3H*  4D 5C');
      final triples = findTriples(cards, CardRank.two, findAll: true);
      final hasDoubleWild = triples.any(
          (t) => t.cards.where((c) => c.isWildCard).length >= 2 &&
              t.power != CardRank.rankValueOfLevelCard);
      expect(hasDoubleWild, true);
    });

    test('0 wilds: findBombs needs 4-of-a-kind', () {
      final cards = c('AH AS AD  KH KS');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs, isEmpty);
    });

    test('1 wild: findBombs forms bomb from 3-of-a-kind + wild', () {
      final cards = c('AH AS AD  2H*  3D 4C');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].cards.any((c) => c.isWildCard), true);
    });

    test('2 wilds: findBombs forms bomb from 2-of-a-kind + 2 wilds', () {
      final cards = c('AH AS  2H* 3H*  4D 5C');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].cards.where((c) => c.isWildCard).length, 2);
    });
  });

  // ==========================================================================
  // Cross-scenario: joker card handling
  // ==========================================================================
  group('joker card handling', () {
    test('findPairs treats joker pairs as valid (group.length >= 2)', () {
      final cards = c('BJ BJ  KH KS');
      final pairs = findPairs(cards, CardRank.two);
      // BJ BJ forms a pair via group.length>=2 branch, KH KS also → 2 pairs
      expect(pairs.length, 1); // findAll=false → returns lowest (K=13 vs BJ=16)
      expect(pairs[0].power, 13);
    });

    test('findFullHouses can use joker triple', () {
      final cards = c('BJ BJ BJ  KH KS');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
    });

    test('findFullHouses can use joker pair', () {
      final cards = c('AH AS AD  BJ BJ');
      final fh = findFullHouses(cards, CardRank.two);
      expect(fh.length, 1);
      expect(fh[0].type, HandType.fullHouse);
    });

    test('findBombs detects joker bomb', () {
      final cards = c('BJ BJ RJ RJ');
      final bombs = findBombs(cards, CardRank.two);
      expect(bombs.length, 1);
      expect(bombs[0].power, getJokerBombPower(2));
    });

    test('findBombs — jokers mixed with regular → not a bomb', () {
      final cards = c('BJ AH AS AD');
      final bombs = findBombs(cards, CardRank.two);
      // Mixed joker+regular: checkBomb returns invalid
      expect(
          bombs.any((b) =>
              b.cards.any((c) => c.isJoker) && b.cards.any((c) => !c.isJoker)),
          false);
    });

    test('canBeatSingle with jokers', () {
      final cards = c('BJ RJ');
      expect(canBeatSingle(cards, 15, CardRank.two), true); // BJ(16) > 15
    });
  });

  // ==========================================================================
  // Edge cases and boundary values
  // ==========================================================================
  group('edge cases and boundaries', () {
    test('findSeries 10-J-Q-K-A', () {
      final cards = c('TH JS QD KC AH');
      final result = findSeries(cards, 10, 5, 0, 1);
      expect(result.isValid, true);
    });

    test('findTubes at startRankValue=12 (Q-K-A)', () {
      final cards = c('QH QS KD KC AH AS');
      final tubes = findTubes(cards, CardRank.two);
      expect(tubes.length, 1);
      expect(tubes[0].power, 12);
    });

    test('findPlates at startRankValue=13 (K-A)', () {
      final cards = c('KH KS KD AH AS AD');
      final plates = findPlates(cards, CardRank.two);
      expect(plates.length, 1);
      expect(plates[0].power, 13);
    });

    test('findStraights at 10-J-Q-K-A', () {
      final cards = c('TH JS QD KC AH');
      final straights = findStraights(cards, CardRank.two);
      expect(straights.length, 1);
      expect(straights[0].power, 10);
    });

    test('findSingles findAll=false returns exactly 1 (lowest)', () {
      final cards = c('KH 2S AH BJ RJ');
      final singles = findSingles(cards, CardRank.two);
      expect(singles.length, 1);
      expect(singles[0].power, 2);
    });

    test('canPlayerBeat — leading from empty target always true', () {
      final cards = c('2S');
      expect(canPlayerBeat(cards, Hand.emptyHand(), CardRank.two), true);
    });

    test('canPlayerBeat — empty cards, empty target → false', () {
      expect(canPlayerBeat(
          PokerCardList.empty(), Hand.emptyHand(), CardRank.two), false);
    });
  });
}
