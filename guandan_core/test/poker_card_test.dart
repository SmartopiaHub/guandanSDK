import 'package:test/test.dart';
import 'package:guandan_core/guandan_core.dart';

void main() {
  group('PokerCard', () {
    test('should create a PokerCard instance', () {
      final card = PokerCard(CardRank('A'), CardSuit.spades, false);
      expect(card.rank, CardRank('A'));
      expect(card.suit, CardSuit.spades);
      expect(card.isLevelCard, false);
    });

    test('should identify a joker card', () {
      final redJoker = PokerCard.redJoker;
      final blackJoker = PokerCard.blackJoker;
      expect(redJoker.isJoker, true);
      expect(blackJoker.isJoker, true);
    });

    test('should identify a wild card', () {
      final wildCard = PokerCard(CardRank('2'), CardSuit.hearts, true);
      expect(wildCard.isWildCard, true);
    });


    test('should create a PokerCard from string', () {
      var card = PokerCard.from('AS');
      expect(card.rank, CardRank.A);
      expect(card.suit, CardSuit.spades);
      expect(card.isLevelCard, false);

      card = PokerCard.from('RJ');
      expect(card.rank, CardRank.redJoker);
      expect(card.suit, CardSuit.red);
      expect(card.isLevelCard, false);

      card = PokerCard.from('BJ');
      expect(card.rank, CardRank.blackJoker);
      expect(card.suit, CardSuit.black);
      expect(card.isLevelCard, false);
    });

    test('cards with the same rank and suit should be equal', () {
      final card1 = PokerCard(CardRank.A, CardSuit.spades, false);
      final card2 = PokerCard(CardRank.A, CardSuit.spades, false);
      expect(card1, card2);
    });

    test('cards with different rank should not be equal', () {
      final card1 = PokerCard(CardRank.A, CardSuit.spades, false);
      final card2 = PokerCard(CardRank.K, CardSuit.spades, false);
      expect(card1, isNot(card2));
    });

    test('cards comparison', () {
      final cardA = PokerCard(CardRank.A, CardSuit.spades, false);
      final cardK = PokerCard(CardRank.K, CardSuit.spades, false);
      final cardQ = PokerCard(CardRank.Q, CardSuit.spades, true);
      expect(cardA > cardK, true);
      expect(cardK < cardA, true);
      expect(cardA < cardQ, true);
      expect(cardQ < PokerCard.blackJoker, true);
      expect(cardQ < PokerCard.blackJoker, true);
      expect(PokerCard.redJoker > PokerCard.blackJoker, true);
      expect(PokerCard.blackJoker < PokerCard.redJoker, true);
      expect(PokerCard.redJoker < PokerCard.redJoker, false);
    });
  });

  test('should convert string to list of PokerCard', () {
    const cardString = 'AS KH RJ';
    final cards = cardsFromString(cardString);
    expect(cards.length, 3);
    expect(cards[0], PokerCard(CardRank.A, CardSuit.spades, false));
    expect(cards[1], PokerCard(CardRank.K, CardSuit.hearts, false));
    expect(cards[2], PokerCard.redJoker);
  });

  test('should convert list of PokerCard to string', () {
    final cards = [
    PokerCard(CardRank.A, CardSuit.spades, false),
    PokerCard(CardRank.K, CardSuit.hearts, false)
    ];
    final cardString = cardsToString(cards);
    expect(cardString, 'AS KH');
  });

  test('should find a valid series', () {
    final cards = PokerCardList.fromString('3S 4S 5S 6S 7S 8S 8S 9S 9H TS TD JS QS KS AH 2D RJ BJ');
    var result = findSeries(cards, 3, 5, 0, 1);
    expect(result.isValid, true);
    expect(result.series.length, 5);
    result = findSeries(cards, 1, 5, 0, 1);
    expect(result.isValid, true);
    expect(result.series.length, 5);
    var hand = result.toHand(CardRank.A);
    expect(hand.type, HandType.straight);
    result = findSeries(cards, 8, 3, 0, 2);
    expect(result.isValid, true);
    expect(result.series.length, 6);
  });

  test('should find a valid series with wild cards', () {
    final cards = PokerCardList.fromString('3S 4S 5S 6S AH 5S 6S');
    var result = findSeries(cards, 2, 5, 1, 1);
    expect(result.isValid, true);
    var hand = result.toHand(CardRank.A);
    expect(hand.type, HandType.bomb);
    expect(hand.cards.length, 5);
    expect(hand.power, 603);

    result = findSeries(cards, 4, 3, 1, 2);
    expect(result.isValid, true);
    hand = result.toHand(CardRank.A);
    expect(hand.type, HandType.tube);
    expect(hand.cards.length, 6);
    expect(hand.power, 4);
  });

  test('should not find an invalid series', () {
    final cards = PokerCardList.fromString('3S 4S 5S 6S 8S 8S 9S TS TS JS JS QS QS KS');
    var result = findSeries(cards, 3, 5, 0, 1);
    expect(result.isValid, false);
    result = findSeries(cards, 10, 5, 0, 1);
    expect(result.isValid, false);
    result = findSeries(cards, 8, 3, 0, 2);
    expect(result.isValid, false);
  });

  test('should return a hand', () {
    var handStr = 'unknown : 9S QC KH 3D 9C 6H 5C AD 3S 6S 3C KS JH BJ JH AC AH QS 2C* TC 4S 4C 5H 4S 2C* 7S QD';
    var hand = Hand.fromString(handStr);
    expect(hand.type, HandType.unknown);
  });

  test('should add two PokerCardLists together', () {
    final list1 = PokerCardList.fromString('AS KH');
    final list2 = PokerCardList.fromString('2D 3C');
    final combinedList = list1 + list2;
    expect(combinedList.length, 4);
    expect(combinedList.cards, containsAll([PokerCard(CardRank.A, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.two, CardSuit.diamonds, false), PokerCard(CardRank.three, CardSuit.clubs, false)]));
  });

  test('should subtract PokerCardLists', () {
    final list1 = PokerCardList.fromString('AS KH 2D 3C');
    final list2 = PokerCardList.fromString('2D 3C');
    final resultList = list1 - list2;
    expect(resultList.length, 2);
    expect(resultList.cards, containsAll([PokerCard(CardRank.A, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.hearts, false)]));
  });

  test('should check if PokerCardList contains a specific card', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    final card = PokerCard(CardRank.A, CardSuit.spades, false);
    expect(list.hasCard(card), true);
  });

  test('should check if PokerCardList contains all specific cards', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    final cardsToCheck = [PokerCard(CardRank.A, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.hearts, false)];
    expect(list.hasCards(cardsToCheck), true);
  });

  test('should shuffle PokerCardList', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    list.shuffle();
    expect(list.length, 4);
  });

  test('should sort PokerCardList by power rank', () {
    final list = PokerCardList.fromString('AS KH 2D* 3C');
    list.sortByPowerRank();
    expect(list.cards.first, PokerCard.from('3C'));
    expect(list.cards.last, PokerCard.from('2D*'));
  });

  test('should sort PokerCardList by natural rank', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    list.sortByNaturalRank();
    expect(list.cards.first, PokerCard(CardRank.two, CardSuit.diamonds, false));
    expect(list.cards.last, PokerCard(CardRank.A, CardSuit.spades, false));
  });

  test('should remove last card from PokerCardList', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    list.removeLast();
    expect(list.length, 3);
    expect(list.cards, containsAll([PokerCard(CardRank.A, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.two, CardSuit.diamonds, false)]));
  });

  test('should create a sublist from PokerCardList', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    final sublist = list.sublist(1, 3);
    expect(sublist.length, 2);
    expect(sublist.cards, containsAll([PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.two, CardSuit.diamonds, false)]));
  });

  test('should find index of a card in PokerCardList', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    final index = list.indexOf(PokerCard(CardRank.K, CardSuit.hearts, false));
    expect(index, 1);
  });

  test('should count cards in PokerCardList that satisfy a condition', () {
    final list = PokerCardList.fromString('AS KH 2D 3C');
    final count = list.count((card) => card.suit == CardSuit.hearts);
    expect(count, 1);
  });

  test('should remove multiple cards from PokerCardList', () {
    var list = PokerCardList.fromString('AS KH KH 3C');
    list.removeCards(PokerCardList.fromString('KH KH').cards);
    expect(list.length, 2);
    expect(list.cards, containsAll(PokerCardList.fromString('AS 3C').cards));

    list = PokerCardList.fromString('AS KH KH 3C');
    list.removeCards(PokerCardList.fromString('KH').cards);
    expect(list.length, 3);
    expect(list.cards, containsAll(PokerCardList.fromString('AS KH 3C').cards));
  });
}