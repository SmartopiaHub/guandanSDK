import 'dart:math';

import 'package:guandan_core/guandan_core.dart';

import 'utility.dart';



class MinHandsCostEstimator implements CostEstimator {

  @override
  final CardRank levelRank;
  
  final int _numberOfDecks;

  @override
  int get deckCount => _numberOfDecks;

  MinHandsCostEstimator(this.levelRank, int deckCount): _numberOfDecks = deckCount;

  @override
  double estimateCards(PokerCardList cards, int wildCards, List<Hand> solution) {
    return calculateMinHands(cards, wildCards, solution).toDouble();
  }

  @override
  double estimateHand(Hand hand) {
    if (hand.type == HandType.bomb) {
      return 0.0;
    }
    return 1;
  }

  int calculateMinHandsImp(int cnt1, int cnt2, int cnt3, int cnt4plus, int wildCards, List<int> wildConfig) {
    if (wildCards <= 0) {
      return cnt1 + max(cnt2, cnt3);
    } else {
      int minHandsPossible = 28;
      if (cnt1 > 0) {
        var cost = calculateMinHandsImp(cnt1 - 1, cnt2 + 1, cnt3, cnt4plus, wildCards - 1, wildConfig);
        if (cost < minHandsPossible) {
          wildConfig[1] = wildConfig[1] + 1; // use a wild card to make a pair
          minHandsPossible = cost;
        }
      }
      if (cnt2 > 0) {
        var cost = calculateMinHandsImp(cnt1, cnt2 - 1, cnt3 + 1, cnt4plus, wildCards - 1, wildConfig);
        if (cost < minHandsPossible) {
          wildConfig[2] = wildConfig[2] + 1; // use a wild card to make a three of a kind
          minHandsPossible = cost;
        }
      }
      if (cnt3 > 0) {
        var cost = calculateMinHandsImp(cnt1, cnt2, cnt3 - 1, cnt4plus + 1, wildCards - 1, wildConfig);
        if (cost < minHandsPossible) {
          wildConfig[3] = wildConfig[3] + 1; // use a wild card to make a bomb
          minHandsPossible = cost;
        }
      }
      if (cnt4plus > 0) {
        var cost = calculateMinHandsImp(cnt1, cnt2, cnt3, cnt4plus, wildCards - 1, wildConfig);
        if (cost < minHandsPossible) {
          wildConfig[4] = wildConfig[4] + 1; // use a wild card to make a bigger bomb
          minHandsPossible = cost;
        }
      }
      var cost = calculateMinHandsImp(cnt1+1, cnt2, cnt3, cnt4plus, wildCards - 1, wildConfig);
      if (cost < minHandsPossible) {
        wildConfig[0] = wildConfig[0] + 1; // use a wild card as a single
        minHandsPossible = cost;
      }
      return minHandsPossible;
    }
  }

  int calculateMinHands(PokerCardList cards, int wildCards, List<Hand> solution) {
    List<int> cnt = List.filled(5, 0);
    Map<CardRank, PokerCardList> group = groupCards(cards);
    group.forEach((rank, v) {
      if (rank == CardRank.redJoker || rank == CardRank.blackJoker) return;
      if (v.length <= 3) {
        cnt[v.length]++;
      } else {
        cnt[4]++;
      }
    });
    List<int> wildConfig = List.filled(5, 0);
    var cost = calculateMinHandsImp(cnt[1], cnt[2], cnt[3], cnt[4], wildCards, wildConfig);
    
    // group regular cards
    var singles = group.entries.where((e) => e.value.length == 1).map((e) => e.value).toList();
    for (var single in singles) {
      solution.add(Hand(single.cards, HandType.single, power: single[0].powerRank));
    }
    var pairs = group.entries.where((e) => e.value.length == 2).map((e) => e.value).toList();
    for (var pair in pairs) {
      solution.add(Hand(pair.cards, HandType.pair, power: pair[0].powerRank));
    }

    var triples = group.entries.where((e) => e.value.length == 3).map((e) => e.value).toList();
    for (var triple in triples) {
      solution.add(Hand(triple.cards, HandType.triple, power: triple[0].powerRank));
    }

    var bombs = group.entries.where((e) => e.value.length >= 4).map((e) => e.value).toList();
    for (var bomb in bombs) {
      var b = checkBomb(bomb, numberOfDecks: _numberOfDecks);
      solution.add(Hand(bomb.cards, HandType.bomb, power: b.power));
    }

    // now consider wild cards
    var wildCard = PokerCard.wildCard(levelRank);
    if (wildConfig[0] > 0) {
      solution.add(Hand([wildCard], HandType.single, power: wildCard.powerRank));
    }

    if (wildConfig[1] > 0) {
      for( var i = 0; i < wildConfig[1]; i++) {
        Hand maxSingleHand = solution.where((hand) => hand.type == HandType.single && !hand.cards[0].isJoker).reduce((a, b) => a.power > b.power ? a : b);
        maxSingleHand.add(wildCard);
        maxSingleHand.type = HandType.pair;
      }
    }

    if (wildConfig[2] > 0) {
      for( var i = 0; i < wildConfig[2]; i++) {
        Hand maxPair = solution.where((hand) => hand.type == HandType.pair && !hand.cards[0].isJoker).reduce((a, b) => a.power > b.power ? a : b);
        maxPair.add(wildCard);
        maxPair.type = HandType.triple;
      }
    }

    if (wildConfig[3] > 0) {
      for( var i = 0; i < wildConfig[3]; i++) {
        Hand maxTriple = solution.where((hand) => hand.type == HandType.triple && !hand.cards[0].isJoker).reduce((a, b) => a.power > b.power ? a : b);
        maxTriple.add(wildCard);
        var b = checkBomb(maxTriple, numberOfDecks: _numberOfDecks);
        maxTriple.type = HandType.bomb;
        maxTriple.power = b.power;
      }
    }

    if (wildConfig[4] > 0) {
      for( var i = 0; i < wildConfig[4]; i++) {
        Hand minBomb = solution.where((hand) => hand.type == HandType.bomb && !hand.cards[0].isJoker).reduce((a, b) => a.power < b.power ? a : b);
        minBomb.add(wildCard);
        var b = checkBomb(minBomb, numberOfDecks: _numberOfDecks);
        minBomb.power = b.power;
      }
    }

    return cost;

  }

  
}

