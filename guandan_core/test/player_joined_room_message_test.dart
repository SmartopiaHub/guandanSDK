import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  test('joining snapshot round-trips auto-delegation state', () {
    final message = PlayerJoinedRoomMessage(
      player: Player('player-1', 1, PlayerTeam.redTeam),
      roomId: 'room-1',
      gameId: 'game-1',
      autoDelegated: true,
    );

    final decoded = PlayerJoinedRoomMessage.fromJson(message.toJson());

    expect(decoded.autoDelegated, isTrue);
  });
}
