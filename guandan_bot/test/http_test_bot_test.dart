import 'dart:convert';
import 'dart:io';

import 'package:guandan_bot/guandan_bot.dart';
import 'package:http/http.dart' as http;
import 'package:test/test.dart';

void main() {
  group('HttpTestBot', () {
    late HttpTestBot bot;

    tearDown(() async {
      await bot.dispose();
    });

    test('requires optional API key and handles session_start', () async {
      bot = HttpTestBot(apiKey: 'secret-test-key');
      await bot.start();

      final unauthorized = await http.post(
        bot.baseUrl.replace(path: '/sessions'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
          const SessionStartMessage(sessionId: 'session-1').toJson(),
        ),
      );
      expect(unauthorized.statusCode, HttpStatus.unauthorized);

      final authorized = await http.post(
        bot.baseUrl.replace(path: '/sessions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer secret-test-key',
        },
        body: jsonEncode(
          const SessionStartMessage(
            sessionId: 'session-1',
            playerId: 'bot-player-1',
            seat: 1,
          ).toJson(),
        ),
      );

      expect(authorized.statusCode, HttpStatus.ok);
      final body = jsonDecode(authorized.body) as Map<String, dynamic>;
      expect(body['type'], 'session_started');
      expect(body['session_id'], 'session-1');
      expect(body['accepted'], true);
      expect(bot.sessionCount, 1);
    });

    test('responds to request_hand with a game_message envelope', () async {
      bot = HttpTestBot();
      await bot.start();

      await http.post(
        bot.baseUrl.replace(path: '/sessions'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
          const SessionStartMessage(
            sessionId: 'session-2',
            playerId: 'bot-player-2',
            seat: 2,
          ).toJson(),
        ),
      );

      final response = await http.post(
        bot.baseUrl.replace(path: '/sessions/session-2/messages'),
        headers: {
          'Content-Type': 'application/json',
          'X-Guandan-Bot-Protocol': 'guandan-bot-v1',
        },
        body: jsonEncode({
          'type': 'game_message',
          'request_id': 'req-1',
          'session_id': 'session-2',
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
        }),
      );

      expect(response.statusCode, HttpStatus.ok);
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      expect(body['type'], 'game_message');
      expect(body['request_id'], 'req-1');
      expect(body['session_id'], 'session-2');
      final payload = body['payload'] as Map<String, dynamic>;
      expect(payload['type'], 'pPlayHandRequest');
      expect((payload['cards'] as String?)?.isNotEmpty, isTrue);
    });

    test('answers authenticated health verification', () async {
      bot = HttpTestBot(apiKey: 'challenge-token');
      await bot.start();

      final unauthorized = await http.get(
        bot.baseUrl.replace(path: '/health'),
      );
      expect(unauthorized.statusCode, HttpStatus.unauthorized);

      final authorized = await http.get(
        bot.baseUrl.replace(path: '/health'),
        headers: {'Authorization': 'Bearer challenge-token'},
      );

      expect(authorized.statusCode, HttpStatus.ok);
      final body = jsonDecode(authorized.body) as Map<String, dynamic>;
      expect(body['status'], 'ok');
    });

    test('registerDeployment sends base HTTP URL and receives issued tokens',
        () async {
      bot = HttpTestBot(apiKey: 'outbound-key');
      await bot.start();

      late Map<String, dynamic> receivedBody;
      late String receivedAuthorization;
      final lobby = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(() => lobby.close(force: true));
      lobby.listen((request) async {
        receivedAuthorization = request.headers['authorization']?.first ?? '';
        receivedBody = jsonDecode(await utf8.decoder.bind(request).join())
            as Map<String, dynamic>;
        request.response
          ..statusCode = HttpStatus.created
          ..headers.contentType = ContentType.json
          ..write(jsonEncode({
            'deployment': {
              'deployment_id': 'dep-1',
              'provider_id': 'provider-1',
              'transport_type': 'http',
              'base_url': receivedBody['base_url'],
              'supported_bot_definition_ids': ['def-1'],
              'supported_protocol_versions': ['guandan-bot-v1'],
              'max_concurrent_sessions': 4,
              'status': 'pending_verification',
              'created_at': DateTime.utc(2026, 6, 5).toIso8601String(),
              'updated_at': DateTime.utc(2026, 6, 5).toIso8601String(),
            },
            'deployment_management_key': 'platform-generated-management-key',
            'api_key': 'platform-generated-management-key',
            'bot_invocation_token': 'platform-generated-invocation-token',
          }))
          ..close();
      });

      final response = await bot.registerDeployment(
        lobbyBaseUrl: Uri.parse('http://127.0.0.1:${lobby.port}'),
        accessToken: 'developer-token',
        deploymentBaseUrl: Uri.parse('https://public-bot.example.com/guandan'),
        request: const RegisterBotDeploymentRequest(
          providerId: 'provider-1',
          transportType: BotTransportType.http,
          supportedBotDefinitionIds: ['def-1'],
          supportedProtocolVersions: ['guandan-bot-v1'],
          maxConcurrentSessions: 4,
        ),
      );

      expect(
        response.deployment!.baseUrl,
        Uri.parse('https://public-bot.example.com/guandan'),
      );
      expect(receivedAuthorization, 'Bearer developer-token');
      expect(receivedBody['transport_type'], 'http');
      expect(
          receivedBody['base_url'], 'https://public-bot.example.com/guandan');
      expect(receivedBody.containsKey('api_key'), isFalse);
      expect(
        response.deploymentManagementKey,
        'platform-generated-management-key',
      );
      expect(
        response.botInvocationToken,
        'platform-generated-invocation-token',
      );
    });
  });
}
