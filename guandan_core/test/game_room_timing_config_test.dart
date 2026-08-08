import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  test('no-limit timing survives a room config JSON round trip', () {
    final original = GameRoomConfig(
      requiredPlayers: 4,
      timingConfig: createPresetTimingConfig(PresetTimingMode.noLimit),
    );

    final decoded = GameRoomConfig.fromJson(original.toJson());

    expect(decoded.isTimed, isFalse);
    expect(decoded.playTimeLimit, isNull);
    expect(decoded.tributeTimeLimit, isNull);
    expect(decoded.returnTimeLimit, isNull);
  });

  test('explicit timed settings survive a room config JSON round trip', () {
    final original = GameRoomConfig(
      requiredPlayers: 4,
      timingConfig: TimingConfig(
        playTimeLimit: 321,
        tributeTimeLimit: 322,
        returnTimeLimit: 323,
      ),
    );

    final decoded = GameRoomConfig.fromJson(original.toJson());

    expect(decoded.playTimeLimit, const Duration(seconds: 321));
    expect(decoded.tributeTimeLimit, const Duration(seconds: 322));
    expect(decoded.returnTimeLimit, const Duration(seconds: 323));
  });
}
