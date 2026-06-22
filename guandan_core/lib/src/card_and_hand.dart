
import 'dart:collection';

import 'package:guandan_core/src/utility.dart';

/// Represents the color of a poker card suit.
enum CardSuitColor {
  black,
  red,
}

/// Represent the suit of a poker card.
///
/// It defines the possible suits for a poker card, including:
/// - [hearts]: Represented by the symbol ♥
/// - [diamonds]: Represented by the symbol ♦
/// - [clubs]: Represented by the symbol ♣
/// - [spades]: Represented by the symbol ♠
/// - [black]: Used for the black joker
/// - [red]: Used for the red joker
enum CardSuit {
  diamonds,
  clubs,
  hearts,
  spades,
  black, // for black joker
  red; // for red joker

  static const List<CardSuit> nonJokerSuits = [CardSuit.diamonds, CardSuit.clubs, CardSuit.hearts, CardSuit.spades];

  String get asCharacter => switch (this) {
        CardSuit.spades => '♠',
        CardSuit.hearts => '♥',
        CardSuit.diamonds => '♦',
        CardSuit.clubs => '♣',
        CardSuit.black => 'Joker',
        CardSuit.red => 'Joker'
      };

  CardSuitColor get color => switch (this) {
        CardSuit.spades || CardSuit.clubs || CardSuit.black => CardSuitColor.black,
        CardSuit.hearts || CardSuit.diamonds || CardSuit.red => CardSuitColor.red
      };
}





/// Represent the rank of a poker card.
/// 
/// It contains the following properties:
/// - [name]: A `String` representing the name associated with the rank.
/// - [value]: An `int` representing the value associated with the rank.
/// 
/// The value corresponds to the rank of the card:
/// - 2-10: Numeric cards
/// - 11: Jack
/// - 12: Queen
/// - 13: King
/// - 14: Ace
/// - 15: Level card
/// - 16: Black joker
/// - 17: Red joker
/// 
/// The name corresponds to the string representation of the rank:
/// - '2'-'9': Numeric cards
/// - 'T': 10
/// - 'J': Jack
/// - 'Q': Queen
/// - 'K': King
/// - 'A': Ace
/// - 'BJ': Black joker
/// - 'RJ': Red joker
/// 
class CardRank {
  final int value;
  final String name;

  CardRank.internal(this.value, this.name);

  /// Creates a [CardRank] instance with the given [name].
  CardRank(this.name) : value = valueOfRank(name);

  /// Creates a [CardRank] instance with the given [value] and [name].
  /// 
  /// 1 is treated as 14 (Ace) for the value.
  CardRank.fromValue(int rankValue)
      : this.internal(
          rankValue == 1 ? 14 : rankValue,
          values.firstWhere((rank) => rank.value == (rankValue == 1 ? 14 : rankValue)).name,
        );

  /// The value of the level card
  static const int rankValueOfLevelCard = 15;

  /// Predefined ranks
  static final CardRank redJoker = CardRank('RJ');
  static final CardRank blackJoker = CardRank('BJ');
  static final CardRank A = CardRank('A');
  static final CardRank K = CardRank('K');
  static final CardRank Q = CardRank('Q');
  static final CardRank J = CardRank('J');
  static final CardRank T = CardRank('T');
  static final CardRank two = CardRank('2');
  static final CardRank three = CardRank('3');
  static final CardRank four = CardRank('4');
  static final CardRank five = CardRank('5');
  static final CardRank six = CardRank('6');
  static final CardRank seven = CardRank('7');
  static final CardRank eight = CardRank('8');
  static final CardRank nine = CardRank('9');

  /// Returns the display name of the rank.
  /// 
  /// - `T` is converted `10`.
  /// - `BJ` and `RJ` are converted to `Joker`.
  /// - other ranks are returned as their [name].
  String get displayName {
    if (isNameOfJoker(name)) {
      return 'Joker';
    }
    if (name == 'T') {
      return '10';
    }
    return name;
  }

  bool get isJoker {
    return isNameOfJoker(name);
  }

