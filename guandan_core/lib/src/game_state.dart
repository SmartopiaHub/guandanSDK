
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:uuid/uuid.dart';

import 'player.dart';
import 'card_and_hand.dart';
import 'utility.dart' as utility;

/// Checks if the round has ended.
/// A round ends if all players of a team have played all their cards.
bool isEndOfRound(List<Player> players) {
  // Get the teams that still have players with cards
  Set<String> teamsWithCards = {
    for (Player player in players)
      if (player.hasAtLeastOneCard) player.team.name
  };

  // If one or zero teams have cards left, the round has ended
  return teamsWithCards.length <= 1;
}


/// Retrieves a player by their ID from a list of players.
/// 
/// Throws an exception if no player with the given ID is found.
Player getPlayerById(List<Player> players, String playerId) {
  return players.firstWhere((player) => player.id == playerId, orElse: () {
    throw Exception('Player with ID $playerId not found');
  });
}

/// Represents the rank of a player in a round result.
enum PlayerRank {
  banker, // 上游
  follower, // 二游
  third, // 三游
  fourth, // 四游, 6 players only
  fifth, // 五游, 6 players only
  dweller; // 下游

  factory PlayerRank.fromName(String name){
    return PlayerRank.values.firstWhere((e) => e.name == name);
  }

}

/// Tracks the cumulative scores for both teams across a series of rounds.
class TeamScores {
  int redTeamScore = 0;
  int blueTeamScore = 0;

  TeamScores();

  /// Creates a deep copy of [other].
  factory TeamScores.from(TeamScores other){
    return TeamScores()
      ..redTeamScore = other.redTeamScore
      ..blueTeamScore = other.blueTeamScore;
  }

  /// Returns the score for the given [team].
  int getScore(PlayerTeam team) {
    if (team == PlayerTeam.redTeam) {
      return redTeamScore;
    } else if (team == PlayerTeam.blueTeam) {
      return blueTeamScore;
    } else {
      throw Exception('Invalid team: $team');
    }
  }

  /// Serializes scores to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'redTeam': redTeamScore,
      'blueTeam': blueTeamScore,
    };
  }

  /// Deserializes scores from a JSON map.
  TeamScores.fromJson(Map<String, dynamic> json) {
    redTeamScore = json['redTeam'] as int? ?? 0;
    blueTeamScore = json['blueTeam'] as int? ?? 0;
  }

  /// Adds [score] to the given [team]'s current total.
  void addScore(PlayerTeam team, int score) {
    if (team == PlayerTeam.redTeam) {
      redTeamScore += score;
    } else if (team == PlayerTeam.blueTeam) {
      blueTeamScore += score;
    } else {
      throw Exception('Invalid team: $team');
    }
  }

  /// Increments [team]'s score by 1 (a round win).
  void increaseScore(PlayerTeam team) {
    addScore(team, 1);
  }
}

/// Tracks the current level rank (打几) for each team.
///
/// Each team's level rank determines which card rank acts as the wild card
/// (level card) for that team. Both teams start at level 2.
class TeamLevelRanks {
  CardRank redTeamLevelRank = CardRank.two;
  CardRank blueTeamLevelRank = CardRank.two;

  TeamLevelRanks();

  /// Creates a deep copy of [other].
  factory TeamLevelRanks.from(TeamLevelRanks other) {
    return TeamLevelRanks()
      ..redTeamLevelRank = other.redTeamLevelRank
      ..blueTeamLevelRank = other.blueTeamLevelRank;
  }

  /// Returns the current level rank for the given [team].
  CardRank getLevelRank(PlayerTeam team) {
    if (team == PlayerTeam.redTeam) {
      return redTeamLevelRank;
    } else if (team == PlayerTeam.blueTeam) {
      return blueTeamLevelRank;
    } else {
      throw Exception('Invalid team: $team');
    }
  }

  /// Sets the level rank for the given [team] to [levelRank].
  void setLevelRank(PlayerTeam team, CardRank levelRank) {
    if (team == PlayerTeam.redTeam) {
      redTeamLevelRank = levelRank;
    } else if (team == PlayerTeam.blueTeam) {
      blueTeamLevelRank = levelRank;
    } else {
      throw Exception('Invalid team: $team');
    }
  }

  /// Serializes the level ranks to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'redTeam': redTeamLevelRank.name,
      'blueTeam': blueTeamLevelRank.name,
    };
  }

  /// Deserializes level ranks from a JSON map.
  TeamLevelRanks.fromJson(Map<String, dynamic> json) {
    redTeamLevelRank = CardRank(json['redTeam'] as String);
    blueTeamLevelRank = CardRank(json['blueTeam'] as String);
  }
}

/// A class representing a turn （一次出牌，包括不出） in the game.
class Turn {

  /// The turn ID, which is unique within a game, in the format of 'R1_P1_T1'.
  String id;

  /// The serial/model number of the bot if the player is a bot.
  String? botCode;

  /// The player who played the turn.
  Player player;

  /// The hand of cards played by the player in this turn. It could be empty if the player passed.
  Hand playedHand;

  /// Played time
  final DateTime playedTime;

  Turn(this.player, this.playedHand, this.id, {DateTime? playedTime, this.botCode}) : playedTime = playedTime ?? DateTime.now();

  /// Checks if the player has passed in this turn.
  bool get isPassed {
    return playedHand.isEmpty;
  }

  /// Converts the turn to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'turn_id': id,
      'player_id': player.id,
      'played_hand': playedHand.toJson(),
      'played_time': playedTime.toIso8601String(),
      'bot_code': botCode,
    };
  }

  /// Creates a turn from a JSON object.
  factory Turn.fromJson(Map<String, dynamic> jsonData, List<Player> players) {
    Player player = players.firstWhere((player) => player.id == jsonData['player_id']);
    Hand handPlayed = Hand.fromJson(jsonData['played_hand'] as Map<String, dynamic>);
    DateTime playedTime = DateTime.parse(jsonData['played_time'] as String);
    String? botCode = jsonData['bot_code'];

    return Turn(player, handPlayed, jsonData['turn_id'] as String, playedTime: playedTime, botCode: botCode);
  }

  Turn copy() {
    return Turn(player, playedHand, id, playedTime: playedTime, botCode: botCode);
  }

  @override
  bool operator ==(Object other) {
    if (other is Turn) {
      return id == other.id;
    }
    return false;
  }

  @override
  int get hashCode => id.hashCode;
}


/// A class representing a phase (一圈) in the game.
/// 
/// The phase starts with a player, who is the first to play a turn in the phase.
class Phase {

  /// The phase ID, which is unique within a round, in the format of 'R1_P1'.
  String id;

  /// The player who starts the phase.
  Player startPlayer;

  /// The list of turns in the phase.
  List<Turn> turns = [];

  Phase(this.startPlayer, [String? phaseId]) : id = phaseId ?? const Uuid().v4();

