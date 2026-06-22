import 'dart:math';
import 'card_and_hand.dart';


/// Count the number of cards with the specified [rank] in a list of poker cards.
/// If [excludeWildCard] is true, then wild cards are not counted.
/// If [suit] is null, then count cards of all suits.
/// If [lowerBound] and [upperBound] are not null, it returns the number of cards with power in the range of [lowerBound] and [upperBound]. Both bounds are inclusive.
int countCards(Iterable<PokerCard> cards, CardRank rank, {CardSuit? suit, bool excludeWildCard = true, int? lowerBound, int? upperBound}) {
  return cards.where((card) => card.rank == rank && 
    (suit == null || card.suit == suit) && 
    (!excludeWildCard || !card.isWildCard) && 
    (lowerBound == null || card.powerRank >= lowerBound) && 
    (upperBound == null || card.powerRank <= upperBound)).length;
}

/// Returns the number of hands of the given hand type in the list of hands.
/// If lowerBound and upperBound are not null, it returns the number of hands with power in the range of [lowerBound] and [upperBound]. Both bounds are inclusive.
int countHands(List<Hand> hands, HandType handType, {int? lowerBound, int? upperBound}){
  return hands.where((h) => h.type == handType && (lowerBound == null || h.power >= lowerBound) && (upperBound == null || h.power <= upperBound)).length;
}

/// Construct a list of poker cards from a string of card representations.
/// See [PokerCard.from] for the format of the card representation.
/// Cards are separated by spaces in[stringOfCards].
List<PokerCard> cardsFromString(String stringOfCards) {
  List<PokerCard> cards = [];
  List<String> cardStrings = stringOfCards.split(' ');

  for (String card in cardStrings) {
    if (card.isEmpty) {
      continue;
    }
    cards.add(PokerCard.from(card));
  }
  return cards;
}

/// Construct a string of card representations from a list of poker cards.
String cardsToString(List<PokerCard> cards) {
  return cards.map((card) => card.toString()).join(' ');
}


/// A class representing the result in [findSeries].
class SeriesResult {

  /// A boolean indicating whether the series is valid/found.
  final bool isValid;

  /// The number of wild cards used in the series. Only meaningful when [isValid] is true.
  final int wildCardsUsed;

  /// The list of cards in the series. Only meaningful when [isValid] is true.
  final PokerCardList series;

  /// The length of the series. Only meaningful when [isValid] is true.
  final int seriesLength;

  /// The starting rank value of the series. Only meaningful when [isValid] is true.
  final int startRankValue; // 1-14, both 1 and 14 represent A

  /// Constructs a [SeriesResult] object.
  SeriesResult({
    required this.isValid,
    required this.wildCardsUsed,
    required this.seriesLength,
    required this.series,
    required this.startRankValue
  });

  /// Converts the result to a [Hand] object. If [isValid] is false, an invalid hand is returned.
  Hand toHand(CardRank levelRank){
    if (!isValid) {
      return Hand.invalidHand(series.cards);
    }

    var cards = PokerCardList.from(series);

    if (wildCardsUsed > 0) {
      for (int i = 0; i < wildCardsUsed; i++) {
        cards.add(PokerCard.wildCard(levelRank));
      }
    }

    HandType type = HandType.unknown;
    int power = -1;
    if (seriesLength == 5){
      type = HandType.straight;
      power = startRankValue;
      var checkResult = checkStraightFlush(cards);
      if (checkResult.valid) {
        //type = HandType.straightFlush;
        type = HandType.bomb;
        power = checkResult.power;
      }
    } 
    if (seriesLength == 3){
      type = HandType.tube;
      power = startRankValue;
    }
    if (seriesLength == 2){
      type = HandType.plate;
      power = startRankValue;
    } 
    if (seriesLength == 1 && series.length == 3){
      type = HandType.triple;
      power = startRankValue;
    } 
    if (seriesLength == 1 && series.length == 2){
      type = HandType.pair;
      power = startRankValue;
    }
    if (seriesLength == 1 && series.length == 1){
      type = HandType.single;
      power = series[0].powerRank;
    }

    if (type == HandType.unknown) {
      // check bombs
      if (series.length >= 4) {
        var checkResult = checkBomb(cards);
        if (checkResult.valid) {
          type = HandType.bomb;
          power = checkResult.power;
        }
      }
    }

    return Hand(cards.cards, type, power: power);
  }
}



/// Find a series of cards with the specified `seriesLength` and `countOfEachRank`, with starting rank value `startRankValue`.
/// - Arguments:
///   - [cards]: The list of poker cards to search for the series. If wild cards are present in the input, they are taken care of automatically, so that [wildCardsAvailable] is always respected.
///   - [startRankValue]: The starting rank value of the series.
///   - [seriesLength]: The length of the series.
///   - [wildCardsAvailable]: The number of wild cards available.
///   - [countOfEachRank]: The number of cards for each rank.
///   - [suit]: The suit of the cards. If not null, only cards of the specified suit are considered.
/// - Returns:
///    A [SeriesResult] object representing the result.
SeriesResult findSeries(Iterable<PokerCard> cards, int startRankValue, int seriesLength, int wildCardsAvailable, int countOfEachRank, {CardSuit? suit}) {
  
  assert(startRankValue > 0 && startRankValue + seriesLength - 1 <= 14);
  
  PokerCardList series = PokerCardList.empty();
  int cardsLacking = 0;

  for (int k = startRankValue; k < startRankValue + seriesLength; k++) {
    CardRank r = CardRank.fromValue(k);
    cardsLacking += max(countOfEachRank - countCards(cards, r, suit: suit, excludeWildCard: true), 0);
  }

  if (cardsLacking > wildCardsAvailable) {
    return SeriesResult(isValid: false, wildCardsUsed: 0, seriesLength: seriesLength, series:PokerCardList.empty(), startRankValue: 0);
  }

  int wildCardsUsed = cardsLacking;
  for (int k = startRankValue; k < startRankValue + seriesLength; k++) {
    CardRank r = CardRank.fromValue(k);
    int j = 0;
    for (PokerCard c in cards) {
      // automatically exclude wild cards here
      if (c.rank == r && (suit == null || c.suit == suit) && !c.isWildCard) {
        if (j < countOfEachRank) {
          series.add(c);
          j++;
        }
      }
    }
  }

  return SeriesResult(isValid: true, wildCardsUsed: wildCardsUsed, seriesLength: seriesLength, series: series, startRankValue: startRankValue);
}
 

/// This function finds all possible tubes (or the first one if `findAll` is false) in a list of poker cards.
/// 
/// A tube is a series of three consecutive cards of the same rank.
/// 
/// - Parameters:
///   - [cards]: The list of poker cards to search for tubes.
///   - [levelRank]: The rank used to create wild cards if needed.
///   - [findAll]: A boolean indicating whether to find all possible tubes or just the first one. Default is false.
///   - [targetPower]: If provided, only tubes with power rank higher than [targetPower] are considered.
/// - Returns: A list of hands representing the found tubes.
List<Hand> findTubes(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  List<Hand> tubes = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  for (int startRankValue = 1; startRankValue <= 12; startRankValue++) {
    if (startRankValue <= resolvedTargetPower) continue; // ensure the tube is stronger than the target hand
    SeriesResult result = findSeries(cards, startRankValue, 3, wildCardsAvailable, 2);
    if (result.isValid) {
      tubes.add(result.toHand(levelRank));
    }
    if (!findAll && tubes.isNotEmpty) {
      return [tubes.first];
    }
  }
  if (!findAll && tubes.isNotEmpty) {
    tubes.sort((a, b) => a.power.compareTo(b.power));
    return [tubes.first];
  }
  return tubes;
}

/// This function finds all possible plates (or the first one if `findAll` is false) in a list of poker cards.
/// If [findAll] is false, only the first plate (the one with the lowest power rank) is returned.
/// If [targetPower] is provided, only plates with power rank higher than [targetPower] are considered.
List<Hand> findPlates(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  List<Hand> plates = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  for (int startRankValue = 1; startRankValue <= 13; startRankValue++) {
    if (startRankValue <= resolvedTargetPower) continue; // ensure the plate is stronger than the target hand
    SeriesResult result = findSeries(cards, startRankValue, 2, wildCardsAvailable, 3);
    if (result.isValid) {
      plates.add(result.toHand(levelRank));
    }
    if (!findAll && plates.isNotEmpty) {
      return [plates.first];
    }
  }
  if (!findAll && plates.isNotEmpty) {
    plates.sort((a, b) => a.power.compareTo(b.power));
    return [plates.first];
  }
  return plates;
}

