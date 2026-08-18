import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

/// A sample extension message defined outside the core's message catalogue,
/// following the documented extension recipe (see [CustomMessageRegistry]):
/// `type: MessageType.custom`, an own wire-type subtype, and a `fromJson`
/// factory registered in the registry.
class TestExtensionMessage extends GameRoomMessage {
  /// The extension's own wire-type subtype.
  static const extensionType = 'iTestExtension';

  final String payload;

  TestExtensionMessage({
    super.messageId,
    required super.roomId,
    required super.gameId,
    required this.payload,
  }) : super(type: MessageType.custom);

  @override
  String get wireType => extensionType;

  factory TestExtensionMessage.fromJson(Map<String, dynamic> json) {
    return TestExtensionMessage(
      messageId: json['message_id'] as String?,
      roomId: json['room_id'] as String,
      gameId: json['game_id'] as String,
      payload: json['payload'] as String,
    );
  }

  @override
  Map<String, dynamic> toJson() {
    final json = super.toJson();
    json['payload'] = payload;
    return json;
  }
}

void main() {
  group('MessageType.custom', () {
    test('from() resolves built-in names as before', () {
      expect(MessageType.from('heartbeat'), MessageType.heartbeat);
      expect(MessageType.from('iNewRound'), MessageType.iNewRound);
      expect(
          MessageType.from('pPlayHandRequest'), MessageType.pPlayHandRequest);
    });

    test('from() resolves unknown names to custom instead of throwing', () {
      expect(MessageType.from('iTestExtension'), MessageType.custom);
      expect(MessageType.from('nonsense'), MessageType.custom);
    });

    test('value of custom is the wire string "custom"', () {
      expect(MessageType.custom.value, 'custom');
    });
  });

  group('wireType', () {
    test('built-in messages emit their MessageType value (unchanged)', () {
      final msg = HeartbeatMessage(playerId: 'p1');
      expect(msg.wireType, MessageType.heartbeat.value);
      expect(msg.toJson()['type'], 'heartbeat');
    });

    test('custom subclasses emit their own subtype string', () {
      final msg = TestExtensionMessage(
        roomId: 'r1',
        gameId: 'g1',
        payload: 'hello',
      );
      expect(msg.type, MessageType.custom);
      expect(msg.wireType, TestExtensionMessage.extensionType);
      expect(msg.toJson()['type'], 'iTestExtension');
    });
  });

  group('CustomMessageRegistry', () {
    test('register rejects collisions with built-in MessageType names', () {
      expect(
        () => CustomMessageRegistry.register(
          'heartbeat',
          TestExtensionMessage.fromJson,
        ),
        throwsArgumentError,
      );
    });

    test('unknown unregistered types still throw through the factory', () {
      expect(
        () => GameMessageFactory.fromJson({'type': 'iUnknownType'}),
        throwsUnsupportedError,
      );
    });

    test('registered extension types deserialize through the factory', () {
      CustomMessageRegistry.register(
        TestExtensionMessage.extensionType,
        TestExtensionMessage.fromJson,
      );

      final parsed = GameMessageFactory.fromJson({
        'type': 'iTestExtension',
        'message_id': 'm1',
        'room_id': 'r1',
        'game_id': 'g1',
        'payload': 'hello',
      });

      expect(parsed, isA<TestExtensionMessage>());
      final ext = parsed as TestExtensionMessage;
      expect(ext.roomId, 'r1');
      expect(ext.gameId, 'g1');
      expect(ext.payload, 'hello');
      expect(ext.messageId, 'm1');
    });

    test('re-registration replaces the factory (idempotent startup)', () {
      CustomMessageRegistry.register(
        TestExtensionMessage.extensionType,
        TestExtensionMessage.fromJson,
      );
      // Registering again (e.g. at a second startup) must not throw.
      CustomMessageRegistry.register(
        TestExtensionMessage.extensionType,
        TestExtensionMessage.fromJson,
      );
      expect(
          CustomMessageRegistry.isRegistered(
              TestExtensionMessage.extensionType),
          isTrue);
    });

    test('registered type survives a toJson/fromJson round trip', () {
      CustomMessageRegistry.register(
        TestExtensionMessage.extensionType,
        TestExtensionMessage.fromJson,
      );

      final original = TestExtensionMessage(
        messageId: 'm2',
        roomId: 'r1',
        gameId: 'g1',
        payload: 'round-trip',
      );
      final restored = GameMessageFactory.fromJson(original.toJson());

      expect(restored.toJson(), original.toJson());
    });

    test(
        'built-in messages still dispatch through the factory (backward compat)',
        () {
      final parsed = GameMessageFactory.fromJson({
        'type': 'heartbeat',
        'message_id': null,
        'player_id': 'p1',
      });
      expect(parsed, isA<HeartbeatMessage>());
    });
  });
}
