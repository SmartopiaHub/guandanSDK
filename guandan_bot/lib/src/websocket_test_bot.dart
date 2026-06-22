import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:guandan_core/guandan_core.dart';
import 'package:logging/logging.dart';

import 'basic_bot.dart';
import 'contracts/bot_protocol_contract.dart';
import 'message_formatter.dart';

/// A WebSocket client bot that connects to the game server's bot gateway,
/// authenticates with a deployment key, and handles game messages via the
/// standard bot protocol (guandan-bot-v1).
///
/// [apiKey] is the *deployment key* — it is sent **by** the bot **to** the
/// game server as `Authorization: Bearer <apiKey>` when connecting.
class WebSocketTestBot {
  WebSocketTestBot({
    required this.gameServerUrl,
    required this.apiKey,
    this.protocolVersion = 'guandan-bot-v1',
    this.deckCount = 2,
    this.reconnectDelay = const Duration(seconds: 3),
    Logger? logger,
  }) : _logger = logger ?? Logger('WebSocketTestBot');

  final String gameServerUrl;

  /// Deployment key presented to the game server (bot → server).
  /// Sent as `Authorization: Bearer <apiKey>` in the WebSocket handshake.
  final String apiKey;

  final String protocolVersion;
  final int deckCount;
  final Duration reconnectDelay;
  final Logger _logger;

  WebSocket? _socket;
  final _sessions = <String, BasicBot>{};
  StreamSubscription<dynamic>? _subscription;
  bool _disposed = false;

  /// Connects to the game server's bot gateway and begins handling
  /// messages. Automatically reconnects on connection loss.
  Future<void> connect() async {
    _disposed = false;
    await _connect();
  }

