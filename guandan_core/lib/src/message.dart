import 'package:guandan_core/guandan_core.dart';

part 'message.g.dart';

/// Defines all message types, payloads, and message structures used for communication
/// between the client and the game server in the Guandan (掼蛋) card game.
///
/// This file does **not** include token or authentication related messages (such as
/// token refresh, sign in, or sign up), except for admission tickets and reconnection tokens.
///
/// ## Message naming convention
/// - `pXxxRequest` — player-to-server requests (client initiates an action).
/// - `sXxxRequest` — server-to-player requests (server asks the player to act).
/// - `iXxx` — informational broadcasts (server informs all or some players of events).
///
/// ## Serialization
/// Messages are serialized to/from JSON via `toJson()` / `fromJson()`. The factory
/// dispatch is handled by the generated `GameMessageFactory.fromJson()` in
/// [message.g.dart], driven by `@MsgAnnotation` annotations.

/// Reason a player was removed from a game room.
enum RemovalReason {
  /// The player exceeded the inactivity timeout.
  inactive,

  /// The player's network connection was lost.
  disconnected,

  /// The player was kicked by the room owner.
  kicked,

  /// The removal reason is unknown or unspecified.
  unknown;

  /// Parses a [RemovalReason] from its JSON-encoded [name] string.
  factory RemovalReason.fromName(String name) {
    return RemovalReason.values.firstWhere((e) => e.name == name);
  }
}

/// Represents the outcome of a request processed by the server.
///
/// Returned as the `result` field of [RequestResultMessage].
enum ServerResponseCode {
  /// The request was processed successfully.
  success,

  /// An unexpected internal server error occurred.
  internalError,

  /// The server received a message type it does not recognize.
  unknownMessage,

  /// The player is not allowed to request more time (e.g. in a timed room).
  extraTimeNotAllowed,

  /// The player is not currently in a game room.
  notInGameRoom,

  /// The specified player ID was not found on the server.
  playerIdNotFound,

  /// The requested room does not exist or is invalid.
  roomNotFound,

  /// The room is already at maximum capacity.
  roomFull,

  /// A room with the requested identifier already exists.
  roomExists,

  /// The player is already in a (different) room.
  alreadyInRoom,

  /// The game has already started and the requested action cannot be performed.
  gameAlreadyStarted,

  /// The hand of cards the player attempted to play is invalid.
  invalidHand,

  /// The tribute card the player attempted to pay is invalid.
  invalidTributeCard,

  /// The return card the player attempted to send back is invalid.
  invalidReturnCard,

  /// The player is not the room owner but tried to perform an owner-only action.
  notRoomOwner,

  /// The round has not ended, but the player requested to start the next round.
  roundNotEnded,

  /// The player has already paid tribute for this round.
  alreadyPaidTribute,

  /// The player has already returned a card for tribute this round.
  alreadyReturnedTribute,

  /// The reconnection token or join ticket is invalid.
  invalidToken,

  /// The player is not authorized to perform this action.
  notAuthorized,

  /// The requested seat number is invalid (out of range).
  invalidSeat,

  /// The requested seat is already taken and not available.
  seatNotAvailable;

  /// Parses a [ServerResponseCode] from its JSON-encoded [name] string.
  factory ServerResponseCode.fromName(String name) {
    return ServerResponseCode.values.firstWhere((e) => e.name == name);
  }

  /// Parses a [ServerResponseCode] from its ordinal [index].
  factory ServerResponseCode.fromIndex(int index) {
    return ServerResponseCode.values.firstWhere((e) => e.index == index);
  }
}

/// Identifies the type of a [GameMessage] sent over the network.
///
/// Naming convention:
/// - `pXxxRequest` — player-to-server request (client initiates an action).
/// - `sXxxRequest` — server-to-player request (server asks the player to act).
/// - `iXxx` — informational broadcast (server pushes event to players).
///
/// Used as the discriminator in JSON serialization (`"type"` field) and as the
/// routing key in [GameMessageFactory.fromJson].
enum MessageType {
  // ── Player-to-server requests ───────────────────────────────────────────

  /// Player requests to create a game room.
  pCreateRoomRequest,

  /// Player requests to join an existing game room.
  pJoinRoomRequest,

  /// Player requests to quit the current game room.
  pQuitRoomRequest,

  /// Player sends a tribute card (进贡) to a higher-ranked opponent.
  pPayTributeRequest,

  /// Player plays a hand of cards during their turn.
  pPlayHandRequest,

  /// Player requests additional time for their current action.
  pMoreTimeRequest,

  /// Player requests to take or change a seat in the room.
  pSeatRequest,

  /// Player sends a card back (还牌) in response to receiving a tribute.
  pReturnCardRequest,

  /// Player (room owner) requests to start the game.
  pStartGameRequest,

  /// Player requests to start a new round after the previous round ended.
  pNewRoundRequest,

  // ── Server-to-player requests ───────────────────────────────────────────

  /// Server asks a player to play a hand (it is their turn).
  sPlayHandRequest,

  /// Server asks a player to select a tribute card to pay.
  sTributeCardRequest,

  /// Server asks a player to select a card to return in response to a tribute.
  sReturnCardRequest,

  // ── Informational broadcasts (server → players) ─────────────────────────

  /// Broadcast when a game room is created.
  iGameRoomCreated,

  /// Broadcast when a new player joins the room.
  iPlayerJoinedRoom,

  /// Broadcast when a player quits the room.
  iPlayerQuitRoom,

  /// Sent to a player when they are removed from the room (e.g. inactivity).
  iPlayerRemovedFromRoom,

  /// Broadcast when the room owner changes (e.g. current owner leaves).
  iRoomOwner,

  /// Broadcast when the game room is closed.
  iGameRoomClosed,

  /// Broadcast when the server is shutting down.
  iServerClosed,

  /// Broadcast when a player takes or changes a seat.
  iPlayerSeat,

  /// Broadcast when a game starts.
  iGameStarted,

  /// Broadcast when a new round starts. Contains player hands and round info.
  iNewRound,

  /// Broadcast when a round ends.
  iRoundEnded,

  /// Broadcast to inform players who the start player is.
  iStartPlayer,

  /// Broadcast when a new phase (turn cycle) starts.
  iNewPhase,

  /// Broadcast when a player successfully plays a hand of cards.
  iHandPlayed,

  /// Sent to a player with the remaining card counts of other players.
  iCardsOnHand,

  /// Sent to a player when they time out on a request.
  iTimeOut,

  /// Broadcast when a player empties their hand (plays their last card).
  iPlayerEmptiedHand,

  /// Broadcast with the (potentially partial) round result.
  iRoundResult,

  /// Broadcast when a player 接风 (leads the next phase because their teammate
  /// emptied their hand and no opponent followed).
  iJieFeng,

  /// Broadcast when the entire game ends.
  iGameEnded,

  /// Broadcast when team scores are updated.
  iTeamScores,

  /// Broadcast when a tribute card is paid.
  iTributeCard,

  /// Broadcast when the tribute is resisted (抗贡).
  /// Contains red joker counts that determined the resistance.
  iTributeResistance,

  /// Broadcast when a card is returned in response to a tribute.
  iReturnCard,

  /// Broadcast when all tributes and returns for the round are complete.
  iTributeResult,

  /// Sent to a player when additional time is granted.
  iMoreTimeGranted,

  /// Sent to a player with the result (accepted/declined) and reason for a
  /// previous request.
  iRequestResult,

  /// Chat message — sent by a player and broadcast to all players in the room.
  /// Heartbeat sent periodically by clients to info health of the client.
  heartbeat,

  /// Auto-delegation (托管) — automatic play via a choosen bot.
  autoDelegated;

  /// Parses a [MessageType] from its JSON-encoded [name] string.
  factory MessageType.from(String name) {
    return MessageType.values.firstWhere((e) => e.name == name);
  }

  /// Returns the enum [name] as the JSON wire value.
  String get value {
    return name;
  }
}

/// Identifies the type of a [MessagePayload] embedded in a [RequestResultMessage].
///
/// Each value corresponds to a concrete [MessagePayload] subclass used to carry
/// extra context when a request fails or requires additional information.
enum PayloadType {
  /// Payload containing info about the player's previous game room.
  /// Used when the player is still in a room and tries to join/create another.
  previousGameRoom,

  /// Payload for a failed join-room request, carrying room info and bot list.
  joinRoomResponse,