  /// Converts the phase to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'phase_id': id,
      'start_player_id': startPlayer.id,
      'turns': turns.map((turn) => turn.toJson()).toList(),
    };
  }

  /// Creates a phase from a JSON object.
  factory Phase.fromJson(Map<String, dynamic> jsonData, List<Player> players) {
    Player startPlayer = getPlayerById(players, jsonData['start_player_id'] as String);
    List<Turn> turns = (jsonData['turns'] as List)
        .map((turn) => Turn.fromJson(turn as Map<String, dynamic>, players))
        .toList();
    return Phase(startPlayer, jsonData['phase_id'] as String)
      ..turns = turns;
  }

  /// Appends a turn to the phase, where the [player] played the [cardsPlayed].
  /// If the [cardsPlayed] is played by a bot (e.g., a bot on the client side), [botCode] can be provided.
  void appendTurn(Player player, Hand cardsPlayed, {String? botCode}) {
    turns.add(Turn(player, cardsPlayed, createTurnId(), botCode: botCode ?? player.botCode));
  }

  /// Updates the start player of the phase.
  void updateStartPlayer(Player player) {
    startPlayer = player;
  }

  /// Creates a unique ID for a turn within the phase.
  String createTurnId() {
    return '${id}_T${turns.length + 1}';
  }

  /// Checks if the phase just started (i.e., no turns have been played yet).
  bool get isStartOfPhase {
    return turns.isEmpty;
  }

  /// Get the cards on the top of the table.
  /// 
  /// Returns the last non-empty hand, or an empty hand if none is known.
  Hand get handOnTable {
    return lastNonPassTurn?.playedHand ?? Hand.emptyHand();
  }

  /// Get the last turn in the phase where the player played at least one card.
  /// 
  /// If no player has played any cards in the known history, returns null.
  Turn? get lastNonPassTurn {
    if (turns.isEmpty) {
      return null;
    }
    for (Turn t in turns.reversed) {
      if (!t.isPassed) {
        return t;
      }
    }
    // A partial phase history (for example, while restoring a client or bot)
    // can legitimately contain only pass turns.
    return null;
  }

  /// Get the last turn in the phase, which could be a pass turn. Returns null if the phase just started.
  Turn? get lastTurn {
    if (turns.isEmpty) {
      return null;
    }
    return turns.last;
  }

  /// Replace a player with a new player in the phase. 
  /// 
  /// This could happen when a player leaves the game and replaced by a bot.
  void replacePlayer(Player exPlayer, Player newPlayer){
    if (startPlayer.id == exPlayer.id) {
      startPlayer = newPlayer;
    }

    for (var turn in turns) {
      if (turn.player.id == exPlayer.id) {
        turn.player = newPlayer;
      }
    }
  }

  /// Checks if the phase has ended.
  bool isEndOfPhase(List<Player> players) {
    if (turns.isEmpty) {
      return false;
    }
    // Case I: all players of a team have played all their cards.
    if (isEndOfRound(players)) {
      return true;
    }
    // Case II: all other players having cards passed, except the last player who played at least one card.
    Turn? t = lastNonPassTurn;
    assert (t != null);

    int tIndex = turns.indexWhere((turn) => turn.id == t!.id);
    Set<String> playersPassed = {
      for (Turn turn in turns.sublist(tIndex + 1))
        if (turn.isPassed) turn.player.id
    };
    for (Player player in players) {
      if (player.id != t?.player.id && player.hasAtLeastOneCard && !playersPassed.contains(player.id)) {
        return false;
      }
    }
    return true;
  }
}


/// Records the outcome of a single round — which players finished in which
/// positions (上游, 二游, etc.) and the associated Ace-passing (过尖) state.
///
/// For a 4-player game, only [banker], [follower], [third], and [dwellers] are
/// populated. For a 6-player game, [fourth] and [fifth] are also used.
class RoundResult {
  Player? banker; // Player 上游
  Player? follower; // Player 二游
  Player? third; // Player 三游
  Player? fourth; // Player 四游, only for 6 players
  Player? fifth; // Player 五游, only for 6 players
  List<Player> dwellers; // List of Players 下游 (可能有两个， 同一个队伍的)

  /// The level rank of the round.
  CardRank? levelRank;

  /// The team who is playing the level rank.
  PlayerTeam? teamOfLevelRank;

  /// number of tries for passing over Ace 过尖 (counting also this round), only non-null when [levelRank] is Ace for the corresponding team
  int? _acePassingTriesOfRedTeam;
  int? _acePassingTriesOfBlueTeam;

  /// The team of the banker (上游), or `null` if not yet determined.
  PlayerTeam? get teamOfBanker => banker?.team;

  /// Returns the [PlayerRank] of the player with the given [playerId], or `null`
  /// if the player is not found in this result.
  PlayerRank? getRankOfPlayer(String playerId) {
    if (banker?.id == playerId) {
      return PlayerRank.banker;
    }
    if (follower?.id == playerId) {
      return PlayerRank.follower;
    }
    if (third?.id == playerId) {
      return PlayerRank.third;
    }
    if (fourth?.id == playerId) {
      return PlayerRank.fourth;
    }
    if (fifth?.id == playerId) {
      return PlayerRank.fifth;
    }
    if (dwellers.any((player) => player.id == playerId)) {
      return PlayerRank.dweller;
    }
    return null; // Player not found in the round result
  }

  /// Returns the number of Ace-passing attempts for [team], or `null` if
  /// [team] is null or no attempts have been recorded. Include the ongoing attempt.
  int? getAcePassingTries(PlayerTeam? team){
    if (team == null) return null;
    if (team == PlayerTeam.redTeam) {
      return _acePassingTriesOfRedTeam;
    }
    return _acePassingTriesOfBlueTeam;
  }

  /// Increments the Ace-passing attempt counter for [team].
  void increaseAcePassingTries(PlayerTeam team){
    if (team == PlayerTeam.redTeam) {
      _acePassingTriesOfRedTeam = (_acePassingTriesOfRedTeam ?? 0) + 1;
    }
    else{
      _acePassingTriesOfBlueTeam = (_acePassingTriesOfBlueTeam ?? 0) + 1;
    }
  }

  /// Sets the Ace-passing attempt counter for [team] to [tries].
  void setAcePassingTries(PlayerTeam team, int? tries){
    if (team == PlayerTeam.redTeam) {
      _acePassingTriesOfRedTeam = tries;
    }
    else{
      _acePassingTriesOfBlueTeam = tries;
    }
  }

  /// Whether the banker's team successfully passed Ace (过尖).
  ///
  /// Returns `true` if the banker and follower are on the same team as
  /// [teamOfLevelRank] and no teammate is a dweller. Returns `null` if the
  /// result is not yet valid/complete or the level rank is not Ace.
  bool? get isAcePassed {
    if (levelRank == null || levelRank != CardRank.A ||  !isValidAndComplete())  return null;

    var bankerTeam = banker!.team;
    if (bankerTeam != teamOfLevelRank) return false; // 上游是敌方
    if (dwellers.any((player) => player.team == bankerTeam)) return false; // 下游有队友
    return true;
  }

  String? roundId;

  // ignore: non_constant_identifier_names
  RoundResult({this.banker, this.follower, this.third, this.fourth, this.fifth, this.dwellers = const [], this.levelRank, int? acePassingTriesOfBlueTeam, int? acePassingTriesOfRedTeam, this.roundId, this.teamOfLevelRank}):
    _acePassingTriesOfBlueTeam = acePassingTriesOfBlueTeam,
    _acePassingTriesOfRedTeam = acePassingTriesOfRedTeam;

  /// Converts the [RoundResult] to a JSON-compatible map.
  ///
  /// Example JSON representation:
  /// ```json
  /// {
  ///   "banker_id": "player1",
  ///   "banker": {"id": "player1", "name": "Alice", "team": "red"},
  ///   "follower_id": "player2",
  ///   "dwellers_id": ["player3", "player4"],
  ///   "round_id": "R1",
  ///   "ace_passing_tries_redteam": 2,
  ///   "ace_passing_tries_blueteam": 1,
  ///   "level_rank": "A",
  ///   "team_of_level_rank": "red"
  /// }
  /// ```
  Map<String, dynamic> toJson() {
    return {
      'banker_id': banker?.id,
      'banker': banker?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'follower_id': follower?.id,
      'follower': follower?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'third_id': third?.id,
      'third': third?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'fourth_id': fourth?.id,
      'fourth': fourth?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'fifth_id': fifth?.id,
      'fifth': fifth?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'dwellers_id': dwellers.map((player) => player.id).toList(),
      'dwellers': dwellers.map((player) => player.toJson(withCardsOnHand: false, withPlayedCards: false)).toList(),
      'round_id': roundId,
      'ace_passing_tries_redteam': _acePassingTriesOfRedTeam,
      'ace_passing_tries_blueteam': _acePassingTriesOfBlueTeam,
      'level_rank': levelRank?.name,
      'team_of_level_rank': teamOfLevelRank?.name,
    };
  }