/// This function finds all possible straights (or the first one if `findAll` is false) in a list of poker cards.
/// If [targetPower] is provided, only straights with power rank higher than [targetPower] are considered.
/// If [findAll] is false, only the straight with the lowest power rank that meets the criteria is returned.
List<Hand> findStraights(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  List<Hand> straights = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  for (int startRankValue = 1; startRankValue <= 10; startRankValue++) {
    if (startRankValue <= resolvedTargetPower) continue; // ensure the straight is stronger than the target hand
    SeriesResult result = findSeries(regularCards, startRankValue, 5, wildCardsAvailable, 1);
    if (result.isValid) {
      straights.add(result.toHand(levelRank));
    }
    if (!findAll && straights.isNotEmpty) {
      return [straights.first];
    }
  }
  if (!findAll && straights.isNotEmpty) {
    straights.sort((a, b) => a.power.compareTo(b.power));
    return [straights.first];
  }
  return straights;
}


/// Find straight flushes from a list of poker cards.
/// If [findAll] is false, only the straight flush with the lowest power rank is returned.
List<Hand> findStraightFlushes(PokerCardList cards, CardRank levelRank, {bool findAll = false}) {
  List<Hand> straightFlushes = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  for (int startRankValue = 1; startRankValue <= 10; startRankValue++) {
    for (var suit in CardSuit.nonJokerSuits) {
      SeriesResult result = findSeries(cards, startRankValue, 5, wildCardsAvailable, 1, suit: suit);
      if (result.isValid) {
        var hand = result.toHand(levelRank);
        var checkResult = checkStraightFlush(hand);
        if (checkResult.valid) {
          straightFlushes.add(Hand(hand.cards, HandType.bomb, power: checkResult.power));
        }
      }
      if (!findAll && straightFlushes.isNotEmpty) {
        break;
      }
    }
  }
  return straightFlushes;
}



/// Finds all possible triples (or the first one if `findAll` is false) in a list of poker cards.
/// If [targetPower] is provided, only triples with power rank higher than [targetPower] are considered.
/// If [findAll] is false, only the triple with the lowest power rank that meets the criteria is returned.
List<Hand> findTriples(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  List<Hand> triples = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));
  for (var group in grouped) {
    if (group[0].powerRank <= resolvedTargetPower) continue; // ensure the triple is stronger than the target hand
    if (group.length >= 3) {
      triples.add(Hand(group.cards.sublist(0,3), HandType.triple, power: group[0].powerRank));
    }
    else if (group.length == 2 && !group[0].isJoker && wildCardsAvailable >= 1) {
      triples.add(Hand(group.cards + [PokerCard.wildCard(levelRank)], HandType.triple, power: group[0].powerRank));
    }
    else if (group.length == 1 && !group[0].isJoker && wildCardsAvailable >= 2) {
      triples.add(Hand(group.cards + [PokerCard.wildCard(levelRank), PokerCard.wildCard(levelRank)], HandType.triple, power: group[0].powerRank));
    }
    if (!findAll && triples.isNotEmpty) {
      return [triples.first];
    }
  }
  if (wildCardsAvailable >= 3) {
    triples.add(Hand([PokerCard.wildCard(levelRank), PokerCard.wildCard(levelRank), PokerCard.wildCard(levelRank)], HandType.triple, power: CardRank.rankValueOfLevelCard));
  }
  if (!findAll && triples.isNotEmpty) {
    triples.sort((a, b) => a.power.compareTo(b.power));
    return [triples.first];
  }
  return triples;
}

/// This function finds all possible pairs (or the first one if `findAll` is false) in a list of poker cards.
/// If [findAll] is false, only the first pair (the one with the lowest power rank) is returned.
/// If [targetPower] is provided, only pairs with power rank higher than [targetPower] are considered.
List<Hand> findPairs(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  List<Hand> pairs = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));
  final resolvedTargetPower = targetPower ?? -1;
  for (var group in grouped) {
    if (group[0].powerRank <= resolvedTargetPower) continue; // ensure the pair is stronger than the target hand
    if (group.length >= 2) {
      pairs.add(Hand(group.cards.sublist(0,2), HandType.pair, power: group[0].powerRank));
    }
    else if (group.length == 1 && !group[0].isJoker && wildCardsAvailable >= 1 && group[0].powerRank > resolvedTargetPower) {
      pairs.add(Hand(group.cards + [PokerCard.wildCard(levelRank)], HandType.pair, power: group[0].powerRank));
    }
  }
  if (wildCardsAvailable >= 2 && CardRank.rankValueOfLevelCard > resolvedTargetPower) {
    pairs.add(Hand([PokerCard.wildCard(levelRank),PokerCard.wildCard(levelRank)], HandType.pair, power: CardRank.rankValueOfLevelCard));
  }
  if (!findAll && pairs.isNotEmpty) {
    pairs.sort((a, b) => a.power.compareTo(b.power));
    return [pairs.first];
  }
  return pairs;
}

/// This function finds all possible full houses (or the first one if `findAll` is false) in a list of poker cards.
/// If [findAll] is false, only the first full house (the one with the lowest power rank) is returned.
/// If [targetPower] is provided, only full houses with power rank higher than [targetPower] are considered.
List<Hand> findFullHouses(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  List<Hand> fullHouses = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  var blackJokers = cards.where((card) => card.rank == CardRank.blackJoker);
  var redJokers = cards.where((card) => card.rank == CardRank.redJoker);
  for (int tripleRankValue = CardRank.two.value; tripleRankValue <= CardRank.redJoker.value; tripleRankValue++) {
    
    // level rank will be considered in the rank from 2 to A.
    if (tripleRankValue == CardRank.rankValueOfLevelCard) continue;

    if (tripleRankValue <= resolvedTargetPower) continue; // ensure the triple is stronger than the target hand

    int wildCardsUsed = 0;
    var tripleRank = CardRank.fromValue(tripleRankValue);
    PokerCardList? cardsOfTriple;

    if (tripleRank.isBlackJoker) {
      if (blackJokers.length >= 3) {
        cardsOfTriple = blackJokers.sublist(0, 3);
      }
    }
    else if (tripleRank.isRedJoker) {
      if (redJokers.length >= 3) {
        cardsOfTriple = redJokers.sublist(0, 3);
      }
    }
    else{
      var triple = findSeries(regularCards, tripleRankValue, 1, wildCardsAvailable, 3);
      if (triple.isValid) {
        cardsOfTriple = triple.toHand(levelRank);
        wildCardsUsed = triple.wildCardsUsed;
      }
    }
  
    if (cardsOfTriple != null) {
      // now try to find a pair to go with the triple to form a full house
      var remainingCards = cards - cardsOfTriple;
      for (int pairRankValue = 1; pairRankValue <= 13; pairRankValue++) {
        if (pairRankValue == tripleRankValue) {
          continue;
        }
        var pair = findSeries(remainingCards, pairRankValue, 1, wildCardsAvailable - wildCardsUsed, 2);
        if (pair.isValid) {
          var hand = Hand(cardsOfTriple.cards + pair.toHand(levelRank).cards, HandType.fullHouse, power: tripleRankValue);
          fullHouses.add(hand);
          if(!findAll && fullHouses.isNotEmpty) {
            return [fullHouses.first];
          }
        }
      }
      // consider a pair of jokers
      if(findAll || fullHouses.isEmpty) {
        if (blackJokers.length >= 2 && tripleRankValue != CardRank.blackJoker.value) {
          var hand = Hand(cardsOfTriple.cards + blackJokers.sublist(0, 2).cards, HandType.fullHouse, power: tripleRankValue);
          fullHouses.add(hand);
        }
      }
      
      if (findAll || fullHouses.isEmpty) {
        if (redJokers.length >= 2 && tripleRankValue != CardRank.redJoker.value) {
          var hand = Hand(cardsOfTriple.cards + redJokers.sublist(0, 2).cards, HandType.fullHouse, power: tripleRankValue);
          fullHouses.add(hand);
        }
      }
    }
  }

  if (!findAll && fullHouses.isNotEmpty) {
    fullHouses.sort((a, b) => a.power.compareTo(b.power));
    return [fullHouses.first];
  }
  return fullHouses;
}

/// This function finds all possible singles (or the first one if `findAll` is false) in a list of poker cards.
/// If [findAll] is false, only the first single (the one with the lowest power rank) is returned.
/// If [targetPower] is provided, only singles with power rank higher than [targetPower] are considered.
List<Hand> findSingles(PokerCardList cards, CardRank levelRank, {bool findAll = false, int? targetPower}) {
  final resolvedTargetPower = targetPower ?? -1;
  final hands = cards
      .where((card) => card.powerRank > resolvedTargetPower)
      .map((card) => Hand([card], HandType.single, power: card.powerRank))
      .toList();
  if (findAll || hands.isEmpty) {
    return hands;
  }
  hands.sort((a, b) => a.power.compareTo(b.power));  return hands.isNotEmpty ? [hands.first] : [];
}