  /// Payload for a failed play-hand request, carrying the invalid hand.
  playHandResponse,

  /// Payload for a failed pay-tribute request, carrying the invalid tribute card.
  payTributeResponse,

  /// Payload for a failed return-card request, carrying the invalid return card.
  returnCardResponse;

  /// Parses a [PayloadType] from its JSON-encoded [name] string.
  factory PayloadType.from(String name) {
    return PayloadType.values.firstWhere((e) => e.name == name);
  }
}

/// Base class for message payloads embedded in [RequestResultMessage].
///
/// Payloads carry extra data when a request fails or requires additional
/// context. They are serialized as part of the `"payload"` field.
///
/// Subclasses are dispatched by [MessagePayload.fromJson] based on the
/// `"type"` discriminator.
abstract class MessagePayload {
  /// The discriminator identifying which concrete payload subclass this is.
  PayloadType type;

  /// Serializes this payload to a JSON-compatible map.
  Map<String, dynamic> toJson() {
    return {
      'type': type.name,
    };
  }

  MessagePayload({required this.type});

  /// Deserializes a [MessagePayload] from JSON, or returns `null` if [json]
  /// is null or empty.
  ///
  /// Dispatches to the correct subclass based on the `"type"` field.
  static MessagePayload? fromJson(Map<String, dynamic>? json) {
    if (json == null || json.isEmpty) {
      return null;
    }
    final type = PayloadType.from(json['type']);
    switch (type) {
      case PayloadType.joinRoomResponse:
        return JoinRoomResponsePayload.fromJson(json);
      case PayloadType.playHandResponse:
        return PlayHandResponsePayload.fromJson(json);
      case PayloadType.payTributeResponse:
        return PayTributeResponsePayload.fromJson(json);
      case PayloadType.returnCardResponse:
        return ReturnCardResponsePayload.fromJson(json);
      case PayloadType.previousGameRoom:
        return PreviousGameRoomPayload.fromJson(json);
    }
  }
}

/// Payload carrying the player's previous game room information.
///
/// Sent by the server when a player attempts to join or create a new room
/// while still in an existing room, or when the player logs back in and the
/// previous room is still active.
class PreviousGameRoomPayload extends MessagePayload {
  /// Information about the player's currently active game room.
  final RoomMetadata roomInfo;

  PreviousGameRoomPayload({
    required this.roomInfo,
  }) : super(type: PayloadType.previousGameRoom);

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['room_info'] = roomInfo.toJson();
    return json;
  }

  factory PreviousGameRoomPayload.fromJson(Map<String, dynamic> json) {
    return PreviousGameRoomPayload(
      roomInfo: RoomMetadata.fromJson(json['room_info']),
    );
  }
}

/// Payload for a failed join-room request.
///
/// Carries room info and the list of bots currently in the room, which the
/// joining player may choose to replace if the room is full.
class JoinRoomResponsePayload extends MessagePayload {
  /// Information about the target game room.
  final RoomMetadata roomInfo;

  /// Bots currently occupying seats in the room, eligible for replacement by
  /// a human player joining a full room.
  final List<Player> bots;

  JoinRoomResponsePayload({
    required this.roomInfo,
    required this.bots,
  }) : super(type: PayloadType.joinRoomResponse);

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['room_info'] = roomInfo.toJson();
    json['bots'] = bots.map((bot) => bot.toJson(withCardsOnHand: false, withPlayedCards: false)).toList();
    return json;
  }

  factory JoinRoomResponsePayload.fromJson(Map<String, dynamic> json) {
    return JoinRoomResponsePayload(
      roomInfo: RoomMetadata.fromJson(json['room_info']),
      bots: json['bots'] == null ? [] : (json['bots'] as List).map((bot) => Player.fromJson(bot)).toList(),
    );
  }
}

/// Payload for a failed play-hand request.
///
/// Carries the player ID and the invalid hand that was rejected by the server.
class PlayHandResponsePayload extends MessagePayload {
  /// The player who attempted to play the hand.
  final String playerId;

  /// The cards the player attempted to play (rejected as invalid).
  final PokerCardList cards;

  PlayHandResponsePayload({
    required this.playerId,
    required this.cards,
  }) : super(type: PayloadType.playHandResponse);

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['cards'] = cards.toString();
    return json;
  }

  factory PlayHandResponsePayload.fromJson(Map<String, dynamic> json) {
    return PlayHandResponsePayload(
      playerId: json['player_id'],
      cards: PokerCardList.fromString(json['cards']),
    );
  }
}


/// Payload for a failed pay-tribute request.
///
/// Carries the player ID and the invalid tribute card that was rejected.
class PayTributeResponsePayload extends MessagePayload {
  /// The player who attempted to pay tribute.
  final String playerId;

  /// The tribute card the player attempted to pay (rejected as invalid).
  final PokerCard tributeCard;

  PayTributeResponsePayload({
    required this.playerId,
    required this.tributeCard,
  }) : super(type: PayloadType.payTributeResponse);

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['tribute_card'] = tributeCard.toString();
    return json;
  }

  factory PayTributeResponsePayload.fromJson(Map<String, dynamic> json) {
    return PayTributeResponsePayload(
      playerId: json['player_id'],
      tributeCard: PokerCard.from(json['tribute_card']),
    );
  }
}

/// Payload for a failed return-card request.
///
/// Carries the player ID and the invalid return card that was rejected.
class ReturnCardResponsePayload extends MessagePayload {
  /// The player who attempted to return a card.
  final String playerId;

  /// The card the player attempted to return in response to a tribute.
  final PokerCard returnCard;

  ReturnCardResponsePayload({
    required this.playerId,
    required this.returnCard,
  }) : super(type: PayloadType.returnCardResponse);

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['return_card'] = returnCard.toString();
    return json;
  }

  factory ReturnCardResponsePayload.fromJson(Map<String, dynamic> json) {
    return ReturnCardResponsePayload(
      playerId: json['player_id'],
      returnCard: PokerCard.from(json['return_card']),
    );
  }
} 

/// Annotation marking a message class for inclusion in the generated
/// [GameMessageFactory.fromJson] dispatch.
///
/// Used by the code generator ([message_helper.dart]) to produce the switch
/// statement in [message.g.dart] that routes JSON `"type"` strings to the
/// correct [GameMessage] subclass.
class MsgAnnotation {
  /// The [MessageType] this class corresponds to on the wire.
  final MessageType type;
  const MsgAnnotation(this.type);
}

/// Base class for all messages exchanged between client and game server.
///
/// Every message has a [type] discriminator and an optional [messageId] for
/// request-response correlation. 
///
/// Subclasses add domain-specific fields and are serialized/deserialized via
/// [toJson] / [fromJson]. Runtime dispatch from raw JSON is handled by the
/// generated [GameMessageFactory.fromJson] in [message.g.dart].
class GameMessage {
  /// The message type discriminator, used as the `"type"` JSON field.
  final MessageType type;

  /// Optional unique identifier for request-response correlation.
  String? messageId;


  GameMessage({required this.type, this.messageId});

  factory GameMessage.fromJson(Map<String, dynamic> json) {
    return GameMessage(
      type: MessageType.from(json['type']),
      messageId: json['message_id'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type.value,
      'message_id': messageId,
    };
  }
}


/// Base class for messages scoped to a specific game room.
///
/// Extends [GameMessage] with a [roomId] that identifies the target game room
/// and a [gameId] that identifies the game instance. Most game-related messages
/// inherit from this class, except for [RequestResultMessage] (which may carry
/// its own optional [roomId]).
///
/// The [gameId] is a UUID generated when [GameState] is created. It is distinct
/// from [roomId]: the room identifies the logical room, while the game
/// identifies a specific game instance within that room.
class GameRoomMessage extends GameMessage {
  /// The unique identifier of the game room this message relates to.
  final String roomId;

  /// The unique identifier of the game instance.
  ///
  /// This is a UUID v4 generated when the [GameState] is first created.
  /// It is distinct from [roomId] — a room may persist across multiple
  /// games, or be reused, while the game ID is unique per game instance.
  final String  gameId;

  GameRoomMessage({required super.type, super.messageId, required this.roomId, required this.gameId});