  /// Creates a [RoundResult] from a JSON map.
  ///
  /// If [players] is provided, players are looked up by ID from that list;
  /// otherwise player objects are deserialized from the JSON inline.
  factory RoundResult.fromJson(Map<String, dynamic> jsonData, List<Player>? players) 
  {
    Player? getPlayerById(String id) => players?.firstWhere((player) => player.id == id, orElse: () => throw Exception('Player with ID $id not found'));

    Player fromJson(Map<String, dynamic> playerJson) => Player.fromJson(playerJson);
    return RoundResult(
      banker: jsonData['banker'] == null ? null : (players != null ? getPlayerById(jsonData['banker_id'] as String) : fromJson(jsonData['banker'])),
      follower: jsonData['follower'] == null ? null : (players != null ? getPlayerById(jsonData['follower_id'] as String) : fromJson(jsonData['follower'])),
      third: jsonData['third'] == null ? null : (players != null ? getPlayerById(jsonData['third_id'] as String) : fromJson(jsonData['third'])),
      fourth: jsonData['fourth'] == null ? null : (players != null ? getPlayerById(jsonData['fourth_id'] as String) : fromJson(jsonData['fourth'])),
      fifth: jsonData['fifth'] == null ? null : (players != null ? getPlayerById(jsonData['fifth_id'] as String) : fromJson(jsonData['fifth'])),
      dwellers: players != null ? (jsonData['dwellers_id'] as List).map((id) => getPlayerById(id as String)!).toList() :
         (jsonData['dwellers'] as List).map((playerJson) => fromJson(playerJson as Map<String, dynamic>)).toList(),
      roundId: jsonData['round_id'] as String,
      acePassingTriesOfRedTeam: jsonData['ace_passing_tries_redteam'] as int?,
      acePassingTriesOfBlueTeam: jsonData['ace_passing_tries_blueteam'] as int?,
      levelRank: jsonData['level_rank'] == null ? null : CardRank(jsonData['level_rank'] as String),
      teamOfLevelRank: jsonData['team_of_level_rank'] == null ? null : PlayerTeam.fromName(jsonData['team_of_level_rank'] as String),
    );
  }

  /// Records that [player] has emptied their hand.
  ///
  /// The first player to finish becomes the banker (上游), the second becomes the
  /// follower (二游). If banker and follower are on the same team (双下 scenario),
  /// the third finisher is also a dweller; otherwise they become third (三游).
  void recordPlayerFinished(Player player) {
    if (banker == null) {
      banker = player;
    } else if (follower == null) {
      follower = player;
    } else {
      if (banker!.team == follower!.team) {
        dwellers.add(player);
      } else {
        third = player;
      }
    }
  }

  /// Checks whether the round result is structurally valid and complete.
  ///
  /// Returns `true` only when banker, follower, and (if not 双下) third are set,
  /// with the correct number of dwellers (1 when not 双下, 2 when 双下).
  bool isValidAndComplete() {
    if (banker == null || follower == null) {
      return false; // The result should specify at least 2 players.
    }
    if (banker!.team == follower!.team) {
      if (third != null) {
        return false; // The result should have no third when 双下.
      }
      if (dwellers.length != 2) {
        return false; // The result should have 2 dwellers when 双下.
      }
    } else {
      if (third == null) {
        return false; // The result should specify the third player when not 双下.
      }
      if (dwellers.length != 1) {
        return false; // The result should have 1 dweller when not 双下.
      }
    }
    return true;
  }

  /// Returns the players who should pay tribute (进贡).
  List<Player> get playersToPayTribute {
    if (!isValidAndComplete()) {
      throw Exception('Cannot deduce tribute info from an invalid or incomplete round result.');
    }
    return dwellers;
  }

  /// Returns the players who should receive tribute (收贡).
  List<Player> get playersToReceiveTribute {
    if (!isValidAndComplete()) {
      throw Exception('Cannot deduce tribute info from an invalid or incomplete round result.');
    }
    if (banker!.team == follower!.team) {
      return [banker!, follower!];
    } else {
      return [banker!];
    }
  }

  @override
  toString() {
    String result = 'RoundResult: ';
    if (banker != null) {
      result += '[Banker: ${banker!.id}] ';
    }
    if (follower != null) {
      result += '[Follower: ${follower!.id}] ';
    }
    if (third != null) {
      result += '[Third: ${third!.id}] ';
    }
    result += '[Dwellers: ${dwellers.map((p) => p.id).join(', ')}] ';
    if (levelRank != null) {
      result += '[Level Rank: ${levelRank?.name}] ';
    }
    return result;
  }
}


/// A class representing the outcome in the stage of tributing (进贡).
class TributeResult {

  /// The list of tributes in the result.
  List<Tribute> tributes = [];

  /// Whether the tribute is resisted (抗贡).
  bool isResisted = false;

  /// If the tribute is resisted, the red jokers held by the players (indexed by seat number).
  Map<int, int> redJokers = {};
  //String startPlayerId = '';

  TributeResult({this.isResisted = false, List<Tribute>? tributes}){
    this.tributes.addAll(tributes ?? []);
  }

  /// Adds a [tribute] to the result. Returns `false` if the tribute is resisted
  /// or the payer has already paid.
  bool addTribute(Tribute tribute) {
    if (isResisted) {
      return false;
    }

    // Check if the payer has already paid tribute
    if (tributes.any((t) => t.payer.id == tribute.payer.id)) {
      return false;
    }

    tributes.add(tribute);
    return true;
  }

  /// Converts the TributeResult to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'tributes': tributes.map((tribute) => tribute.toJson()).toList(),
      'is_resisted': isResisted,
      'red_jokers': redJokers.map((key, value) => MapEntry(key.toString(), value)),
      //'start_player_id': startPlayerId
    };
  }

  /// Creates a TributeResult from a JSON object.
  factory TributeResult.fromJson(Map<String, dynamic> jsonData, List<Player>? players) {
    List<Tribute> tributes = (jsonData['tributes'] as List)
        .map((tribute) => Tribute.fromJson(tribute as Map<String, dynamic>, players))
        .toList();
    Map<int, int> redJokers = jsonData['red_jokers'] != null
        ? (jsonData['red_jokers'] as Map<String, dynamic>).map((key, value) => MapEntry(int.parse(key), value as int))
        : {};
    //String startPlayerId = jsonData['start_player_id'] as String;
    var result =  TributeResult(isResisted: jsonData['is_resisted'] as bool); 
    result.tributes = tributes;
    result.redJokers = redJokers;
    //result.startPlayerId = startPlayerId;
    return result;
  }
}


/// A class representing a round (一局) in the game.
/// 
/// A round consists of a series of phases, each of which consists of a series of turns.
class Round {

  /// The ID of the round, which is unique within a game, in the format of 'R1'.
  String id;

  /// The player who starts the round.
  Player? startPlayer;

  /// The list of players in the game.
  List<Player> players;

  /// The list of phases in the round.
  List<Phase> phases = [];

  /// The level rank of the round.
  CardRank levelRank;

  /// Is tribute stage enabled?
  bool tributeEnabled;

  /// The number of Ace-passing attempts for the current [teamOfLevelRank].
  /// Returns `null` when [levelRank] is not Ace or there is no previous round.
  int? get aPlusTries {
    if (levelRank != CardRank.A || previousRoundResult == null || teamOfLevelRank == null) {
      return null;
    }
    return roundResult.getAcePassingTries(teamOfLevelRank!);    
  }

  /// The result of the round.
  RoundResult roundResult;

  /// The result of the previous round.
  RoundResult? previousRoundResult;

  /// The tribute results of the round.
  TributeResult tributeResult = TributeResult();

  /// Whether all required tributes have been paid (or there is no previous round).
  bool get allTributesPaid {
    if (previousRoundResult == null) {
      return true;
    }
    return tributeResult.tributes.length == previousRoundResult!.dwellers.length;
  }

  /// The hands of cards held by the players at the start of the round.
  Map<String, List<PokerCard>> handsAtStart = {};