  bool get isBlackJoker {
    return name == blackJoker.name;
  }

  bool get isRedJoker {
    return name == redJoker.name;
  }


  /// Returns `true` if the given [name] is a joker (black or red).
  static bool isNameOfJoker(String name) {
    return name == redJoker.name || name == blackJoker.name;
  }

  /// Returns the value of the rank with the given [name].
  static int valueOfRank(String name) {
    var i = CardRank.values.indexWhere((rank) => rank.name == name);
    if (i == -1) {
      throw Exception('Invalid rank name.');
    }
    return CardRank.values[i].value;
  }


  /// The list of predefined ranks
  static final List<CardRank> values = [
    CardRank.internal(2, '2'),
    CardRank.internal(3, '3'),
    CardRank.internal(4, '4'),
    CardRank.internal(5, '5'),
    CardRank.internal(6, '6'),
    CardRank.internal(7, '7'),
    CardRank.internal(8, '8'),
    CardRank.internal(9, '9'),
    CardRank.internal(10, 'T'), // 10 is represented by 'T'
    CardRank.internal(11, 'J'),
    CardRank.internal(12, 'Q'),
    CardRank.internal(13, 'K'),
    CardRank.internal(14, 'A'),
    // 15 is reserved for the level card
    CardRank.internal(16, 'BJ'),
    CardRank.internal(17, 'RJ')
  ];


  /// Two ranks are equal if the same value and name
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    if (other is! CardRank) return false;
    return value == other.value && name == other.name;
  }

  @override
  int get hashCode => value.hashCode ^ name.hashCode;
}

/// A class representing a poker card with a suit and a rank.
///
/// This class encapsulates the properties of a standard poker card,
/// including its suit (e.g., hearts, diamonds, clubs, spades) and its rank
/// (e.g., 2-10, Jack, Queen, King, Ace).
///
class PokerCard {

  /// The rank of the card.
  final CardRank rank;

  /// The suit of the card.
  final CardSuit suit;

  /// Whether this card is a level card.
  final bool isLevelCard;

  /// Creates a [PokerCard] with the given [rank], [suit], and [isLevelCard] status.
  PokerCard(this.rank, this.suit, this.isLevelCard);

  /// Creates a [PokerCard] instance from a string representation of the card.
  /// 
  /// Supported formats: 
  ///    for jokers: 'BJ' (black joker) or 'RJ' (red joker)
  ///    for other cards: rank.name + first letter of suit (upper case) + '*' (for level cards)
  /// 
  /// Examples:
  /// - '2H': 2 of hearts
  /// - '3D': 3 of diamonds
  /// - '4C*': 4 of clubs and '4' is the level rank
  /// - '5S*': 5 of spades and '5' is the level rank
  /// - 'TH': 10 of hearts
  /// - 'BJ': Black joker
  /// - 'RJ': Red joker
  PokerCard.from(String cardString)
      : rank = cardString[0] == 'R' ? CardRank.redJoker : (cardString[0]=='B' ? CardRank.blackJoker : CardRank(cardString[0])),
        suit = cardString[0] == 'R' ? CardSuit.red : 
            (cardString[0]=='B' ? CardSuit.black :  
                CardSuit.values.firstWhere((s) => s.toString().split('.').last.toUpperCase()[0] == cardString[1])),
        isLevelCard = cardString.endsWith('*');

  /// Returns `true` if the card is a black or red joker.
  bool get isJoker {
    return rank.value == 16 || rank.value == 17;
  }

  /// Returns `true` if the card is a red joker.
  bool get isRedJoker {
    return rank.value == 17;
  }

  /// Returns `true` if the card is a black joker.
  bool get isBlackJoker {
    return rank.value == 16;
  }

  /// Returns `ture` if the card is a wild card.
  bool get isWildCard {
    return isLevelCard && suit == CardSuit.hearts;
  }

  /// Creates a wild card with the given [level].
  factory PokerCard.wildCard(CardRank level) {
    return PokerCard(level, CardSuit.hearts, true);
  }


