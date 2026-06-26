import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  group('GameState Tests', () {
    late GameState gameState;
    late Player player1;
    late Player player2;
    late Player player3;
    late Player player4;

    setUp(() {
      player1 = Player('Player 1', 1, PlayerTeam.redTeam, displayName: 'alex');
      player2 = Player('Player 2', 2, PlayerTeam.blueTeam, displayName: 'alex');
      player3 = Player('Player 3', 3, PlayerTeam.redTeam, displayName: 'alex');
      player4 = Player('Player 4', 4, PlayerTeam.blueTeam, displayName: 'alex');

      gameState = GameState();
      gameState.addPlayer(player1);
      gameState.addPlayer(player2);
      gameState.addPlayer(player3);
      gameState.addPlayer(player4);
    });

    test('Get Player', () {
      expect(gameState.players.length, 4);
      expect(gameState.getPlayerBySeat(1)!.name, 'alex');
      expect(gameState.getPlayerById('Player 2').name, 'bob');
    });

    test('New Round', () {
      gameState.newRound(startPlayer: player1);
      expect(gameState.currentRound!.id, 'R1');
      expect(gameState.currentRound!.startPlayer!.id, player1.id);
    });

    test('Play Cards', () {
      gameState.newRound(startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S'));
      Hand hand = Hand.fromString('3D 3S');
      gameState.playCards(player1, hand);
      expect(gameState.currentRound!.currentPhase.turns.length, 1);
      expect(gameState.currentRound!.currentPhase.turns[0].player.id, player1.id);
      expect(gameState.currentRound!.currentPhase.turns[0].playedHand, hand);
    });

    test('Can Pass', () {
      gameState.newRound(startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S'));
      player2.setCardsOnHand(Hand.fromString('4D 4S'));
      expect(gameState.canPass(), false);
      Hand hand = Hand.fromString('3D 3S');
      gameState.playCards(player1, hand);
      expect(gameState.canPass(), true);
    });

    test('Can Play', () {
      gameState.newRound(startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S 3D 2H* 2S*'));
      player2.setCardsOnHand(Hand.emptyHand());
      player4.setCardsOnHand(Hand.fromString('AD AS'));
      player3.setCardsOnHand(Hand.fromString('4D 4S RJ RJ'));
      Hand hand1 = Hand.fromString('3D 3S');
      hand1 = deduceHandType(hand1);
      expect(gameState.canPlay(hand1, player1.id), true);
      Hand hand2 = Hand.fromString('2H* 2S*');
      hand2 = deduceHandType(hand2);
      gameState.playCards(player1, hand2);
      expect(gameState.currentPlayerToPlay!.id, player3.id);
      expect(gameState.canPlay(Hand.fromString('4D 4S'), player1.id), false);
      expect(gameState.canPlay(Hand.fromString('4D 4S'), player2.id), false);
      expect(gameState.canPlay(Hand.fromString('4D 4S 4S'), player3.id), false);
      expect(gameState.canPlay(Hand.fromString('4D 4S'), player3.id), false);
      expect(gameState.canPlay(Hand.fromString('RJ RJ'), player3.id), true);
    });

    test('Cannot pass before any non-empty hand is on the table', () {
      gameState.newRound(startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S'));
      player2.setCardsOnHand(Hand.fromString('4D 4S'));
      player3.setCardsOnHand(Hand.fromString('5D 5S'));
      player4.setCardsOnHand(Hand.fromString('6D 6S'));

      expect(gameState.canPlay(Hand.emptyHand(), player1.id), isFalse);

      gameState.currentRound!.currentPhase.appendTurn(player1, Hand.emptyHand());
      expect(gameState.currentPlayerToPlay!.id, player2.id);
      expect(gameState.canPlay(Hand.emptyHand(), player2.id), isFalse);
      expect(gameState.currentRound!.currentPhase.isEndOfPhase(gameState.players), isFalse);
    });

    test('Can pass after a non-empty hand is on the table', () {
      gameState.newRound(startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S'));
      player2.setCardsOnHand(Hand.fromString('4D 4S'));

      final hand = deduceHandType(Hand.fromString('3D 3S'));
      gameState.playCards(player1, hand);

      expect(gameState.canPlay(Hand.emptyHand(), player2.id), isTrue);
    });

    test('Current Player To Play', () {
      gameState.newRound(startPlayer: player1);
      expect(gameState.currentPlayerToPlay!.id, player1.id);
    });

    test('Save game state', () {
      gameState.newRound( startPlayer: player1);
      player1.setCardsOnHand(Hand.fromString('3D 3S 3D 2H* 2S*'));
      player2.setCardsOnHand(Hand.fromString('4D 4S'));
      player3.setCardsOnHand(Hand.fromString('4D 4S RJ RJ'));
      player4.setCardsOnHand(Hand.fromString('AD AS'));
      gameState.playCards(player1, Hand.fromString('3D 3S'));
      gameState.playCards(player2, Hand.fromString('4D 4S'));
      gameState.playCards(player3, Hand.fromString('4D 4S'));
      gameState.playCards(player4, Hand.fromString('AD AS'));
      gameState.saveToFile('saved_games/${gameState.id}-${gameState.lastTurnId}.json');
      gameState.loadFromFile('saved_games/${gameState.id}-${gameState.lastTurnId}.json');

    });
  });
}