/// This function finds all possible bombs (or the first one if `findAll` is false) in a list of poker cards.
/// If [findAll] is false, only the first bomb (the one with the lowest power rank) is returned.
/// If [targetPower] is provided, only bombs with power rank higher than [targetPower] are considered.
List<Hand> findBombs(PokerCardList cards, CardRank levelRank, {bool findAll = false, bool includeStraightFlush=false, int deckCount = 2, int? targetPower}) {

  List<Hand> bombs = [];
  var regularCards = extractRegularCards(cards);
  var wildCardsAvailable = cards.length - regularCards.length;
  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));
  for (var group in grouped) {
    if (group[0].isJoker) {
      continue;
    }
    else {
      for (var w = 0; w <= wildCardsAvailable; w++) {
        if (group.length + w >= 4) {
          bombs.add(Hand(group.cards + List.filled(w, PokerCard.wildCard(levelRank)), HandType.bomb,
          power: getBombPower(group.length+w, group.cards[0].powerRank, deckCount, false, false)));
        }
      }
    }
  }
  // joker bombs
  var blackJokers = cards.where((card) => card.rank == CardRank.blackJoker);
  var redJokers = cards.where((card) => card.rank == CardRank.redJoker);
  if (blackJokers.length == deckCount && redJokers.length == deckCount) {
    bombs.add(Hand(List.filled(deckCount, PokerCard.redJoker)+List.filled(deckCount, PokerCard.blackJoker), 
      HandType.bomb, power: getJokerBombPower(deckCount)));
      // TODO consider minor joker bomb for 6 players
  }
  // straight flush bombs
  if (includeStraightFlush) {
    var straightFlushes = findStraightFlushes(cards, levelRank, findAll: true);
    bombs.addAll(straightFlushes);
  }

  if (targetPower != null) {
    bombs = bombs.where((hand) => hand.power > targetPower).toList();
  }

  if (!findAll && bombs.isNotEmpty) {
    bombs.sort((a, b) => a.power.compareTo(b.power));
    return [bombs.first];
  }
  return bombs;
}