  /// Returns the power rank of the card, where level cards are treated as 15.
  /// 
  /// The power rank is used for comparing the cards (taking level rank into account).
  int get powerRank {
    return isLevelCard ? 15 : rank.value;
  }

  /// Returns the natural rank order of the card (without considering the level rank).
  int get naturalRank {
    return rank.value;
  }

  /// Returns the sort index of the card.
  /// 
  /// The sort index is calculated based on the rank and suit of the card, without considering the level rank.
  int get naturalSortIndex {
    return naturalRank * 10 + suit.index;
  }

  /// Returns the sort index of the card, considering the level rank.
  int get powerSortIndex {
    return powerRank * 10 + suit.index;
  }

  /// Returns the string representation of the card. See [PokerCard.from] for supported formats.
  @override
  String toString() {
    if (isJoker) {
      return rank.name;
    }
    return '${rank.name}${suit.toString().split('.').last.toUpperCase()[0]}${isLevelCard ? "*" : ""}';
  }

  /// Two cards are equal if they have the same rank, suit, and level card status
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    if (other is! PokerCard) return false;
    return rank.value == other.rank.value && suit == other.suit && isLevelCard == other.isLevelCard;
  }

  @override
  int get hashCode => rank.value.hashCode ^ suit.hashCode ^ isLevelCard.hashCode;

  /// compare two cards by their power rank
  bool operator > (PokerCard other) {
    return powerRank > other.powerRank;
  }

  /// compare two cards by their power rank
  bool operator < (PokerCard other) {
    return powerRank < other.powerRank;
  }


  /// Predefined black joker
  static final PokerCard blackJoker = PokerCard(CardRank.blackJoker, CardSuit.black, false);

  /// Predefined red joker
  static final PokerCard redJoker = PokerCard(CardRank.redJoker, CardSuit.red, false);  
}


/// An enumeration representing the type of a hand.
enum HandType {
  single, /// 单张
  pair, /// 对子
  triple, /// 三不带
  fullHouse, /// 三带一对
  straight, /// 顺子
  tube, /// 三连对、木板
  plate, /// 钢板
  //straightFlush, /// 同花顺
  bomb, /// 炸弹
  empty, /// 空手牌, 不出
  invalid, /// 无效牌型
  unknown; /// 未知牌型

  static const List<HandType> validTypes = [
    single,
    pair,
    triple,
    fullHouse,
    straight,
    tube,
    plate,
    bomb,
  ];

  static const List<HandType> validNonBombTypes = [
    single,
    pair,
    triple,
    fullHouse,
    straight,
    tube,
    plate,
  ];

  bool get isUnknownOrInvalid {
    return this == HandType.unknown || this == HandType.invalid;
  }

  int? get numberOfCards {
    switch (this) {
      case HandType.single:
        return 1;
      case HandType.pair:
        return 2;
      case HandType.triple:
        return 3;
      case HandType.fullHouse:
      case HandType.straight:
        return 5;
      case HandType.tube:
      case HandType.plate:
        return 6;
      default:
        return null;
    }
  }
}


/// Interface for a read-only list of poker cards.
///
/// Implemented by [PokerCardList] and [Hand] to provide a common contract
/// for accessing the card collection and its size.
abstract class IPokerCardList {
  /// The list of poker cards.
  List<PokerCard> get cards;
  /// The number of cards currently in the list.
  int get length;
}


/// Implement the [IPokerCardList] interface
class PokerCardList extends IPokerCardList with Iterable<PokerCard>  {
  
  List<PokerCard> _cards = [];

  @override
  List<PokerCard> get cards{
    return UnmodifiableListView(_cards);
  }


  /// Creates a [PokerCardList] instance with the given list of [PokerCard].
  /// 
  /// The cards are shallowly copied from the given list.
  PokerCardList(Iterable<PokerCard> cardList){
    _cards = List.from(cardList);
  }


  /// Creates a [PokerCardList] instance from some [PokerCard]s.
  /// 
  /// The cards are shallowly copied from the given list.
  PokerCardList.from(Iterable<PokerCard> cards){
    _cards = List.from(cards);
  }