  factory GameRoomMessage.fromJson(Map<String, dynamic> json) {
    return GameRoomMessage(
      type: MessageType.from(json['type']),
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'] ?? ''
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['room_id'] = roomId;
    json['game_id'] = gameId;
    return json;
  }
}

/// Broadcast to all players when a new round starts.
///
/// Each player receives their own copy with [hand] containing their personal
/// dealt cards. The message includes the round metadata, level rank, team-level
/// ranks, player roster, and optional previous round result.
///
/// Sent by [GameRoom._dealCardsAndSendToPlayers] in [game_room.dart].
@MsgAnnotation(MessageType.iNewRound)
class NewRoundMessage extends GameRoomMessage {
  /// Unique identifier for this round (e.g. `"R1"`, `"R2"`).
  final String roundId;

  /// The player ID of the start player for this round, or null if not yet determined.
  final String? startPlayerId;

  /// The level rank (card rank) for this round, e.g. `"2"`.
  final CardRank levelRank;

  /// The level rank for each team, keyed by team ID.
  final TeamLevelRanks teamLevelRank;

  /// The result of the previous round, or null if this is the first round.
  final RoundResult? previousRoundResult;

  /// All players in the room (IDs, seats, teams). Cards-on-hand are stripped.
  final List<Player> players;

  /// The cards dealt to the receiving player for this round.
  final PokerCardList hand;

  /// Whether this is the first round of the game (no previous round exists).
  bool get isFirstRound => previousRoundResult == null;

  NewRoundMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.roundId,
    this.startPlayerId,
    required this.levelRank,
    required this.teamLevelRank,
    this.previousRoundResult,
    required this.players,
    required this.hand,
  }) : super(type: MessageType.iNewRound);

  factory NewRoundMessage.fromJson(Map<String, dynamic> json) {
    final rawPlayers = json['players'] as List;
    final players = rawPlayers.map((playerJson) => Player.fromJson(playerJson)).toList();
    return NewRoundMessage(
      players: players,
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      roundId: json['round_id'],
      startPlayerId: json['start_player_id'],
      levelRank: CardRank(json['level_rank']),
      teamLevelRank: TeamLevelRanks.fromJson(json['team_level_rank'] as Map<String, dynamic>),
      previousRoundResult: json['previous_round_result'] != null ? RoundResult.fromJson(json['previous_round_result'], players) : null,
      hand: Hand.fromString(json['hand']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['round_id'] = roundId;
    json['start_player_id'] = startPlayerId;
    json['level_rank'] = levelRank.name;
    json['team_level_rank'] = teamLevelRank.toJson();
    json['previous_round_result'] = previousRoundResult?.toJson();
    json['players'] = players.map((player) => player.toJson(withCardsOnHand: false)).toList();
    json['hand'] = hand.toString();
    return json;
  }
}

/// Broadcast when a new phase (turn cycle) starts within a round.
///
/// A phase groups one or more turns where each player gets to play in sequence.
/// A new phase starts when the previous phase ends (e.g. after 接风).
@MsgAnnotation(MessageType.iNewPhase)
class NewPhaseMessage extends GameRoomMessage {
  /// Unique identifier for this phase within the round.
  final String phaseId;

  /// The player ID who leads (starts) this phase.
  final String startPlayerId;

  NewPhaseMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,

    required this.phaseId,
    required this.startPlayerId,
  }) : super(type: MessageType.iNewPhase);

  factory NewPhaseMessage.fromJson(Map<String, dynamic> json) {
    return NewPhaseMessage(
      messageId: json['message_id'],
      phaseId: json['phase_id'],
      startPlayerId: json['start_player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['phase_id'] = phaseId;
    json['start_player_id'] = startPlayerId;
    return json;
  }
}


/// Broadcast to inform players who the start player is for a round or phase.
///
/// Sent when the start player is determined, e.g. after tribute resolution or
/// at the beginning of a new phase.
@MsgAnnotation(MessageType.iStartPlayer)
class StartPlayerMessage extends GameRoomMessage {
  /// The player ID of the start player.
  final String startPlayerId;

  /// The round in which this player starts.
  final String roundId;

  /// The phase in which this player starts.
  final String phaseId;

  StartPlayerMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.startPlayerId,
    required this.roundId,
    required this.phaseId,
  }) : super(type: MessageType.iStartPlayer);

  factory StartPlayerMessage.fromJson(Map<String, dynamic> json) {
    return StartPlayerMessage(
      messageId: json['message_id'],
      startPlayerId: json['start_player_id'],
      roundId: json['round_id'],
      phaseId: json['phase_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['start_player_id'] = startPlayerId;
    json['round_id'] = roundId;
    json['phase_id'] = phaseId;
    return json;
  }
}


@MsgAnnotation(MessageType.iHandPlayed)
class HandPlayedMessage extends GameRoomMessage {
  /// The player who played the cards.
  final String playerId;

  /// The round in which the cards were played.
  final String roundId;

  /// The phase within the round.
  final String phaseId;

  /// The turn within the phase. Each turn represents one player's play action.
  final String turnId;

  /// The cards that were played, including their deduced hand type.
  final Hand cards;

  /// The seat number (1–4) of the player who played the cards.
  final int seat;

  /// The bot model/code that played the cards, if the player is a bot.
  final String? botCode;

  HandPlayedMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.roundId,
    required this.phaseId,
    required this.turnId,
    required this.cards,
    required this.seat,
    this.botCode,
  }) : super(type: MessageType.iHandPlayed);

  factory HandPlayedMessage.fromJson(Map<String, dynamic> json) {
    return HandPlayedMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roundId: json['round_id'],
      phaseId: json['phase_id'],
      turnId: json['turn_id'],
      cards: Hand.fromString(json['cards']),
      seat: json['seat'] ?? 0,
      botCode: json['bot_code'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['round_id'] = roundId;
    json['phase_id'] = phaseId;
    json['turn_id'] = turnId;
    json['cards'] = cards.toString();
    json['seat'] = seat;
    if (botCode != null) {
      json['bot_code'] = botCode;
    }
    return json;
  }

  @override
  String toString() {
    return 'HandPlayedMessage{type: $type, playerId: $playerId, seat: $seat, gameId: $gameId, roundId: $roundId, phaseId: $phaseId, turnId: $turnId, cards: $cards}';
  }
}

/// Broadcast when all tributes and returns for a round are complete.
///
/// Contains the resolved [TributeResult] which maps payers to winners and
/// records the tribute/return cards.
@MsgAnnotation(MessageType.iTributeResult)
class TributeResultMessage extends GameRoomMessage {
  /// The resolved tribute result for the round.
  final TributeResult tributeResult;

  /// The round this tribute result applies to.
  final String roundId;

  TributeResultMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.tributeResult,
    required this.roundId,
  }) : super(type: MessageType.iTributeResult);

  factory TributeResultMessage.fromJson(Map<String, dynamic> json, {List<Player>? players}) {
    return TributeResultMessage(
      messageId: json['message_id'],
      tributeResult: TributeResult.fromJson(json['tribute_result'], players),
      roundId: json['round_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['tribute_result'] = tributeResult.toJson();
    json['round_id'] = roundId;
    return json;
  }
}

/// Abstract base for server-to-player request messages within a game room.
///
/// Adds a [timeout] duration, the [playerId] of the targeted player, and the
/// [roundId] to a [GameRoomMessage]. Subclasses represent specific requests
/// like playing a hand, paying tribute, or returning a card.
///
/// Concrete subclasses: [ServerPlayHandRequest], [ServerTributeRequest],
/// [ServerReturnCardRequest].
abstract class ServerRequestMessage extends GameRoomMessage {
  ServerRequestMessage({
    required super.type,
    required super.roomId,
    required super.gameId,
    required super.messageId,
    this.timeout,
    required this.playerId,
    required this.roundId,
  });

  /// How long the player has to respond before timing out, or null if no limit.
  final Duration? timeout;

  /// The player being asked to perform the action.
  final String playerId;

  /// The round this request relates to.
  final String roundId;

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['timeout'] = timeout?.inSeconds;
    json['player_id'] = playerId;
    json['round_id'] = roundId;
    return json;
  }
}


/// Sent by the server to a player when it is their turn to play cards.
///
/// Includes the current hand on the table that must be responded to, the level
/// rank, and the player's available cards. [gameStateSnapshot] provides a
/// full game state view for the receiving player (including their own hand).
///
/// [handOnTable] is empty at the start of a phase (the player leads).
@MsgAnnotation(MessageType.sPlayHandRequest)
class ServerPlayHandRequest extends ServerRequestMessage {
  ServerPlayHandRequest({
    required super.roomId,
    required super.gameId,
    required super.messageId,
    super.timeout,
    required super.playerId,
    required this.handOnTable,
    required this.seatOfHandOnTable,
    required this.levelRank,
    required super.roundId,
    required this.turnId,
    this.availableCards,
    this.gameStateSnapshot,
  }) : super(type: MessageType.sPlayHandRequest);

