import 'package:guandan_core/guandan_core.dart';


abstract class CostEstimator {

  /// Estimate the cost of a list of cards, with a given number of wild cards. The solution with the lowest cost is stored in [solution]
  double estimateCards(PokerCardList cards, int wildCards, List<Hand> solution);

  /// Estimate the cost of a hand
  double estimateHand(Hand hand);

  /// The leve rank
  CardRank get levelRank;

  /// The number of standard decks
  int get deckCount;
}


/// A class representing the result in [searchHandsAndEstimateCost] and [tryExtractOneHand].
class SearchResult {
  /// The minimum cost found so far.
  final double minCost;

  /// The position of the type being searched
  final int typePosition;

  /// The current starting number/rank being searched
  final int currentStartRankValue;

  SearchResult(this.minCost, this.typePosition, this.currentStartRankValue);
}


/// Tries to extract a hand of a given series length with a specified number of cards for each rank.
/// 
/// This function is adapted from the c++ file of https://github.com/Bobgy/poker-guandan-strategy
/// 
/// - Parameters:
///   - [suit]: The suit of the cards.
///   - [seriesLength]: The length of the series.
///   - [cardCount]: The number of cards for each rank.
///   - [typePosition]: The position of the type being searched.
///   - [currentTypePosition]: The current position of the type being searched.
///   - [currentStartRankValue]: The current starting rank value of the series.
///   - [cards]: The list of cards.
///   - [wildCardsLeft]: The number of wild cards available.
///   - [costEstimator]: The cost estimator.
///   - [solutions]: The solutions found so far.
///   - [minCost]: The minimum cost found so far.
///   - [levelRank]: The current level rank.
/// - Returns: A tuple containing the minimum cost found, the position of the type in the hand, and the current starting number/rank of the series.
SearchResult tryExtractOneHand(
  CardSuit? suit,
  int seriesLength,
  int cardCount,
  int typePosition,
  int currentTypePosition,
  int currentStartRankValue,
  PokerCardList cards,
  int wildCardsLeft,
  CostEstimator costEstimator,
  List<List<Hand>> solutions,
  double minCost) {

    var levelRank = costEstimator.levelRank;
  
    typePosition += 1;
    if (currentTypePosition > typePosition) {
      return SearchResult(minCost, typePosition, currentStartRankValue);
    } 
    else if (currentTypePosition < typePosition) {
      currentStartRankValue = 1;
    }

    for (int startRankValue = currentStartRankValue; startRankValue <= 15 - seriesLength; startRankValue++) {
    SeriesResult result = findSeries(cards, startRankValue, seriesLength, wildCardsLeft, cardCount, suit: suit);
    if (result.isValid) {
      List<List<Hand>> tmpSolutions = [];
      var hand = result.toHand(levelRank);

      var cardsLeft = cards - result.series;
      double remainingCost = searchHandsAndEstimateCost(cardsLeft, tmpSolutions, wildCardsLeft - result.wildCardsUsed, costEstimator, 
                                  currentTypePosition: typePosition, currentStartRankValue: startRankValue) + costEstimator.estimateHand(hand);
      if (remainingCost <= minCost) {
        if (remainingCost < minCost) {
          solutions.clear();
        }
        minCost = remainingCost;
        for (int i = 0; i < tmpSolutions.length; i++) {
          tmpSolutions[i].add(hand);
        }
        solutions.addAll(tmpSolutions);
      }
    }
  }

  return SearchResult(minCost, typePosition, currentStartRankValue);
}

/// Estimate the cost of the remaining cards and tries to extract hands from them.
/// 
/// This function is adapted from the c++ file of https://github.com/Bobgy/poker-guandan-strategy
/// 
/// - Parameters:
///   - [nonWildCards]: The list of nonwild cards.
///   - [solutions]: The solutions found so far.
///   - [wildCards]: The number of wild cards available.
///   - [costEstimator]: The cost estimator.
///   - [currentTypePosition]: The current position of the type being searched.
///   - [currentStartRankValue]: The current starting number of the series being searched.
/// - Returns: The minimum cost found.
double searchHandsAndEstimateCost(PokerCardList nonWildCards, List<List<Hand>> solutions,  int wildCards, CostEstimator costEstimator, {int currentTypePosition = 0,  int currentStartRankValue = 1}) {
 
  if (nonWildCards.any((card) => card.isWildCard)) {
    nonWildCards = nonWildCards.where((card) => !card.isWildCard);
  }
  
  int typePosition = 0;
  List<Hand> basicSolution = [];
  double minCost = costEstimator.estimateCards(nonWildCards, wildCards, basicSolution);
  if (nonWildCards.isEmpty) { 
    var wc = PokerCard.wildCard(costEstimator.levelRank);
    if (wildCards > 0) {
      var hand = Hand(List.filled(wildCards, wc), HandType.unknown);
      hand = deduceHandType(hand, deckCount: costEstimator.deckCount);
      solutions.add(<Hand>[hand]); 
    }
    else{
      solutions.add(<Hand>[]);
    }
    
  }
  else { 
    solutions.add(basicSolution); 
  }

  List<CardSuit?> suits = [CardSuit.spades, CardSuit.hearts, CardSuit.diamonds, CardSuit.clubs, null];

  // Try straight and straight flush
  for (int tt = 0; tt < 5; tt++) {
    var result = tryExtractOneHand(suits[tt], 5, 1, typePosition, currentTypePosition, currentStartRankValue, nonWildCards, wildCards, costEstimator, solutions, minCost);
    minCost = result.minCost;
    typePosition = result.typePosition;
    currentStartRankValue = result.currentStartRankValue;
  }

  // Try tube and plate
  var result = tryExtractOneHand(null, 3, 2, typePosition, currentTypePosition, currentStartRankValue, nonWildCards, wildCards, costEstimator, solutions, minCost);
  minCost = result.minCost;
  typePosition = result.typePosition;
  currentStartRankValue = result.currentStartRankValue;

  result = tryExtractOneHand(null, 2, 3, typePosition, currentTypePosition, currentStartRankValue, nonWildCards, wildCards, costEstimator, solutions, minCost);
  minCost = result.minCost;
  typePosition = result.typePosition;
  currentStartRankValue = result.currentStartRankValue;

  //TODO: Try other types??

  return minCost;
}