/// Find hands of a specific type and level rank from a list of poker cards.
/// If [findAll] is false, only the first hand (the one with the lowest power rank) that meets the criteria is returned.
/// If [targetPower] is provided, only hands with power rank higher than [targetPower] are considered.
/// [includeStraightFlush] is only applicable when [handType] is [HandType.bomb]. If true, straight flushes are also considered as bombs.
/// [deckCount] is the number of standard decks used in the game, which affects the power calculation of bombs.
List<Hand> findHands(PokerCardList cards, CardRank levelRank, HandType handType, {bool findAll = false, bool includeStraightFlush=false, int deckCount = 2, int? targetPower}) {
  List<Hand> hands = [];
  switch (handType) {
    case HandType.single:
      hands = findSingles(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.pair:
      hands = findPairs(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.triple:
      hands = findTriples(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.straight:
      hands = findStraights(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.tube:
      hands = findTubes(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.plate:
      hands = findPlates(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.fullHouse:
      hands = findFullHouses(cards, levelRank, findAll: findAll, targetPower: targetPower);
      break;
    case HandType.bomb:
      hands = findBombs(cards, levelRank, findAll: findAll, includeStraightFlush: includeStraightFlush, deckCount: deckCount, targetPower: targetPower);
      break;
    default:
      break;
  }
  return hands;
}


/// Separates wild cards from a set of cards.
///
/// This function extracts wild cards from a set of cards based on the specified level rank.
///
/// Args:
///   - [cards] : A list of PokerCard objects to check.
///
/// Returns:
///   A list of two lists, the first list contains the wild cards and the second list contains the regular cards without wild cards.
List<PokerCardList> separateWildCards(Iterable<PokerCard> cards) {
  var wildCards = PokerCardList(cards.where((card) => card.isWildCard));
  var regularCards =  PokerCardList(cards.where((card) => !card.isWildCard));
  return [wildCards, regularCards];
}


/// Extracts regular cards (which are not wild cards) from a list of poker cards.
PokerCardList extractRegularCards(Iterable<PokerCard> cards) {
  if (cards is PokerCardList) {
    return cards.where((card) => !card.isWildCard);
  }
  return PokerCardList(cards.where((card) => !card.isWildCard));
}

PokerCardList extractWildCards(Iterable<PokerCard> cards) {
  if (cards is PokerCardList) {
    return cards.where((card) => card.isWildCard);
  }
  return PokerCardList(cards.where((card) => card.isWildCard));
}

/// A class representing the result in [HandTypeCheckResult].
class HandTypeCheckResult {

  /// A boolean indicating whether the cards form a valid hand type.
  final bool valid;

  /// The power of the hand type.
  final int power;

  int? seriesStartRankValue; // for straight, tube, plate

  HandTypeCheckResult(this.valid, this.power, {this.seriesStartRankValue});

  static HandTypeCheckResult invalid = HandTypeCheckResult(false, -1);
}

/// Checks if a set of cards is a single card.
///
/// This function checks if the specified cards form a single card.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
///
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a single card and the rank index of the single card.
HandTypeCheckResult checkSingle(PokerCardList cards) {
  if (cards.length != 1) {
    return HandTypeCheckResult.invalid;
  }
  return HandTypeCheckResult(true, cards[0].powerRank);
}

/// Checks if a set of cards is a single
bool isSingle(PokerCardList cards) {
  return checkSingle(cards).valid;
}

/// Checks if a set of cards is a pair.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
///   - [wildAsRegular]: A boolean flag indicating whether to treat wild cards as regular cards.
///
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a pair and the rank index of the pair.
HandTypeCheckResult checkPair(PokerCardList cards, {bool wildAsRegular = false}) {
  if (cards.length != 2) {
    return HandTypeCheckResult.invalid;
  }

  if (cards[0].rank == cards[1].rank) {
    return HandTypeCheckResult(true, cards[0].powerRank);
  }

  if (!wildAsRegular) {
    var separated = separateWildCards(cards);
    var wild = separated[0];
    var regular = separated[1];
    if (wild.isNotEmpty) {
      if (regular.isEmpty) {
        return HandTypeCheckResult(true, wild[0].powerRank);
      } else {
        return HandTypeCheckResult(!regular[0].isJoker, regular[0].powerRank);
      }
    }
  }
  return HandTypeCheckResult.invalid;
}

/// Checks if a set of cards is a pair.
bool isPair(PokerCardList cards, {bool wildAsRegular = false}) {
  return checkPair(cards, wildAsRegular: wildAsRegular).valid;
}

/// Checks if a set of cards is a triple.
///
/// This function checks if the specified cards form a triple.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
///   - [wildAsRegular]: A boolean flag indicating whether to ignore wildcards.
///
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a triple and the rank index of the triple.
HandTypeCheckResult checkTriple(PokerCardList cards, {bool wildAsRegular = false}) {
  if (cards.length != 3) {
    return HandTypeCheckResult.invalid;
  }

  if (cards[0].rank == cards[1].rank && cards[1].rank == cards[2].rank) {
    return HandTypeCheckResult(true, cards[0].powerRank);
  }

  if (!wildAsRegular) {
    var separated = separateWildCards(cards);
    var wild = separated[0];
    var regular = separated[1];
    if (regular.isEmpty) {
      return HandTypeCheckResult(true, wild[0].powerRank);
    }

    var r = regular[0].rank;
    if (regular.every((card) => card.rank == r)) { // all regular cards are the same rank
      if (!regular[0].isJoker) {
        return HandTypeCheckResult(true, regular[0].powerRank);
      } 
      else { // all regular cards are jokers
        if (wild.isEmpty) {
          return HandTypeCheckResult(true, regular[0].powerRank);
        } else {
          return HandTypeCheckResult.invalid;
        }
      }
    }
  }
  return HandTypeCheckResult.invalid;
}

/// Checks if a set of cards is a triple.
bool isTriple(PokerCardList cards, {bool wildAsRegular = false}) {
  return checkTriple(cards, wildAsRegular: wildAsRegular).valid;
}


/// Checks if a set of cards is a full house.
///
/// This function checks if the specified cards form a full house, which is a combination of a triple and a pair.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a full house and the rank index of the triple.
HandTypeCheckResult checkFullHouse(PokerCardList cards) {
  if (cards.length != 5) {
    return HandTypeCheckResult.invalid;
  }

  cards.sortByNaturalRank();

  // Check if the first three cards form a triple and the last two form a pair
  var tripleResult = checkTriple(cards.sublist(0, 3), wildAsRegular: true);
  if (tripleResult.valid && checkPair(cards.sublist(3), wildAsRegular: true).valid) {
    return HandTypeCheckResult(true, tripleResult.power);
  }

  // Check if the first two cards form a pair and the last three form a triple
  tripleResult = checkTriple(cards.sublist(2));
  if (checkPair(cards.sublist(0, 2)).valid && tripleResult.valid) {
    return HandTypeCheckResult(true, tripleResult.power);
  }

  // Consider wild cards
  var separated = separateWildCards(cards);
  var wild = separated[0];
  var regular = separated[1];

  regular.sortByPowerRank();

  if (regular.length > 4) {
    return HandTypeCheckResult.invalid;
  }

  if (regular.isEmpty) {
    return HandTypeCheckResult(true, wild[0].powerRank);
  }

  if (wild.isNotEmpty) {
    if (regular.length == 1) {
      if (regular[0].isJoker) {
        return HandTypeCheckResult.invalid;
      } else {
        return HandTypeCheckResult(true, regular[0].powerRank);
      }
    }

    if (regular.length == 2) {
      if (regular[0].rank == regular[1].rank) {
        return HandTypeCheckResult(true, wild[0].powerRank);
      } 
      else if (regular[0].isJoker || regular[1].isJoker) {
        return HandTypeCheckResult.invalid;
      }
      else{
        return HandTypeCheckResult(true, regular[1].powerRank);
      }
    }

    if (regular.length == 3) {
      if (regular[0].rank == regular[1].rank && regular[1].rank == regular[2].rank) {
        return HandTypeCheckResult(true, regular[0].powerRank);
      } else if (regular[0].rank != regular[1].rank && regular[1].rank != regular[2].rank) {
        return HandTypeCheckResult.invalid;
      } else if (regular[0].isJoker) {
        return HandTypeCheckResult.invalid;
      } else if (regular[2].isJoker) {
        return HandTypeCheckResult(true, regular[0].powerRank);
      } else {
        return HandTypeCheckResult(true, regular[2].powerRank);
      }
    }

    if (regular.length == 4) {
      var blackJokers = regular.where((card) => card.isBlackJoker).toList();
      var redJokers = regular.where((card) => card.isRedJoker).toList();
      var m = blackJokers.length;
      var n = redJokers.length;

      if (m==1 || n==1 || m+n==4 || (m==2 && n==2)) {
        return HandTypeCheckResult.invalid;
      }

      if (m == 3) {
        return HandTypeCheckResult(true, blackJokers[0].powerRank);
      }
      if (n == 3) {
        return HandTypeCheckResult(true, redJokers[0].powerRank);
      }
      // below, at most 1 pair of joker of the same color
      if (regular[0].rank == regular[1].rank && regular[1].rank == regular[2].rank) {
        return HandTypeCheckResult(true, regular[0].powerRank);
      }
      if (regular[1].rank == regular[2].rank && regular[2].rank == regular[3].rank) {
        return HandTypeCheckResult(true, regular[3].powerRank);
      }
      if (regular[0].rank == regular[1].rank && regular[2].rank == regular[3].rank) {
        return HandTypeCheckResult(true, m == 2 || n==2 ? regular[0].powerRank : regular[3].powerRank);
      }
    }
  }


  return HandTypeCheckResult.invalid;
}

/// Checks if a set of cards is a full house.
bool isFullHouse(PokerCardList cards) {
  return checkFullHouse(cards).valid;
}


/// Checks if a set of cards is a plate.
///
/// This function checks if the specified cards form a plate, which is a combination of two consecutive triples.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
///
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a plate and the rank index of the plate.
HandTypeCheckResult checkPlate(PokerCardList cards) {
  if (cards.length != 6) {
    return HandTypeCheckResult.invalid;
  }

  cards.sortByNaturalRank(); // .sort((a, b) => a.naturalSortIndex.compareTo(b.naturalSortIndex));

  if (cards.any((card) => card.isJoker)) {
    return HandTypeCheckResult.invalid;
  }

  // Check if there are two consecutive triples
  var triple1 = checkTriple(cards.sublist(0, 3), wildAsRegular: true);
  var triple2 = checkTriple(cards.sublist(3, 6), wildAsRegular: true);
  if (triple1.valid && triple2.valid) {
    var rank1 = cards[0].naturalRank;
    var rank2 = cards[3].naturalRank;

    if ((rank2 - rank1).abs() == 1) {
      int power = rank2 > rank1 ? rank1 : rank2;
      return HandTypeCheckResult(true, power, seriesStartRankValue: power);
    }

    if (cards[3].rank == CardRank.A && cards[0].rank == CardRank.two) {
      return HandTypeCheckResult(true, 1, seriesStartRankValue: 1);
    }
  }

  // Consider wild cards
  var separated = separateWildCards(cards);
  var wild = separated[0];
  var regular = separated[1];
  if (regular.isEmpty) {
    return HandTypeCheckResult(true, wild[0].powerRank, seriesStartRankValue: wild[0].powerRank);
  }

  bool isValidPlateWithWildCards(PokerCardList regular, int wildCardsAvailable, int startRankValue) {
    var wildCardsNeeded = 0;
    for (int r = startRankValue; r <= startRankValue + 1; r++) {
      var c = countCards(regular, CardRank.fromValue(r));
      if (c >= 4) {
        return false;
      }
      wildCardsNeeded += 3 - c;
    }
    return wildCardsNeeded == wild.length;
  }

  regular.sortByNaturalRank();// .sort((a, b) => a.naturalSortIndex.compareTo(b.naturalSortIndex));
  var startRankValue = regular.first.naturalRank;
  var endRankValue = regular.last.naturalRank;
  if (endRankValue - startRankValue >= 2) {
    if (regular.last.rank == CardRank.A && regular.first.rank == CardRank.two) {
      if (isValidPlateWithWildCards(regular, wild.length, 1)) {
        return HandTypeCheckResult(true, 1, seriesStartRankValue: 1);
      }
    }
    return HandTypeCheckResult.invalid;
  }

  if (isValidPlateWithWildCards(regular, wild.length, startRankValue)) {
    return HandTypeCheckResult(true, startRankValue, seriesStartRankValue: startRankValue);
  }

  return HandTypeCheckResult.invalid;
}


/// Checks if a set of cards is a plate.
bool isPlate(PokerCardList cards) {
  return checkPlate(cards).valid;
}


/// Checks if a set of cards is a tube.
///
/// This function checks if the specified cards form a tube, which is a combination of three consecutive pairs.
///
/// Args:
///   - [cards]: A list of PokerCard objects to check.
///
/// Returns:
///   A [HandTypeCheckResult] containing a boolean indicating if the cards form a tube and the rank index of the tube.
HandTypeCheckResult checkTube(PokerCardList cards) {
  if (cards.length != 6) {
    return HandTypeCheckResult.invalid;
  }

  if (cards.any((card) => card.isJoker)) {
    return HandTypeCheckResult.invalid;
  }

  var separated = separateWildCards(cards);
  var wild = separated[0];
  var regular = separated[1];
  regular.sortByNaturalRank(); // .sort((a, b) => a.naturalSortIndex.compareTo(b.naturalSortIndex));

  if (regular.isEmpty) {
    return HandTypeCheckResult(true, CardRank.Q.value, seriesStartRankValue: CardRank.Q.value);
  }

  var ret = findSeries(cards, min(regular[0].rank.value, CardRank.Q.value), 3, wild.length, 2);
  if (ret.isValid) {
    var power = min(ret.startRankValue, CardRank.Q.value);
    return HandTypeCheckResult(true, power, seriesStartRankValue: power);
  }

  ret = findSeries(cards, 1, 3, wild.length, 2); // A-2-3
  if (ret.isValid) {
    return HandTypeCheckResult(true, 1, seriesStartRankValue: 1);
  }

  return HandTypeCheckResult.invalid;
}


/// Checks if a set of cards is a tube.
bool isTube(PokerCardList cards) {
  return checkTube(cards).valid;
}


/// Checks if a set of cards is a straight.
/// 
/// This function checks if the specified cards form a straight, which is a combination of five consecutive cards.
/// 
/// Args:
///  - [cards]: A list of PokerCard objects to check.
/// 
HandTypeCheckResult checkStraight(Iterable<PokerCard> cards) {
  if (cards.length != 5) {
    return HandTypeCheckResult.invalid;
  }

  if (cards.any((card) => card.isJoker)) {
    return HandTypeCheckResult.invalid;
  }

  var separated = separateWildCards(cards);
  var wild = separated[0];
  var regular = separated[1];
  regular.sortByNaturalRank(); // .sort((a, b) => a.naturalSortIndex.compareTo(b.naturalSortIndex));


  if (regular.isEmpty) {
    return HandTypeCheckResult(true, CardRank.T.value, seriesStartRankValue: CardRank.T.value);
  }

  var ret = findSeries(cards, min(regular[0].rank.value, CardRank.T.value), 5, wild.length, 1);
  if (ret.isValid) {
    return HandTypeCheckResult(true, ret.startRankValue, seriesStartRankValue: ret.startRankValue);
  }

  ret = findSeries(cards, 1, 5, wild.length, 1); // A-2-3-4-5
  if (ret.isValid) {
    return HandTypeCheckResult(true, 1, seriesStartRankValue: 1);
  }

  return HandTypeCheckResult.invalid;
}


/// Checks if a set of cards is a straight.
bool isStraight(PokerCardList cards) {
  return checkStraight(cards).valid;
}

/// Checks if a set of cards is a straight flush.
HandTypeCheckResult checkStraightFlush(Iterable<PokerCard> cards) {
  var s = checkStraight(cards);
  if (s.valid){
    var regularCards = extractRegularCards(cards);
    if (regularCards.every((card) => card.suit == regularCards[0].suit)){
      return HandTypeCheckResult(true, getNonJokerBombPower(6, s.power), seriesStartRankValue: s.seriesStartRankValue);
    }
  }
  return HandTypeCheckResult.invalid;
}

/// Checks if a set of cards is a straight flush.
bool isStraightFlush(Iterable<PokerCard> cards) {
  return checkStraightFlush(cards).valid;
}


/// Define the power for bomb with m cards and the rank
/// Args:
///  - [m]: number of cards of this bomb
///  - [rank]: the rank or the start rank if it is [straightFlush] bomb
///  - [numberOfDecks]: the number of standard decks in the game
///  - [straightFlush]: whether this is a straight flush bomb
///  - [jokerBomb]: whether this is a joker bomb
int getBombPower(int m, int rank, int numberOfDecks,  bool straightFlush, bool jokerbomb)
{
  if (jokerbomb){
    assert (m == numberOfDecks*2);
    return getJokerBombPower(numberOfDecks);
  }

  if (straightFlush){
    assert (m==5);
    return getNonJokerBombPower(6, rank);
  }
  
  if (m <= 5) return getNonJokerBombPower(m, rank);
  
  return getNonJokerBombPower(m+1, rank);

}


/// Define power for (non-joker) bomb
/// 
/// The power is derived from the rank of the bomb and the number of cards in the bomb.
/// [major] is the number of cards in the bomb, determined in the following way:
///   - If it is a straight flush bomb, then [major] is 6. 
///   - Otherwise, if number of cards <= 5, then [major] is the number of cards in the bomb; otherwise, [major] is the number of cards in the bomb minus + 1.
/// [minor] is the rank value of the bomb
int getNonJokerBombPower(int major, int minor){
  return major * 100 + minor;
}

/// The maximum power of a non-joker bomb.
int maxNonJokerBombPower(int numberOfDecks){
  return getNonJokerBombPower(5*numberOfDecks+1, CardRank.rankValueOfLevelCard);
}

/// Define power for joker bomb
int getJokerBombPower(int numberOfDecks){
  return maxNonJokerBombPower(numberOfDecks)*10;
}

/// Checks if a set of cards is a bomb.
HandTypeCheckResult checkBomb(PokerCardList cards, {int numberOfDecks=2}) {
  if (cards.length < 4) {
    return HandTypeCheckResult.invalid;
  }

  var jokers = cards.where((card) => card.isJoker).toList();
  if (jokers.length == cards.length && jokers.length == numberOfDecks*2) {
    return HandTypeCheckResult(true, getJokerBombPower(numberOfDecks));
  }

  if(jokers.isNotEmpty){
    return HandTypeCheckResult.invalid;
  }

  var regularCards = extractRegularCards(cards);

  if(regularCards.isEmpty){
    if (cards.length == 5){ // all five cards are wild cards, considered as the highest straight flush bomb
      return HandTypeCheckResult(true, getNonJokerBombPower(6, CardRank.A.value));
    }
    else{
      var major = cards.length + (cards.length <= 5 ?  0: 1);
      return HandTypeCheckResult(true, getNonJokerBombPower(major, CardRank.rankValueOfLevelCard));
    }
  }

  if (regularCards.every((card) => card.rank == regularCards[0].rank)) {
    var major = cards.length + (cards.length <= 5 ?  0: 1);
    return HandTypeCheckResult(true, getNonJokerBombPower(major, regularCards[0].powerRank));
  }

  var sf = checkStraightFlush(cards);
  if (sf.valid){
    return HandTypeCheckResult(true, sf.power);
  }

  return HandTypeCheckResult.invalid;
}

/// Checks if a set of cards is a bomb.
bool isBomb(PokerCardList cards, {int numberOfDecks=2}) {
  return checkBomb(cards, numberOfDecks: numberOfDecks).valid;
}

/// checks if a set of cards is a joker bomb.
bool isJokerBomb(PokerCardList cards, {int numberOfDecks=2}) {
  var b = checkBomb(cards, numberOfDecks: numberOfDecks);
  if (b.valid){
    return b.power == getJokerBombPower(numberOfDecks);
  }
  return false;
}


/// Deduce the hand type of a set of cards, and calculate the power of the hand if it is a valid hand.
/// Args:
///  - [handOrCards]: A Hand object or a list of PokerCard objects.
///  - [deckCount]: The number of standard decks used in the game. Default is 2.
///  - [forced]: A boolean flag indicating whether to force the deduction of the hand type even when the hand type is already known and valid. If false, the hand type of [cards] will be deduced only when it is unknown, invalid, with power < 0, or [cards] is not a Hand object.
Hand deduceHandType(PokerCardList cards, {int deckCount=2, bool forced=false}){

  if (!forced){
    if (cards is Hand && !cards.type.isUnknownOrInvalid && cards.power >= 0){
      return cards;
    }
  }

  Hand createNewHandWhenNeeded(dynamic handOrCardList, HandType type, int power){
    if (handOrCardList is Hand){
      handOrCardList.type = type;
      handOrCardList.power = power;
      return handOrCardList;
    }
    else if (handOrCardList is List<PokerCard>){
      return Hand(handOrCardList, type, power: power);
    }
    else if (handOrCardList is PokerCardList){
      return Hand(handOrCardList.cards, type, power: power);
    }
    throw ArgumentError('handOrCards must be either Hand or List<PokerCard> or PokerCardList');
  }

  if (cards.isEmpty){
    return createNewHandWhenNeeded(cards, HandType.empty, 0);
  }

  var result = checkBomb(cards, numberOfDecks: deckCount);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.bomb,  result.power);
  }

  result = checkStraightFlush(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.bomb,  result.power);
  }

  result = checkStraight(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.straight, result.power);
  }

  result = checkFullHouse(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.fullHouse, result.power);
  }

  result = checkTube(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.tube, result.power);
  }

  result = checkPlate(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.plate, result.power);
  }

  result = checkTriple(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.triple, result.power);
  }

  result = checkPair(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.pair, result.power);
  }

  result = checkSingle(cards);
  if (result.valid){
    return createNewHandWhenNeeded(cards, HandType.single, result.power);
  }
  
  return createNewHandWhenNeeded(cards, HandType.invalid, -1);
}