  /// The hand currently on the table that the player must respond to.
  /// Empty ([Hand.empty]) at the start of a phase when the player leads.
  final Hand handOnTable;

  /// Unique identifier for this turn within the phase.
  final String turnId;

  /// Cards available to the receiving player (only non-null for the target).
  final PokerCardList? availableCards;

  /// The level rank for this round, determining which cards are wild.
  final CardRank levelRank;

  /// A snapshot of the full game state visible to the receiving player.
  final GameState? gameStateSnapshot;

  /// The seat of the player who played [handOnTable], or null at phase start.
  final int? seatOfHandOnTable;

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['hand_on_table'] = handOnTable.toString();
    json['turn_id'] = turnId;
    if (availableCards != null) {
      json['available_cards'] = availableCards.toString();
    }
    json['level_rank'] = levelRank.name;
    if (seatOfHandOnTable != null) {
      json['seat_of_hand_on_table'] = seatOfHandOnTable;
    }
    if (gameStateSnapshot != null) {
      json['game_state_snapshot'] = gameStateSnapshot!.toJson(includeCardsOnHandForPlayers: [playerId], includePlayedCards: true);
    }
    return json;
  }

  factory ServerPlayHandRequest.fromJson(Map<String, dynamic> json) {
    return ServerPlayHandRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      timeout: json['timeout'] != null ? Duration(seconds: json['timeout']) : null,
      roundId: json['round_id']!,
      handOnTable: Hand.fromString(json['hand_on_table']),
      seatOfHandOnTable: json['seat_of_hand_on_table'] != null ? int.tryParse(json['seat_of_hand_on_table'].toString()) : null,
      turnId: json['turn_id'],
      roomId: json['room_id']!,
      gameId: json['game_id'],
      levelRank: CardRank(json['level_rank']),
      availableCards: json['available_cards'] != null ? PokerCardList.fromString(json['available_cards']) : null,
      gameStateSnapshot: json['game_state_snapshot'] != null ? GameState.fromJson(json['game_state_snapshot']) : null,
    );
  }
}

/// Represents a request message sent to a player to pay a tribute.
/// This message includes the tribute card, the player who pays the tribute, and the game and round IDs.
/// Sent by the server to a player requesting them to select a tribute card (进贡).
///
/// [availableCards] is set only for the target player (null for other recipients
/// of the broadcast).
@MsgAnnotation(MessageType.sTributeCardRequest)
class ServerTributeRequest extends ServerRequestMessage {
  ServerTributeRequest({
    required super.messageId,
    super.timeout,
    required super.playerId,
    required super.roundId,
    required super.roomId,
    required super.gameId,
    this.availableCards,
  }) : super(type: MessageType.sTributeCardRequest);

  /// Cards available for the target player to choose a tribute from.
  /// Only non-null for the player being asked to pay tribute.
  final PokerCardList? availableCards;

  factory ServerTributeRequest.fromJson(Map<String, dynamic> json) {
    return ServerTributeRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      timeout: json['timeout'] != null ? Duration(seconds: json['timeout']) : null,
      roundId: json['round_id']!,
      roomId: json['room_id']!,
      gameId: json['game_id'],
      availableCards: json['available_cards'] != null ? PokerCardList.fromString(json['available_cards']) : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    if (availableCards != null) {
      json['available_cards'] = availableCards!.toString();
    }
    return json;
  }
}


/// Sent by the server to a player requesting them to return a card (还牌)
/// in response to receiving a tribute.
///
/// [availableCards] is set only for the target player — the card chosen from
/// these will be sent back to the tribute payer.
@MsgAnnotation(MessageType.sReturnCardRequest)
class ServerReturnCardRequest extends ServerRequestMessage {
  ServerReturnCardRequest({
    required super.messageId,
    super.timeout,
    required super.playerId,
    required super.roundId,
    required super.roomId,
    required super.gameId,
    this.availableCards,
  }) : super(type: MessageType.sReturnCardRequest);

  /// The available cards that can be returned by the player.
  /// This field is only non-null when the receiver of this message is the player requested to return a card.
  final PokerCardList? availableCards;

  factory ServerReturnCardRequest.fromJson(Map<String, dynamic> json) {
    return ServerReturnCardRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      timeout: json['timeout'] != null ? Duration(seconds: json['timeout']) : null,
      roundId: json['round_id']!,
      roomId: json['room_id']!,
      gameId: json['game_id'],
      availableCards: json['available_cards'] != null ? PokerCardList.fromString(json['available_cards']) : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    if (availableCards != null) {
      json['available_cards'] = availableCards!.toString();   
    }
    return json;
  }
}


/// Abstract base for player-to-server request messages within a game room.
///
/// Adds the requesting [playerId] to a [GameRoomMessage]. Subclasses represent
/// specific player actions like joining a room, playing cards, paying tribute,
/// or starting a game.
///
/// Concrete subclasses: [JoinRoomRequest], [QuitRoomRequest],
/// [PlayerPlayHandRequest], [PlayerPayTributeRequest], [PlayerReturnCardRequest],
/// [NewRoundRequest], [StartGameRequest], [CreateRoomRequest],
/// [MoreTimeRequest], [SeatRequest].
abstract class PlayerRequestMessage extends GameRoomMessage {
  /// The ID of the player making this request.
  final String playerId;

  PlayerRequestMessage({
    required super.roomId,
    required super.gameId,
    required super.type,
    super.messageId,
    required this.playerId,
  });

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    return json;
  }
}

/// Player-to-server request to join a game room.
///
/// May include a [joinTicket] (lobby-issued admission token) or a
/// [reconnectToken] (for reconnecting after a disconnection). If the room is
/// full, [replacedPlayerId] can specify a bot to replace.
@MsgAnnotation(MessageType.pJoinRoomRequest)
class JoinRoomRequest extends PlayerRequestMessage {
  /// The ID of a bot to replace if the room is full, or null.
  final String? replacedPlayerId;

  /// The player's display name for use in the room.
  ///
  /// The lobby server is the authoritative source for profiles; this field
  /// provides an optional initial display name that the game server can use.
  final String? displayName;

  /// A lobby-issued admission ticket granting access to this room.
  final String? joinTicket;

  /// A cryptographically secure token that allows the player to rejoin the
  /// same runtime room after a network disconnection without presenting a
  /// new lobby-issued admission ticket.
  final String? reconnectToken;

  JoinRoomRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    String? gameId, // optional, '' if null
    this.replacedPlayerId,
    this.displayName,
    this.joinTicket,
    this.reconnectToken,
  }) : super(type: MessageType.pJoinRoomRequest, gameId: gameId ?? '');

  factory JoinRoomRequest.fromJson(Map<String, dynamic> json) {
    return JoinRoomRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'] ?? '',
      replacedPlayerId: json['replaced_player_id'],
      displayName: json['display_name'] as String?,
      joinTicket: json['join_ticket'] as String?,
      reconnectToken: json['reconnect_token'] as String?,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    if (replacedPlayerId != null) {
      json['replaced_player_id'] = replacedPlayerId;
    }
    if (displayName != null) {
      json['display_name'] = displayName;
    }
    if (joinTicket != null) {
      json['join_ticket'] = joinTicket;
    }
    if (reconnectToken != null) {
      json['reconnect_token'] = reconnectToken;
    }
    return json;
  }
}


/// Player-to-server request to leave the current game room.
@MsgAnnotation(MessageType.pQuitRoomRequest)
class QuitRoomRequest extends PlayerRequestMessage {
  QuitRoomRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    String? gameId,
  }) : super(type: MessageType.pQuitRoomRequest, gameId: gameId ?? '');

  factory QuitRoomRequest.fromJson(Map<String, dynamic> json) {
    return QuitRoomRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'] ?? '',
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    return json;
  }
}

/// Player-to-server request to play a hand of cards.
///
/// Includes the cards being played, identified by [roundId] and [turnId].
/// For bots, [botCode] identifies the bot making the play.
@MsgAnnotation(MessageType.pPlayHandRequest)
class PlayerPlayHandRequest extends PlayerRequestMessage {
  /// The cards being played (hand type is deduced during deserialization).
  final PokerCardList cards;