  /// Creates an empty [PokerCardList] instance.
  PokerCardList.empty();


  /// Creates a [PokerCardList] instance from a string representation of the cards or a hand.
  /// 
  /// See [cardListFromString] for supported formats.
  PokerCardList.fromString(String handString): _cards = cardListFromString(handString);


  /// Creates a deck according to [requiredPlayers] and the [levelRank].
  /// 
  /// [requiredPlayers]/2 standard decks will be returned, where a standard deck of 54 poker cards consists of:
  /// - 2-10, J, Q, K, A of hearts, diamonds, clubs, and spades
  /// - two black jokers
  /// - two red jokers
  static PokerCardList createDeck(CardRank levelRank, {int requiredPlayers = 4, bool shuffle = true}) {
    List<PokerCard> deck = [];
    int n = (requiredPlayers / 2).round();
    for (var i = 0; i < n; i++) {
      for (var suit in CardSuit.values) {
        if (suit == CardSuit.black || suit == CardSuit.red) continue; // Skip jokers for now
        for (var rank in CardRank.values) {
          if (rank == CardRank.blackJoker || rank == CardRank.redJoker) continue; // Skip jokers for now
          deck.add(PokerCard(rank, suit, rank==levelRank));
        }
      }
      // Add 2 jokers
      deck.add(PokerCard.blackJoker);
      deck.add(PokerCard.redJoker);
    }

    if (shuffle) {
      deck.shuffle();
    }
    
    return PokerCardList.from(deck);
  }    


  /// Construct a list of poker cards from a string representation of the cards.
  /// 
  /// The string should contain 
  ///   - the cards separated by spaces, or 
  ///   - type and power information followed by a colon (':') and then the cards separated by spaces.
  /// 
  /// Only the cards will be extracted and returned; the type and power information will be ignored if present.
  /// 
  /// An empty string will return an empty list.
  static List<PokerCard> cardListFromString(String cardsString) {
    List<PokerCard> cards = [];
    if (cardsString.isEmpty) {
      return cards;
    }
    if (cardsString.contains(':')) {
      cardsString = cardsString.split(':').last;
    }

    List<String> cardStrings = cardsString.split(' ');

    for (String card in cardStrings) {
      if (card.isEmpty) {
        continue;
      }
      cards.add(PokerCard.from(card));
    }
    return cards;
  }


  /// Add a new card to the list.
  void add(PokerCard newCard) {
    _cards.add(newCard);
  }

  /// Add multiple cards to the list.
  void addAll(Iterable<PokerCard> newCards) {
    _cards.addAll(newCards);
  }

  /// Clear the list of cards.
  void clear()
  {
    _cards.clear();
  }

  /// Remove the card at the specified index.
  void removeAt(int index){
    _cards.removeAt(index);
  }

  /// Inserts [card] at the given [index].
  void insert(int index, PokerCard card){
    _cards.insert(index, card);
  }

  /// Converts a list of [PokerCard]s to a space-separated string.
  static String cardListToString(List<PokerCard> cards) {
    return cards.map((card) => card.toString()).join(' ');
  }

  /// Returns the space-separated string representation of all cards.
  @override
  String toString() {
    return cardListToString(cards);
  }

  /// Whether this list contains no cards.
  @override
  bool get isEmpty {
    return cards.isEmpty;
  }

  /// Whether this list contains at least one card.
  @override
  bool get isNotEmpty {
    return cards.isNotEmpty;
  }

  /// Removes a single [card] from the list.
  void removeCard(PokerCard card) {
    removeCards([card]);
  }

  /// Returns a new [PokerCardList] containing the cards from both operands.
  PokerCardList operator + (PokerCardList other) {
    PokerCardList combinedCards = PokerCardList.from(this)..addAll(other.cards);
    return combinedCards;
  }

  /// Returns a new [PokerCardList] with the cards in [other] removed.
  PokerCardList operator - (PokerCardList other) {
    PokerCardList result = PokerCardList.from(this);
    result.removeCards(other.cards);
    return result;
  }