/// Check if the hand or cards can be played on the hand on table
/// If [allowEmptyHand] is true, then an empty hand can be played on any valid hand on table
/// If [forced] is true, then the hand type of [handOrCardsToPlay] will be recalculated; see [deduceHandType] for details.
bool canPlay(PokerCardList handOrCardsToPlay, Hand handOnTable, {bool allowEmptyHand=false, int deckCount=2, bool forced=false}){

  if (handOnTable.type.isUnknownOrInvalid){
    handOnTable = deduceHandType(handOnTable, deckCount: deckCount, forced: forced);
  }

  if (handOnTable.type.isUnknownOrInvalid){
    return false;
  }

  Hand handToPlay = deduceHandType(handOrCardsToPlay, deckCount: deckCount, forced: forced);
  if (handToPlay.type.isUnknownOrInvalid){
    return false;
  }

  if (handToPlay.type == HandType.empty){
    return allowEmptyHand;
  }

  if (handOnTable.type == HandType.empty){
    return true;
  }

  // below both handToPlay and handOnTable are not empty

  if (handToPlay.type == HandType.bomb){
    return handToPlay.power > handOnTable.power;
  }

  // below handToPlay is not bomb
  if (handOnTable.type == HandType.bomb){
    return false;
  }

  // below both handToPlay and handOnTable are not bomb
  if (handOnTable.type == HandType.tube && handToPlay.type == HandType.plate){
    // check whether a plate can be played as tube (due to the wild cards)
    var checkTubeResult = checkTube(handToPlay);
    if (checkTubeResult.valid && checkTubeResult.power > handOnTable.power){
      return true;
    }
  }

  if (handOnTable.type == HandType.plate && handToPlay.type == HandType.tube){
    // check whether a tube can be played as plate (due to the wild cards)
    var checkPlateResult = checkPlate(handToPlay);
    if (checkPlateResult.valid && checkPlateResult.power > handOnTable.power){
      return true;
    }
  }

  return handToPlay.type == handOnTable.type && handToPlay.power > handOnTable.power;
}