  /// The round in which the cards are played.
  final String roundId;

  /// The turn within the phase this play responds to.
  final String turnId;

  /// The bot model/code making this play, if the player is a bot.
  final String? botCode;

  PlayerPlayHandRequest({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required super.playerId,
    required this.cards,
    required this.roundId,
    required this.turnId,
    this.botCode,
  }) : super(type: MessageType.pPlayHandRequest);

  factory PlayerPlayHandRequest.fromJson(Map<String, dynamic> json) {
    return PlayerPlayHandRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      cards: deduceHandType(PokerCardList.fromString(json['cards'])),
      roundId: json['round_id'],
      turnId: json['turn_id'],
      botCode: json['bot_code'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['cards'] = cards.toString();
    json['round_id'] = roundId;
    json['turn_id'] = turnId;
    if (botCode != null) {
      json['bot_code'] = botCode;
    }
    return json;
  }
}


/// Player-to-server request to pay a tribute card (进贡) to a higher-ranked opponent.
@MsgAnnotation(MessageType.pPayTributeRequest)
class PlayerPayTributeRequest extends PlayerRequestMessage {

  /// The tribute card that the player attempts to pay.
  final PokerCard tribute;

  /// The ID of the round this tribute is related to.
  final String roundId;

  /// The model/code of the bot that is attempting to pay the tribute, if applicable.
  final String? botCode;

  PlayerPayTributeRequest({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required super.playerId,
    required this.tribute,
    required this.roundId,
    this.botCode,
  }) : super(type: MessageType.pPayTributeRequest);

  factory PlayerPayTributeRequest.fromJson(Map<String, dynamic> json) {
    return PlayerPayTributeRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      tribute: PokerCard.from(json['tribute_card']),
      roundId: json['round_id'],
      botCode: json['bot_code'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['tribute_card'] = tribute.toString();
    json['round_id'] = roundId;
    if (botCode != null) {
      json['bot_code'] = botCode;
    }
    return json;
  }
}

/// Player-to-server request to return a card (还牌) in response to receiving a tribute.
@MsgAnnotation(MessageType.pReturnCardRequest)
class PlayerReturnCardRequest extends PlayerRequestMessage {

  /// The card that the player attempts to return.
  final PokerCard returnCard;

  /// The ID of the round this return card request is related to.
  final String roundId;

  /// The model/code of the bot that is attempting to return the card, if applicable.
  final String? botCode;

  PlayerReturnCardRequest({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required super.playerId,
    required this.returnCard,
    required this.roundId,
    this.botCode,
  }) : super(type: MessageType.pReturnCardRequest);

  factory PlayerReturnCardRequest.fromJson(Map<String, dynamic> json) {
    return PlayerReturnCardRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      returnCard: PokerCard.from(json['return_card']),
      roundId: json['round_id'],
      botCode: json['bot_code'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['return_card'] = returnCard.toString();
    json['round_id'] = roundId;
    if (botCode != null) {
      json['bot_code'] = botCode;
    }
    return json;
  }
}

/// Player-to-server request to start the next round.
///
/// Sent by the room owner after a round ends. If the game hasn't started yet,
/// the server treats this as a request to start the game instead.
@MsgAnnotation(MessageType.pNewRoundRequest)
class NewRoundRequest extends PlayerRequestMessage {

  NewRoundRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    required super.gameId,
  }) : super(type: MessageType.pNewRoundRequest);

  factory NewRoundRequest.fromJson(Map<String, dynamic> json) {
    return NewRoundRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }
}


/// Player-to-server request (from room owner) to start the game.
///
/// Optionally carries a [gameStateSnapshot] to restore/resume from a previous
/// state, [startPlayerSeat] and [levelRank] overrides, and a [fillWithBots]
/// flag (defaults to true) that automatically fills empty seats with bots.
@MsgAnnotation(MessageType.pStartGameRequest)
class StartGameRequest extends PlayerRequestMessage {
  /// An optional snapshot of the game state to restore or start from.
  final GameState? gameStateSnapshot;

  /// Override for the starting player's seat (1–4), or null for default.
  final int? startPlayerSeat;

  /// Override for the level rank, or null for default.
  final CardRank? levelRank;

  /// Whether to automatically fill empty seats with bots. Defaults to true.
  final bool fillWithBots;

  StartGameRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    required super.gameId,
    this.gameStateSnapshot,
    this.startPlayerSeat,
    this.levelRank,
    this.fillWithBots = true,
  }) : super(type: MessageType.pStartGameRequest);

  factory StartGameRequest.fromJson(Map<String, dynamic> json) {
    return StartGameRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      startPlayerSeat: json['start_player_seat'] != null ? int.tryParse(json['start_player_seat'].toString()) : null,
      levelRank: json['level_rank'] != null ? CardRank(json['level_rank']) : null,
      fillWithBots: json['fill_with_bots'] ?? true,
      gameStateSnapshot: json['game_state_snapshot'] != null
          ? GameState.fromJson(json['game_state_snapshot'])
          : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    if (gameStateSnapshot != null) {
      final playerIds = gameStateSnapshot!.players.map((p) => p.id).toList();
      json['game_state_snapshot'] = gameStateSnapshot!.toJson(includeCardsOnHandForPlayers: playerIds, includePlayedCards: true, includePlayerTypeInfo: true);
      json['start_player_seat'] = startPlayerSeat;
      json['level_rank'] = levelRank?.name;
      json['fill_with_bots'] = fillWithBots;
    }
    return json;
  }
}


/// Player-to-server request to create a new game room.
///
/// Specifies the room name, type (public or private), configuration, and
/// optionally a map of bot specifications keyed by seat number (seat 1 is
/// always the room creator; bots start from seat 2).
///
@MsgAnnotation(MessageType.pCreateRoomRequest)
class CreateRoomRequest extends PlayerRequestMessage {

  /// The name of the room to be created.
  final String roomName;

  /// The configuration of the room, including settings like maximum players, game type, etc.
  /// This is an instance of [GameRoomConfig] which contains various settings for the room
  final GameRoomConfig roomConfig;

  /// Specifies bots (e.g., bot model or json string, and interpretation depends on the game server) to be used in the room for each seat (starting from seat 2, as the room creator always has seat 1).
  ///
  /// If not specified, the corresponding seat will remain open.
  /// If a seat number larger than [roomConfig.maxPlayers] is specified, it will be ignored.
  final Map<int, String>? bots;

  /// Constructor for creating an instance of [CreateRoomRequest].
  /// [roomId] is the unique identifier for the room, [roomName] is the name of the room. However, the server may generate a new room ID even when provided.
  CreateRoomRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    required this.roomName,
    required this.roomConfig,
    String? gameId, // optional, set to '' if null
    this.bots,
  }) : super(type: MessageType.pCreateRoomRequest, gameId: gameId ?? '');

  factory CreateRoomRequest.fromJson(Map<String, dynamic> json) {
    return CreateRoomRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'] ?? '',
      roomName: json['room_name'],
      roomConfig: GameRoomConfig.fromJson(json['room_config']),
      bots: json['bots'] != null
          ? (json['bots'] as Map<String, dynamic>).map((key, value) {
              final seat = int.tryParse(key)!;
              return MapEntry(seat, value as String);
            })
          : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['room_name'] = roomName;
    json['room_config'] = roomConfig.toJson();
    if (bots != null) {
      json['bots'] = bots?.map((seat, botCode) {
        return MapEntry(seat.toString(), botCode);
      });
    }
    return json;
  }
}

/// Broadcast when the room owner changes (e.g. current owner leaves).
@MsgAnnotation(MessageType.iRoomOwner)
class RoomOwnerMessage extends GameRoomMessage {
  /// The player ID of the new room owner.
  final String ownerId;

  RoomOwnerMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.ownerId,
  }) : super(type: MessageType.iRoomOwner);

  factory RoomOwnerMessage.fromJson(Map<String, dynamic> json) {
    return RoomOwnerMessage(
      roomId: json['room_id'],
      gameId: json['game_id'],
      ownerId: json['owner_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['owner_id'] = ownerId;
    return json;
  }
}


/// Broadcast when a player joins a game room.
///
/// Sent to the joining player with [roomInfo], [gameState], and [reconnectToken]
/// (for reconnection after disconnection). Broadcast to other players without
/// those fields. If the room was full, [replacedPlayerId] identifies the bot
/// that was replaced.
@MsgAnnotation(MessageType.iPlayerJoinedRoom)
class PlayerJoinedRoomMessage extends GameRoomMessage {
  /// The player who joined the room (ID, seat, name, team, etc.).
  final Player player;

  /// The ID of the bot being replaced by the joining player, or null.
  final String? replacedPlayerId;

  /// The bot code/model if the joining player is a bot, or null.
  final String? botCode;

  /// Room metadata sent only to the joining player.
  final RoomMetadata? roomInfo;

  /// Full game state snapshot sent only to the joining player.
  final GameState? gameState;

  /// A cryptographically secure token that allows the player to reconnect
  /// to this runtime room after a network disconnection.
  final String? reconnectToken;

  /// Whether this player is currently using explicit auto-delegation.
  /// Included in the private joining snapshot so reconnecting clients can
  /// restore their controls from authoritative room state.
  final bool? autoDelegated;

  PlayerJoinedRoomMessage({
    required this.player,
    required super.roomId,
    required super.gameId,
    this.replacedPlayerId,
    this.botCode,
    this.roomInfo,
    super.messageId,
    this.gameState,
    this.reconnectToken,
    this.autoDelegated,
  }) : super(type: MessageType.iPlayerJoinedRoom);

  factory PlayerJoinedRoomMessage.fromJson(Map<String, dynamic> json) {
    return PlayerJoinedRoomMessage(
      messageId: json['message_id'],
      player: Player.fromJson(json['player']),
      roomId: json['room_id'],
      gameId: json['game_id'],
      botCode: json['bot_code'],
      replacedPlayerId: json['replaced_player_id'],
      roomInfo: json['room_info']!=null ? RoomMetadata.fromJson(json['room_info']) : null,
      gameState: json['game_state']!=null ? GameState.fromJson(json['game_state']) : null,
      reconnectToken: json['reconnect_token'] as String?,
      autoDelegated: json['auto_delegated'] as bool?,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player'] = player.toJson(withCardsOnHand: true);
    if (botCode != null) {
      json['bot_code'] = botCode;
    }
    if (replacedPlayerId != null) {
      json['replaced_player_id'] = replacedPlayerId;
    }
    if (roomInfo != null) {
      json['room_info'] = roomInfo!.toJson();
    }
    if (gameState != null) {
      json['game_state'] = gameState!.toJson(
        includePlayedCards: true, 
        includeCardsOnHandForPlayers: gameState!.players.map((p) => p.id).toList(),
        includePlayerTypeInfo: true);
    }
    if (reconnectToken != null) {
      json['reconnect_token'] = reconnectToken;
    }
    if (autoDelegated != null) {
      json['auto_delegated'] = autoDelegated;
    }
    return json;
  }
}


/// Broadcast when a player quits the game room.
///
/// If the game is in progress, [replacementPlayer] identifies the bot that
/// takes over the departing player's seat.
@MsgAnnotation(MessageType.iPlayerQuitRoom)
class PlayerQuitRoomMessage extends GameRoomMessage {
  /// The ID of the player who left.
  final String playerId;

  /// The bot that replaces the departing player, if the game is in progress.
  final Player? replacementPlayer;

  PlayerQuitRoomMessage({
    required this.playerId,
    required super.roomId,
    required super.gameId,
    this.replacementPlayer,
    super.messageId,
  }) : super(type: MessageType.iPlayerQuitRoom);

  factory PlayerQuitRoomMessage.fromJson(Map<String, dynamic> json) {
    return PlayerQuitRoomMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      replacementPlayer: json.containsKey('replacement_player') ? Player.fromJson(json['replacement_player']) : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    if (replacementPlayer != null) {
      json['replacement_player'] = replacementPlayer!.toJson(withCardsOnHand: false);
    }
    return json;
  }
}


/// Sent to a player with the result of a previous request.
///
/// Unlike most messages, this extends [GameMessage] directly (not
/// [GameRoomMessage]) so it can carry an optional [roomId]. The [result]
/// indicates success or the specific error code, and [payload] provides
/// additional context (e.g. the invalid hand, or previous room info).
@MsgAnnotation(MessageType.iRequestResult)
class RequestResultMessage extends GameMessage {
  /// The player who made the request, or null if not applicable.
  final String? playerId;

  /// The type of the request this result responds to.
  final MessageType? request;

  /// The outcome — [ServerResponseCode.success] or an error code.
  final ServerResponseCode result;

  /// The room this result relates to, if applicable.
  final String? roomId;

  /// Additional context for the result (e.g. previous room info, invalid hand).
  final MessagePayload? payload;

  RequestResultMessage({
    super.messageId,
    this.roomId,
    this.playerId,
    this.request,
    required this.result,
    this.payload,
  }) : super(type: MessageType.iRequestResult);

  factory RequestResultMessage.fromJson(Map<String, dynamic> json) {
    return RequestResultMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      request: json['request'] != null ? MessageType.from(json['request']) : null,
      result: ServerResponseCode.fromName(json['result']),
      payload: json['payload'] != null ? MessagePayload.fromJson(json['payload']) : null,
      roomId: json['room_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    if (request!=null) {
      json['request'] = request!.name;
    }
    json['result'] = result.name;
    if (payload != null) {
      json['payload'] = payload;
    }
    if (roomId != null) {
      json['room_id'] = roomId;
    }
    return json;
  }
}


/// Sent to a player when additional time is granted for their current action.
///
/// Used in rooms without a time limit (不计时的房间).
@MsgAnnotation(MessageType.iMoreTimeGranted)
class MoreTimeGrantedMessage extends GameRoomMessage {
  /// The player who received the additional time.
  final String playerId;

  /// The new total allocated time in seconds (remaining + additional).
  final int newAllocatedSeconds;


  MoreTimeGrantedMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.newAllocatedSeconds,
  }) : super(type: MessageType.iMoreTimeGranted);

  factory MoreTimeGrantedMessage.fromJson(Map<String, dynamic> json) {
    return MoreTimeGrantedMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      newAllocatedSeconds: json['new_allocated_seconds'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['new_allocated_seconds'] = newAllocatedSeconds;
    return json;
  }
}


/// Specifies which bot to use for auto-delegation. Sent from client to server
/// when a player enables auto-play with a specific bot choice. The server
/// omits this field in broadcast messages.
class BotSelectionData {
  /// The type of bot: `'builtin'` for platform bots (basicBot, strongBot) or
  /// `'deployed'` for third-party HTTP/WebSocket bots.
  final String type;

  /// For built-in bots: the bot code (e.g. `'basicBot'`, `'strongBot'`).
  /// For deployed bots: the bot code/model string (e.g. `providerId-botCode-version`).
  final String botCode;

  /// Fields for deployed bots only (null for built-in).
  final String? deploymentId;
  final String? botDefinitionId;
  final String? baseUrl;
  final String? transportType;
  final String? protocolVersion;
  final String? authorizationApiKey;

  const BotSelectionData({
    required this.type,
    required this.botCode,
    this.deploymentId,
    this.botDefinitionId,
    this.baseUrl,
    this.transportType,
    this.protocolVersion,
    this.authorizationApiKey,
  });

  factory BotSelectionData.fromJson(Map<String, dynamic> json) {
    return BotSelectionData(
      type: json['type'] as String,
      botCode: json['bot_code'] as String,
      deploymentId: json['deployment_id'] as String?,
      botDefinitionId: json['bot_definition_id'] as String?,
      baseUrl: json['base_url'] as String?,
      transportType: json['transport_type'] as String?,
      protocolVersion: json['protocol_version'] as String?,
      authorizationApiKey: json['authorization_api_key'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'type': type,
      'bot_code': botCode,
    };
    if (deploymentId != null) json['deployment_id'] = deploymentId;
    if (botDefinitionId != null) json['bot_definition_id'] = botDefinitionId;
    if (baseUrl != null) json['base_url'] = baseUrl;
    if (transportType != null) json['transport_type'] = transportType;
    if (protocolVersion != null) json['protocol_version'] = protocolVersion;
    if (authorizationApiKey != null) {
      json['authorization_api_key'] = authorizationApiKey;
    }
    return json;
  }
}

/// Sent by a player to enable/disable auto-delegation (托管), and broadcast
/// by the server to inform other players of the change.
@MsgAnnotation(MessageType.autoDelegated)
class AutoDelegationMessage extends GameRoomMessage {
  /// The player enabling or disabling auto-delegation.
  final String playerId;

  /// Whether auto-delegation is enabled.
  final bool autoDelegated;

  /// Optional bot selection sent by the client when enabling auto-delegation.
  /// When null (or when autoDelegated is false), the server falls back to the
  /// default StrongBot. Server-to-client broadcasts omit this field.
  final BotSelectionData? botSelection;

  AutoDelegationMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.autoDelegated,
    this.botSelection,
  }) : super(type: MessageType.autoDelegated);

  factory AutoDelegationMessage.fromJson(Map<String, dynamic> json) {
    return AutoDelegationMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      autoDelegated: json['auto_delegated'] as bool,
      roomId: json['room_id'],
      gameId: json['game_id'],
      botSelection: json['bot_selection'] != null
          ? BotSelectionData.fromJson(json['bot_selection'] as Map<String, dynamic>)
          : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['auto_delegated'] = autoDelegated;
    if (botSelection != null) {
      json['bot_selection'] = botSelection!.toJson();
    }
    return json;
  }
}