  /// Creates a new instance of [Round], with the given [players], [id], [levelRank], and optional [previousRoundResult] and [startPlayer].
  /// 
  /// The [previousRoundResult] is null for the first round.
  /// The [startPlayer] is null if it is not yet determined.
  Round(this.players, this.id, this.levelRank, {this.previousRoundResult, this.startPlayer, DateTime? creationTime, this.tributeEnabled = true}): 
      creationTime = creationTime ?? DateTime.now(), 
      roundResult = RoundResult(roundId: id, 
        levelRank: levelRank, 
        acePassingTriesOfBlueTeam: previousRoundResult?.getAcePassingTries(PlayerTeam.blueTeam),
        acePassingTriesOfRedTeam: previousRoundResult?.getAcePassingTries(PlayerTeam.redTeam),
        teamOfLevelRank: previousRoundResult?.banker?.team)
  {
        if (levelRank == CardRank.A && previousRoundResult != null && teamOfLevelRank != null) {
          roundResult.increaseAcePassingTries(teamOfLevelRank!);
        }
        if (previousRoundResult?.isAcePassed != null){
          if (previousRoundResult?.isAcePassed == true){ // 过尖了, reset the tries for both teams
            roundResult.setAcePassingTries(PlayerTeam.redTeam, null);
            roundResult.setAcePassingTries(PlayerTeam.blueTeam, null);
          }
          else{ // 没过尖
            var tries = previousRoundResult?.getAcePassingTries(previousRoundResult!.teamOfLevelRank!);
            if (tries != null && tries >= 3){ // 三次没过尖
              roundResult.setAcePassingTries(previousRoundResult!.teamOfLevelRank!, null);
            }
            /*else if (tries != null){
              roundResult.setAPlusTries(previousRoundResult!.teamOfLevelRank!, tries+1);
            }*/
          }
        }
  }

  /// Checks if the round is ready to play (after the tribute stage is completed).
  /// 
  /// Return false if the tribute is not completed or if any player does not have 27 cards on hand.
  bool get readyToPlay {
    if (!isTributeStageCompleted) {
      return false;
    }
    return players.every((player) => player.cardCountOnHand == 27) && startPlayer != null;
  }

  /// The team whose level rank is being played this round.
  /// `null` for the first round (both teams start at level 2).
  PlayerTeam? get teamOfLevelRank {
    return previousRoundResult?.banker?.team;
  }

  /// Round creation time
  final DateTime creationTime;

  /// tributeCompletionTime
  DateTime tributeCompletionTime = DateTime.now();


  /// Whether the tribute stage has concluded.
  ///
  /// Returns `true` if tributing is disabled, if this is the first round, if
  /// tribute was resisted, if all required tributes are paid with returns, or
  /// if gameplay has already started (phases exist with turns).
  bool get isTributeStageCompleted {
    if (!tributeEnabled) {
      return true; // tribute stage is not enabled, so it is considered completed
    }
    bool tributeCompleted = false;
    if (previousRoundResult == null) { // 第一轮
      tributeCompleted = true;
    }
    else if(tributeResult.isResisted){
      tributeCompleted = true;
    }
    else if(tributeResult.tributes.length == previousRoundResult!.playersToPayTribute.length){
      tributeCompleted = tributeResult.tributes.every((tribute) => tribute.returnCard != null);
    }
    if(!tributeCompleted){ // deduce from other information
      if(phases.isNotEmpty && phases.last.turns.isNotEmpty){
        return true;
      }
    }
    
    return tributeCompleted;
  }

  /// Whether at least one phase has been started in this round.
  bool get hasPhase {
    return phases.isNotEmpty;
  }

  /// Whether the round is at the end of the current phase (all other players
  /// have passed or the round has ended).
  bool get isEndOfCurrentPhase {
    return hasPhase && currentPhase.isEndOfPhase(players);
  }
  
  

  /// Converts the round to a JSON object.
  /// 
  /// If [withCardsOnHand] is true, the cards on hand are included in the JSON object.
  /// If [withPlayedCards] is true, the played cards are included in the JSON object.
  Map<String, dynamic> toJson({bool withCardsOnHand = true, bool withPlayedCards = true}) {
    return {
      'round_id': id,
      'creation_time': creationTime.toIso8601String(),
      'start_player_id': startPlayer?.id,
      'players': players.map((player) => player.toJson(withCardsOnHand: withCardsOnHand, withPlayedCards: withPlayedCards)).toList(),
      'level_rank': levelRank.name,
      'round_result': roundResult.toJson(),
      'previous_round_result': previousRoundResult?.toJson(),
      'tribute_result': tributeResult.toJson(),
      'hands_at_start': {
        for (var player in players)
          player.id: PokerCardList.cardListToString(withCardsOnHand ? handsAtStart[player.id] ?? [] : [])
      } ,
      'phases': phases.map((phase) => phase.toJson()).toList(),
      'tribute_enabled': tributeEnabled,
    };
  }

  /// Creates a round from a JSON object.
  factory Round.fromJson(Map<String, dynamic> jsonData, {List<Player>? players}) {
    players ??= (jsonData['players'] as List)
        .map((playerJson) => Player.fromJson(playerJson as Map<String, dynamic>))
        .toList();
    Player? startPlayer = jsonData['start_player_id'] != null
        ? getPlayerById(players, jsonData['start_player_id'] as String)
        : null;
    List<Phase> phases = (jsonData['phases'] as List)
        .map((phase) => Phase.fromJson(phase as Map<String, dynamic>, players!))
        .toList();
    String levelRank = jsonData['level_rank'] as String;
    RoundResult roundResult = RoundResult.fromJson(jsonData['round_result'] as Map<String, dynamic>, players);
    RoundResult? previousRoundResult = jsonData['previous_round_result'] != null
        ? RoundResult.fromJson(jsonData['previous_round_result'] as Map<String, dynamic>, players)
        : null;
    TributeResult tributes = TributeResult.fromJson(jsonData['tribute_result'] as Map<String, dynamic>, players);
    Map<String, List<PokerCard>> handsAtStart = {
      for (var entry in (jsonData['hands_at_start'] as Map<String, dynamic>).entries)
        entry.key: PokerCardList.cardListFromString(entry.value as String)
    };
    final tributeEnabled = jsonData['tribute_enabled'] as bool? ?? true;

    DateTime creationTime = DateTime.parse(jsonData['creation_time'] as String);

    return Round(players, jsonData['round_id'] as String, CardRank(levelRank), creationTime: creationTime,
        startPlayer: startPlayer, previousRoundResult: previousRoundResult, tributeEnabled: tributeEnabled)
      ..phases = phases
      ..roundResult = roundResult
      ..tributeResult = tributes
      ..handsAtStart = handsAtStart;
  }

  /// Updates the round with the result of the round.
  void updateRoundResult(RoundResult result) {
    roundResult = result;
  }


