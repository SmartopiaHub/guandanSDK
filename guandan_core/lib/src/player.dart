
import 'dart:core';

import 'package:guandan_core/guandan_core.dart';

/// Teams in the game
enum PlayerTeam { 
  redTeam, 
  blueTeam;

  static PlayerTeam fromName(String name) {
    return PlayerTeam.values.firstWhere((e) => e.toString().split('.').last == name);
  }
}

/// Positions of the players in the game, relative to a player (anchor player)
enum PlayerPosition { 
  self, // the current player
  leftOpponent, // for 4 and 6 players
  teamMate, // for 4 players only
  rightOpponent, // for 4 and 6 players
  oppositeOpponent, // for 6 players only
  leftTeamMate, // for 6 players only
  rightTeamMate; // for 6 players only

  int get value {
    switch (this) {
      case PlayerPosition.self:
        return 0;
      case PlayerPosition.leftOpponent:
        return 3;
      case PlayerPosition.teamMate:
        return 2;
      case PlayerPosition.rightOpponent:
        return 1;
      case PlayerPosition.oppositeOpponent:
        return 4;
      case PlayerPosition.leftTeamMate:
        return 4;
      case PlayerPosition.rightTeamMate:
        return 2;
    }
  }
 }


/// A class representing a player in the game
/// 
/// A player has a unique id, a seat in the game, a team, a name, a hand of cards, a hand of played cards, and a list of hands left to play.
/// 
class Player {

  /// The id of the player
  final String id;

  /// The seat of the player, assigned by the server (optionally in response to a seat change request), between 1-4 or 1-6
  int seat;

  /// The team of the player
  PlayerTeam team;

  /// The display name of the player, for UI purposes only.
  ///
  /// Falls back to [id] when not set.
  String? displayName;

  /// The bot model if this is an AI player, or null if human.
  ///
  /// Examples: `'basicBot'`, `'strongBot'`, `'providerId-botCode-version'`.
  String? botCode;

  /// The display name, falling back to [id].
  String get name => displayName ?? id;

  /// Whether this player is a human (botCode is null).
  bool get isHumanPlayer => botCode == null;

  /// Whether this player is an AI (botCode is not null).
  bool get isAIPlayer => !isHumanPlayer;

  // The cards on hand, to be dynamically updated as the player plays cards in each round
  PokerCardList? _cardsOnHand;

  /// The cards played by the player, to be dynamically updated as the player plays cards in each round
  PokerCardList playedCards = Hand.emptyHand();

  /// Create a player from a json representation based on the 'is_human' and 'bot_model' fields
  /// If the player is human, it is created as a [HumanPlayer], otherwise, it is created as an AIPlayer
  /// If the bot_model is 'basicBot', it is created as a [BasicBot], otherwise, it is created using the factory function registered with the bot_model
  /// If no factory is registered with the bot_model, it is created as a [BasicBot]
  factory Player.fromJson(Map<String, dynamic> jsonData,) {
    var p = Player(
      Player.readId(jsonData),
      Player.readSeat(jsonData),
      Player.readTeam(jsonData),
      displayName: Player.readDisplayName(jsonData),
      botCode: Player.readBotCode(jsonData),
      cardsOnHand: Player.readCardsOnHand(jsonData),
    );
    p.playedCards = Player.readPlayedCards(jsonData);
    return p;
  }

  Player.deepCopy(Player player, {String? newId, bool withPlayedCards = true, bool withCardsOnHand = true})
      : id = newId ?? player.id,
        seat = player.seat,
        team = player.team,
        displayName = player.displayName,
        botCode = player.botCode,
        _cardsOnHand = withCardsOnHand && player._cardsOnHand != null ? PokerCardList.from(player._cardsOnHand!) : null,
        playedCards = withPlayedCards ? PokerCardList.from(player.playedCards) : PokerCardList.empty();

