

import 'package:guandan_core/guandan_core.dart';
import 'hand_splitter_impl.dart';

abstract class HandSplitter {
  /// Returns one preferred split result for the given [cards] and its estimated score
  (List<Hand>, double) split(PokerCardList cards);
}

class PowerBasedHandSplitter implements HandSplitter {

  final CardRank levelRank;
  final int numberOfPlayers;

  int get _deckCount => (numberOfPlayers / 2).round();

  PowerBasedHandSplitter(this.levelRank, this.numberOfPlayers);

  @override
  (List<Hand>, double) split(PokerCardList cards) {
    final result = combine(cards, OverallValueCostEstimator(levelRank, _deckCount));
    return (result.bestSolution, result.cost);
  }
}


