import 'dart:convert';

import 'package:guandan_core/guandan_core.dart';

/// Discriminated message types for the bot WebSocket protocol.
enum BotMessageType {
  sessionStart('session_start'),
  sessionStarted('session_started'),
  sessionEnd('session_end'),
  sessionEnded('session_ended'),
  gameMessage('game_message'),
  error('error');

  const BotMessageType(this.code);

  final String code;

  static BotMessageType fromCode(String code) {
    return BotMessageType.values.firstWhere(
      (t) => t.code == code,
      orElse: () => BotMessageType.error,
    );
  }
}

/// Base class for all bot protocol messages.
///
/// Use [BotMessage.fromJson] to deserialize a decoded JSON map, or
/// [BotMessage.parse] to parse a raw JSON string into the appropriate subtype.
sealed class BotMessage {
  const BotMessage();

  String get sessionId;
  BotMessageType get type;
  Map<String, dynamic> toJson();

  /// Parses a raw JSON string into the appropriate [BotMessage] subtype.
  static BotMessage parse(String jsonString) {
    final decoded = jsonDecode(jsonString);
    if (decoded is! Map) {
      throw const FormatException('Bot message must be a JSON object');
    }
    return fromJson(Map<String, dynamic>.from(decoded));
  }

  /// Deserializes a decoded JSON map into the appropriate [BotMessage] subtype.
  static BotMessage fromJson(Map<String, dynamic> json) {
    final typeCode = json['type'] as String? ?? '';
    final type = BotMessageType.fromCode(typeCode);
    return switch (type) {
      BotMessageType.sessionStart => SessionStartMessage.fromJson(json),
      BotMessageType.sessionStarted => SessionStartedMessage.fromJson(json),
      BotMessageType.sessionEnd => SessionEndMessage.fromJson(json),
      BotMessageType.sessionEnded => SessionEndedMessage.fromJson(json),
      BotMessageType.gameMessage => GameMessageEnvelope.fromJson(json),
      BotMessageType.error => BotErrorMessage.fromJson(json),
    };
  }
}

// ---------------------------------------------------------------------------
// Session management messages
// ---------------------------------------------------------------------------

/// Sent by the game server to initialize a bot session.
///
/// The gateway sends a minimal version (only [sessionId], [deploymentId],
/// [protocolVersion]).  The outbound agent sends the full set including
/// [playerId], [seat], [ruleSet], and [deckCount].
class SessionStartMessage extends BotMessage {
  @override
  final String sessionId;

  /// The bot definition ID (outbound agent only).
  final String? botDefinitionId;

  /// The deployment ID this session is for.
  final String? deploymentId;

  /// The player ID assigned to this bot (outbound agent only).
  final String? playerId;

  /// The seat number (outbound agent only).
  final int? seat;

  /// The rule set to use, e.g. "classic" (outbound agent only).
  final String? ruleSet;

  /// The protocol version, always "guandan-bot-v1".
  final String? protocolVersion;

  /// The number of standard decks in the game (outbound agent only).
  final int? deckCount;

  @override
  BotMessageType get type => BotMessageType.sessionStart;

  const SessionStartMessage({
    required this.sessionId,
    this.botDefinitionId,
    this.deploymentId,
    this.playerId,
    this.seat,
    this.ruleSet,
    this.protocolVersion,
    this.deckCount,
  });

  factory SessionStartMessage.fromJson(Map<String, dynamic> json) {
    return SessionStartMessage(
      sessionId: json['session_id'] as String,
      botDefinitionId: json['bot_definition_id'] as String?,
      deploymentId: json['deployment_id'] as String?,
      playerId: json['player_id'] as String?,
      seat: json['seat'] as int?,
      ruleSet: json['rule_set'] as String?,
      protocolVersion: json['protocol_version'] as String?,
      deckCount: json['number_of_standard_decks'] as int?,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
      if (botDefinitionId != null) 'bot_definition_id': botDefinitionId,
      if (deploymentId != null) 'deployment_id': deploymentId,
      if (playerId != null) 'player_id': playerId,
      if (seat != null) 'seat': seat,
      if (ruleSet != null) 'rule_set': ruleSet,
      if (protocolVersion != null) 'protocol_version': protocolVersion,
      if (deckCount != null)
        'number_of_standard_decks': deckCount,
    };
  }
}

