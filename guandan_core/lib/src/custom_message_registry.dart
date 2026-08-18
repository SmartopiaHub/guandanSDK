import 'message.dart';

/// Registry for extension message types defined outside `guandan_core`.
///
/// `guandan_core` ships a closed set of built-in [GameMessage] types whose
/// wire strings are enumerated by [MessageType]. Packages outside the core
/// (e.g. `guandan_shared`) can extend the wire protocol **without modifying
/// `guandan_core`**:
///
/// 1. Subclass [GameMessage] (or [GameRoomMessage]) with
///    `type: MessageType.custom`.
/// 2. Override [GameMessage.wireType] to return the extension's own subtype
///    string — this is the value of the JSON `"type"` field and the
///    discriminator that distinguishes the extension class from other custom
///    messages.
/// 3. Implement a `fromJson` factory and register it here **before** any
///    frame of that type can arrive (e.g. at process startup):
///
///    ```dart
///    CustomMessageRegistry.register(MyMessage.type, MyMessage.fromJson);
///    ```
///
/// 4. [GameMessageFactory.fromJson] then deserializes the type through the
///    registered factory, so both ends of a connection can treat extension
///    messages as ordinary [GameMessage]s routed by the standard dispatch.
///
/// Registration is process-global. Registering an existing wire type again
/// replaces its factory (idempotent — safe to call at every startup). A wire
/// type that collides with a built-in [MessageType] name is rejected: built-in
/// messages always win in [GameMessageFactory.fromJson].
final class CustomMessageRegistry {
  CustomMessageRegistry._();

  static final Map<String, GameMessage Function(Map<String, dynamic>)>
      _factories = <String, GameMessage Function(Map<String, dynamic>)>{};

  /// Registers [fromJson] as the deserializer for the wire [type] string.
  ///
  /// [type] must not collide with a built-in [MessageType] name.
  static void register(
    String type,
    GameMessage Function(Map<String, dynamic>) fromJson,
  ) {
    if (MessageType.from(type) != MessageType.custom) {
      throw ArgumentError.value(
        type,
        'type',
        'collides with a built-in MessageType; built-in messages cannot be '
            'overridden by the registry',
      );
    }
    _factories[type] = fromJson;
  }

  /// Returns the factory registered for [type], or null when none is
  /// registered.
  static GameMessage Function(Map<String, dynamic>)? lookup(String type) =>
      _factories[type];

  /// Whether a factory is currently registered for [type].
  static bool isRegistered(String type) => _factories.containsKey(type);
}