/// Find the rank of a hand, defined in the following way:
/// - For a single card, the rank is the rank of the card.
/// - For a pair, the rank is the rank of the pair.
/// - For a triple, the rank is the rank of the triple.
/// - For a full house, the rank is the rank of the triple.
/// - For a tube, the rank is the rank of the first pair.
/// - For a plate, the rank is the rank of the first triple.
/// - For a straight (including straight flush), the rank is the rank of first card.
/// - For a bomb, the rank is the rank of the bomb.
CardRank? rankOfHand(Hand hand, CardRank levelRank, {int numberOfDecks=2}){
  if (hand.type == HandType.single || hand.type == HandType.pair || hand.type == HandType.triple ||
    hand.type == HandType.fullHouse || hand.type == HandType.tube || hand.type == HandType.plate){
    return hand.power == CardRank.rankValueOfLevelCard ? levelRank : CardRank.fromValue(hand.power);
  }

  if (hand.type == HandType.bomb){
    if (hand.power == getJokerBombPower(numberOfDecks)){
      return CardRank.blackJoker;
    }
    if (hand.cards.length == 5){
      var b = checkStraight(hand);
      if (b.valid){
        return CardRank.fromValue(b.power);
      }
    }
    var regular = extractRegularCards(hand);
    assert (regular.isNotEmpty);
    return regular[0].rank;
  }

  return null;
}

/// Filter a list of hands to meet given constraints.
/// 
/// Args:
///  - [hands]: A list of Hand objects to search from.
///  - [handType]: The type of hand to search for. If not specified, the function will search for any type of hand.
///  - [numberOfDecks]: The number of standard decks used in the game. Default is 2.
///  - [lowerBound]: The (not included) lower bound of power of the hand to search for. Default is null, meaning no lower bound. 
///  - [upperBound]: The (not included) upper bound of power of the hand to search for. Default is null, meaning no upper bound.
/// 
/// For plate, tube, and fullhouse, it also tries to combine
///  - triples into plates if [triplesToPlates] is true
///  - triples and pairs into full houses if [triplesAndPairsToFullHouses] is true
///  - pairs into plates if [pairsToTubes] is true
/// 
List<Hand> filterHands(List<Hand> hands, {HandType? handType, int numberOfDecks = 2, int? lowerBound, int? upperBound, 
    bool triplesToPlates = true, bool triplesAndPairsToFullHouses = true, bool pairsToTubes = true, bool pairJokers=false}) {

  assert (hands.every((h) => h.type != HandType.unknown && h.type != HandType.invalid && h.power >= 0));
  
  List<Hand> result = [];
  
  lowerBound ??= -1;

  upperBound ??= getJokerBombPower(numberOfDecks);

  for (var hand in hands) {
    if (handType != null && hand.type != handType) {
      continue;
    }
    int index = hand.power;
    if (index > lowerBound && index < upperBound) {
      result.add(hand);
    }
  }

  List<Hand> pairsFromJokers(){
    var jokerPairs =<Hand>[];
    var allCards = hands.expand((h) => h.cards).toList();
    var blackJokers = allCards.where((c) => c.isBlackJoker).toList();
    if (blackJokers.length >= 2){
      jokerPairs.add(Hand(blackJokers.sublist(0,2), HandType.pair, power: CardRank.blackJoker.value));
    }
    var redJokers = allCards.where((c) => c.isRedJoker).toList();
    if (redJokers.length >= 2){
      jokerPairs.add(Hand(redJokers.sublist(0,2), HandType.pair, power: CardRank.redJoker.value));
    }
    return jokerPairs;
  }

  if (handType == HandType.pair && pairJokers){
    result.addAll(pairsFromJokers());
  }

  if (handType == HandType.plate && triplesToPlates) {
    for (var startRankValue = 1; startRankValue <= CardRank.K.value; startRankValue++) {
      if (startRankValue <= lowerBound || startRankValue >= upperBound) {
        continue;
      }
      var startRank = CardRank.fromValue(startRankValue);
      var endRank = CardRank.fromValue(startRankValue + 1);
      var startTriples = hands.where((h) => h.type == HandType.triple && h.power == startRank.value).toList();
      if (startTriples.isEmpty) {
        continue;
      }
      var endTriples = hands.where((h) => h.type == HandType.triple && h.power == endRank.value).toList();
      if (endTriples.isEmpty) {
        continue;
      }
      result.add(Hand(startTriples[0].cards + endTriples[0].cards, HandType.plate, power: startRankValue));
    }
  }

  if (handType == HandType.tube && pairsToTubes) {
    for (var startRankValue = 1; startRankValue <= CardRank.Q.value; startRankValue++) {
      if (startRankValue <= lowerBound || startRankValue >= upperBound) {
        continue;
      }

      var startRank = CardRank.fromValue(startRankValue);
      var middleRank = CardRank.fromValue(startRankValue + 1);
      var endRank = CardRank.fromValue(startRankValue + 2);
      var startPairs = hands.where((h) => h.type == HandType.pair && h.power == startRank.value).toList();
      if (startPairs.isEmpty) {
        continue;
      }
      var middlePairs = hands.where((h) => h.type == HandType.pair && h.power == middleRank.value).toList();
      if (middlePairs.isEmpty) {
        continue;
      }
      var endPairs = hands.where((h) => h.type == HandType.pair && h.power == endRank.value).toList();
      if (endPairs.isEmpty) {
        continue;
      }
      result.add(Hand(startPairs[0].cards + endPairs[0].cards, HandType.plate, power: startRankValue));
    }
  }

  if (handType == HandType.fullHouse && triplesAndPairsToFullHouses) {
    var triples = hands.where((c) => c.type == HandType.triple).toList();
    var pairs = hands.where((c) => c.type == HandType.pair).toList();
    if (pairs.isEmpty && pairJokers){
      pairs = pairsFromJokers();
    }

    if (triples.isNotEmpty && pairs.isNotEmpty) {
      // it is sensible to attach the smallest pair for forming a full house
      var minPair = pairs.reduce((a, b) => a.power < b.power ? a : b);
      for (var triple in triples) {
        if (triple.power <= lowerBound || triple.power >= upperBound) {
          continue;
        }
        result.add(Hand(triple.cards + minPair.cards, HandType.fullHouse, power: triple.power));
      }
    }
  }

  return result;
}