/// Broadcast when a player takes or changes a seat in the room.
@MsgAnnotation(MessageType.iPlayerSeat)
class PlayerSeatMessage extends GameRoomMessage {
  /// The player changing seats.
  final String playerId;

  /// The new seat number (1–4).
  final int seat;

  /// The team the player is assigned to.
  final PlayerTeam team;

  PlayerSeatMessage({
    super.messageId,
    required this.playerId,
    required this.seat,
    required this.team,
    required super.roomId,
    required super.gameId,
  }) : super(type: MessageType.iPlayerSeat);

  factory PlayerSeatMessage.fromJson(Map<String, dynamic> json) {
    return PlayerSeatMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      seat: json['seat'],
      team: PlayerTeam.fromName(json['team']),
      roomId: json['room_id'], 
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['seat'] = seat;
    json['team'] = team.name;
    return json;
  }
}


/// Broadcast when the game room is closed.
@MsgAnnotation(MessageType.iGameRoomClosed)
class GameRoomClosedMessage extends GameRoomMessage {

  GameRoomClosedMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
  }) : super(type: MessageType.iGameRoomClosed);

  factory GameRoomClosedMessage.fromJson(Map<String, dynamic> json) {
    return GameRoomClosedMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }
} 


/// Broadcast when a player 接风 (leads the next phase because their teammate
/// emptied their hand and no opponent followed with a valid play).
@MsgAnnotation(MessageType.iJieFeng)
class JieFengMessage extends GameRoomMessage {
  /// The player who gains the lead (接风).
  final String playerId;

  /// The phase in which the player takes the lead.
  final String phaseId;

  JieFengMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.phaseId,
  }) : super(type: MessageType.iJieFeng);

  factory JieFengMessage.fromJson(Map<String, dynamic> json) {
    return JieFengMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      phaseId: json['phase_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['phase_id'] = phaseId;
    return json;
  }
}


/// Broadcast when team scores are updated (e.g. after a round with A+ results).
@MsgAnnotation(MessageType.iTeamScores)
class TeamScoresMessage extends GameRoomMessage {
  /// The updated cumulative scores for both teams.
  final TeamScores scores;

  TeamScoresMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.scores,
  }) : super(type: MessageType.iTeamScores);

  factory TeamScoresMessage.fromJson(Map<String, dynamic> json) {
    return TeamScoresMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      scores: TeamScores.fromJson(json['team_scores'] as Map<String, dynamic>),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['team_scores'] = scores.toJson();
    return json;
  }
}

/// Broadcast when a player empties their hand (plays their last card) in a round.
///
/// The [playerRank] records the player's finishing position (first, second,
/// third, or fourth).
@MsgAnnotation(MessageType.iPlayerEmptiedHand)
class PlayerEmptiedHandMessage extends GameRoomMessage {
  /// The player who emptied their hand.
  final String playerId;

  /// The round in which the player emptied their hand.
  final String roundId;

  /// The player's finishing rank in the round (first, second, third, or fourth).
  final PlayerRank playerRank;

  PlayerEmptiedHandMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.roundId,
    required this.playerRank,
  }) : super(type: MessageType.iPlayerEmptiedHand);

  factory PlayerEmptiedHandMessage.fromJson(Map<String, dynamic> json) {
    return PlayerEmptiedHandMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roundId: json['round_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      playerRank: PlayerRank.fromName(json['player_rank']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['round_id'] = roundId;
    json['player_rank'] = playerRank.name;
    return json;
  }
}

/// Broadcast with the (potentially partial) result of a round.
///
/// Partial results are sent after each player empties their hand. The final
/// result with [isPartial] = false is sent when the round fully ends.
@MsgAnnotation(MessageType.iRoundResult)
class RoundResultMessage extends GameRoomMessage {
  /// The current round result (may be partial).
  final RoundResult roundResult;

  /// The player who just emptied their hand triggering this update, or null.
  final String? emptiedByPlayerId;

  /// Whether this is a partial (mid-round) result. False when the round ends.
  final bool isPartial;

  RoundResultMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.roundResult,
    required this.isPartial,
    this.emptiedByPlayerId,
  }) : super(type: MessageType.iRoundResult);

  factory RoundResultMessage.fromJson(Map<String, dynamic> json, {List<Player>? players}) {
    return RoundResultMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      emptiedByPlayerId: json['emptied_by'],
      isPartial: json['is_partial'] ?? false,
      roundResult: RoundResult.fromJson(json['round_result'], players),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['round_result'] = roundResult.toJson();
    if (emptiedByPlayerId != null) {
      json['emptied_by'] = emptiedByPlayerId;
    }
    json['is_partial'] = isPartial;
    return json;
    
  }
}


/// Sent to a player with the remaining card counts (or full hands) of other players.
///
/// Used to update the UI card counters. Values may be null if a player's hand
/// is not visible to the receiver.
@MsgAnnotation(MessageType.iCardsOnHand)
class CardsOnHandMessage extends GameRoomMessage {
  /// Map from player ID to their current cards on hand (null if hidden).
  final Map<String, PokerCardList?> cardsOnHand;

  CardsOnHandMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.cardsOnHand,
  }) : super(type: MessageType.iCardsOnHand);

  factory CardsOnHandMessage.fromJson(Map<String, dynamic> json) {
    final rawCards = json['cards_on_hand'] as Map<String, dynamic>;
    final cardsOnHand = rawCards.map((k, v) => MapEntry(k, v != null ? PokerCardList.fromString(v) : null));
    return CardsOnHandMessage(
      messageId: json['message_id'],
      cardsOnHand: cardsOnHand,
      roomId: json['room_id'],
      gameId: json['game_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['cards_on_hand'] = cardsOnHand.map((k, v) => MapEntry(k, v?.toString()));
    return json;
  }

}


/// Sent to a player when they are removed from the room (e.g. inactivity,
/// disconnection, or kicked by the owner).
@MsgAnnotation(MessageType.iPlayerRemovedFromRoom)
class PlayerRemovedMessage extends GameRoomMessage {
  /// The player being removed.
  final String playerId;

  /// Why the player was removed, or null if unspecified.
  final RemovalReason? reason;

  PlayerRemovedMessage({
    super.messageId,
    required this.playerId,
    required super.roomId,
    required super.gameId,
    this.reason,
  }) : super(type: MessageType.iPlayerRemovedFromRoom);

  factory PlayerRemovedMessage.fromJson(Map<String, dynamic> json) {
    return PlayerRemovedMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      reason: RemovalReason.fromName(json['reason']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    if (reason != null) {
      json['reason'] = reason!.name;
    }
    return json;
  }
}


/// Sent to all players when a player times out on a server request
/// (e.g. failing to play a hand within the allotted time).
@MsgAnnotation(MessageType.iTimeOut)
class PlayerTimeoutMessage extends GameRoomMessage {
  /// The player who timed out.
  final String playerId;

  /// The type of request the player failed to respond to in time.
  final MessageType request;

  /// The round the timeout occurred in, if applicable.
  final String? roundId;

  /// The turn the timeout occurred on, if applicable.
  final String? turnId;

  PlayerTimeoutMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.playerId,
    required this.request,
    this.roundId,
    this.turnId,
  }) : super(type: MessageType.iTimeOut);

  factory PlayerTimeoutMessage.fromJson(Map<String, dynamic> json) {
    return PlayerTimeoutMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      playerId: json['player_id'],
      request: MessageType.from(json['request']),
      roundId: json['round_id'],
      turnId: json['turn_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    json['request'] = request.name;
    if (roundId != null) {
      json['round_id'] = roundId;
    }
    if (turnId != null) {
      json['turn_id'] = turnId;
    }
    return json;
  }
}

/// Broadcast when a tribute card (进贡) is paid by one player to another.
@MsgAnnotation(MessageType.iTributeCard)
class TributeCardMessage extends GameRoomMessage {
  /// The player paying the tribute.
  final String payerId;

  /// The player receiving the tribute, or null if not yet determined.
  final String? winnerId;

  /// The round this tribute is for.
  final String roundId;

  /// The card being paid as tribute.
  final PokerCard tribute;

  TributeCardMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.payerId,
    this.winnerId,
    required this.roundId,
    required this.tribute,
  }) : super(type: MessageType.iTributeCard);

  factory TributeCardMessage.fromJson(Map<String, dynamic> json) {
    return TributeCardMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      payerId: json['payer_id'],
      winnerId: json['winner_id'],
      roundId: json['round_id'],
      tribute: PokerCard.from(json['tribute']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['payer_id'] = payerId;
    json['winner_id'] = winnerId;
    json['round_id'] = roundId;
    json['tribute'] = tribute.toString();
    return json;
  }
}


