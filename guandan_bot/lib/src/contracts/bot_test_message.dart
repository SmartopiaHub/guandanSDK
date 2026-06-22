import 'dart:convert';

/// Types of messages exchanged between the test script and the game server
/// over the test-game SSE channel.
enum BotTestMessageType {
  control('control'),
  gameEvent('game_event'),
  response('response');

  const BotTestMessageType(this.code);

  final String code;

  static BotTestMessageType fromCode(String code) {
    return BotTestMessageType.values.firstWhere(
      (t) => t.code == code,
      orElse: () =>
          throw FormatException('Unknown BotTestMessageType: $code'),
    );
  }
}

/// Types of control messages that the test script can send to the game server.
enum BotTestControlType {
  start('start'),
  stop('stop'),
  cancel('cancel');

  const BotTestControlType(this.code);

  final String code;

  static BotTestControlType fromCode(String code) {
    return BotTestControlType.values.firstWhere(
      (t) => t.code == code,
      orElse: () =>
          throw FormatException('Unknown BotTestControlType: $code'),
    );
  }
}

/// Predefined response codes for [BotTestResponseMessage].
enum BotTestResponseCode {
  success('success'),
  gameNotFound('game_not_found'),
  gameAlreadyStarted('game_already_started'),
  gameNotStarted('game_not_started'),
  gameAlreadyCompleted('game_already_completed'),
  invalidControl('invalid_control'),
  missingParameter('missing_parameter'),
  internalError('internal_error'),
  unauthorized('unauthorized'),
  scopeMissing('scope_missing');

  const BotTestResponseCode(this.code);

  final String code;
}

// ===========================================================================
// Base message class
// ===========================================================================

/// Base class for all messages exchanged between the test script and the
/// game server.
///
/// Use [BotTestMessage.fromJson] to deserialize a decoded JSON map, or
/// [BotTestMessage.parse] to parse a raw JSON string.
sealed class BotTestMessage {
  const BotTestMessage();

  /// Every message belongs to a specific test game.
  String get testGameId;

  /// Discriminated message type.
  BotTestMessageType get type;

  /// The SSE event name to use when transmitting this message.
  String get sseEvent;

  Map<String, dynamic> toJson();

  /// Parses a raw JSON string into the appropriate [BotTestMessage] subtype.
  static BotTestMessage parse(String jsonString) {
    final decoded = jsonDecode(jsonString);
    if (decoded is! Map) {
      throw const FormatException('BotTestMessage must be a JSON object');
    }
    return fromJson(Map<String, dynamic>.from(decoded));
  }

  /// Deserializes a decoded JSON map into the appropriate [BotTestMessage]
  /// subtype.
  static BotTestMessage fromJson(Map<String, dynamic> json) {
    final typeCode = json['type'] as String? ?? '';
    final type = BotTestMessageType.fromCode(typeCode);
    return switch (type) {
      BotTestMessageType.control =>
        BotTestControlMessage.fromJson(json),
      BotTestMessageType.gameEvent =>
        BotTestGameEventMessage.fromJson(json),
      BotTestMessageType.response =>
        BotTestResponseMessage.fromJson(json),
    };
  }
}

// ===========================================================================
// Control message — test script → game server
// ===========================================================================

/// Sent by the test script to the game server to control the test game
/// (e.g. start, stop, cancel).
///
/// Delivered via HTTP POST to
/// `/api/v1/test-games/{testGameId}/control`.
class BotTestControlMessage extends BotTestMessage {
  @override
  final String testGameId;

  /// The specific control operation requested.
  final BotTestControlType controlType;

  /// Optional client-generated request ID for correlation with the
  /// corresponding [BotTestResponseMessage].
  final String? requestId;

  /// Optional parameters for the control operation.
  final Map<String, dynamic>? params;

  @override
  BotTestMessageType get type => BotTestMessageType.control;

  @override
  String get sseEvent => 'control.${controlType.code}';

  const BotTestControlMessage({
    required this.testGameId,
    required this.controlType,
    this.requestId,
    this.params,
  });

  factory BotTestControlMessage.fromJson(Map<String, dynamic> json) {
    return BotTestControlMessage(
      testGameId: json['test_game_id'] as String? ?? '',
      controlType:
          BotTestControlType.fromCode(json['control_type'] as String? ?? ''),
      requestId: json['request_id'] as String?,
      params: json['params'] is Map
          ? Map<String, dynamic>.from(json['params'] as Map)
          : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'test_game_id': testGameId,
      'control_type': controlType.code,
      if (requestId != null) 'request_id': requestId,
      if (params != null && params!.isNotEmpty) 'params': params,
    };
  }
}

// ===========================================================================
// Game event message — game server → test script
// ===========================================================================

/// Sent by the game server to the test script as an envelope for game-room
/// events (agent messages, lifecycle changes, heartbeats).
///
/// The [event] field carries the logical event name (e.g. `agent.message`,
/// `game.created`, `game.completed`), and [data] contains the event payload.
class BotTestGameEventMessage extends BotTestMessage {
  @override
  final String testGameId;

  /// The logical event name, used as the SSE `event:` field.
  final String event;

  /// The event payload.
  final Map<String, dynamic> data;

  @override
  BotTestMessageType get type => BotTestMessageType.gameEvent;

  @override
  String get sseEvent => event;

  const BotTestGameEventMessage({
    required this.testGameId,
    required this.event,
    required this.data,
  });