  /// Returns the card at the given [index].
  PokerCard operator [](int index) {
    return _cards[index];
  }

  /// Returns the number of cards in this list.
  @override
  int get length => _cards.length;

  /// Returns a sublist of the cards in this list, starting at [start] and ending at [end] (exclusive).
  /// If [end] is not provided, the sublist extends to the end of the list.
  /// Returns a sublist from [start] to [end] (exclusive).
  PokerCardList sublist(int start, [int? end]) {
    return PokerCardList.from(_cards.sublist(start, end));
  }

  /// Returns the index of the first card matching [test], or -1 if none match.
  int indexWhere(bool Function(PokerCard) test, [int start = 0]) {
    return _cards.indexWhere(test, start);
  }

  /// Returns the index of [card] in the list, or -1 if not found.
  int indexOf(PokerCard card, [int start = 0]) {
    return _cards.indexWhere((c) => c == card, start);
  }

  /// Returns a new [PokerCardList] containing only cards that satisfy [test].
  @override
  PokerCardList where(bool Function(PokerCard) test) {
    return PokerCardList.from(_cards.where(test).toList());
  }

  /// Returns the count of cards that satisfy [test].
  int count(bool Function(PokerCard) test){
    return _cards.where(test).length;
  }

  /// Subtracts [cards2] from [cards1] accounting for multiplicity.
  ///
  /// If two `3S` cards are in [cards1], two `3S` in [cards2] will be removed.
  /// When [inPlace] is `true`, [cards1] is mutated directly and returned.
  static List<PokerCard> subtractCards(List<PokerCard> cards1, List<PokerCard> cards2, {bool inPlace = false}) {
    List<PokerCard> ret = inPlace ? cards1 : List.from(cards1);
    for (PokerCard card in cards2) {
      int? i = ret.indexWhere((c) => c.powerSortIndex == card.powerSortIndex);
      if (i != -1) {
        ret.removeAt(i);
      } else {
        throw Exception('Card not found: $card');
      }
    }
    return ret;
  }

  /// Removes [cardsToRemove] from this list, accounting for multiplicity.
  void removeCards(List<PokerCard> cardsToRemove) {
    subtractCards(_cards, cardsToRemove, inPlace: true);
  }

  /// Returns `true` if this list contains [card].
  bool hasCard(PokerCard card) {
    return _cards.contains(card);
  }

  /// Returns `true` if this list contains all cards in [cardsToCheck],
  /// accounting for multiplicity (e.g., two `3S` required means two `3S` must exist).
  bool hasCards(List<PokerCard> cardsToCheck) {
    for (PokerCard card in cardsToCheck) {
      if (_cards.where((c) => c == card).length < cardsToCheck.where((c) => c == card).length) {
        return false;
      }
    }
    return true;
  }

  /// Returns cards in [cardsToCheck] that are missing from this list,
  /// accounting for multiplicity.
  List<PokerCard> findMissing(Iterable<PokerCard> cardsToCheck) {
    List<PokerCard> missing = [];
    Set<PokerCard> uniqueCardsToCheck = cardsToCheck.toSet();
    for (PokerCard card in uniqueCardsToCheck) {
      final countInThis = _cards.where((c) => c == card).length;
      final countInCheck = cardsToCheck.where((c) => c == card).length;
      if (countInThis < countInCheck) {
         missing.addAll(List.filled(countInCheck - countInThis, card));
      }
    }
    return missing;
  }

  /// Randomly shuffles the cards in place.
  void shuffle(){
    _cards.shuffle();
  }

  /// Sorts the cards in place by power rank (level rank aware).
  void sortByPowerRank(){
    _cards.sort((a, b) => a.powerRank.compareTo(b.powerRank));
  }

  /// Sorts the cards in place by natural rank (ignoring level rank).
  void sortByNaturalRank(){
    _cards.sort((a, b) => a.naturalSortIndex.compareTo(b.naturalSortIndex));
  }

