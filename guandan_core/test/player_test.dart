import 'package:guandan_core/guandan_core.dart';
import 'package:test/test.dart';

void main() {
  group('Player', () {
    test('toJson and fromJson', () {
      final player = Player('Player 1', 1, PlayerTeam.redTeam);
      final json = player.toJson();
      final newPlayer = Player.fromJson(json);

      expect(newPlayer.id, player.id);
      expect(newPlayer.seat, player.seat);
      expect(newPlayer.team, player.team);
      expect(newPlayer.name, player.name);
    });

    test('hasCards', () {
      final player = Player('1', 1, PlayerTeam.redTeam);
      final card1 = PokerCard.from('AS');
      final card2 = PokerCard.from('KH');
      player.setCardsOnHand(PokerCardList([card1, card2]));

      expect(player.hasCards([card1]), true);
      expect(player.hasCards([card2]), true);
      expect(player.hasCards([PokerCard.from('QH')]), false);
      expect(player.hasCards([card1, card1]), false);
    });

    test('hasAtLeastOneCard', () {
      final player = Player('1', 1, PlayerTeam.redTeam);
      player.setCardsOnHand(Hand.emptyHand());
      expect(player.hasAtLeastOneCard, false);

      player.cardsOnHand!.addAll([PokerCard.from('QH')]);
      expect(player.hasAtLeastOneCard, true);
    });

    test('cardCountOnHand', () {
      final player = Player('1', 1, PlayerTeam.redTeam);
      player.setCardsOnHand(Hand(List.generate(25, (index) => PokerCard.from('QH')), HandType.unknown));
      expect(player.cardCountOnHand, 25);

      player.cardsOnHand!.addAll([PokerCard.from('QH')]);
      expect(player.cardCountOnHand, 26);
    });

    test('play', () {
      final player = Player('1', 1, PlayerTeam.redTeam);
      final card1 = PokerCard.from('QH');
      final card2 = PokerCard.from('AH');
      player.setCardsOnHand(PokerCardList([card1, card2]));

      player.play(Hand([card1], HandType.single));
      expect(player.cardsOnHand!.hasCards([card1]), false);
      expect(player.playedCards.hasCards([card1]), true);
    });

    test('reset', () {
      final player = Player('1', 1, PlayerTeam.redTeam);
      player.setCardsOnHand(PokerCardList.fromString('QH'));
      player.playedCards.addAll([PokerCard.from('QH')]);

      player.resetHands();
      expect(player.cardsOnHand!.length, 0);
      expect(player.playedCards.length, 0);
    });
  });

  group('nextSeat', () {
    test('nextSeat calculation', () {
      expect(nextSeat(1, 4), 2);
      expect(nextSeat(2, 4), 3);
      expect(nextSeat(3, 4), 4);
      expect(nextSeat(4, 4), 1);
      expect(nextSeat(3, 6), 4);
      expect(nextSeat(6, 6), 1);
    });
  });

  group('nextPlayer', () {
    test('nextPlayer returns correct player', () {
      final player1 = Player('1', 1, PlayerTeam.redTeam);
      player1.setCardsOnHand(Hand.emptyHand());
      final player2 = Player('2', 2, PlayerTeam.blueTeam);
      player2.setCardsOnHand(Hand.emptyHand());
      final player3 = Player('3', 3, PlayerTeam.redTeam);
      player3.setCardsOnHand(Hand.emptyHand());
      final player4 = Player('4', 4, PlayerTeam.blueTeam);
      player4.setCardsOnHand(Hand.emptyHand());
      final players = [player1, player2, player3, player4];

      expect(nextPlayer(player1, players, false, false)?.id, player2.id);
      expect(nextPlayer(player2, players, false, false)?.id, player3.id);
      expect(nextPlayer(player3, players, false, false)?.id, player4.id);
      expect(nextPlayer(player4, players, false, false)?.id, player1.id);
      expect(nextPlayer(player1, players, true, false)?.id, player3.id);
      expect(nextPlayer(player2, players, true, false)?.id, player4.id);
      expect(nextPlayer(player3, players, true, false)?.id, player1.id);
      expect(nextPlayer(player4, players, true, false)?.id, player2.id);
      expect(nextPlayer(player1, players, false, true), null);
    });
  });
}