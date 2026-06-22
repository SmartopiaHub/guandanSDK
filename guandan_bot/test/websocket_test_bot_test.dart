import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:guandan_bot/guandan_bot.dart';
import 'package:test/test.dart';

/// Starts a mock game server bot gateway and returns the port.
Future<int> _startMockGateway({
  required void Function(WebSocket) onConnected,
}) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  final port = server.port;

  server.listen((request) async {
    if (request.uri.path == '/bot-gateway/v1') {
      final auth = request.headers['authorization']?.first ?? '';
      if (!auth.contains('Bearer ')) {
        request.response
          ..statusCode = HttpStatus.unauthorized
          ..close();
        return;
      }
      final socket = await WebSocketTransformer.upgrade(request);
      onConnected(socket);
      return;
    }
    request.response
      ..statusCode = HttpStatus.notFound
      ..close();
  });

  return port;
}

/// Parses the first response from [responses] whose decoded JSON contains
/// the given [key] / [value] pair.
Map<String, dynamic>? _firstResponseByType(
  List<String> responses,
  String type,
) {
  for (final r in responses) {
    final decoded = jsonDecode(r) as Map<String, dynamic>;
    if (decoded['type'] == type) {
      return decoded;
    }
  }
  return null;
}

void main() {
  group('WebSocketTestBot', () {
    test('connects to bot gateway with API key and handles session_start',
        () async {
      final connected = Completer<WebSocket>();
      final responses = <String>[];
      final port = await _startMockGateway(
        onConnected: (socket) {
          connected.complete(socket);
          socket.listen((frame) {
            responses.add(frame as String);
          });
        },
      );

      final bot = WebSocketTestBot(
        gameServerUrl: 'ws://127.0.0.1:$port',
        apiKey: 'Q57ZXEnaPuKaJt3_18QCSg6pFN_Cv9_92WW2Wey9ylI',
      );

      unawaited(bot.connect());

      final mockSocket = await connected.future.timeout(
        const Duration(seconds: 5),
      );

      // Send session_start
      mockSocket.add(jsonEncode({
        'type': 'session_start',
        'session_id': 'test-session-1',
        'seat': 1,
        'player_id': 'bot-player-1',
        'rule_set': 'classic',
      }));

      await Future.delayed(const Duration(milliseconds: 500));

      final sessionResponse = _firstResponseByType(responses, 'session_started');
      expect(sessionResponse, isNotNull,
          reason: 'Expected session_started response, got: $responses');
      expect(sessionResponse!['session_id'], 'test-session-1');
      expect(sessionResponse['accepted'], true);

      await bot.dispose();
      await mockSocket.close();
    });

    test('responds to request_hand with a game_message envelope', () async {
      final connected = Completer<WebSocket>();
      final responses = <String>[];
      final port = await _startMockGateway(
        onConnected: (socket) {
          connected.complete(socket);
          socket.listen((frame) {
            responses.add(frame as String);
          });
        },
      );

      final bot = WebSocketTestBot(
        gameServerUrl: 'ws://127.0.0.1:$port',
        apiKey: 'test-key',
      );

      unawaited(bot.connect());

      final mockSocket = await connected.future.timeout(
        const Duration(seconds: 5),
      );

      // Start session with cards
      mockSocket.add(jsonEncode({
        'type': 'session_start',
        'session_id': 'test-session-2',
        'seat': 2,
        'player_id': 'bot-player-2',
      }));
      await Future.delayed(const Duration(milliseconds: 200));

      // Request hand using a game_message envelope
      mockSocket.add(jsonEncode({
        'type': 'game_message',
        'request_id': 'req-1',
        'session_id': 'test-session-2',
        'payload': {
          'type': 'sPlayHandRequest',
          'room_id': 'room-1',
          'game_id': 'game-1',
          'round_id': 'round-1',
          'player_id': 'bot-player-2',
          'turn_id': 'turn-1',
          'available_cards': 'AS AH AD AC 2S 2H 2D 2C',
          'hand_on_table': '',
          'level_rank': '2',
          'timeout': 3000,
        },
      }));

      await Future.delayed(const Duration(milliseconds: 500));

      final handResponse = _firstResponseByType(responses, 'game_message');
      expect(handResponse, isNotNull,
          reason: 'Expected game_message response, got: $responses');
      if (handResponse != null) {
        expect(handResponse['request_id'], 'req-1');
        expect(handResponse['payload'], isA<Map>());
        final payload = handResponse['payload'] as Map<String, dynamic>;
        expect(payload['type'], 'pPlayHandRequest');
        expect((payload['cards'] as String?)?.isNotEmpty, isTrue);
      }

      await bot.dispose();
      await mockSocket.close();
    });

    test('responds to request_tribute with a game_message envelope', () async {
      final connected = Completer<WebSocket>();
      final responses = <String>[];
      final port = await _startMockGateway(
        onConnected: (socket) {
          connected.complete(socket);
          socket.listen((frame) {
            responses.add(frame as String);
          });
        },
      );

      final bot = WebSocketTestBot(
        gameServerUrl: 'ws://127.0.0.1:$port',
        apiKey: 'test-key',
      );

      unawaited(bot.connect());

      final mockSocket = await connected.future.timeout(
        const Duration(seconds: 5),
      );

      mockSocket.add(jsonEncode({
        'type': 'session_start',
        'session_id': 'test-session-3',
        'seat': 1,
        'player_id': 'bot-player-3',
      }));
      await Future.delayed(const Duration(milliseconds: 200));

      mockSocket.add(jsonEncode({
        'type': 'game_message',
        'request_id': 'req-trib-1',
        'session_id': 'test-session-3',
        'payload': {
          'type': 'sTributeCardRequest',
          'room_id': 'room-1',
          'game_id': 'game-1',
          'round_id': 'round-1',
          'player_id': 'bot-player-3',
          'available_cards': 'AS AH AD 2S',
          'timeout': 3000,
        },
      }));

      await Future.delayed(const Duration(milliseconds: 500));

      final gameResponses = responses
          .map((r) => jsonDecode(r) as Map<String, dynamic>)
          .where((r) => r['type'] == 'game_message')
          .toList();

      expect(gameResponses, isNotEmpty,
          reason: 'Expected game_message response, got: $responses');

      final tributeResponse = gameResponses.firstWhere(
        (r) {
          final payload = r['payload'] as Map<String, dynamic>?;
          return payload?['type'] == 'pPayTributeRequest';
        },
        orElse: () => <String, dynamic>{},
      );
      expect(tributeResponse, isNotEmpty,
          reason: 'Expected pPayTributeRequest payload');
      if (tributeResponse.isNotEmpty) {
        final payload = tributeResponse['payload'] as Map<String, dynamic>;
        expect(
          (payload['tribute_card'] as String?)?.isNotEmpty,
          isTrue,
        );
      }

      await bot.dispose();
      await mockSocket.close();
    });

    test('handles session_end and cleanup', () async {
      final connected = Completer<WebSocket>();
      final responses = <String>[];
      final port = await _startMockGateway(
        onConnected: (socket) {
          connected.complete(socket);
          socket.listen((frame) {
            responses.add(frame as String);
          });
        },
      );

      final bot = WebSocketTestBot(
        gameServerUrl: 'ws://127.0.0.1:$port',
        apiKey: 'test-key',
      );

      unawaited(bot.connect());

      final mockSocket = await connected.future.timeout(
        const Duration(seconds: 5),
      );

      mockSocket.add(jsonEncode({
        'type': 'session_start',
        'session_id': 'test-session-4',
        'seat': 1,
        'player_id': 'bot-player-4',
      }));
      await Future.delayed(const Duration(milliseconds: 200));

      mockSocket.add(jsonEncode({
        'type': 'session_end',
        'session_id': 'test-session-4',
      }));

      await Future.delayed(const Duration(milliseconds: 500));

      final endResponse = _firstResponseByType(responses, 'session_ended');
      expect(endResponse, isNotNull,
          reason: 'Expected session_ended response, got: $responses');
      expect(endResponse!['session_id'], 'test-session-4');

      await bot.dispose();
      await mockSocket.close();
    });
  });
}