  /// Convenience constructor: game created (room provisioned, waiting for SSE).
  factory BotTestGameEventMessage.gameCreated({
    required String testGameId,
    required String gameId,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'game.created',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
      },
    );
  }

  /// Convenience constructor: game started.
  factory BotTestGameEventMessage.gameStarted({
    required String testGameId,
    required String gameId,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'game.started',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
      },
    );
  }

  /// Convenience constructor: game completed.
  factory BotTestGameEventMessage.gameCompleted({
    required String testGameId,
    required String gameId,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'game.completed',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
      },
    );
  }

  /// Convenience constructor: game cancelled.
  factory BotTestGameEventMessage.gameCancelled({
    required String testGameId,
    required String gameId,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'game.cancelled',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
      },
    );
  }

  /// Convenience constructor: agent message envelope.
  factory BotTestGameEventMessage.agentMessage({
    required String testGameId,
    required String gameId,
    required String playerId,
    required Map<String, dynamic> message,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'agent.message',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
        'player_id': playerId,
        'message': message,
      },
    );
  }

  /// Convenience constructor: heartbeat.
  factory BotTestGameEventMessage.heartbeat({
    required String testGameId,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'heartbeat',
      data: {
        'sent_at': DateTime.now().toUtc().toIso8601String(),
      },
    );
  }

  /// Convenience constructor: round completed.
  factory BotTestGameEventMessage.roundCompleted({
    required String testGameId,
    required String gameId,
    required String roundId,
    required int numRoundsCompleted,
    required int targetRounds,
    required int numSeriesCompleted,
    required int targetSeries,
    Map<String, dynamic>? roundResult,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'round.completed',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
        'round_id': roundId,
        'num_rounds_completed': numRoundsCompleted,
        'target_rounds': targetRounds,
        'num_series_completed': numSeriesCompleted,
        'target_series': targetSeries,
        if (roundResult != null) 'round_result': roundResult,
      },
    );
  }

  /// Convenience constructor: test completed (all series/rounds finished).
  factory BotTestGameEventMessage.testCompleted({
    required String testGameId,
    required String gameId,
    required int numSeriesCompleted,
    required int targetSeries,
    required int numRoundsCompleted,
    required int targetRounds,
    required List<Map<String, dynamic>> roundResults,
  }) {
    return BotTestGameEventMessage(
      testGameId: testGameId,
      event: 'test.completed',
      data: {
        'test_game_id': testGameId,
        'game_id': gameId,
        'num_series_completed': numSeriesCompleted,
        'target_series': targetSeries,
        'num_rounds_completed': numRoundsCompleted,
        'target_rounds': targetRounds,
        'round_results': roundResults,
      },
    );
  }

  factory BotTestGameEventMessage.fromJson(Map<String, dynamic> json) {
    return BotTestGameEventMessage(
      testGameId: json['test_game_id'] as String? ?? '',
      event: json['event'] as String? ?? '',
      data: json['data'] is Map
          ? Map<String, dynamic>.from(json['data'] as Map)
          : <String, dynamic>{},
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'test_game_id': testGameId,
      'event': event,
      'data': data,
    };
  }
}

// ===========================================================================
// Response message — game server → test script
// ===========================================================================

/// Sent by the game server to the test script in response to a
/// [BotTestControlMessage], or as an asynchronous error notification.
class BotTestResponseMessage extends BotTestMessage {
  @override
  final String testGameId;

  /// Whether the requested operation succeeded.
  final bool success;

  /// A machine-readable response code (see [BotTestResponseCode]).
  final String code;

  /// A human-readable message (typically provided for errors).
  final String? message;

  /// The [BotTestControlMessage.requestId] that triggered this response,
  /// if applicable.
  final String? requestId;

  /// Optional response payload.
  final Map<String, dynamic>? data;

  @override
  BotTestMessageType get type => BotTestMessageType.response;

  @override
  String get sseEvent => 'response';

  const BotTestResponseMessage({
    required this.testGameId,
    required this.success,
    required this.code,
    this.message,
    this.requestId,
    this.data,
  });

  /// Convenience constructor for a successful response.
  factory BotTestResponseMessage.ok({
    required String testGameId,
    String? requestId,
    Map<String, dynamic>? data,
  }) {
    return BotTestResponseMessage(
      testGameId: testGameId,
      success: true,
      code: BotTestResponseCode.success.code,
      requestId: requestId,
      data: data,
    );
  }

  /// Convenience constructor for an error response.
  factory BotTestResponseMessage.error({
    required String testGameId,
    required String code,
    String? message,
    String? requestId,
  }) {
    return BotTestResponseMessage(
      testGameId: testGameId,
      success: false,
      code: code,
      message: message,
      requestId: requestId,
    );
  }

  factory BotTestResponseMessage.fromJson(Map<String, dynamic> json) {
    return BotTestResponseMessage(
      testGameId: json['test_game_id'] as String? ?? '',
      success: json['success'] as bool? ?? false,
      code: json['code'] as String? ?? BotTestResponseCode.internalError.code,
      message: json['message'] as String?,
      requestId: json['request_id'] as String?,
      data: json['data'] is Map
          ? Map<String, dynamic>.from(json['data'] as Map)
          : null,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    return {
      'type': type.code,
      'test_game_id': testGameId,
      'success': success,
      'code': code,
      if (message != null) 'message': message,
      if (requestId != null) 'request_id': requestId,
      if (data != null && data!.isNotEmpty) 'data': data,
    };
  }
}