  Future<void> _connect() async {
    if (_disposed) return;
    try {
      final uri = Uri.parse('$gameServerUrl/bot-gateway/v1');
      _logger.info('Connecting to bot gateway at $uri');
      _socket = await WebSocket.connect(
        uri.toString(),
        headers: {
          'Authorization': 'Bearer $apiKey',
          'X-Guandan-Bot-Protocol': protocolVersion,
        },
      );
      _logger.info('Connected to bot gateway');

      _subscription = _socket!.listen(
        _handleFrame,
        onError: (Object error, StackTrace stackTrace) {
          _logger.warning('WebSocket error', error, stackTrace);
          _scheduleReconnect();
        },
        onDone: () {
          _logger.info('WebSocket connection closed');
          _scheduleReconnect();
        },
        cancelOnError: false,
      );
    } catch (error, stackTrace) {
      _logger.warning('Failed to connect to game server', error, stackTrace);
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _logger.info('Reconnecting in ${reconnectDelay.inSeconds}s...');
    Future.delayed(reconnectDelay, _connect);
  }

  void _handleFrame(dynamic frame) {
    final receivedAt = DateTime.now().toUtc();
    final rawFrame = frame as String;
    try {
      final message = BotMessage.parse(rawFrame);
      _logReceivedMessage(message, rawFrame.length, receivedAt);
      final response = _handleEnvelope(message);
      if (response != null &&
          _socket != null &&
          _socket!.readyState == WebSocket.open) {
        final encoded = jsonEncode(response.toJson());
        _logSentMessage(response, encoded.length);
        _socket!.add(encoded);
      }
    } catch (error, stackTrace) {
      _logger.warning(
        'Failed to handle received bot frame at ${receivedAt.toIso8601String()} '
        '(bytes=${rawFrame.length})',
        error,
        stackTrace,
      );
      if (_socket != null && _socket!.readyState == WebSocket.open) {
        final errorMessage = BotErrorMessage(
          sessionId: '',
          code: 'invalid_bot_message',
          message: error.toString(),
        );
        final encoded = jsonEncode(errorMessage.toJson());
        _logSentMessage(errorMessage, encoded.length);
        _socket!.add(encoded);
      }
    }
  }

  void _logReceivedMessage(
    BotMessage message,
    int bytes,
    DateTime receivedAt,
  ) {
    _logger.info(
      '← Received ${MessageFormatter.format(message)} '
      'bytes=$bytes '
      'at=${receivedAt.toIso8601String()}',
    );
  }

  void _logSentMessage(BotMessage message, int bytes) {
    _logger.info(
      '→ Sent ${MessageFormatter.format(message)} '
      'bytes=$bytes '
      'at=${DateTime.now().toUtc().toIso8601String()}',
    );
  }

  BotMessage? _handleEnvelope(BotMessage message) {
    return switch (message) {
      SessionStartMessage _ => _handleSessionStart(message),
      SessionEndMessage(:final sessionId) => _handleSessionEnd(sessionId),
      GameMessageEnvelope(:final sessionId, :final requestId, :final payload) =>
        _handleGameMessage(sessionId, requestId, payload),
      _ => BotErrorMessage(
          sessionId: message.sessionId,
          code: 'unsupported_message_type',
          message: 'Unsupported bot message type: ${message.type.code}',
        ),
    };
  }

  SessionStartedMessage _handleSessionStart(SessionStartMessage msg) {
    final sessionId = msg.sessionId;
    final seat = msg.seat ?? 1;
    final playerId = msg.playerId ?? 'ws-test-$seat';
    final decks = msg.deckCount ?? deckCount;
    final team = seat % 2 == 0 ? PlayerTeam.blueTeam : PlayerTeam.redTeam;
    _sessions[sessionId] = BasicBot(
      playerId,
      seat,
      team,
      decks,
      botCode: 'WebSocketTestBot',
    );
    _logger.info('Session started: $sessionId (seat $seat, team $team)');
    return SessionStartedMessage(sessionId: sessionId, accepted: true);
  }

  SessionEndedMessage _handleSessionEnd(String sessionId) {
    _sessions.remove(sessionId);
    _logger.info('Session ended: $sessionId');
    return SessionEndedMessage(sessionId: sessionId);
  }

  BotMessage? _handleGameMessage(
    String sessionId,
    String? requestId,
    GameMessage payload,
  ) {
    final bot = _sessions[sessionId];
    if (bot == null) {
      return BotErrorMessage(
        sessionId: sessionId,
        code: 'unknown_session',
        message: 'Bot session has not been started.',
      );
    }

    return switch (payload) {
      ServerPlayHandRequest(
        :final availableCards,
        :final handOnTable,
        :final levelRank
      ) =>
        _handleRequestHand(
            sessionId, requestId, bot, availableCards, handOnTable, levelRank),
      ServerTributeRequest(:final availableCards) =>
        _handleRequestTribute(sessionId, requestId, bot, availableCards),
      ServerReturnCardRequest(:final availableCards) =>
        _handleRequestReturn(sessionId, requestId, bot, availableCards),
      _ => () {
          bot.receiveMessage(payload);
          return null;
        }(),
    };
  }

  GameMessageEnvelope? _handleRequestHand(
    String sessionId,
    String? requestId,
    BasicBot bot,
    PokerCardList? availableCards,
    Hand handOnTable,
    CardRank levelRank,
  ) {
    // Play requests are broadcast to all players; only the targeted player
    // has non-empty availableCards. Skip response for other players.
    if (availableCards == null || availableCards.isEmpty) {
      return null;
    }
    bot.setCardsOnHand(PokerCardList.from(availableCards));
    final hand = bot.getCardsToPlay(handOnTable, levelRank);
    return GameMessageEnvelope(
      sessionId: sessionId,
      requestId: requestId,
      payload: PlayerPlayHandRequest(
        roomId: '',
        gameId: '',
        playerId: bot.id,
        cards: hand,
        roundId: '',
        turnId: '',
      ),
    );
  }

  GameMessageEnvelope? _handleRequestTribute(
    String sessionId,
    String? requestId,
    BasicBot bot,
    PokerCardList? availableCards,
  ) {
    // Tribute requests are broadcast; skip if not our turn (empty availableCards).
    if (availableCards == null || availableCards.isEmpty) {
      return null;
    }
    bot.setCardsOnHand(PokerCardList.from(availableCards));
    return GameMessageEnvelope(
      sessionId: sessionId,
      requestId: requestId,
      payload: PlayerPayTributeRequest(
        roomId: '',
        gameId: '',
        playerId: bot.id,
        tribute: bot.tribute(),
        roundId: '',
      ),
    );
  }

  GameMessageEnvelope? _handleRequestReturn(
    String sessionId,
    String? requestId,
    BasicBot bot,
    PokerCardList? availableCards,
  ) {
    // Return-card requests are broadcast; skip if not our turn (empty availableCards).
    if (availableCards == null || availableCards.isEmpty) {
      return null;
    }
    bot.setCardsOnHand(PokerCardList.from(availableCards));
    return GameMessageEnvelope(
      sessionId: sessionId,
      requestId: requestId,
      payload: PlayerReturnCardRequest(
        roomId: '',
        gameId: '',
        playerId: bot.id,
        returnCard: bot.returnCard(),
        roundId: '',
      ),
    );
  }

  /// Disconnects and releases all resources.
  Future<void> dispose() async {
    _disposed = true;
    await _subscription?.cancel();
    await _socket?.close();
    _socket = null;
    _sessions.clear();
    _logger.info('Bot disposed');
  }
}