  /// Create a player from another player
  Player.copy(Player player, {String? newId})
      : id = newId ?? player.id,
        seat = player.seat,
        team = player.team,
        displayName = player.displayName,
        botCode = player.botCode,
        _cardsOnHand = player._cardsOnHand,
        playedCards = player.playedCards;

  /// Create a player with the given id, seat, team, and optional fields.
  ///
  /// [displayName] is for UI display only; defaults to null (falling back to [id] via [name]).
  /// [botCode] identifies bots; null means human player.
  Player(this.id, this.seat, this.team, {this.displayName, this.botCode, PokerCardList? cardsOnHand})
      : _cardsOnHand = cardsOnHand;

  /// The json representation of the player
  ///
  /// If [withCardsOnHand] is true, the cards on hand are included in the json representation.
  /// If [withPlayedCards] is true, the played cards are included in the json representation.
  /// If [withPlayerType] is true, additional player type information (bot model and human status) is included.
  Map<String, dynamic> toJson({bool withCardsOnHand = true, bool withPlayedCards = true, bool withPlayerType = false}) {
    Map<String, dynamic> J = {
      'player_id': id,
      'seat': seat,
      'team': team.toString().split('.').last,
    };
    if (displayName != null) {
      J['display_name'] = displayName;
    }
    if (botCode != null) {
      J['bot_model'] = botCode;
    }
    if (withPlayerType) {
      J['is_human'] = isHumanPlayer;
      if (botCode != null) {
        J['bot_model'] = botCode;
      }
    }
    if (withPlayedCards) {
      J['played_cards'] = playedCards.toString();
    }
    if (withCardsOnHand) {
      if (_cardsOnHand != null) {
        J['cards_on_hand'] = _cardsOnHand!.toString();
      }
    }
    return J;
  }

  static String readId(Map<String, dynamic> jsonData) {
    return jsonData['player_id'] as String;
  }

  static int readSeat(Map<String, dynamic> jsonData) {
    return jsonData['seat'] as int;
  }

  /// Reads the display name from JSON. Falls back to the old `profile.nickname`
  /// for backward compatibility with serialized game snapshots.
  static String? readDisplayName(Map<String, dynamic> jsonData) {
    if (jsonData.containsKey('display_name')) {
      return jsonData['display_name'] as String?;
    }
    // Backward compat: read from old `profile` map.
    if (jsonData.containsKey('profile') && jsonData['profile'] != null) {
      final profile = jsonData['profile'] as Map<String, dynamic>;
      return profile['nickname'] as String?;
    }
    return null;
  }

  /// Reads the bot model from JSON. Falls back to the old `profile.bot_model`
  /// for backward compatibility with serialized game snapshots.
  static String? readBotCode(Map<String, dynamic> jsonData) {
    if (jsonData.containsKey('bot_model')) {
      return jsonData['bot_model'] as String?;
    }
    // Backward compat: read from old `profile` map.
    if (jsonData.containsKey('profile') && jsonData['profile'] != null) {
      final profile = jsonData['profile'] as Map<String, dynamic>;
      if (profile.containsKey('bot_model')) {
        return profile['bot_model'] as String?;
      }
    }
    // Backward compat: explicit is_human field.
    if (jsonData.containsKey('is_human')) {
      return jsonData['is_human'] == false ? 'basicBot' : null;
    }
    return null;
  }

  static PlayerTeam readTeam(Map<String, dynamic> jsonData) {
    return PlayerTeam.values.firstWhere((e) => e.toString().split('.').last == jsonData['team']);
  }

  static PokerCardList? readCardsOnHand(Map<String, dynamic> jsonData) {
    return !jsonData.containsKey('cards_on_hand') || jsonData['cards_on_hand'] == null ? null : PokerCardList.fromString(jsonData['cards_on_hand'] as String);
  }

  static PokerCardList readPlayedCards(Map<String, dynamic> jsonData) {
    return jsonData['played_cards'] == null ? PokerCardList.empty() : PokerCardList.fromString(jsonData['played_cards'] as String);
  }