  /// Replaces a player with a new player in the round.
  /// 
  /// This could happen when a player leaves the game and replaced by a bot.
  void replacePlayer(Player exPlayer, Player newPlayer){
    var index = players.indexWhere((player) => player.id == exPlayer.id);
    if (index == -1) {
      index = players.indexWhere((player) => player.id == newPlayer.id);
      if (index == -1 || players[index].seat != exPlayer.seat) {
        throw Exception('Player not found in the round.');
      }
      else{
        return; // already replaced
      }
    }
    players[index] = newPlayer;

    if(startPlayer?.id == exPlayer.id){
      startPlayer = newPlayer;
    }

    for (var phase in phases) {
      phase.replacePlayer(exPlayer, newPlayer);
    }

    if(roundResult.banker?.id == exPlayer.id){
      roundResult.banker = newPlayer;
    }
    if(roundResult.follower?.id == exPlayer.id){
      roundResult.follower = newPlayer;
    }
    if(roundResult.third?.id == exPlayer.id){
      roundResult.third = newPlayer;
    }
    for (var dweller in roundResult.dwellers) {
      if (dweller.id == exPlayer.id) {
        roundResult.dwellers[roundResult.dwellers.indexOf(dweller)] = newPlayer;
      }
    }

    if (previousRoundResult != null) {
      if (previousRoundResult!.banker?.id == exPlayer.id) {
        previousRoundResult!.banker = newPlayer;
      }
      if (previousRoundResult!.follower?.id == exPlayer.id) {
        previousRoundResult!.follower = newPlayer;
      }
      if (previousRoundResult!.third?.id == exPlayer.id) {
        previousRoundResult!.third = newPlayer;
      }
      for (var dweller in previousRoundResult!.dwellers) {
        if (dweller.id == exPlayer.id) {
          previousRoundResult!.dwellers[previousRoundResult!.dwellers.indexOf(dweller)] = newPlayer;
        }
      }
    }

    if (tributeResult.tributes.isNotEmpty) {
      for (var tribute in tributeResult.tributes) {
        if (tribute.payer.id == exPlayer.id) {
          tribute.payer = newPlayer;
        }
        if (tribute.winner?.id == exPlayer.id) {
          tribute.winner = newPlayer;
        }
      }
    }

  }

  /// Get the current phase of the round.
  Phase get currentPhase {
    if (phases.isEmpty) {
      if (startPlayer == null) {
        throw Exception('No phase in the round and start player is not set.');
      }
      newPhase(startPlayer!);
    }
    return phases.last;
  }

  /// Update the start player of the round.
  void updateStartPlayer(Player startPlayer) {
    if (!isAtStartOfRound) {
      throw Exception('Cannot update the start player in the middle of a round.');
    }
    this.startPlayer = startPlayer;
    currentPhase.updateStartPlayer(startPlayer);
  }

  /// Checks if the round has ended.
  bool get hasEnded {
    return isEndOfRound(players);
  }

  /// The ID of the next turn to be played in this round, or `null` if the
  /// round has not started or has ended.
  String? get currentTurnId {
    try{
      return currentPhase.createTurnId();
    } catch (e) {
      return null;
    }
  }

  /// The last turn played in the round, or `null` if no turn has been played.
  Turn? get lastTurn {

    if(phases.isEmpty || (phases.length == 1 && currentPhase.isStartOfPhase)){
      return null;
    }

    if(currentPhase.turns.isEmpty){
      return phases[phases.length - 2].turns.last;
    }

    return currentPhase.lastTurn;
  }

  /// Returns the ID of the next turn, creating a new phase ID if the current
  /// phase has ended. Returns `null` if the round has ended.
  String? nextTurnId(){
    if (phases.isEmpty || currentPhase.isEndOfPhase(players)) {
      var phaseId = createPhaseId();
      return '${phaseId}_T1';
    }
    return currentPhase.createTurnId();
  }

  /// Whether the round has just started (no phases or the current phase has no turns).
  bool get isAtStartOfRound {
    if (phases.isEmpty) {
      return true;
    }
    if (phases.length > 1) {
      return false;
    }
    return currentPhase.isStartOfPhase;
  }

  /// Creates a unique ID for a phase within the round.
  String createPhaseId() {
    return '${id}_P${phases.length + 1}';
  }


  /// Checks if this is a 接风 (jie-feng) scenario — the player who emptied
  /// their hand in the last phase hands the lead to their teammate for the
  /// next phase.
  bool isJieFeng(Player startPlayerOfPhase){
    if (hasEnded) {
      throw Exception('The round has ended.');
    }
   
    if (phases.isEmpty) {
      return false;
    }

    var phase = phases.last;
    if (phase.isStartOfPhase) {
      if (phases.length <= 1) return false;
      phase = phases[phases.length - 2];
    }

    // deduce from the turns of the current phase
    var t = phase.lastNonPassTurn!;
    if (t.player.cardCountOnHand > 0) {
      return false;
    }

    var next = nextPlayer(t.player, players, true, true);
    if (next == null)  return false;
    return next.id == startPlayerOfPhase.id;
  }


  /// Deduce the start player for the next phase.
  Player startPlayerForNextPhase() {
    if (hasEnded) {
      throw Exception('The round has ended.');
    }
   
    if (phases.isEmpty) {
      if (startPlayer == null) {
        throw Exception('No phase in the round and start player is not set.');
      }
      return startPlayer!;
    }

    var currentPhase = phases.last;
    if (currentPhase.isStartOfPhase) {
      return currentPhase.startPlayer;
    }

    // deduce from the turns of the current phase
    var t = currentPhase.lastNonPassTurn!;
    var currentPlayer = t.player;
    if (!currentPlayer.hasAtLeastOneCard) {
      // 接风
      var next = nextPlayer(currentPlayer, players, true, true);
      if (next == null) {
        throw Exception('No player found to play the turn.');
      }
      currentPlayer = next;
    }
    else{
      // 下一位
      var next = nextPlayer(currentPlayer, players, false, true);
      if (next == null) {
        throw Exception('No player found to play the turn.');
      }
      currentPlayer = next;
    }
    return currentPlayer;
  }

  /// Starts a new phase in the round.
  void newPhase(Player startPlayer, [String? phaseId]) {
    if (phases.isEmpty) {
      Phase phase = Phase(startPlayer, phaseId ?? createPhaseId());
      phases.add(phase);
      return;
    }
    
    Phase currentPhase = this.currentPhase;
    if(currentPhase.id == phaseId && currentPhase.isStartOfPhase){
      return;
    }
    if (!currentPhase.isEndOfPhase(players)) {
      throw Exception('Cannot start a new phase before the current phase ends.');
    }
    if (hasEnded) {
      throw Exception('Cannot start a new phase at the end of a round.');
    }

    Turn? t = currentPhase.lastNonPassTurn;
    Player startPlayerOfPhase = t!.player;
    if (!startPlayerOfPhase.hasAtLeastOneCard) {
      startPlayerOfPhase = players.firstWhere((player) => player.hasAtLeastOneCard && player.team == startPlayerOfPhase.team);
    }
    Phase phase = Phase(startPlayerOfPhase, phaseId ?? createPhaseId());
    phases.add(phase);
  }

  /// Completes the round result.
  void completeRoundResult() {
    RoundResult r = roundResult;
    if (r.banker == null || r.follower == null) {
      throw Exception('The result should specify at least 2 players.');
    }
    if (r.banker!.team == r.follower!.team) {
      if (r.third != null) {
        throw Exception('The result should have no third when 双下.');
      }
      r.dwellers = players.where((player) => player.team != r.banker!.team).toList();
    } else {
      if (r.third == null) {
        throw Exception('The result should specify the third player when not 双下.');
      }
      r.dwellers = players.where((player) => ![r.banker!.id, r.follower!.id, r.third!.id].contains(player.id)).toList();
    }
  }


  /// Save the round to a file.
  void saveToFile(String fullFilePath, String gameId){
    File file = File(fullFilePath);
    final encoder = JsonEncoder.withIndent('  ');
    var data = toJson();
    data['game_id'] = gameId;
    file.writeAsString(encoder.convert(data));
  }

}

/// Represents a consecutive series of rounds (系列) played between two teams.
///
/// A series starts at [startRoundId] and ends at [endRoundId]. The [winnerTeam]
/// is set once the series concludes (e.g., a team passes A).
class RoundSeries {
  /// The ID of the round where this series begins.
  String startRoundId;
  /// The ID of the round where this series ends, or `null` if still in progress.
  String? endRoundId;
  /// The team that won the series, or `null` if still in progress.
  PlayerTeam? winnerTeam;

  RoundSeries(this.startRoundId, {this.endRoundId, this.winnerTeam});

  Map<String, dynamic> toJson() {
    return {
      'start_round_id': startRoundId,
      'end_round_id': endRoundId,
      'winner_team': winnerTeam?.name,
    };
  }