class OverallValueCostEstimator implements CostEstimator {
  @override
  final CardRank levelRank;

  final int _deckCount;

  @override
  int get deckCount => _deckCount;

  OverallValueCostEstimator(this.levelRank, int deckCount): _deckCount = deckCount;

  int _getOrder(int power){

    if (power >= 15) { return power - 3; }
    var ordinalRank = power == 1 ? 14 : power;
    if (ordinalRank > levelRank.value) {
      return ordinalRank - 3;
    } else {
      return ordinalRank - 2;
    }
  }

  double linear(double l, double r, double valueL, double valueR, double x){
    assert(l < r);
    return (x - l) * (valueR - valueL) / (r - l) + valueL;
  }

  PokerCard _cardOfRegularBomb(Hand hand){ // bombs that are not joker bombs or straight flush bombs
    assert (hand.type == HandType.bomb);
    var regular = extractRegularCards(hand);
    return regular[0];
  }


  @override
  double estimateHand(Hand hand) {
    hand = deduceHandType(hand, deckCount: deckCount);
    var actualRank = (hand.power == 14 ? 1 : hand.power).toDouble();
    var order = _getOrder(hand.power).toDouble();

    if (hand.type == HandType.single) {
      if (order >= 14) {
        return -1;
      } else if (order == 13) {
        return -0.2;
      } else if (order == 12) {
        return -0.1;
      } else {
        return linear(1, 11, 1.3, 0.0, order);
      }
    } else if (hand.type == HandType.pair) {
      if (order >= 14) {
        return -1;
      } else if (order == 13) {
        return -0.9;
      } else if (order == 12) {
        return -0.8;
      } else if (order == 11) {
        return -0.5;
      } else {
        return linear(1, 10, 1.0, -0.1, order);
      }
    } else if (hand.type == HandType.triple || hand.type == HandType.fullHouse) {
      if (order >= 12) {
        return -0.9;
      } else if (order == 11) {
        return -0.8;
      } else if (order == 10) {
        return -0.6;
      } else {
        return linear(1, 9, 1.0, -0.3, order);
      }
    } else if (hand.type == HandType.straight) {
      return 0.6 * linear(0, 9, 1.0, -1.0, actualRank);
    } else if (hand.type == HandType.tube) {
      return 0.4 * linear(1, 12, 1.0, -1.0, actualRank);
    } else if (hand.type == HandType.plate) {
      return 0.3 * linear(1, 13, 1.0, -1.0, actualRank);
    } if (hand.type == HandType.bomb) {
      if (isJokerBomb(hand)) {
        return -2.0;
      }

      if (hand.cards.length >= 6) {
        return -1.9;
      } else if (hand.cards.length == 5) {
        if (isStraightFlush(hand))
        {
          var b = checkStraight(hand);
          return linear(5, 14, -1.3, -1.5, b.power.toDouble());
        }
        else{
          var c = _cardOfRegularBomb(hand);
          return linear(0, 12, -1.5, -1.7, _getOrder(c.powerRank).toDouble());
        }
      } else { // bomb of 4
        var c = _cardOfRegularBomb(hand);
        return linear(0, 12, -1.0, -1.3, _getOrder(c.powerRank).toDouble());
      }
    } 
    throw ArgumentError("Unknown hand type");
  }

  @override
  double estimateCards(PokerCardList cards, int wildCardCount, List<Hand> solution) {
    var nonJokerCards = cards.where((c) => !c.isJoker);
    var groupedCards = groupCards(nonJokerCards);
    var cost = estimateCardsImp(groupedCards, wildCardCount, solution);
    for(var joker in cards.where((c) => c.isJoker)){
      var hand = Hand([joker], HandType.single, power: joker.powerRank);
      cost += estimateHand(hand);
      solution.add(hand);
    }
    return cost;
  }