/// Finds the minimum-power hand of a specified type from a list of hands to meet given constraints.
/// 
/// Args:
///  - [hands]: A list of Hand objects to search from.
///  - [handType]: The type of hand to search for. If not specified, the function will search for any type of hand.
///  - [numberOfDecks]: The number of standard decks used in the game. Default is 2.
///  - [lowerBound]: The (not included) lower bound of power of the hand to search for. Default is null, meaning no lower bound. 
///  - [upperBound]: The (not included) upper bound of power of the hand to search for. Default is null, meaning no upper bound.
///  - [triplesToPlates]: If true, also consider plates formed by triples.
///  - [triplesAndPairsToFullHouses]: If true, also consider full houses formed by triples and pairs.
///  - [pairsToTubes]: If true, also consider plates formed by pairs.
Hand? minOfHands(List<Hand> hands, {HandType? handType, int numberOfDecks = 2, int? lowerBound, int? upperBound, 
    bool singleFromPairs = false, bool singleFromTriples = false,
    bool triplesToPlates = false, bool triplesAndPairsToFullHouses = false, 
    bool pairsToTubes = false, bool pairJokers = false}) {
  
  lowerBound ??= -1;
  upperBound ??= getJokerBombPower(numberOfDecks);

  var filtered = filterHands(hands, handType: handType, numberOfDecks: numberOfDecks, lowerBound: lowerBound, upperBound: upperBound, 
    triplesToPlates: triplesToPlates, triplesAndPairsToFullHouses: triplesAndPairsToFullHouses, pairsToTubes: pairsToTubes, pairJokers: pairJokers);

  if (filtered.isNotEmpty){
    return filtered.reduce((a, b) => a.power < b.power ? a : b);
  }

  if (handType == HandType.single){

    Hand? result;

    if (singleFromTriples){
      var triples = filterHands(hands, handType: HandType.triple, numberOfDecks: numberOfDecks, lowerBound: lowerBound, upperBound: upperBound);
      if (triples.isNotEmpty){
        result = triples.reduce((a, b) => a.power < b.power ? a : b);
      }
    }

    if (result==null && singleFromPairs){
      var pairs = filterHands(hands, handType: HandType.pair, numberOfDecks: numberOfDecks, lowerBound: lowerBound, upperBound: upperBound);
      if (pairs.isNotEmpty){
        result = pairs.reduce((a, b) => a.power < b.power ? a : b);
      }
    }
    if (result != null){
      var regularCards = extractRegularCards(result);
      if (regularCards.isNotEmpty){
        return Hand(result.cards.sublist(0, 1), HandType.single, power: result.first.powerRank);
      }
      else {
        return Hand(result.cards.sublist(0, 1), HandType.single, power: result.first.powerRank);
      }
    }    
  }

  if (handType == HandType.pair && pairJokers){
    var jokerPairs = filterHands(hands, handType: HandType.pair, numberOfDecks: numberOfDecks, lowerBound: lowerBound, upperBound: upperBound, pairJokers: true);
    if (jokerPairs.isNotEmpty){
      return jokerPairs.reduce((a, b) => a.power < b.power ? a : b);
    }
  }

  return null;
}

/// Finds the maximum-power hand of a specified type from a list of hands to meet given constraints.
/// 
/// Args:
///  - [hands]: A list of Hand objects to search from.
///  - [handType]: The type of hand to search for. If not specified, the function will search for any type of hand.
///  - [numberOfDecks]: The number of standard decks used in the game. Default is 2.
///  - [lowerBound]: The (not included) lower bound of power of the hand to search for. Default is null, meaning no lower bound. 
///  - [upperBound]: The (not included) upper bound of power of the hand to search for. Default is null, meaning no upper bound.
///  - [triplesToPlates]: If true, also consider plates formed by triples.
///  - [triplesAndPairsToFullHouses]: If true, also consider full houses formed by triples and pairs.
///  - [pairsToTubes]: If true, also consider plates formed by pairs.
Hand? maxOfHands(List<Hand> hands, {HandType? handType, int numberOfDecks = 2, int? lowerBound, int? upperBound, 
    bool triplesToPlates = false, bool triplesAndPairsToFullHouses = false, bool pairsToTubes = false, bool pairJokers = false}) {

  lowerBound ??= -1;
  upperBound ??= getJokerBombPower(numberOfDecks);

  var filtered = filterHands(hands, handType: handType, numberOfDecks: numberOfDecks, lowerBound: lowerBound, upperBound: upperBound, 
    triplesToPlates: triplesToPlates, triplesAndPairsToFullHouses: triplesAndPairsToFullHouses, pairsToTubes: pairsToTubes, pairJokers: pairJokers);

  if (filtered.isNotEmpty){
    return filtered.reduce((a, b) => a.power > b.power ? a : b);
  }

  return null;
}

bool isMaxOfHandType(Hand hand, {required int numberOfDecks}){
  switch (hand.type){
    case HandType.single:
    case HandType.pair:
      return hand.power == PokerCard.redJoker.powerRank;
    case HandType.triple:
    case HandType.fullHouse:
      return hand.power == CardRank.rankValueOfLevelCard;
    case HandType.tube:
      return hand.power == CardRank.Q.value;
    case HandType.plate:
      return hand.power == CardRank.K.value;
    case HandType.straight:
      return hand.power == CardRank.T.value;
    case HandType.bomb:
      return hand.power == getJokerBombPower(numberOfDecks);
    default:
      return false;
  }
}

int isMaxBombPowerOf(int cardsCount, {required int numberOfDecks, bool includeJokerBomb=false}){
  if (cardsCount < 4){
    return 0;
  }
  if (cardsCount == 4){
    if (numberOfDecks == 2 && includeJokerBomb){
      return getJokerBombPower(numberOfDecks);
    }
    else{
      return getNonJokerBombPower(4, CardRank.rankValueOfLevelCard);
    }
  }
  if (cardsCount == 5){
    return getBombPower(5, CardRank.T.value, numberOfDecks, true, false);
  }

  return getNonJokerBombPower(cardsCount+1, CardRank.rankValueOfLevelCard);
  
}


/// Extract a pair from a triple, with tht following:
/// - if the number of cards with power > [lowerBound] is less than 2, return null
/// - if there are two regular cards, return the pair of regular cards
/// - else if there is one regular card and one wild card, return the pair of regular card and wild card
/// - else if there are two wild cards, return the pair of wild cards
Hand? extractPairFromTriple(Hand triple, [int lowerBound=-1, bool returnMax=false]){ 
  assert (triple.type == HandType.triple);
  return extractRegularPairIfPossible(triple, lowerBound, null, returnMax);
}

/// Extract triples from a plate, with the following:
/// - if the number of cards with power > [lowerBound] is less than 3, return an empty list
/// - else add the triples in sequence to the return list
///   - triple with regular cards
///   - triple with two regular cards and one wild card
///   - triple with one regular card and two wild cards
///   - triple with three wild cards
/// - if [returnMax] is true, return the triples in descending order of power, otherwise return the triples that use regular cards first
List<Hand> extractTriplesFromPlate(Hand plate, [int lowerBound=-1, bool returnMax=false]){
  assert (plate.type == HandType.plate);
  var cards = plate;
  var regularCards = cards.where((card) => !card.isWildCard && (card.powerRank > lowerBound));
  var wildCards = cards.where((card) => card.isWildCard && card.powerRank > lowerBound);
  if (regularCards.length + wildCards.length < 3) {
    return [];
  }
  if (regularCards.isEmpty) {
    return [Hand([wildCards[0], wildCards[1], wildCards[2]], HandType.triple, power: wildCards[0].powerRank)];
  }

  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));

  List<Hand> triples = [];
  for (var group in grouped) {
    if (group.length == 3) {
      triples.add(Hand(group.cards, HandType.triple, power: group[0].powerRank));
    }
  }
  if (wildCards.isNotEmpty) {
    for (var group in grouped) {
      if (group.length == 2) {
        triples.add(Hand(group.cards + [wildCards[0]], HandType.triple, power: group[0].powerRank));
      }
    }
  }
  
  if (wildCards.length > 1) {
    for (var group in grouped) {
      if (group.length == 1) {
        triples.add(Hand(group.cards + wildCards.sublist(0, 2).cards, HandType.triple, power: group[0].powerRank));
      }
    }
  }

  if (returnMax) {
    triples.sort((a, b) => a.power.compareTo(b.power));
    return triples.reversed.toList();
  }

  return triples;
}


/// Extract a pair from a full house, with the following:
/// - if the number of cards with power > [lowerBound] is less than 2, return null
/// - if the pair in the full house is regular and with power > [lowerBound], return the pair
/// - else if there are two regular cards in the triple of the full house and their power > [lowerBound], return the pair
/// - else if there is one regular card and one wild card with power > [lowerBound] in the full house, return the pair
Hand? extractPairFromFullHouse(Hand fullHouse, [int lowerBound=-1, int? upperBound, bool returnMax=false])
{
  assert (fullHouse.type == HandType.fullHouse);
  return extractRegularPairIfPossible(fullHouse, lowerBound, upperBound, returnMax);
}

/// Extract a pair from a plate, with the following:
/// - if the number of cards with power > [lowerBound] is less than 2, return null
/// - if there are two regular cards, return the pair of regular cards
Hand? extractPairFromPlate(Hand plate, [int lowerBound = -1, int? upperBound, bool returnMax=false]){
  assert (plate.type == HandType.plate);
  return extractRegularPairIfPossible(plate, lowerBound, upperBound, returnMax);
}

/// Extract a pair from a tube, using regular cards first if possible
Hand? extractPairFromTube(Hand tube, [int lowerBound=-1, int? upperBound, bool returnMax=false])
{
  assert (tube.type == HandType.tube);
  return extractRegularPairIfPossible(tube, lowerBound, upperBound, returnMax);
}

