import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:guandan_core/guandan_core.dart';
import 'package:http/http.dart' as http;
import 'package:logging/logging.dart';

import 'basic_bot.dart';
import 'contracts/bot_protocol_contract.dart';
import 'contracts/bot_registry_contract.dart';
import 'message_formatter.dart';

/// A small HTTP bot server for local tests and development.
///
/// It accepts guandan-bot-v1 [BotMessage] envelopes at:
///
/// - `POST /sessions`
/// - `POST /sessions/{sessionId}/messages`
/// - `DELETE /sessions/{sessionId}`
///
/// If [apiKey] is provided (the *bot invocation key*), every incoming request
/// must include `Authorization: Bearer <apiKey>` or `X-Api-Key: <apiKey>`.
/// This key is the *bot invocation token* issued by the platform — it is
/// sent **to** the bot **from** the game server.
class HttpTestBot {
  HttpTestBot({
    this.host = '127.0.0.1',
    this.port = 0,
    this.apiKey,
    this.protocolVersion = 'guandan-bot-v1',
    this.deckCount = 2,
    Logger? logger,
  }) : _logger = logger ?? Logger('HttpTestBot');

  final String host;
  final int port;

  /// Optional bot invocation key checked on incoming requests (server → bot).
  /// When set, every request must include a matching `Authorization: Bearer`
  /// or `X-Api-Key` header.
  final String? apiKey;

  final String protocolVersion;
  final int deckCount;
  final Logger _logger;

  HttpServer? _server;
  final _sessions = <String, BasicBot>{};

  int get sessionCount => _sessions.length;

  Uri get baseUrl {
    final server = _server;
    if (server == null) {
      throw StateError('HttpTestBot has not been started.');
    }
    return Uri.parse('http://$host:${server.port}');
  }

  Future<void> start() async {
    _server = await HttpServer.bind(host, port);
    _logger.info('HttpTestBot listening at $baseUrl');
    unawaited(_serve(_server!));
  }

  Future<void> _serve(HttpServer server) async {
    await for (final request in server) {
      await _handleRequest(request);
    }
  }

  Future<void> _handleRequest(HttpRequest request) async {
    try {
      if (!_isAuthorized(request)) {
        await _writeJson(
          request,
          HttpStatus.unauthorized,
          BotErrorMessage(
            sessionId: _sessionIdFromPath(request) ?? '',
            code: 'unauthorized',
            message: 'Authorization: Bearer <api_key> is required.',
          ).toJson(),
        );
        return;
      }

      if (request.method == 'GET' && request.uri.path == '/health') {
        await _writeJson(request, HttpStatus.ok, {'status': 'ok'});
        return;
      }

      if (request.method == 'POST' && request.uri.path == '/sessions') {
        final message = await _readBotMessage(request);
        final response = _handleEnvelope(message);
        await _writeBotResponse(request, response);
        return;
      }

      final segments = request.uri.pathSegments;
      if (segments.length == 3 &&
          segments[0] == 'sessions' &&
          segments[2] == 'messages' &&
          request.method == 'POST') {
        final message = await _readBotMessage(request);
        if (message.sessionId != segments[1]) {
          await _writeJson(
            request,
            HttpStatus.badRequest,
            BotErrorMessage(
              sessionId: message.sessionId,
              code: 'session_id_mismatch',
              message: 'Path session ID does not match message session ID.',
            ).toJson(),
          );
          return;
        }
        final response = _handleEnvelope(message);
        await _writeBotResponse(request, response);
        return;
      }

      if (segments.length == 2 &&
          segments[0] == 'sessions' &&
          request.method == 'DELETE') {
        final response = _handleSessionEnd(segments[1]);
        await _writeBotResponse(request, response);
        return;
      }

      await _writeText(request, HttpStatus.notFound, 'Not Found');
    } catch (error, stackTrace) {
      _logger.warning('Failed to handle HTTP bot request', error, stackTrace);
      await _writeJson(
        request,
        HttpStatus.badRequest,
        BotErrorMessage(
          sessionId: _sessionIdFromPath(request) ?? '',
          code: 'invalid_bot_message',
          message: error.toString(),
        ).toJson(),
      );
    }
  }