  double estimateCardsImp2(Map<CardRank, PokerCardList> groupedCards, int wildCards, Map<CardRank, int> wildCardConfig) {
    if (wildCards == 0) {
      int pairsInFullHouse = 0;
      double valueSum = 0.0;
      groupedCards.forEach((rank, v) {
        if (v.length == 3) {
          pairsInFullHouse += 1;
          var hand = Hand(List.from(v), HandType.triple, power: v[0].powerRank);
          valueSum += estimateHand(hand);
        }
      });
      groupedCards.forEach((rank, v) {
        double value = 0;
        if (v.length == 1) {
          var hand = Hand(List.from(v), HandType.single, power: v[0].powerRank);
          valueSum += estimateHand(hand);
        } 
        else if (v.length == 2) {
          var hand = Hand(List.from(v), HandType.pair, power: v[0].powerRank);
          value = estimateHand(hand);
          if (value > 0 && pairsInFullHouse > 0) {
            pairsInFullHouse -= 1;
          } else {
            valueSum += value;
          }
        } else if (v.length != 3 && v.isNotEmpty) {
          var b = checkBomb(v, numberOfDecks: deckCount);
          var hand = Hand(v.cards, HandType.bomb, power: b.power);
          valueSum += estimateHand(hand);
        }
      });
      
      return valueSum;
    } 
    else { // when there are wild cards
      double minValueSum = double.infinity;
      for (var rank in CardRank.values){
        if (rank.isJoker) continue;
        if (!groupedCards.containsKey(rank)){
          groupedCards[rank] = PokerCardList.empty();
        }
        var g = groupedCards[rank]!;
        g.add(PokerCard.wildCard(levelRank));
        if(wildCardConfig.containsKey(rank)){
          wildCardConfig[rank] = wildCardConfig[rank]! + 1;
        }
        else{
          wildCardConfig[rank] = 1;
        }
        var s = estimateCardsImp2(groupedCards, wildCards - 1, wildCardConfig);
        if (s < minValueSum) {
          minValueSum = s;
        }
        // reset
        g.removeLast();
        wildCardConfig[rank] = wildCardConfig[rank]! - 1;
      }
      return minValueSum;
    }
  }

  double estimateCardsImp(Map<CardRank, PokerCardList> groupedCards, int wildCards, List<Hand> solution) {
    if (wildCards == 0) {
      int pairsInFullHouse = 0;
      double valueSum = 0.0;
      groupedCards.forEach((rank, v) {
        if (v.length == 3) {
          pairsInFullHouse += 1;
          var hand = Hand(List.from(v), HandType.triple, power: v[0].powerRank);
          valueSum += estimateHand(hand);
          solution.add(hand);
        }
      });
      groupedCards.forEach((rank, v) {
        double value = 0;
        if (v.length == 1) {
          var hand = Hand(List.from(v), HandType.single, power: v[0].powerRank);
          valueSum += estimateHand(hand);
          solution.add(hand);
        } 
        else if (v.length == 2) {
          var hand = Hand(List.from(v), HandType.pair, power: v[0].powerRank);
          value = estimateHand(hand);
          solution.add(hand);
          if (value > 0 && pairsInFullHouse > 0) {
            pairsInFullHouse -= 1;
          } else {
            valueSum += value;
          }
        } else if (v.length != 3 && v.isNotEmpty) {
          var b = checkBomb(v, numberOfDecks: deckCount);
          var hand = Hand(v.cards, HandType.bomb, power: b.power);
          valueSum += estimateHand(hand);
          solution.add(hand);
        }
      });
      return valueSum;
    } 
    else { // when there are wild cards
      double minValueSum = double.infinity;
      for (var rank in CardRank.values){
        if (rank.isJoker) continue;
        if (!groupedCards.containsKey(rank)){
          groupedCards[rank] = PokerCardList.empty();
        }
        var g = groupedCards[rank]!;
        g.add(PokerCard.wildCard(levelRank));
        List<Hand> tmpSolution = [];
        var s = estimateCardsImp(groupedCards, wildCards - 1, tmpSolution);
        if (s < minValueSum) {
          minValueSum = s;
          solution.clear();
          solution.addAll(tmpSolution);
        }
        g.removeLast();
      }
      return minValueSum;
    }
  }

}

class StategicCombinationResult {
  final List<Hand> bestSolution;
  final double cost;

  StategicCombinationResult(this.bestSolution, this.cost);
}

StategicCombinationResult combine(PokerCardList cards, CostEstimator costEstimator) {
    final solutions = <List<Hand>>[];
    int wildCards  = cards.where((card) => card.isWildCard).length;
    var regularCards = cards.where((card) => !card.isWildCard);
    final cost = searchHandsAndEstimateCost(regularCards, solutions, wildCards, costEstimator);
    return StategicCombinationResult(solutions.first, cost);
  }

double estimateCost(PokerCardList cards, CostEstimator costEstimator) {
    int wildCards  = cards.where((card) => card.isWildCard).length;
    var regularCards = cards.where((card) => !card.isWildCard);
    return searchHandsAndEstimateCost(regularCards, [], wildCards, costEstimator);
}