/// Extract the triple from a full house, using regular cards first if possible
Hand? extractTripleFromFullHouse(Hand fullHouse, [int lowerBound=-1])
{
  assert (fullHouse.type == HandType.fullHouse);
  var cards = fullHouse;
  var regularCards = cards.where((card) => !card.isWildCard && (card.powerRank > lowerBound));
  var wildCards = cards.where((card) => card.isWildCard && card.powerRank > lowerBound);
  if (regularCards.length + wildCards.length < 3) {
    return null;
  }
  if (regularCards.isEmpty) {
    return Hand([wildCards[0], wildCards[1], wildCards[2]], HandType.triple, power: wildCards[0].powerRank);
  }

  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));
  for (var group in grouped) {
    if (group.length == 3) {
      return Hand(group.cards, HandType.triple, power: group[0].powerRank);
    }
  }
  for (var group in grouped) {
    if (group.length >= 3) {
      return Hand(group.sublist(0, 3).cards, HandType.triple, power: group[0].powerRank);
    }
  }

  if (wildCards.isNotEmpty) {
    for (var group in grouped) {
      if (group.length == 2) {
        return Hand(group.sublist(0, 2).cards + [wildCards[0]], HandType.triple, power: group[0].powerRank);
      }
    }
  }

  if(wildCards.length > 1) {
    for (var group in grouped) {
      if (group.length == 1) {
        return Hand(group.cards + wildCards.sublist(0, 2).cards, HandType.triple, power: group[0].powerRank);
      }
    }
  }
  return null; 
}



/// Extract a full house from a plate
Hand? extractFullHouseFromPlate(Hand plate, [int lowerBound=-1, bool returnMax=false]){
  var triples = extractTriplesFromPlate(plate, lowerBound, returnMax);
  if (triples.isEmpty) {
    return null;
  }
  var pair = extractRegularPairIfPossible(plate - triples.first);
  if (pair == null) {
    return null;
  }
  return Hand(triples.first.cards + pair.cards, HandType.fullHouse, power: triples.first.power);
}

/// Group a list of hand by their type
Map<HandType, List<Hand>> groupHandsByType(List<Hand> hands){
  var grouped = <HandType, List<Hand>>{};
  for (var hand in hands) {
    if (!grouped.containsKey(hand.type)) {
      grouped[hand.type] = [];
    }
    grouped[hand.type]!.add(hand);
  }
  return grouped;
}

/// Extract a nonwild single card from a list of cards. If there is no nonwild card, return the first card.
PokerCard extractRegularSingleIfPossible(List<PokerCard> cards, {bool returnMax=false}) {
  if (cards.length == 1) {
    return cards.first;
  }
  var regularCards = cards.where((card) => !card.isWildCard).toList();
  if (regularCards.isNotEmpty) {
    if (returnMax) {
      return regularCards.reduce((a, b) => a.powerRank > b.powerRank ? a : b);
    }
    return regularCards.first;
  }
  return cards.first;
}

/// Extract a pair from a list of cards, with the following:
/// - if the number of cards with power > [lowerBound] is less than 2, return null
/// - if there is a pair of two regular cards wit power > [lowerBound], return the pair of regular cards
/// - else if there is one regular card and one wild card with power > [lowerBound], return the pair of regular card and wild card
/// - else if there are two wild cards with power > [lowerBound], return the pair of wild cards
/// - if [returnMax] is true, return the pair with the largest power, otherwise return the pair with the min power satisfying the condition
Hand? extractRegularPairIfPossible(Iterable<PokerCard> cards, [int lowerBound=-1, int? upperBound, bool returnMax=false]) {
  upperBound ??= PokerCard.redJoker.powerRank;
  var regularCards = cards.where((card) => !card.isWildCard && card.powerRank > lowerBound && card.powerRank < upperBound!);
  var wildCards = cards.where((card) => card.isWildCard && card.powerRank > lowerBound).toList();
  if (regularCards.length + wildCards.length < 2) {
    return null;
  }

  if (regularCards.isEmpty){
    return Hand([wildCards[0], wildCards[1]], HandType.pair, power: wildCards[0].powerRank); // TODO: allow user to specify the actual power of the wild cards
  }

  var grouped = groupCards(regularCards).values.toList()..sort((a, b) => a[0].powerRank.compareTo(b[0].powerRank));

  if (returnMax) {
    for (var group in grouped.reversed) {
      if (group.length == 2) {
        return Hand(group.cards, HandType.pair, power: group[0].powerRank);
      }
      else if (group.length >= 2) {
        return Hand(group.sublist(0, 2).cards, HandType.pair, power: group[0].powerRank);
      }
      else if (wildCards.isNotEmpty) {
        return Hand(group.cards + wildCards.sublist(0, 1), HandType.pair, power: group[0].powerRank);
      }
    }
  }

  for (var group in grouped) {
    if (group.length == 2) {
      return Hand(group.sublist(0, 2).cards, HandType.pair, power: group[0].powerRank);
    }
  }

  for (var group in grouped) {
    if (group.length >= 2) {
      return Hand(group.sublist(0, 2).cards, HandType.pair, power: group[0].powerRank);
    }
  }

  if (wildCards.isNotEmpty) {
    for (var group in grouped) {
      if (group.length == 1) {
        return Hand(group.cards + wildCards.sublist(0, 1), HandType.pair, power: group[0].powerRank);
      }
    }
  }


  return null;
}

// ---------------------------------------------------------------------------
// canBeatXXX — parallel the findXXX methods above.
//
// Each function answers: "from [cards], can the player form a hand of the
// given type whose power exceeds [targetPower]?"
//
// Wild cards are handled correctly because every function delegates to the
// corresponding findXXX method (which already manages wild-card accounting)
// and simply tests whether any returned hand beats the target.
// ---------------------------------------------------------------------------

/// Whether [cards] can form a single whose power exceeds [targetPower].
bool canBeatSingle(PokerCardList cards, int targetPower, CardRank levelRank) {
  if (cards.isEmpty) return false;
  for (final c in cards) {
    if (c.powerRank > targetPower) return true;
  }
  return false;
}

/// Whether [cards] can form a pair whose power exceeds [targetPower].
bool canBeatPair(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findPairs(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a triple whose power exceeds [targetPower].
bool canBeatTriple(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findTriples(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a full house whose triple power exceeds
/// [targetPower].
bool canBeatFullHouse(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findFullHouses(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a straight whose start-rank exceeds
/// [targetPower].
bool canBeatStraight(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findStraights(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a tube whose start-rank exceeds [targetPower].
bool canBeatTube(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findTubes(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a plate whose start-rank exceeds [targetPower].
bool canBeatPlate(PokerCardList cards, int targetPower, CardRank levelRank) {
  final hands = findPlates(cards, levelRank, targetPower: targetPower);
  return hands.isNotEmpty;
}

/// Whether [cards] can form a bomb whose power exceeds [targetPower].
bool canBeatBomb(PokerCardList cards, int targetPower, CardRank levelRank,
    {int deckCount = 2}) {
  final hands = findBombs(cards, levelRank,
      includeStraightFlush: true, deckCount: deckCount, targetPower: targetPower);
  return hands.isNotEmpty;
}


/// Whether a player holding [cards] can legally play against [targetHand].
///
/// Returns `true` if at least one valid Guandan hand can be formed from
/// [cards] that beats [targetHand] according to the rules (same type +
/// higher power, OR any bomb vs non-bomb, OR higher bomb vs bomb).
///
/// If [targetHand] is empty the query asks "can the player lead?" — always
/// true when [cards] is non-empty.
///
bool canPlayerBeat(PokerCardList cards, Hand targetHand, CardRank levelRank,
    {int deckCount = 2}) {
  if (cards.isEmpty) return false;

  // Leading — can always play the lowest single.
  if (targetHand.isEmpty) return true;

  // Any bomb beats a non-bomb.  This check is independent of the
  // type-match check below — the two branches are OR'd, so wild cards
  // are not required to serve both simultaneously.
  if (!targetHand.isBomb) {
    if (canBeatBomb(cards, targetHand.power, levelRank,
        deckCount: deckCount)) {
      return true;
    }
  }

  // Try to match the target type with higher power.
  switch (targetHand.type) {
    case HandType.single:
      return canBeatSingle(cards, targetHand.power, levelRank);
    case HandType.pair:
      return canBeatPair(cards, targetHand.power, levelRank);
    case HandType.triple:
      return canBeatTriple(cards, targetHand.power, levelRank);
    case HandType.fullHouse:
      return canBeatFullHouse(cards, targetHand.power, levelRank);
    case HandType.straight:
      return canBeatStraight(cards, targetHand.power, levelRank);
    case HandType.tube:
      return canBeatTube(cards, targetHand.power, levelRank);
    case HandType.plate:
      return canBeatPlate(cards, targetHand.power, levelRank);
    case HandType.bomb:
      return canBeatBomb(cards, targetHand.power, levelRank,
          deckCount: deckCount);
    default:
      return false;
  }
}