  factory RoundSeries.fromJson(Map<String, dynamic> jsonData) {
    return RoundSeries(
      jsonData['start_round_id'] as String,
      endRoundId: jsonData['end_round_id'] as String?,
      winnerTeam: jsonData['winner_team'] == null ? null : PlayerTeam.fromName(jsonData['winner_team'] as String),
    );
  }
}  

/// A class representing a tribute in the game.
class Tribute {

  /// The player who pays the tribute.
  Player payer;

  /// The player who receives the tribute. This could be deduced later after all tributes are paid.
  Player? winner;

  /// The card paid as tribute.
  PokerCard? tributeCard;

  /// The card returned from the receiver.
  PokerCard? returnCard;

  /// The model/code of the bot that plays the tribute card, if the payer is a bot.
  String? payerBotCode;

  /// The model/code of the bot that plays the return card, if the winner is a bot.
  String? winnerBotCode;

  /// Creates a tribute with [payer] (required) and optional [winner],
  /// [tributeCard], [returnCard], and bot codes.
  Tribute({required this.payer, this.winner, this.tributeCard, this.returnCard, this.payerBotCode, this.winnerBotCode});

  @override
  String toString() {
    return 'Tribute: ${payer.name} -> ${winner?.name ?? 'Unknown'}: $tributeCard -> $returnCard';
  }

  /// Serializes the tribute to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'payer_id': payer.id,
      'payer': payer.toJson(withCardsOnHand: false, withPlayedCards: false),
      'receiver_id': winner?.id,
      'winner': winner?.toJson(withCardsOnHand: false, withPlayedCards: false),
      'tribute_card': tributeCard.toString(),
      'return_card': returnCard?.toString(),
      'payer_bot_code': payerBotCode,
      'winner_bot_code': winnerBotCode,
    };
  }

  factory Tribute.fromJson(Map<String, dynamic> jsonData, List<Player>? players) {
    Player payer = players != null ?  getPlayerById(players, jsonData['payer_id'] as String)
        : Player.fromJson(jsonData['payer'] as Map<String, dynamic>);
    Player? winner = jsonData['receiver_id'] != null
        ? (players != null ? getPlayerById(players, jsonData['receiver_id'] as String) : Player.fromJson(jsonData['winner'] as Map<String, dynamic>))
        : null;
    PokerCard tributeCard = PokerCard.from(jsonData['tribute_card'] as String);
    PokerCard? returnCard = jsonData['return_card'] != null
        ? PokerCard.from(jsonData['return_card'] as String)
        : null;
    String? tributeCardBotModel = jsonData['payer_bot_code'] as String?;
    String? returnCardBotModel = jsonData['winner_bot_code'] as String?;
    return Tribute(
        payer: payer,
        winner: winner,
        tributeCard: tributeCard,
        returnCard: returnCard,
        payerBotCode: tributeCardBotModel,
        winnerBotCode: returnCardBotModel);
  }
}


/// A class representing the state of the game.
class GameState {

  /// The list of players in the game.
  final List<Player> players;

  /// Returns `true` if a player with the given [playerId] is in the game.
  bool hasPlayer(String playerId){
    return players.any((player) => player.id == playerId);
  }

  /// The level rank of each team in the game.
  TeamLevelRanks teamLevelRank;

  /// The score of each time in the game.
  TeamScores teamScores = TeamScores();

  /// The list of rounds in the game.
  List<Round> rounds;

  /// Series
  List<RoundSeries> series = [];

  /// The unique ID of the game.
  /// The unique identifier of this game instance.
  ///
  /// This is a UUID v4 generated by [createGameId] when the game state is
  /// first created. It is distinct from the room ID — a room may persist
  /// across multiple games, each with its own unique game ID.
  String id;

  /// The number of players required to start the game.
  final int requiredPlayers;

  /// Get a snapshot of the current game state with the current round only.
  /// If [playersToIncludeCardsOnHand] is provided, it includes the cards on hand for the players with the given IDs. If not provided, it does not include the cards on hand.
  GameState snapshot({List<String>? playersToIncludeCardsOnHand}) {
    final s = GameState(
      id: id,
      requiredPlayers: requiredPlayers,
    )
      ..players.addAll(players.map((p) => Player.deepCopy(p, 
        withCardsOnHand: playersToIncludeCardsOnHand != null && playersToIncludeCardsOnHand.contains(p.id))).toList());
    if (currentRound != null) {
      s.rounds.add(currentRound!);
    }
    s.teamScores = TeamScores.from(teamScores);
    s.teamLevelRank = TeamLevelRanks.from(teamLevelRank);
    s.series.addAll(series);
    return s;
  }

  /// Restores the game state from a [snapshot].
  ///
  /// If [reservePlayers] is `true`, the players already in this game state
  /// (identified by seat) are kept; missing players are added from the snapshot.
  /// Existing players in the snapshot are replaced with their local counterparts.
  bool restoreFromSnapshot(GameState snapshot, {bool reservePlayers = true}) {
    if (snapshot.players.length != snapshot.requiredPlayers) return false;
    if (reservePlayers) {
      for (final player in players) {
        final exPlayer = snapshot.players.firstWhere((p) => p.seat == player.seat, orElse: () => player);
        snapshot.replacePlayer(exPlayer, player);
      }
    }
    players.clear();
    players.addAll(snapshot.players);
    teamScores = TeamScores.from(snapshot.teamScores);
    teamLevelRank = TeamLevelRanks.from(snapshot.teamLevelRank);
    rounds.clear();
    rounds.addAll(snapshot.rounds);
    series.clear();
    series.addAll(snapshot.series);
    return true;
  }

  /// Creates a new instance of [GameState], optionally with the given [id] and [requiredPlayers].
  /// 
  /// The [id] is a unique identifier for the game. If not provided, a new UUID is generated.
  /// The [requiredPlayers] is the number of players required to start the game. The default value is 4. Currently, only 4 players are supported.
  GameState({String? id, this.requiredPlayers = 4})
      : players = [],
        //currentLevelRank = CardRank.two,
        teamLevelRank = TeamLevelRanks(),
        rounds = [],
        series = [],
        id = id ?? ''
  {
        if (requiredPlayers != 4) {
          throw Exception('Currently, only 4 players are supported.');
        }
  }
  

  /// The level rank of the current round, or [CardRank.two] if no round has started.
  CardRank get currentLevelRank {
    return currentRound ==null ? CardRank.two : currentRound!.levelRank;
  }

  /// Adds a [player] to the game if not already present. Players are sorted by seat.
  void addPlayer(Player player) {
    if (players.every((p) => p.id != player.id)) {
      players.add(player);
      players.sort((a, b) => a.seat.compareTo(b.seat));
    }
  }

  /// Adds all players from [players] to the game, skipping duplicates.
  void addPlayers(List<Player> players) {
    for (var player in players) {
      addPlayer(player);
    }
  }

  /// Returns the player with the given [playerId]. Throws if not found.
  Player getPlayerById(String playerId) {
    return players.firstWhere((player) => player.id == playerId);
  }

  /// Replaces [exPlayer] with [newPlayer] in both the player list and current round.
  /// 
  /// This could happen when a player leaves the game and replaced by a bot.
  void replacePlayer(Player exPlayer, Player newPlayer){
    var index = players.indexWhere((player) => player.id == exPlayer.id);
    if (index == -1) {
      throw Exception('Player not found in the game.');
    }
    
    if (currentRound != null) {
      currentRound!.replacePlayer(exPlayer, newPlayer);
    }

    players[index] = newPlayer;
  }

  
  /// Whether the current round is ready for gameplay — it exists, has not ended,
  /// has a start player, and tributing is complete.
  bool get currentRoundReady {
    var r = currentRound;
    if (r == null) return false;
    if (r.hasEnded) return false;
    if (r.startPlayer == null) return false;
    if (r.tributeEnabled && !r.isTributeStageCompleted) return false;

    return true;
  }

  /// Whether the Ace-passing (过尖) feature is enabled.
  bool get aPlusEnabled => true;

  /// Whether at least one round has been started.
  bool get hasGameStarted => currentRound != null;

