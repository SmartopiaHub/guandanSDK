import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  group('Player - after PlayerProfile removal', () {
    test('constructor with displayName and botCode', () {
      final player = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'Alice', botCode: 'strongBot');

      expect(player.id, 'p1');
      expect(player.seat, 1);
      expect(player.team, PlayerTeam.redTeam);
      expect(player.displayName, 'Alice');
      expect(player.botCode, 'strongBot');
      expect(player.name, 'Alice');
      expect(player.isHumanPlayer, false);
      expect(player.isAIPlayer, true);
    });

    test('human player has null botCode', () {
      final player = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'Human');

      expect(player.isHumanPlayer, true);
      expect(player.isAIPlayer, false);
      expect(player.botCode, isNull);
    });

    test('name falls back to id when displayName is null', () {
      final player = Player('player-uuid', 1, PlayerTeam.redTeam);
      expect(player.name, 'player-uuid');
    });

    test('toJson and fromJson round-trip (new format)', () {
      final player = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'TestPlayer', botCode: 'basicBot');
      player.playedCards.addAll([
        PokerCard.from('AH'),
        PokerCard.from('AS'),
      ]);

      final json = player.toJson(withCardsOnHand: false, withPlayedCards: true);
      expect(json['player_id'], 'p1');
      expect(json['seat'], 1);
      expect(json['display_name'], 'TestPlayer');
      expect(json['bot_model'], 'basicBot');
      // Old profile key should NOT be present
      expect(json.containsKey('profile'), false);

      // Round-trip
      final restored = Player.fromJson(json);
      expect(restored.id, 'p1');
      expect(restored.displayName, 'TestPlayer');
      expect(restored.botCode, 'basicBot');
      expect(restored.isHumanPlayer, false);
    });

    test('fromJson backward compat: reads old profile format', () {
      final oldJson = {
        'player_id': 'p1',
        'seat': 1,
        'team': 'redTeam',
        'profile': {
          'nickname': 'OldPlayer',
          'bot_model': 'legacyBot',
        },
        'played_cards': '',
      };

      final player = Player.fromJson(oldJson);
      expect(player.id, 'p1');
      expect(player.displayName, 'OldPlayer');
      expect(player.botCode, 'legacyBot');
    });

    test('deepCopy preserves displayName and botCode', () {
      final original = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'Original', botCode: 'testBot');
      final copy = Player.deepCopy(original);

      expect(copy.displayName, 'Original');
      expect(copy.botCode, 'testBot');
      expect(copy.isHumanPlayer, false);
    });

    test('deepCopy with newId', () {
      final original = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'Original');
      final copy = Player.deepCopy(original, newId: 'p2');

      expect(copy.id, 'p2');
      expect(copy.displayName, 'Original');
    });

    test('Player.copy preserves displayName and botCode', () {
      final original = Player('p1', 1, PlayerTeam.redTeam,
          displayName: 'Original', botCode: 'testBot');
      final copy = Player.copy(original);

      expect(copy.displayName, 'Original');
      expect(copy.botCode, 'testBot');
    });
  });
}
