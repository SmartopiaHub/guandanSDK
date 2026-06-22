import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';


void main() {
  group('Utility functions tests', () {
    test('countCards should return correct count', () {
      var cards = PokerCardList.fromString('AH* AS AC AH*');
      expect(countCards(cards, CardRank.A, suit: CardSuit.spades), 1);
      expect(countCards(cards, CardRank.A,), 2);
      expect(countCards(cards, CardRank.A, suit: CardSuit.hearts, excludeWildCard: false), 2);
      expect(countCards(cards, CardRank.A, excludeWildCard: false), 4);
    });

    test('cardsFromString should return correct list of PokerCard', () {
      String cardString = 'AH AS KH AH*';
      List<PokerCard> cards = cardsFromString(cardString);
      expect(cards.length, 4);
      expect(cards[0], PokerCard(CardRank.A, CardSuit.hearts, false));
      expect(cards[1], PokerCard(CardRank.A, CardSuit.spades, false));
      expect(cards[2], PokerCard(CardRank.K, CardSuit.hearts, false));
      expect(cards[3], PokerCard(CardRank.A, CardSuit.hearts, true));
    });

    test('cardsToString should return correct string representation', () {
      List<PokerCard> cards = [
        PokerCard(CardRank.A, CardSuit.hearts, false),
        PokerCard(CardRank.A, CardSuit.spades, false),
        PokerCard(CardRank.K, CardSuit.hearts, false),
        PokerCard(CardRank.A, CardSuit.hearts, true),
      ];
      String cardString = cardsToString(cards);
      expect(cardString, 'AH AS KH AH*');
    });

    test('findSeries should return correct SeriesResult', () {
      var cards = PokerCardList.fromString('AH 2H 3H 4D 5H');
      SeriesResult result = findSeries(cards, 1, 5, 0, 1);
      expect(result.isValid, true);
      expect(result.toHand(CardRank.two).type, HandType.straight);
      expect(result.series.length, 5);
    });

    test('findTubes should return correct list of Hands', () {
      var cards = PokerCardList.fromString('AH AS 3D 3H 2S 2D');
      List<Hand> tubes = findTubes(cards, CardRank.A);
      expect(tubes.length, 1);
      expect(tubes[0].type, HandType.tube);
    });

    test('separateWildCards should separate wild cards correctly', () {
      var cards = PokerCardList.fromString('AH* KS AH*');
      var separated = separateWildCards(cards);
      expect(separated[0].length, 2); // Wild cards
      expect(separated[1].length, 1); // Regular cards
    });

    test('checkSingle should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH');
      HandTypeCheckResult result = checkSingle(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);
    });

    test('checkPair should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH AS');
      HandTypeCheckResult result = checkPair(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);
    });

    test('checkPair should return correct HandTypeCheckResult when there are wild cards', () {
      var cards = PokerCardList.fromString('AH* AS');
      HandTypeCheckResult result = checkPair(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.rankValueOfLevelCard);
    });

    test('checkTriple should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH AS AD');
      HandTypeCheckResult result = checkTriple(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);
    });

    test('checkTriple should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH* AS AD');
      HandTypeCheckResult result = checkTriple(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.rankValueOfLevelCard);
    });

    test('checkPlate should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH* AS AD 2S 2D 2H');
      HandTypeCheckResult result = checkPlate(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.two.value);

      cards = PokerCardList.fromString('AH AS AD KH KD KS');
      result = checkPlate(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.K.value);
    });

    test('checkPlate should return correct HandTypeCheckResult where there are wild cards', () {
      var cards = PokerCardList.fromString('QH* AS AD 2H 2S 2H');
      HandTypeCheckResult result = checkPlate(cards);
      expect(result.valid, true);
      expect(result.power, 1);
    });

    test('countCards should return 0 for non-existing cards', () {
      var cards = PokerCardList.fromString('AH AS');
      expect(countCards(cards, CardRank.K, suit: CardSuit.hearts), 0);
      expect(countCards(cards, CardRank.K), 0);
    });

    test('cardsFromString should return empty list for empty string', () {
      String cardString = '';
      List<PokerCard> cards = cardsFromString(cardString);
      expect(cards.length, 0);
    });

    test('findSeries should return invalid result for non-series cards', () {
      var cards = PokerCardList.fromString('AH 3H 5H');
      SeriesResult result = findSeries(cards, 1, 3, 0, 1);
      expect(result.isValid, false);
    });

    test('findTubes should return empty list for non-tube cards', () {
      var cards = PokerCardList.fromString('AH KS QD');
      List<Hand> tubes = findTubes(cards, CardRank.A);
      expect(tubes.length, 0);
    });

    test('checkSingle should return invalid result for multiple cards', () {
      var cards = PokerCardList.fromString('AH KS');
      HandTypeCheckResult result = checkSingle(cards);
      expect(result.valid, false);
    });

    test('checkPair should return invalid result for non-pair cards', () {
      var cards = PokerCardList.fromString('AH KS');
      HandTypeCheckResult result = checkPair(cards);
      expect(result.valid, false);
    });

    test('checkTriple should return invalid result for non-triple cards', () {
      var cards = PokerCardList.fromString('AH QS QD');
      HandTypeCheckResult result = checkTriple(cards);
      expect(result.valid, false);
    });

    test('checkPlate should return invalid result for non-plate cards', () {
      var cards = PokerCardList.fromString('AH KS QD JC TH 9S');
      HandTypeCheckResult result = checkPlate(cards);
      expect(result.valid, false);
    });

    test('checkFullHouse should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH AS AD KH KS');
      HandTypeCheckResult result = checkFullHouse(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);
    });

    test('checkFullHouse should return correct HandTypeCheckResult with wild cards', () {
      var cards = PokerCardList.fromString('QH* AS AD KH KS');
      HandTypeCheckResult result = checkFullHouse(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);
    });

    test('checkFullHouse should return correct HandTypeCheckResult with jokers', () {
      var cards = PokerCardList.fromString('BJ BJ AS AD AH');
      HandTypeCheckResult result = checkFullHouse(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.A.value);

      cards = PokerCardList.fromString('BJ BJ BJ AD AH');
      result = checkFullHouse(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.blackJoker.value);
    });

    test('checkFullHouse should return invalid HandTypeCheckResult with jokers', () {
      var cards = PokerCardList.fromString('BJ BJ RJ AD QH');
      var result = checkFullHouse(cards);
      expect(result.valid, false);

      cards = PokerCardList.fromString('BJ BJ RJ RJ QH');
      result = checkFullHouse(cards);
      expect(result.valid, false);

      cards = PokerCardList.fromString('BJ BJ RJ RJ QH');
      result = checkFullHouse(cards);
      expect(result.valid, false);
      
    });

    test('checkFullHouse should return invalid result for non-full house cards', () {
      var cards = PokerCardList.fromString('AH AS KD KH QS');
      HandTypeCheckResult result = checkFullHouse(cards);
      expect(result.valid, false);
    });

    test('checkFullHouse should return invalid result for insufficient cards', () {   
      var cards = PokerCardList.fromString('AH AS KD');
      HandTypeCheckResult result = checkFullHouse(cards);
      expect(result.valid, false);
    });

    test('checkTube should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH AS KD KH QD QC');
      HandTypeCheckResult result = checkTube(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.Q.value);
    });

    test('checkTube should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH AS 2D 2C 3D 3C');
      HandTypeCheckResult result = checkTube(cards);
      expect(result.valid, true);
      expect(result.power, 1);
    });



    test('checkTube should return correct HandTypeCheckResult with wild cards', () {
      var cards = PokerCardList.fromString('AH* AS AD KC QD QC');
      HandTypeCheckResult result = checkTube(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.Q.value);

      cards = PokerCardList.fromString('AH* AH* JD KC QD QC');
      result = checkTube(cards);
      expect(result.valid, true);
      expect(result.power, CardRank.J.value);
    });

    test('checkTube should return correct HandTypeCheckResult with jokers', () {
      
      var cards = PokerCardList.fromString('BJ BJ AS AD KD KC');
      HandTypeCheckResult result = checkTube(cards);
      expect(result.valid, false);
    });

    test('checkStraight should return correct HandTypeCheckResult', () {
      var cards = PokerCardList.fromString('AH 2S 3D 4C 5H');
      HandTypeCheckResult result = checkStraight(cards);
      expect(result.valid, true);
      expect(result.power, 1);
    });

    test('checkStraight should return invalid result for non-straight cards', () {
      var cards = PokerCardList.fromString('AH 2S 3D 5C 6H');
      HandTypeCheckResult result = checkStraight(cards);
      expect(result.valid, false);
    });

    test('checkStraight should return correct HandTypeCheckResult with wild cards', () {
      var cards = PokerCardList.fromString('AH* 2S 3D 4C 5H');
      HandTypeCheckResult result = checkStraight(cards);
      expect(result.valid, true);
      expect(result.power, 2);
    });

    test('checkStraight should return invalid HandTypeCheckResult with jokers', () {
      var cards = PokerCardList.fromString('BJ 2S 3D 4C 5H');
      HandTypeCheckResult result = checkStraight(cards);
      expect(result.valid, false);
    });

    test('isStraightFlush should return true for valid straight flush', () {
      var cards = PokerCardList.fromString('AH 2H 3H 4H 5H');
      bool result = isStraightFlush(cards);
      expect(result, true);
    });

    test('isStraightFlush should return false for non-straight flush cards', () {
      var cards = PokerCardList.fromString('AH* 2H 3H 5C 6H');
      bool result = isStraightFlush(cards);
      expect(result, false);
    });

    test('isStraightFlush should return true with T J Q K A', () {
      var cards = PokerCardList.fromString('AH KH QH JH TH');
      bool result = isStraightFlush(cards);
      expect(result, true);
    });

    test('isStraightFlush should return invalid with jokers', () {
      var cards = PokerCardList.fromString('BJ 2H 3H 4H 5H');
      bool result = isStraightFlush(cards);
      expect(result, false);
    });

    test('isStraightFlush should return false for mixed suits', () {
      var cards = PokerCardList.fromString('AH 2S 3H 4H 5C');
      bool result = isStraightFlush(cards);
      expect(result, false);
    });

    test('checkBomb should return correct HandTypeCheckResult for four of a kind', () {
      var cards = PokerCardList.fromString('AH AS AD AC');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, 414);
    });

    test('checkBomb should return correct HandTypeCheckResult for five of a kind', () {
      var cards = PokerCardList.fromString('AH AS AD AC AH*');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, 514);
    });

    test('checkBomb should return correct HandTypeCheckResult for straight flush bomb', () {
      var cards = PokerCardList.fromString('AH 2H 3H 4H 5H');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, 601);
    });

    test('checkBomb should return correct HandTypeCheckResult for joker bomb', () {
      var cards = PokerCardList.fromString('BJ BJ RJ RJ');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, getJokerBombPower(2));
    });

    test('checkBomb should return invalid HandTypeCheckResult for insufficient cards', () {
      var cards = PokerCardList.fromString('AH AS AD');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, false);
    });

    test('checkBomb should return correct HandTypeCheckResult with wild cards', () {
      var cards = PokerCardList.fromString('AH* KS KD KC');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, 413);
    });

    test('checkBomb should return invalid HandTypeCheckResult for mixed ranks', () {
      var cards = PokerCardList.fromString('AH KS KD KC');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, false);
    });

    test('check bomb power', () {
      var cards = PokerCardList.fromString('AD AD AC AC AH AH AS AS QH* QH*');
      HandTypeCheckResult result = checkBomb(cards);
      expect(result.valid, true);
      expect(result.power, 1114);
      var bomb1 = Hand(cards.cards, HandType.bomb, power:result.power);

      cards = PokerCardList.fromString('BJ BJ RJ RJ');
      result = checkBomb(cards);
      expect(result.valid, true);
      var bomb2 = Hand(cards.cards, HandType.bomb, power:result.power);

      cards = PokerCardList.fromString('TD JD QD KD 2H*');
      result = checkBomb(cards);
      expect(result.valid, true);
      var bomb3 = Hand(cards.cards, HandType.bomb, power:result.power);

      cards = PokerCardList.fromString('AD AD AS AS AC');
      result = checkBomb(cards);
      expect(result.valid, true);
      var bomb4 = Hand(cards.cards, HandType.bomb, power:result.power);

      cards = PokerCardList.fromString('2D 2D 2S 2S 2C 2C');
      result = checkBomb(cards);
      expect(result.valid, true);
      var bomb5 = Hand(cards.cards, HandType.bomb, power:result.power);

      expect(bomb1 < bomb2, true);
      expect(bomb2 > bomb1, true);
      expect(bomb3 < bomb2, true);
      expect(bomb3 < bomb1, true);
      expect(bomb4 < bomb3, true);
      expect(bomb5 > bomb3, true);
    });

    test('canPlay should return false for empty handOnTable', () {
      var cardsToPlay = PokerCardList.fromString('AH');
      Hand handOnTable = Hand.emptyHand();
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for empty handOnTable with allowEmptyHand', () {
      var cardsToPlay = PokerCardList.empty();
      Hand handOnTable = Hand.emptyHand();
      expect(canPlay(cardsToPlay, handOnTable, allowEmptyHand: true), true);
    });

    test('canPlay should return false for empty handOnTable without allowEmptyHand', () {
      var cardsToPlay = PokerCardList.empty();
      Hand handOnTable = Hand.emptyHand();
      expect(canPlay(cardsToPlay, handOnTable, allowEmptyHand: false), false);
    });

    test('canPlay should return true for valid single card play', () {
      var cardsToPlay = PokerCardList.fromString('AH');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.spades, false)], HandType.single, power: CardRank.K.value);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return false for invalid single card play', () {
      var cardsToPlay = PokerCardList.fromString('QH');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.spades, false)], HandType.single, power: CardRank.K.value);
      expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('canPlay should return true for valid pair play', () {
      var cardsToPlay = PokerCardList.fromString('AH AS');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.K, CardSuit.spades, false)], HandType.pair, power: CardRank.K.value);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return false for 3S 3D on 2S* 2C*', () {
      var cardsToPlay = PokerCardList.fromString('3S 3D');
      Hand handOnTable = Hand(cardsFromString('2S* 2D*'), HandType.pair, power: 15);
      expect(canPlay(cardsToPlay, handOnTable), false);
      handOnTable = deduceHandType(PokerCardList.fromString('2S* 2D*'));
       expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('canPlay should return false for invalid pair play', () {
      var cardsToPlay = PokerCardList.fromString('QH QS');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.K, CardSuit.spades, false)], HandType.pair, power: CardRank.K.value);
      expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('canPlay should return true for valid bomb play', () {
      var cardsToPlay = PokerCardList.fromString('AH AS AD AC');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.K, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.diamonds, false), PokerCard(CardRank.K, CardSuit.clubs, false)], HandType.bomb, power: 413);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return false for invalid bomb play', () {
      var cardsToPlay = PokerCardList.fromString('QH QS QD QC');
      Hand handOnTable = Hand([PokerCard(CardRank.K, CardSuit.hearts, false), PokerCard(CardRank.K, CardSuit.spades, false), PokerCard(CardRank.K, CardSuit.diamonds, false), PokerCard(CardRank.K, CardSuit.clubs, false)], HandType.bomb);
      handOnTable = deduceHandType(handOnTable);
      expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('canPlay should return false for invalid plate play', () {
      var cardsToPlay = PokerCardList.fromString('AH AS AD 2H 2H 2D');
      Hand handOnTable = Hand(cardsFromString('QD QD QC KD KS KD'), HandType.plate, power: CardRank.K.value);
      expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('canPlay should return true for valid plate play', () {
      var cardsToPlay = PokerCardList.fromString('QD QD QC KD KS KD');
      Hand handOnTable = Hand(cardsFromString('TS TS TD JS JS JD'), HandType.plate);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for valid plate play', () {
      var cardsToPlay = PokerCardList.fromString('BJ BJ BJ RJ RJ RJ');
      Hand handOnTable = Hand(cardsFromString('TS TS TD JS JS JD'), HandType.plate);
      handOnTable = deduceHandType(handOnTable, deckCount: 3);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable, deckCount: 3), true);
    });

    test('canPlay should return true for valid plate play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD KD KS AH* AH*'); // can be treated as a plate
      Hand handOnTable = Hand(cardsFromString('TS TS TD JS JS JD'), HandType.plate);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for valid tube play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD KD KS AH* AH*'); // can be treated as a tube
      Hand handOnTable = Hand(cardsFromString('TS TS JD JS QS QD'), HandType.plate);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for valid bomb play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD QD AH*'); 
      Hand handOnTable = Hand(cardsFromString('TS TS JD JS QS QD'), HandType.plate);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for valid triple play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD QD'); 
      Hand handOnTable = Hand(cardsFromString('TS TS TD'), HandType.triple);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });


    test('canPlay should return true for valid fullhouse play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD QD 3H 3H'); 
      Hand handOnTable = Hand(cardsFromString('TS TS TD AD AD'), HandType.triple);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for valid fullhouse play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD 3D* 3H* 3D*'); 
      Hand handOnTable = Hand(cardsFromString('TS TS TD AD AD'), HandType.fullHouse);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), true);
    });

    test('canPlay should return true for invalid fullhouse play', () {
      var cardsToPlay = PokerCardList.fromString('QS QD 3D 3H 3D'); 
      Hand handOnTable = Hand(cardsFromString('TS* TS* TH* AD AD'), HandType.fullHouse);
      handOnTable = deduceHandType(handOnTable);
      expect(handOnTable.power > 0, true);
      expect(canPlay(cardsToPlay, handOnTable), false);
    });

    test('find plates', () {
      var cards = PokerCardList.fromString('QD QS KD KD KS AD AD AC 2H*');
      List<Hand> plates = findPlates(cards, CardRank.two, findAll: true);
      expect(plates.length, 2);
      expect(plates[0].power, 12);
      expect(plates[1].power, 13);
    });

    test('find triples', () {
      var cards = PokerCardList.fromString('QD QS KD KD KS AD AD AC 2H*');
      List<Hand> results = findTriples(cards, CardRank.two, findAll: true);
      expect(results.length, 3);
      expect(results[0].power, 12);
      expect(results[1].power, 13);
      expect(results[2].power, 14);
    });

    test('find pairs', () {
      var cards = PokerCardList.fromString('JS QD QS KD KD KS AD AD AC 2H* 2S* 2D*');
      List<Hand> results = findPairs(cards, CardRank.two, findAll: true);
      expect(results.length, 5);
      expect(results[0].power, 11);
      expect(results[1].power, 12);
      expect(results[2].power, 13);
      expect(results[3].power, 14);
      expect(results[4].power, 15);
    });

    test('find full houses', () {
      var cards = PokerCardList.fromString('JS JS QD QS KD KD KS 2H* RJ RJ BJ');
      List<Hand> results = findFullHouses(cards, CardRank.two, findAll: true);
      expect(results.length, 9);
      expect(results[0].power, 11);
      expect(results[1].power, 11);
      expect(results[2].power, 11);
    });

    test('minOfHand', () {
      var hands = [
        Hand(cardsFromString('8S'), HandType.single, power: 8),
        Hand(cardsFromString('BJ'), HandType.single, power: 16),
        Hand(cardsFromString('RJ'), HandType.single, power: 17),
        Hand(cardsFromString('JS JS'), HandType.pair, power: 11),
        Hand(cardsFromString('2S 2S'), HandType.pair, power: 2),
        Hand(cardsFromString('3S 3D'), HandType.pair, power: 3),
        Hand(cardsFromString('4S 4D'), HandType.pair, power: 4),
        Hand(cardsFromString('AS 2D 3S 4D 5H'), HandType.straight, power: 1),
        Hand(cardsFromString('2D 3S 4D 5H 6D'), HandType.straight, power: 2),
        Hand(cardsFromString('TS JD QH KD AS'), HandType.straight, power: 10),
        Hand(cardsFromString('7S 7D 7H'), HandType.triple, power: 7),
        Hand(cardsFromString('8S 8D 8H'), HandType.triple, power: 8),
        Hand(cardsFromString('TS TD TH'), HandType.triple, power: 10),
        Hand(cardsFromString('JS JS QD QS KD KD'), HandType.tube, power: 11),
        Hand(cardsFromString('QS QS QD KS KD KD'), HandType.plate, power: 12),
        Hand(cardsFromString('AS AS AD 2S 2D 2D'), HandType.plate, power: 1),
        Hand(cardsFromString('AS AS AD KS KD KD'), HandType.plate, power: 13),
      ];

      var minSingle = minOfHands(hands, handType: HandType.single);
      var maxSingle = maxOfHands(hands, handType: HandType.single);
      expect(minSingle!=null && minSingle.power == 8, true);
      expect(maxSingle!=null && maxSingle.cards[0].isRedJoker, true);
      minSingle = minOfHands(hands, handType: HandType.single, lowerBound: 8);
      maxSingle = maxOfHands(hands, handType: HandType.single, upperBound: 17);
      expect(minSingle!=null && minSingle.power == 16, true);
      expect(maxSingle!=null && maxSingle.power == 16, true);

      var minPair = minOfHands(hands, handType: HandType.pair);
      var maxPair = maxOfHands(hands, handType: HandType.pair);
      expect(minPair!=null && minPair.power == 2, true);
      expect(maxPair!=null && maxPair.power == 11, true);
      minPair = minOfHands(hands, handType: HandType.pair, lowerBound: 2);
      maxPair = maxOfHands(hands, handType: HandType.pair, upperBound: 11);
      expect(minPair!=null && minPair.power == 3, true);
      expect(maxPair!=null && maxPair.power == 4, true);

      var minStraight = minOfHands(hands, handType: HandType.straight);
      var maxStraight = maxOfHands(hands, handType: HandType.straight);
      expect(minStraight!=null && minStraight.power == 1, true);
      expect(maxStraight!=null && maxStraight.power == 10, true);
      minStraight = minOfHands(hands, handType: HandType.straight, lowerBound: 1);
      maxStraight = maxOfHands(hands, handType: HandType.straight, upperBound: 10);
      expect(minStraight!=null && minStraight.power == 2, true);
      expect(maxStraight!=null && maxStraight.power == 2, true);

      var minTriple = minOfHands(hands, handType: HandType.triple);
      var maxTriple = maxOfHands(hands, handType: HandType.triple);
      expect(minTriple!=null && minTriple.power == 7, true);
      expect(maxTriple!=null && maxTriple.power == 10, true);
      minTriple = minOfHands(hands, handType: HandType.triple, lowerBound: 7);
      maxTriple = maxOfHands(hands, handType: HandType.triple, upperBound: 10);
      expect(minTriple!=null && minTriple.power == 8, true);
      expect(maxTriple!=null && maxTriple.power == 8, true);

      var minFullHouse = minOfHands(hands, handType: HandType.fullHouse);
      var maxFullHouse = maxOfHands(hands, handType: HandType.fullHouse, triplesAndPairsToFullHouses: true);
      expect(minFullHouse!=null, false);
      expect(maxFullHouse!=null && maxFullHouse.power == 10, true);
      minFullHouse = minOfHands(hands, handType: HandType.fullHouse, lowerBound: 7, triplesAndPairsToFullHouses: true);
      maxFullHouse = maxOfHands(hands, handType: HandType.fullHouse, upperBound: 10, triplesAndPairsToFullHouses: true);
      expect(minFullHouse!=null && minFullHouse.power == 8, true);
      expect(maxFullHouse!=null && maxFullHouse.power == 8, true);
      maxFullHouse = maxOfHands(hands, handType: HandType.fullHouse, upperBound: 11, triplesAndPairsToFullHouses: true);
      expect(maxFullHouse!=null && maxFullHouse.power == 10, true);
      minFullHouse = minOfHands(hands, handType: HandType.fullHouse, lowerBound: 11);
      expect(minFullHouse==null, true);

      var minTube = minOfHands(hands, handType: HandType.tube, pairsToTubes: true);
      var maxTube = maxOfHands(hands, handType: HandType.tube, pairsToTubes: true);
      expect(minTube!=null && minTube.power == 2, true);
      expect(maxTube!=null && maxTube.power == 11, true);
      minTube = minOfHands(hands, handType: HandType.tube, lowerBound: 2);
      maxTube = maxOfHands(hands, handType: HandType.tube, upperBound: 11, pairsToTubes: true);
      expect(minTube!=null && minTube.power == 11, true);
      expect(maxTube!=null && maxTube.power == 2, true);
      minTube = minOfHands(hands, handType: HandType.tube, pairsToTubes: false);
      expect(minTube!=null && minTube.power==11, true);
      minTube = minOfHands(hands, handType: HandType.tube, pairsToTubes: false, upperBound: 10);
      expect(minTube==null, true);

      var minPlate = minOfHands(hands, handType: HandType.plate);
      var maxPlate = maxOfHands(hands, handType: HandType.plate, triplesToPlates: true);
      expect(minPlate!=null && minPlate.power == 1, true);
      expect(maxPlate!=null && maxPlate.power == 13, true);
      minPlate = minOfHands(hands, handType: HandType.plate, lowerBound: 1, triplesToPlates: true);
      maxPlate = maxOfHands(hands, handType: HandType.plate, upperBound: 13, triplesToPlates: true);
      expect(minPlate!=null && minPlate.power == 7, true);
      expect(maxPlate!=null && maxPlate.power == 12, true);
      minPlate = minOfHands(hands, handType: HandType.plate, lowerBound: 1, triplesToPlates: false);
      expect(minPlate!=null && minPlate.power == 12, true);
    });

  });
}