  /// Two lists are equal if they contain the same cards (including multiplicity).
  @override
  bool operator == (Object other) {
    if (identical(this, other)) return true;
    if (other is! PokerCardList) return false;
    if (_cards.length != other.cards.length) return false;
    if (_cards.isEmpty) return true;
    return _cards.every((card) => countCards(this, card.rank, suit: card.suit) == countCards(other, card.rank, suit: card.suit));
  }

  @override
  int get hashCode {
    return _cards.fold(0, (prev, card) => prev ^ card.hashCode);
  }

  @override
  Iterator<PokerCard> get iterator => _cards.iterator;

  /// Removes and discards the last card in the list.
  void removeLast(){
    _cards.removeLast();
  }
}



/// A class representing a hand of poker cards, including the type of the hand and the power of the hand.
class Hand extends PokerCardList {


  /// The type of the hand.
  HandType type;

  /// The power of the hand, used for comparing hands (taking level rank into account).
  /// Invalid hands have a power of -1, but empty hands have a power of 0.
  int power; 


  /// Creates a [Hand] instance with the given list of [cards] and [type].
  Hand(super.cards, this.type, {this.power = -1});

  /// Creates an empty [Hand] instance with an empty list of cards and an empty type.
  Hand.emptyHand() : type = HandType.empty, power = 0, super([]);

  /// Creates an empty [Hand] instance representing a pass.
  Hand.pass() : type = HandType.empty, power = 0, super([]); // 不出

  /// Creates a [Hand] instance with an invalid type.
  Hand.invalidHand(super.cards) : type = HandType.invalid, power = -1;

  /// Creates a [Hand] instance with an unknown type.
  Hand.unknownHand(super.cards) : type = HandType.unknown, power = -1;


  /// Extract the type of the hand from a string representation of the hand.
  static HandType extractHandType(String handString) {
    if (handString.isEmpty || !handString.contains(':')) {
      return HandType.unknown;
    }
    var typeAndPower = handString.split(':').first;
    var typeString = typeAndPower.contains('-') ? typeAndPower.split('-').first : typeAndPower;
    return HandType.values.firstWhere((type) => type.toString().split('.').last == typeString.trim());
  }

  /// Extract the list of cards from a string representation of the hand.
  static List<PokerCard> extractCardList(String handString) {
    if (handString.isEmpty) {
      return [];
    }
    if (!handString.contains(':')) {
      return PokerCardList.cardListFromString(handString);
    }
    else{
      return PokerCardList.cardListFromString(handString.split(':').last);
    }
  }

  /// Extract the power of the hand from a string representation of the hand.
  static int extractPower(String handString) {
    if (handString.isEmpty || !handString.contains(':')) {
      return -1;
    }
    var typeAndPower = handString.split(':').first;
    var handType = extractHandType(handString);
    if (handType.isUnknownOrInvalid) {
      return -1;
    }
    var powerString = typeAndPower.split('-').last;
    return int.tryParse(powerString) ?? -1;
  }

  /// Creates a [Hand] instance from a string representation of the hand.
  Hand.fromString(String handString)
      : type = extractHandType(handString),
        power = extractPower(handString),
        super(extractCardList(handString));

  /// Creates a [Hand] from a JSON map with `cards`, `type`, and `power` keys.
  factory Hand.fromJson(Map<String, dynamic> json) {
    return Hand(
      PokerCardList.cardListFromString(json['cards'] as String),
      HandType.values.firstWhere((type) => type.toString().split('.').last == json['type']),
      power: json['power'] as int,
    );
  }