/// Sent by the bot to acknowledge a [SessionStartMessage].
class SessionStartedMessage extends BotMessage {
  @override
  final String sessionId;

  /// Whether the bot accepted the session.
  final bool accepted;

  @override
  BotMessageType get type => BotMessageType.sessionStarted;

  const SessionStartedMessage({
    required this.sessionId,
    required this.accepted,
  });

  factory SessionStartedMessage.fromJson(Map<String, dynamic> json) {
    return SessionStartedMessage(
      sessionId: json['session_id'] as String,
      accepted: json['accepted'] as bool? ?? true,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
      'accepted': accepted,
    };
  }
}

/// Sent by the game server to terminate a bot session.
class SessionEndMessage extends BotMessage {
  @override
  final String sessionId;

  @override
  BotMessageType get type => BotMessageType.sessionEnd;

  const SessionEndMessage({required this.sessionId});

  factory SessionEndMessage.fromJson(Map<String, dynamic> json) {
    return SessionEndMessage(sessionId: json['session_id'] as String);
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
    };
  }
}

/// Sent by the bot to acknowledge a [SessionEndMessage].
class SessionEndedMessage extends BotMessage {
  @override
  final String sessionId;

  @override
  BotMessageType get type => BotMessageType.sessionEnded;

  const SessionEndedMessage({required this.sessionId});

  factory SessionEndedMessage.fromJson(Map<String, dynamic> json) {
    return SessionEndedMessage(sessionId: json['session_id'] as String);
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
    };
  }
}

// ---------------------------------------------------------------------------
// Game message envelope
// ---------------------------------------------------------------------------

/// Wraps any [GameMessage] for transport over the bot WebSocket protocol.
///
/// Used for requests (server → bot), responses (bot → server), and
/// informational messages (server → bot).  The [payload] contains a typed
/// [GameMessage] subclass whose `type` field determines the specific game
/// operation.
class GameMessageEnvelope extends BotMessage {
  @override
  final String sessionId;

  /// A unique ID for request / response correlation.
  /// Must be echoed back by the bot in its response.
  final String? requestId;

  /// The deadline for the response, in milliseconds since epoch.
  final int? deadlineMillis;

  /// The game message being transported.
  final GameMessage payload;

  @override
  BotMessageType get type => BotMessageType.gameMessage;

  const GameMessageEnvelope({
    required this.sessionId,
    this.requestId,
    this.deadlineMillis,
    required this.payload,
  });

  factory GameMessageEnvelope.fromJson(Map<String, dynamic> json) {
    final payloadJson = Map<String, dynamic>.from(json['payload'] as Map);
    return GameMessageEnvelope(
      sessionId: json['session_id'] as String,
      requestId: json['request_id'] as String?,
      deadlineMillis: json['deadline_millis'] as int?,
      payload: GameMessageFactory.fromJson(payloadJson),
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
      if (requestId != null) 'request_id': requestId,
      if (deadlineMillis != null) 'deadline_millis': deadlineMillis,
      'payload': payload.toJson(),
    };
  }
}

// ---------------------------------------------------------------------------
// Error message
// ---------------------------------------------------------------------------

/// Sent by either the game server or the bot to report a protocol error.
class BotErrorMessage extends BotMessage {
  @override
  final String sessionId;

  /// A machine-readable error code.
  final String code;

  /// A human-readable error description.
  final String message;

  @override
  BotMessageType get type => BotMessageType.error;

  const BotErrorMessage({
    required this.sessionId,
    required this.code,
    required this.message,
  });

  factory BotErrorMessage.fromJson(Map<String, dynamic> json) {
    return BotErrorMessage(
      sessionId: json['session_id'] as String? ?? '',
      code: json['code'] as String? ?? 'unknown_error',
      message: json['message'] as String? ?? '',
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'session_id': sessionId,
      'code': code,
      'message': message,
    };
  }
}