  /// Check if the player has the given hand or cards, counting duplicates
  bool hasCards(dynamic handOrCards) {
    var cardsToCheck = handOrCards is PokerCardList ? handOrCards.cards : handOrCards as List<PokerCard>;
    return _cardsOnHand!.hasCards(cardsToCheck);
  }

  /// Whether the player has at least one card on hand
  bool get hasAtLeastOneCard {
    return cardCountOnHand > 0;
  }

  /// The number of cards on hand
  int get cardCountOnHand {
    if (_cardsOnHand != null) {
      return _cardsOnHand!.length;
    }
    return 27 - playedCards.length;
  }

  /// Play the given hand. This will remove the cards from the player's hand and add them to the played cards.
  void play(Hand hand) {
    if(_cardsOnHand !=null && _cardsOnHand!.isNotEmpty)
    {
      _cardsOnHand!.removeCards(hand.cards);
    }
    playedCards.addAll(hand.cards);
  }

  /// Reset the player's hand and played cards
  void resetHands() {
    _cardsOnHand = null;
    playedCards.clear();
  }

  /// set the player's hand
  void setCardsOnHand(PokerCardList hand) {
    if (hand is Hand) {
      _cardsOnHand = hand;
      return;
    } 
    _cardsOnHand = Hand(hand.cards, HandType.unknown);
  }

  /// Get the cards on hand. Returns null if it is unknown (e.g., for other players in the client side)
  PokerCardList? get cardsOnHand {
    return _cardsOnHand;
  }

  Player deepCopyWith({
    String? id,
  }) {
    return Player.deepCopy(
      this,
      newId: id ?? this.id,
    );
  }
}


/// Get the seat of the player next to the given [seat] in the game, with the given [maxPlayers] number of players.
/// 
/// The seat numbers are 1-based.
int nextSeat(int seat, int maxPlayers) {
  seat = (seat + 1) % maxPlayers;
  if (seat == 0) {
    seat = maxPlayers;
  }
  return seat;
}

/// Get the player next (counter clockwise) to the [currentPlayer] in the game, according to the given criteria. 
/// This never returns the current player.
/// Returns null if no player is found.
Player? nextPlayer(Player currentPlayer, List<Player> players, bool teamMateOnly, bool nonemptyHandOnly) {
  for (int i = 0; i < players.length-1; i++) {
    var seat = nextSeat(currentPlayer.seat + i, players.length);
    var player = players.firstWhere((p) => p.seat == seat);
    if (teamMateOnly && player.team != currentPlayer.team) {
      continue;
    }
    if (nonemptyHandOnly && !player.hasAtLeastOneCard) {
      continue;
    }
    return player;
  }
  return null;
}


/// Get the relative position of a [player] next (counter clockwise) to the [self] in the game.
/// 
/// The [numberOfPlayers] is the total number of players in the game.
PlayerPosition getPlayerPosition(Player self, Player player, int numberOfPlayers) {
  int relativePosition = (player.seat - self.seat + numberOfPlayers) % numberOfPlayers;

  switch (numberOfPlayers) {
    case 4:
      switch (relativePosition) {
        case 0:
          return PlayerPosition.self;
        case 1:
          return PlayerPosition.rightOpponent;
        case 2:
          return PlayerPosition.teamMate;
        case 3:
          return PlayerPosition.leftOpponent;
      }
      break;
    case 6:
      switch (relativePosition) {
        case 0:
          return PlayerPosition.self;
        case 1:
          return PlayerPosition.rightOpponent;
        case 2:
          return PlayerPosition.rightTeamMate;
        case 3:
          return PlayerPosition.oppositeOpponent;
        case 4:
          return PlayerPosition.leftTeamMate;
        case 5:
          return PlayerPosition.leftOpponent;
      }
      break;
  }
  throw ArgumentError('Invalid number of players or player positions');
}