  /// Serializes the hand to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'cards': PokerCardList.cardListToString(cards),
      'type': type.toString().split('.').last,
      'power': power,
    };
  }

  /// The string representation of the hand, including the type, power and the cards.
  /// If the hand is invalid or unknown, the power may not be included.
  /// Example: 'single-3 : 3H'
  /// Example: 'pair-4 : 4H 3H*'
  /// Example: 'invalid : 5H 5D 5C 4D'
  /// Example: 'unknown : 5H 5D 5C 4D'
  @override
  String toString() {
    if (type.isUnknownOrInvalid) {
      return '${type.toString().split('.').last} : ${cards.join(' ')}';
    }
    return '${type.toString().split('.').last}-$power : ${cards.join(' ')}';
  }  

  /// Compare the power of two hands of same types, return `true` if this hand has higher power.
  /// 
  /// If the hands are of different types or one of them is invalid, an exception will be thrown.
  bool operator > (Hand other) {
    if (type.isUnknownOrInvalid || other.type.isUnknownOrInvalid) {
      throw Exception('不能比较未知或不合规牌型。');
    }
    if (type == other.type) {
      return power > other.power;
    }
    throw Exception('不能比较不同类型的牌型。');
  }

  bool operator < (Hand other) {
    return other > this;
  }

  /// Two hands are equal if they have the same list of cards, accounting for multiplicity and level cards.
  @override
  bool operator == (Object other) {
    if (identical(this, other)) return true;
    if (other is! Hand) return false;
    if (cards.length != other.cards.length) return false;
    if (cards.isEmpty) return true;
    return cards.every((card) => countCards(this, card.rank, suit: card.suit) == countCards(other, card.rank, suit: card.suit));
  }

  @override
  int get hashCode {
    return cards.fold(0, (prev, card) => prev ^ card.hashCode);
  }

  /// Whether this hand is a bomb.
  bool get isBomb => type == HandType.bomb;
  /// Whether this hand is a straight.
  bool get isStraight => type == HandType.straight;
  /// Whether this hand is a tube (三连对/木板).
  bool get isTube => type == HandType.tube;
  /// Whether this hand is a plate (钢板).
  bool get isPlate => type == HandType.plate;
  /// Whether this hand is a full house (三带一对).
  bool get isFullHouse => type == HandType.fullHouse;
  /// Whether this hand is a triple (三不带).
  bool get isTriple => type == HandType.triple;
  /// Whether this hand is a pair.
  bool get isPair => type == HandType.pair;
  /// Whether this hand is a single card.
  bool get isSingle => type == HandType.single;

  /// Sort the cards in the hand according to the hand type and power, and taking the wild cards (if any) into account.
  Hand sort(){
    _cards = orderHandCards(_cards, type, power);
    return this;
  }
}


/// Returns `true` if [tributeCard] is a valid tribute given [cardsOnHand].
///
/// A red joker is always valid. A wild card is never valid as a tribute.
/// Otherwise, all non-wild cards on hand must have a power rank ≤ the tribute
/// card's power rank (i.e., the tribute card must be one of the highest cards).
bool isValidTributeCard(PokerCard tributeCard, PokerCardList cardsOnHand){
  if (tributeCard.isRedJoker) {
    return true;
  }
  if (tributeCard.isWildCard){
    return false;
  }

  return cardsOnHand.cards.every((card) => card.isWildCard || card.powerRank <= tributeCard.powerRank);
}


/// Returns `true` if [returnCard] is a valid return (回贡) given [cardsOnHand].
///
/// A return card is valid if all cards on hand have power rank ≥ the return
/// card's power rank, or the return card's power rank is ≤ 10.
bool isValidReturnCard(PokerCard returnCard, PokerCardList cardsOnHand){
  if (cardsOnHand.cards.every((card) => card.powerRank >= returnCard.powerRank)) {
    return true;
  }
  return returnCard.powerRank <= 10;
}


/// Groups [cards] by their [CardRank], returning a map from rank to card list.
Map<CardRank, PokerCardList> groupCards(Iterable<PokerCard> cards) {
    Map<CardRank, PokerCardList> group = {};
    for (var card in cards) {
      if (group.containsKey(card.rank)) {
        group[card.rank]!.add(card);
      } else {
        group[card.rank] = PokerCardList.from([card]);
      }
    }
    return group;
}


int _powerAndSuitComparator(PokerCard a, PokerCard b){
  if (a.powerRank == b.powerRank){
    return a.suit.index - b.suit.index;
  }
  return a.powerRank - b.powerRank;
}

