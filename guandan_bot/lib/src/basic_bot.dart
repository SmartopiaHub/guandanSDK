import 'package:guandan_core/guandan_core.dart';

import 'bot.dart';

class BasicBot extends BotPlayer {
  BasicBot(super.id, super.seat, super.team, this.deckCount, {super.displayName, super.botCode, super.cardsOnHand});

  BasicBot.copy(super.player, this.deckCount, {super.newId}): super.copy();

  BasicBot.deepCopy(super.player, this.deckCount, {super.newId, super.withCardsOnHand, super.withPlayedCards}): 
    super.deepCopy();

  final int deckCount;

  static const String basicBotCode = 'BasicBot';

  @override
  String get botCode => basicBotCode;

  @override
  PokerCard tribute() {
    cardsOnHand!.sortByPowerRank();
    for (var card in cardsOnHand!.cards.reversed) {
      if (!card.isWildCard) {
        return card;
      }
    }
    throw Exception('No non-wild card to tribute');
  }

  @override
  Map<String, dynamic> toJson({bool withCardsOnHand = true, bool withPlayedCards = true, bool withPlayerType = false}) {
    var json = super.toJson(withCardsOnHand: withCardsOnHand, withPlayedCards: withPlayedCards, withPlayerType: withPlayerType);
    json['player_type'] = 'BasicBot';
    return json;
  }

  factory BasicBot.fromJson(Map<String, dynamic> jsonData, int deckCount) {
    var player = BasicBot(Player.readId(jsonData), Player.readSeat(jsonData), Player.readTeam(jsonData), deckCount, displayName: Player.readDisplayName(jsonData), botCode: Player.readBotCode(jsonData), cardsOnHand: Player.readCardsOnHand(jsonData));
    player.playedCards = Player.readPlayedCards(jsonData);
    return player;
  }

  @override
  PokerCard returnCard() {
    cardsOnHand!.sortByPowerRank();
    return cardsOnHand!.cards.first;
  }

  @override
  Hand getCardsToPlay(Hand handOnTable, CardRank levelRank) {

    if (hasAtLeastOneCard){
      var hand = _randomPlay(handOnTable, levelRank);
      if (hand.isNotEmpty) {
        return hand;
      }
      if (handOnTable.isNotEmpty) {
        return Hand.pass();
      }
    }

    throw Exception('AI has no cards to play');
  }

  Hand _randomPlay(Hand handOnTable, CardRank levelRank) {
    var handFinders = {
      HandType.plate: findPlates,
      HandType.tube: findTubes,
      HandType.fullHouse: findFullHouses,
      HandType.straight: findStraights,
      HandType.triple: findTriples,
      HandType.pair: findPairs,
      HandType.single: findSingles,
      //HandType.bomb: findBombs
    };

    if(handOnTable.isNotEmpty){
      handOnTable = deduceHandType(handOnTable, deckCount: deckCount);
      // ignore: collection_methods_unrelated_type
      if (handFinders.containsKey(handOnTable.type)) {
        // ignore: collection_methods_unrelated_type
        var find = handFinders[handOnTable.type]!;
        var handList = find(cardsOnHand!, levelRank, findAll: true);
        for (var hand in handList) {
          if (canPlay(hand, handOnTable, deckCount: deckCount)) {
            return hand;
          }
        }
      }
    }
    else
    {
      var finders = handFinders.values.toList();
      finders.shuffle();
      for (var finder in finders) {
        var handList = finder(cardsOnHand!, levelRank);
        for (var hand in handList) {
          if (canPlay(hand, handOnTable, deckCount: deckCount)) {
            return hand;
          }
        }
      }
    }
    return Hand.pass();
  }
}