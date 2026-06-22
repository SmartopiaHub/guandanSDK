

import 'package:guandan_core/guandan_core.dart';

import 'hand_splitter_impl.dart';


abstract class PlayScoreEstimator {

  /// Estimate the score of playing a list of cards.
  /// The score is a relative measure of how valuable it is to play the cards, with lower values indicating more valuable plays. 
  double estimateScore(PokerCardList cards);

  /// The level rank, which can be used to adjust the estimation based on the current level of the game.
  CardRank get levelRank;
}

class PowerBasedScoreEstimator implements PlayScoreEstimator {

  @override
  final CardRank levelRank;
  final int numberOfPlayers;

  PowerBasedScoreEstimator(this.levelRank, this.numberOfPlayers);

  int get _deckCount => (numberOfPlayers / 2).round();

  @override
  double estimateScore(PokerCardList cards) {
    // A simple implementation that estimates score based on the power of the cards. 
    // This is a placeholder and can be replaced with a more sophisticated estimation algorithm.
    return estimateCost(cards, OverallValueCostEstimator(levelRank, _deckCount));
  }
}
