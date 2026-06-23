import 'dart:core';

import 'package:guandan_core/guandan_core.dart';

/// An abstract class representing an AI player in the game
abstract class BotPlayer extends Player {

  /// The model of the AI player — delegates to [Player.botCode].
  @override
  String? get botCode;

  /// Randomness factor for the AI player
  double randomness = 0.3; // 0.0 means no randomness, 1.0 means large randomness

  /// Strength factor for the AI player
  double strength = 1.0; // 0.0 means weakest, 1.0 means full strength

  BotPlayer(super.id, super.seat, super.team, {super.displayName, super.botCode, super.cardsOnHand});

  BotPlayer.copy(super.player, {super.newId}): super.copy();

  BotPlayer.deepCopy(super.player, {super.newId, super.withCardsOnHand, super.withPlayedCards}):
    super.deepCopy();

  @override
  Map<String, dynamic> toJson({bool withCardsOnHand = true, bool withPlayedCards = true, bool withPlayerType = false}) {
    var p = super.toJson(withCardsOnHand: withCardsOnHand, withPlayedCards: withPlayedCards, withPlayerType: withPlayerType);
    p['bot_model'] = botCode;
    return p;
  }

  @override
  bool get isHumanPlayer => false;

  /// Provide the cards to play in response to a request, but do not actually play them
  Hand getCardsToPlay(Hand handOnTable, CardRank levelRank);

  /// Provide a tribute card upon request
  PokerCard tribute();

  /// Return a card in response to a tribute received
  PokerCard returnCard();

  void receiveMessage(GameMessage message) {
    if (message is NewRoundMessage) {
      setCardsOnHand(PokerCardList.from(message.hand));
    }
    else if (message is HandPlayedMessage) {
      if (message.playerId == id) {
        cardsOnHand!.removeCards(message.cards.cards);
      }
    }
    else if (message is TributeResultMessage) {
      for (final t in message.tributeResult.tributes) {
        if (t.winner!.id == id) {
          cardsOnHand!.add(t.tributeCard!);
          cardsOnHand!.removeCard(t.returnCard!);
        }
        if (t.payer.id == id) {
          cardsOnHand!.removeCard(t.tributeCard!);
          cardsOnHand!.add(t.returnCard!);
        }
      }
    }
    else if (message is PlayerJoinedRoomMessage) {
      if (message.player.id == id) {
        final gameState = message.gameState;
        if (gameState != null) {
          final playerInGameState = gameState.players.firstWhere((p) => p.id == id, orElse: () => this);
          if (playerInGameState.cardsOnHand != null) {
            setCardsOnHand(playerInGameState.cardsOnHand!);
          }
        }
      }
    }
  }
}