  /// Updates team level ranks after a round ends or via a direct override.
  ///
  /// Two modes:
  /// - Provide [previousRoundResult] to compute the new level rank automatically
  ///   (accounting for Ace-passing rules and round outcome).
  /// - Provide [team] and [levelRank] to set a team's level rank directly.
  ///
  /// The two modes are mutually exclusive.
  CardRank updateTeamLevelRank({RoundResult? previousRoundResult, PlayerTeam? team, CardRank? levelRank}) {

    if (previousRoundResult == null) {
      if (team != null && levelRank != null) {
        teamLevelRank.setLevelRank(team, levelRank);
        return levelRank;
      }
      throw Exception('Either roundResult or team and levelRank should be provided.');
    }

    if (team != null || levelRank != null) {
      throw Exception('Either roundResult or team and levelRank should be provided, but not both.');
    }

    // 如果过尖，更新过尖次数，以及可能的过尖队伍的等级牌
    if (aPlusEnabled) {
      var teamOfLevelRank =  previousRoundResult.teamOfLevelRank; // 前轮的等级牌的队伍
      if (teamOfLevelRank != null && previousRoundResult.levelRank == CardRank.A){ // 且前轮的等级牌是A
          if (previousRoundResult.isAcePassed == true){ // 过尖了
            teamLevelRank.setLevelRank(PlayerTeam.redTeam, CardRank.two); // 回到了2
            teamLevelRank.setLevelRank(PlayerTeam.blueTeam, CardRank.two); // 回到了2
            return CardRank.two;
          }
          else{ // 未过尖
            var tries = previousRoundResult.getAcePassingTries(teamOfLevelRank) ?? 0; // 已经过尖的次数（包括本轮）
            if (tries < 3){ // 还有机会过尖
              if (previousRoundResult.banker!.team == team) return CardRank.A;  // 继续过尖，头游
            }
            else{ // 三次没过尖
              teamLevelRank.setLevelRank(teamOfLevelRank, CardRank.two); //  降级到2
              if (previousRoundResult.banker!.team == teamOfLevelRank){ // 未过尖，但头游
                return CardRank.two;
              }
            }
          }
      }
    }

    // 没有启用过尖，或者前轮没有过尖，或者前轮的等级牌不是A
    if (players.length == 4) {
      var bankerTeam = previousRoundResult.banker!.team;
      int levelUp = 0;
      if (bankerTeam == previousRoundResult.follower!.team) {
        levelUp = 3;
      } 
      else if (bankerTeam == previousRoundResult.third!.team) {
        levelUp = 2;
      } 
      else if (bankerTeam== previousRoundResult.dwellers[0].team) {
        levelUp = 1;
      } 
      else {
        throw Exception('The first player should be in the same team with at least one other player.');
      }
      teamLevelRank.setLevelRank(bankerTeam, CardRank.fromValue(min((teamLevelRank.getLevelRank(bankerTeam)).value + levelUp, CardRank.A.value)));
      return teamLevelRank.getLevelRank(bankerTeam);
    }

    throw UnimplementedError('This function is not implemented for 6 players yet.');
  }

  /// Resets both teams' level ranks back to the default (level 2).
  void resetTeamLevelRank() {
    teamLevelRank = TeamLevelRanks();
  }

  /// The team whose level rank is being played this round.
  /// `null` for the first round or if no round has started.
  PlayerTeam? teamOfCurrentLevelRank() {
    if (currentRound == null) {
      return null;
    }

    if(currentRound!.previousRoundResult == null){
      return null;
    } 

    var bankerOfPreviousRound = currentRound!.previousRoundResult!.banker;
    return bankerOfPreviousRound?.team;
  }

  /// Updates the series tracking when a round starts or ends.
  ///
  /// Passing [start] opens a new series (if none is in progress). Passing [end]
  /// closes the in-progress series and records the winner team. If
  /// [ignoreIfInProgress] is `true`, duplicate/concurrent start/end calls are
  /// silently ignored instead of throwing.
  void updateSeries({Round? start, Round? end, ignoreIfInProgress = true}) {
    if (start == null && end == null) {
      throw Exception('Either start or end rounds is required.');
    }

    if (start != null) {
      if (series.any((s) => s.endRoundId == null)) {
        if (!ignoreIfInProgress){ throw Exception('There is already a series in progress.'); }
        return;
      }
      if (series.any((s) => s.startRoundId == start.id)) {
        return;
      }
      series.add(RoundSeries(start.id));
    }
    else if (end != null) {
      if (series.isEmpty || series.every((s) => s.endRoundId != null) ) {
        if(!ignoreIfInProgress) throw Exception('There is no series in progress.');
        return;
      }
      if (series.where((s) => s.endRoundId == null).length > 1){
        throw Exception('There are multiple series in progress.');
      }
      var s = series.firstWhere((s) => s.endRoundId == null);
      s.endRoundId = end.id;
      s.winnerTeam = end.roundResult.banker!.team;
      if (end.roundResult.isAcePassed == true) {
        teamScores.increaseScore(s.winnerTeam!);
      }
    }
  }


  /// Starts a new round in the game, with the given [levelRank], and optionally [startPlayer], [previousRoundResult], and [roundId].
  /// 
  /// The [levelRank] is the rank of the cards to be played in the round.
  /// The [startPlayer] is the player who starts the round. If not provided, it is determined after the tributing stage.
  /// The [previousRoundResult] is the result of the previous round. It is null for the first round.
  /// The [roundId] is the unique ID of the round. If not provided, a new ID is generated.
  void newRound({Player? startPlayer, RoundResult? previousRoundResult, String? roundId, CardRank? levelRank, bool tributeEnabled = true}) {
    if (previousRoundResult != null){
      var newLevelRank = updateTeamLevelRank(previousRoundResult: previousRoundResult);
      levelRank ??= newLevelRank;
      if (newLevelRank != levelRank) {
        throw Exception('The level rank is not consistent with the result of the previous round.');
      }
    }
    levelRank ??= CardRank.two;
    Round round = Round(players, roundId ?? createRoundId(), levelRank, previousRoundResult: previousRoundResult, 
      startPlayer: startPlayer, tributeEnabled: tributeEnabled);

    rounds.add(round);
    updateSeries(start: round, ignoreIfInProgress: true);
    for (var player in players) {
      player.resetHands();
    }
  }

  /// Generates a unique round ID (e.g. "R1", "R2") by incrementing from the
  /// last round's ID or using [rounds.length + 1].
  String createRoundId({String? previousRoundId}) {
    previousRoundId ??= rounds.isEmpty ? null : rounds.last.id;
    if (previousRoundId != null) {
      var r = int.tryParse(previousRoundId.substring(1));
      r ??= 0;
      return 'R${r + 1}';
    }
    return 'R${rounds.length + 1}';
  }

  /// The current round of the game.
  Round? get currentRound {
    if (rounds.isEmpty) {
      return null;
    }
    return rounds.last;
  }

  /// Assigns [seat] to the player with [playerId].
  ///
  /// Only allowed before the first round starts. The player's team is derived
  /// from the seat via [assignTeam]. Returns `false` if the player is not found
  /// or the seat is already occupied by another player.
  bool setSeat(String playerId, int seat){
    if (currentRound!=null){
      return false;
    }
    if (players.every((p) => p.id != playerId)){
      return false;
    }
    if (players.any((p) => p.seat == seat && p.id != playerId)){
      return false;
    }
  
    var player = players.firstWhere((p) => p.id == playerId);
    player.seat = seat;
    player.team = assignTeam(seat);
    players.sort((a, b) => a.seat.compareTo(b.seat));
    return true;
  }

  /// Derives the team for a given [seat]: odd seats → red, even seats → blue.
  PlayerTeam assignTeam(int seat) {
    return seat % 2 == 1 ? PlayerTeam.redTeam : PlayerTeam.blueTeam;
  }

  /// Number of 54-card standard decks used, equal to `requiredPlayers / 2`.
  int get deckCount {
    return (requiredPlayers / 2).round();
  }