  Future<BotMessage> _readBotMessage(HttpRequest request) async {
    final raw = await utf8.decoder.bind(request).join();
    return BotMessage.parse(raw);
  }

  bool _isAuthorized(HttpRequest request) {
    final expected = apiKey;
    if (expected == null || expected.isEmpty) {
      return true;
    }
    final bearer = request.headers['authorization']?.firstOrNull;
    if (bearer == 'Bearer $expected') {
      return true;
    }
    final apiKeyHeader = request.headers['x-api-key']?.firstOrNull;
    return apiKeyHeader == expected;
  }

  String? _sessionIdFromPath(HttpRequest request) {
    final segments = request.uri.pathSegments;
    if (segments.length >= 2 && segments[0] == 'sessions') {
      return segments[1];
    }
    return null;
  }

  BotMessage? _handleEnvelope(BotMessage message) {
    _logReceivedMessage(message);
    final response = switch (message) {
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
    if (response != null) {
      _logSentMessage(response);
    }
    return response;
  }

  SessionStartedMessage _handleSessionStart(SessionStartMessage msg) {
    final seat = msg.seat ?? 1;
    final playerId = msg.playerId ?? 'http-test-$seat';
    final decks = msg.deckCount ?? deckCount;
    final team = seat % 2 == 0 ? PlayerTeam.blueTeam : PlayerTeam.redTeam;
    _sessions[msg.sessionId] = BasicBot(
      playerId,
      seat,
      team,
      decks,
      botCode: 'HttpTestBot',
    );
    return SessionStartedMessage(sessionId: msg.sessionId, accepted: true);
  }

  SessionEndedMessage _handleSessionEnd(String sessionId) {
    _sessions.remove(sessionId);
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
          sessionId,
          requestId,
          bot,
          availableCards,
          handOnTable,
          levelRank,
        ),
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

  Future<BotRegistrationResponse> registerDeployment({
    required Uri lobbyBaseUrl,
    required String accessToken,
    required RegisterBotDeploymentRequest request,
    Uri? deploymentBaseUrl,
  }) async {
    final body = request.toJson()
      ..['transport_type'] = BotTransportType.http.code
      ..['base_url'] = (deploymentBaseUrl ?? baseUrl).toString();

    final response = await http.post(
      lobbyBaseUrl.replace(path: '/api/bots/deployments'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $accessToken',
      },
      body: jsonEncode(body),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw HttpException(
        'Bot deployment registration failed: '
        '${response.statusCode} ${response.body}',
      );
    }
    return BotRegistrationResponse.fromJson(
      Map<String, dynamic>.from(jsonDecode(response.body) as Map),
    );
  }

  void _logReceivedMessage(BotMessage message) {
    _logger.info(
      '← Received ${MessageFormatter.format(message)}',
    );
  }

  void _logSentMessage(BotMessage message) {
    _logger.info(
      '→ Sent ${MessageFormatter.format(message)}',
    );
  }

  Future<void> _writeBotResponse(
    HttpRequest request,
    BotMessage? response,
  ) async {
    if (response == null) {
      request.response.statusCode = HttpStatus.noContent;
      await request.response.close();
      return;
    }
    await _writeJson(request, HttpStatus.ok, response.toJson());
  }

  Future<void> _writeJson(
    HttpRequest request,
    int statusCode,
    Map<String, dynamic> body,
  ) async {
    request.response
      ..statusCode = statusCode
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(body));
    await request.response.close();
  }

  Future<void> _writeText(
    HttpRequest request,
    int statusCode,
    String body,
  ) async {
    request.response
      ..statusCode = statusCode
      ..write(body);
    await request.response.close();
  }

  Future<void> dispose() async {
    await _server?.close(force: true);
    _server = null;
    _sessions.clear();
  }
}

extension _HeaderFirst on List<String>? {
  String? get firstOrNull {
    final self = this;
    if (self == null || self.isEmpty) return null;
    return self.first;
  }
}