/// Broadcast when a card is returned (还牌) in response to receiving a tribute.
@MsgAnnotation(MessageType.iReturnCard)
class ReturnCardMessage extends GameRoomMessage {
  /// The player who paid tribute (now receiving a card back).
  final String payerId;

  /// The player who received tribute (now returning a card).
  final String winnerId;

  /// The round this return is for.
  final String roundId;

  /// The card being returned.
  final PokerCard returnCard;

  ReturnCardMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.payerId,
    required this.winnerId,
    required this.roundId,
    required this.returnCard,
  }) : super(type: MessageType.iReturnCard);

  factory ReturnCardMessage.fromJson(Map<String, dynamic> json) {
    return ReturnCardMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      payerId: json['payer_id'],
      winnerId: json['winner_id'],
      roundId: json['round_id'],
      returnCard: PokerCard.from(json['return_card']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['payer_id'] = payerId;
    json['winner_id'] = winnerId;
    json['round_id'] = roundId;
    json['return_card'] = returnCard.toString();
    return json;
  }
}


/// Broadcast when tribute is resisted (抗贡).
///
/// Resistance occurs when both teams have equal red joker counts, cancelling
/// the tribute obligation. [redJokerCounts] shows the counts that triggered
/// the resistance.
@MsgAnnotation(MessageType.iTributeResistance)
class TributeResistanceMessage extends GameRoomMessage {
  /// The round in which tribute is being resisted.
  final String roundId;

  /// The player who starts the round due to resistance.
  final String startPlayerId;

  /// The count of red jokers held by each player, keyed by seat number (1–4).
  final Map<int, int> redJokerCounts;

  TributeResistanceMessage({
    super.messageId,
    required this.startPlayerId,
    required super.roomId,
    required super.gameId,
    required this.roundId,
    required this.redJokerCounts,
  }) : super(type: MessageType.iTributeResistance);

  factory TributeResistanceMessage.fromJson(Map<String, dynamic> json) {
    return TributeResistanceMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      roundId: json['round_id'],
      startPlayerId: json['start_player_id'],
      redJokerCounts: Map<int, int>.from(
        (json['red_joker_counts'] as Map<String, dynamic>).map((k, v) => MapEntry(int.parse(k), v))
      ),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['round_id'] = roundId;
    json['start_player_id'] = startPlayerId;
    json['red_joker_counts'] = redJokerCounts.map((k, v) => MapEntry(k.toString(), v));
    return json;
  }
}


/// Broadcast to the room creator when a game room is successfully created.
///
/// Includes the room metadata and the initial player list (just the creator).
@MsgAnnotation(MessageType.iGameRoomCreated)
class GameRoomCreatedMessage extends GameRoomMessage {
  /// The newly created room's metadata and configuration.
  final RoomMetadata roomInfo;

  /// The initial list of players in the room (creator only, cards hidden).
  final List<Player> players;

  GameRoomCreatedMessage({
    super.messageId,
    required this.roomInfo,
    required this.players,
    required super.roomId,
    required super.gameId,
  }) : super(type: MessageType.iGameRoomCreated);

  factory GameRoomCreatedMessage.fromJson(Map<String, dynamic> json) {
    return GameRoomCreatedMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      players: (json['players'] as List<dynamic>)
          .map((playerJson) => Player.fromJson(playerJson as Map<String, dynamic>))
          .toList(),
      roomInfo: RoomMetadata.fromJson(json['room_info'] as Map<String, dynamic>),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['room_info'] = roomInfo.toJson();
    json['players'] = players.map((player) => player.toJson(withCardsOnHand: false)).toList();
    return json;
  }
}

/// Periodic heartbeat sent by clients to keep the WebSocket connection alive.
///
/// The server echoes the heartbeat back to confirm connectivity.
@MsgAnnotation(MessageType.heartbeat)
class HeartbeatMessage extends GameMessage {
  /// The player sending the heartbeat.
  final String playerId;

  HeartbeatMessage({
    super.messageId,
    required this.playerId,
  }) : super(type: MessageType.heartbeat);

  factory HeartbeatMessage.fromJson(Map<String, dynamic> json) {
    return HeartbeatMessage(
      messageId: json['message_id'],
      playerId: json['player_id'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['player_id'] = playerId;
    return json;
  }
}



/// Player-to-server request for additional time on the current action.
@MsgAnnotation(MessageType.pMoreTimeRequest)
class MoreTimeRequest extends PlayerRequestMessage {
  /// The round in which more time is requested.
  final String roundId;

  /// The turn in which more time is requested, if applicable.
  final String? turnId;

  /// The number of seconds requested, or null for default.
  final int? seconds;

  MoreTimeRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    required super.gameId,
    required this.roundId,
    this.seconds,
    this.turnId,
  }) : super(type: MessageType.pMoreTimeRequest);

  factory MoreTimeRequest.fromJson(Map<String, dynamic> json) {
    return MoreTimeRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      roundId: json['round_id'],
      turnId: json.containsKey('turn_id') ? json['turn_id'] : null,
      seconds: json.containsKey('seconds') ? json['seconds'] : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['round_id'] = roundId;
    if (turnId != null) {
      json['turn_id'] = turnId;
    }
    if (seconds != null) {
      json['seconds'] = seconds;
    }
    return json;
  }
}


/// Player-to-server request to change to a different seat in the room.
@MsgAnnotation(MessageType.pSeatRequest)
class SeatRequest extends PlayerRequestMessage {
  /// The desired new seat number (1–4).
  final int newSeat;

  SeatRequest({
    super.messageId,
    required super.playerId,
    required super.roomId,
    required super.gameId,
    required this.newSeat,
  }) : super(type: MessageType.pSeatRequest);

  factory SeatRequest.fromJson(Map<String, dynamic> json) {
    return SeatRequest(
      messageId: json['message_id'],
      playerId: json['player_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      newSeat: json['new_seat'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['new_seat'] = newSeat;
    return json;
  }
}

/// Broadcast when the game server is shutting down.
@MsgAnnotation(MessageType.iServerClosed)
class ServerClosedMessage extends GameMessage {
  /// Optional human-readable reason for the shutdown.
  final String? reason;

  ServerClosedMessage({
    super.messageId,
    this.reason,
  }) : super(type: MessageType.iServerClosed);

  factory ServerClosedMessage.fromJson(Map<String, dynamic> json) {
    return ServerClosedMessage(
      messageId: json['message_id'],
      reason: json['reason'],
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['reason'] = reason;
    return json;
  }
}


/// Broadcast when a round ends, carrying the full [Round] object with all
/// phase, turn, and result details for the completed round.
@MsgAnnotation(MessageType.iRoundEnded)
class RoundEndedMessage extends GameRoomMessage {
  /// The ID of the round that ended.
  final String roundId;

  /// The complete round object with all phases, turns, and results.
  final Round round;

  RoundEndedMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.round,
    required this.roundId,
  }) : super(type: MessageType.iRoundEnded);

  factory RoundEndedMessage.fromJson(Map<String, dynamic> json) {
    return RoundEndedMessage(
      messageId: json['message_id'],
      roomId: json['room_id'],
      gameId: json['game_id'],
      roundId: json['round_id'],
      round: Round.fromJson(json['round']),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['round_id'] = roundId;
    json['round'] = round.toJson();
    return json;
  }
}