/// Returns a new list of [cards] sorted by power rank.
///
/// When [sortSuit] is `true`, cards of equal power rank are further ordered by suit.
List<PokerCard> sortByPowerRank(Iterable<PokerCard> cards, {bool sortSuit = false}){
  var newCards = List<PokerCard>.from(cards);
  if (!sortSuit) {
    newCards.sort((a, b) => a.powerRank.compareTo(b.powerRank));
  }
  else{
    newCards.sort(_powerAndSuitComparator);
  }
  return newCards;
}

/// Sort a hand of cards given the hand type and power.
/// 
/// This method place wild cards (if any) in the correct position accordingly.
List<PokerCard> orderHandCards(Iterable<PokerCard> cards, HandType type, int power){
    List<PokerCard> sortStraight(){
      var newCards = <PokerCard>[];
      List<PokerCard> wildCards = cards.where((card) => card.isWildCard).toList();
      List<PokerCard> nonWildCards = cards.where((card) => !card.isWildCard).toList();
      var s = checkStraight(cards).seriesStartRankValue!;
      for(var startRankValue = s; startRankValue < s + 5; startRankValue++){
        var rv = startRankValue == 1 ? CardRank.A.value : startRankValue;
        var index = nonWildCards.indexWhere((card) => card.rank.value == rv);
        if (index != -1){
          newCards.add(nonWildCards[index]);
        }
        else{
          newCards.add(wildCards.removeAt(0));
        }
      }
      return newCards;
    }
  
    switch(type){
      case HandType.single:
      case HandType.pair:
      case HandType.triple:
      case HandType.bomb:
        if (checkStraightFlush(cards).valid){
          return sortStraight();
        }
        else{
          return sortByPowerRank(cards, sortSuit: true);
        }
      case HandType.straight:
        return sortStraight();
      case HandType.tube:
      case HandType.plate:
        var newCards = <PokerCard>[];
        var wildCards = cards.where((card) => card.isWildCard).toList();
        var nonWildCards = cards.where((card) => !card.isWildCard).toList();
        var grouped = groupCards(nonWildCards).values.toList();
        var s = type == HandType.tube ? 3 : 2;
        var n = s == 3 ? 2 : 3;
        for(var startRankValue = power; startRankValue < power + s; startRankValue++){
          var rv = startRankValue == 1 ? CardRank.A.value : startRankValue;
          var index = grouped.indexWhere((group) => group[0].rank.value == rv);
          int w = 0;
          if (index != -1){
            newCards.addAll(sortByPowerRank(grouped[index], sortSuit: true));
            if (grouped[index].length != n){
              newCards.addAll(wildCards.sublist(w, w + n-grouped[index].length));
              w += n-grouped[index].length;
            }
          }
          else{
            newCards.addAll(wildCards.sublist(w, w+n));
            w += n;
          }
        }
        return newCards;
      case HandType.fullHouse:
        var wildCards = cards.where((card) => card.isWildCard).toList();
        var nonWildCards = cards.where((card) => !card.isWildCard).toList();
        if (wildCards.isEmpty){
          var grouped = groupCards(nonWildCards).values.toList();
          var pair = sortByPowerRank(grouped.firstWhere((group) => group.length == 2), sortSuit: true);
          var triple = sortByPowerRank(grouped.firstWhere((group) => group.length == 3), sortSuit: true);
          return pair + triple;
        }
        else{
          var grouped = groupCards(nonWildCards).values.toList();
          var newCards = <PokerCard>[];
          int w = 0;
          var g = grouped.firstWhere((group) => group[0].powerRank == power);
          newCards.addAll(sortByPowerRank(g, sortSuit: true));
          if (g.length != 3){
            newCards.addAll(wildCards.sublist(w, w+3-g.length));
            w += 3-g.length;
          }
          g = grouped.firstWhere((group) => group[0].powerRank != power);
          newCards.addAll(sortByPowerRank(g, sortSuit: true));
          if (g.length != 2){
            newCards.addAll(wildCards.sublist(w, w+2-g.length));
            w += 2-g.length;
          }
          return newCards.reversed.toList();
        }
      default:
        break;
    }
  return List<PokerCard>.from(cards);
}