  /// The player whose turn it currently is, or `null` if the game hasn't started
  /// or the round has ended.
  Player? get currentPlayerToPlay {
    try{
      if (currentRound == null) {
        return null;
      }
      if (currentRound!.hasEnded) {
        return null;
      }
      Phase currentPhase = currentRound!.currentPhase;
      if (currentPhase.isEndOfPhase(players)) {
        return currentRound!.startPlayerForNextPhase();
        //throw Exception('Cannot determine the current player at the end of a phase.');
      }
      if (currentPhase.isStartOfPhase) {
        return currentPhase.startPlayer;
      }
      Turn t = currentPhase.lastTurn!;
      var player = nextPlayer(t.player, players, false, true);
      if (player == null) {
        throw Exception('No player found to play the turn.');
      }
      return player;
    }
    catch (e) {
      return null;
    }
  }

  /// Update the start player of the current round.
  void updateStartPlayer(Player startPlayer) {
    Round? r = currentRound;
    if (r != null) {
      r.updateStartPlayer(startPlayer);
    }
  }

  /// The player with [playerId] plays the cards in [cardsToPlay].
  /// Update the game state accordingly and the player's hand.
  void playCards(Player player, Hand cardsToPlay, {String? botCode}) {
    player.play(cardsToPlay);
    currentRound!.currentPhase.appendTurn(player, cardsToPlay, botCode: botCode);
  }

  /// Whether the current player is allowed to pass (must not be the phase starter).
  bool canPass() {
    Phase currentPhase = currentRound!.currentPhase;
    return !currentPhase.isStartOfPhase;
  }

  /// Whether [playerId] can play [cardsToPlay] right now.
  ///
  /// Checks that it is the player's turn, the player actually holds the cards,
  /// and that the cards form a valid play against what's on the table.
  bool canPlay(PokerCardList cardsToPlay, String playerId) {
    Player player = players.firstWhere((p) => p.id == playerId);
    Player? turnPlayer = currentPlayerToPlay;
    if (player.id != turnPlayer?.id) {
      return false;
    }

    if (cardsToPlay.isEmpty) {
      return canPass();
    }

    if (!player.hasCards(cardsToPlay)) {
      return false;
    }

    Hand cardsOnTable = currentRound!.currentPhase.handOnTable;
    return utility.canPlay(cardsToPlay, cardsOnTable, deckCount: deckCount, forced: true);
  }

  
  /// Returns the player occupying [seat], or throws if not found.
  Player? getPlayerBySeat(int seat) {
    return players.firstWhere((player) => player.seat == seat);
  }

  /// Returns the player at the given [position] relative to [anchorPlayer].
  Player? getPlayerByPosition(Player anchorPlayer, PlayerPosition position) {
    int seat = (anchorPlayer.seat + position.value) % players.length;
    seat = seat == 0 ? players.length : seat;
    return getPlayerBySeat(seat);
  }

  /// Adds [card] to the hand of the player with [playerId].
  void addCardToHand(String playerId, PokerCard card) {
    Player player = players.firstWhere((p) => p.id == playerId, orElse: () => throw Exception('Player with ID $playerId not found'));
    player.cardsOnHand!.add(card);
  }

  /// Removes [card] from the hand of the player with [playerId].
  void removeCardFromHand(String playerId, PokerCard card) {
    Player player = players.firstWhere((p) => p.id == playerId, orElse: () => throw Exception('Player with ID $playerId not found'));
    player.cardsOnHand!.removeCard(card);
  }

  /// Converts the game state to a JSON object.
  Map<String, dynamic> toJson({List<String>? includeCardsOnHandForPlayers, bool includePlayedCards = false, bool currentRoundOnly = true, bool includePlayerTypeInfo = false}) {
    return {
      'game_id': id,
      'required_players': requiredPlayers,
      'players': players.map((player) {
        var p = player.toJson(withCardsOnHand: includeCardsOnHandForPlayers!=null && includeCardsOnHandForPlayers.contains(player.id), withPlayedCards: includePlayedCards);
        if (!includePlayerTypeInfo) {
          p['is_human'] = true;
          p.remove('bot_code');
        }
        return p;
      }).toList(),
      'team_level_rank': teamLevelRank.toJson(),
      'team_scores': teamScores.toJson(),
      'series': currentRoundOnly ? [] : series.map((s) => s.toJson()).toList(),
      'rounds': (currentRoundOnly && rounds.isNotEmpty ? rounds.sublist(rounds.length-1) : rounds).map((round) => round.toJson(withCardsOnHand: false, withPlayedCards: false)).toList(),
    };
  }

  /// Creates a game state from a JSON object.
  factory GameState.fromJson(Map<String, dynamic> jsonData) {
    String id = jsonData['game_id'] as String;
    int requiredPlayers = jsonData['required_players'] as int? ?? 4;
    final teamLevelRank = TeamLevelRanks.fromJson(jsonData['team_level_rank'] as Map<String, dynamic>);
    List<Player> players = (jsonData['players'] as List)
        .map((player) {
          return Player.fromJson(player as Map<String, dynamic>);
        })
        .toList();
    List<RoundSeries> series = jsonData['series'] == null ? [] : (jsonData['series'] as List)
        .map((s) => RoundSeries.fromJson(s as Map<String, dynamic>))
        .toList();
    List<Round> rounds = (jsonData['rounds'] as List)
        .map((round) => Round.fromJson(round as Map<String, dynamic>, players: players))
        .toList();
    var state = GameState(id: id, requiredPlayers: requiredPlayers);
    state.addPlayers(players);
    //state.currentLevelRank = currentLevelRank;
    state.teamLevelRank = teamLevelRank;
    state.series = series;

    state.rounds = rounds;
    if (jsonData['team_scores']!=null){
      state.teamScores = TeamScores.fromJson(jsonData['team_scores'] as Map<String, dynamic>);
    }
    //state.stage = stage;
    return state;
  }

  /// Save the game state to a file.
  /// 
  /// If [currentRoundOnly] is true, only the current round is saved.
  void saveToFile(String fullFilePath, {bool currentRoundOnly=true}) async {
    final file = File(fullFilePath);
    final encoder = JsonEncoder.withIndent('  ');
    file.writeAsStringSync(encoder.convert(toJson(includeCardsOnHandForPlayers: players.map((player) => player.id).toList(), includePlayedCards: true, currentRoundOnly: currentRoundOnly)));
    
  }


  /// Load the game state from a file.
  void loadFromFile(String fullJsonFilePath) {
    final file = File(fullJsonFilePath);
    final jsonString = file.readAsStringSync();
    final jsonData = jsonDecode(jsonString) as Map<String, dynamic>;
    loadFromJson(jsonData);
  }

  /// Load the game state from a JSON object.
  void loadFromJson(Map<String, dynamic> jsonData) {
    var newState = GameState.fromJson(jsonData);
    players.clear();
    players.addAll(newState.players);
    teamLevelRank = newState.teamLevelRank;
    rounds = newState.rounds;
    series = newState.series;
    teamScores = newState.teamScores;
    id = newState.id;
  }

  /// The ID of the next turn to be played, or `null` if no round has started.
  String? get currentTurnId {
    if (currentRound == null) {
      return null;
    }
    return currentRound!.currentTurnId;
  }

  /// The ID of the most recently played turn, or `null` if none has been played.
  String? get lastTurnId {
    if(currentRound == null){
      return null;
    }

    if(currentRound!.phases.isEmpty || (currentRound!.phases.length == 1 && currentRound!.currentPhase.isStartOfPhase)){
      if(rounds.length == 1){
        return null;
      }
      return rounds[rounds.length - 2].phases.last.turns.last.id;
    }

    var currentPhase = currentRound!.currentPhase;
    if(currentPhase.turns.isEmpty){
      return currentRound!.phases[currentRound!.phases.length - 2].turns.last.id;
    }

    return currentRound!.currentPhase.lastTurn!.id;
  }

}
