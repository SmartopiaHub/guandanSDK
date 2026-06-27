"""Developer-facing bot API and a small reference bot."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from guandan_core import Card, GameMessage, Hand, HandType, MessageType, PokerCardList
from guandan_core.utility import (
    can_play,
    find_full_houses,
    find_pairs,
    find_plates,
    find_singles,
    find_straights,
    find_triples,
    find_tubes,
)


@dataclass(frozen=True)
class BotContext:
    session_id: str
    player_id: str
    seat: int
    team: str
    deck_count: int = 2
    rule_set: str = "guandan-standard-v1"


@dataclass(frozen=True)
class PlayRequest:
    cards: PokerCardList
    hand_on_table: Hand
    level_rank: str
    room_id: str
    game_id: str
    round_id: str
    turn_id: str
    seat_of_hand_on_table: int | None = None
    game_state_snapshot: dict[str, Any] | None = None


@dataclass(frozen=True)
class TributeRequest:
    cards: PokerCardList
    room_id: str
    game_id: str
    round_id: str


@dataclass(frozen=True)
class ReturnCardRequest(TributeRequest):
    pass


class Bot(ABC):
    """Base class for bots.

    Implement the three abstract decision methods. The SDK supplies a fresh
    request containing the available cards and maintains ``cards_on_hand``.
    ``on_message`` is optional and receives informational game messages.
    """

    context: BotContext
    cards_on_hand: PokerCardList

    @abstractmethod
    def play_hand(self, request: PlayRequest) -> Hand:
        """Choose a legal hand, or ``Hand.empty_hand()`` to pass."""

    @abstractmethod
    def tribute_card(self, request: TributeRequest) -> Card:
        """Choose a card to pay as tribute."""

    @abstractmethod
    def return_card(self, request: ReturnCardRequest) -> Card:
        """Choose a card to return after receiving tribute."""

    def on_message(self, message: GameMessage) -> None:
        """Observe a non-decision game message. Override when useful."""

    def _bind(self, context: BotContext) -> None:
        self.context = context
        self.cards_on_hand = PokerCardList.empty()

    def _receive(self, payload: dict[str, Any]) -> None:
        message_type = payload.get("type")
        if message_type == MessageType.I_NEW_ROUND.value:
            self.cards_on_hand = PokerCardList.parse(payload.get("hand", ""), payload.get("level_rank", "2"))
        elif message_type == MessageType.I_HAND_PLAYED.value and payload.get("player_id") == self.context.player_id:
            hand = Hand.parse(payload.get("cards", ""))
            self.cards_on_hand.remove_cards(hand.cards)
        elif message_type == MessageType.I_TRIBUTE_RESULT.value:
            for tribute in payload.get("tribute_result", {}).get("tributes", []):
                tribute_card = tribute.get("tribute_card")
                return_card = tribute.get("return_card")
                if tribute.get("receiver_id") == self.context.player_id:
                    if tribute_card:
                        self.cards_on_hand.add(Card.parse(tribute_card))
                    if return_card:
                        self.cards_on_hand.remove_card(Card.parse(return_card))
                if tribute.get("payer_id") == self.context.player_id:
                    if tribute_card:
                        self.cards_on_hand.remove_card(Card.parse(tribute_card))
                    if return_card:
                        self.cards_on_hand.add(Card.parse(return_card))
        self.on_message(GameMessage.from_json(payload))


class BasicBot(Bot):
    """Reference bot: plays the first inexpensive legal non-bomb hand."""

    def __init__(self, *, randomize_leads: bool = True) -> None:
        self.randomize_leads = randomize_leads

    def tribute_card(self, request: TributeRequest) -> Card:
        candidates = sorted((card for card in request.cards if not card.is_wild), key=lambda card: card.power_rank)
        if not candidates:
            raise ValueError("no non-wild card is available to tribute")
        return candidates[-1]

    def return_card(self, request: ReturnCardRequest) -> Card:
        return min(request.cards, key=lambda card: card.power_rank)

    def play_hand(self, request: PlayRequest) -> Hand:
        finders = [find_plates, find_tubes, find_full_houses, find_straights, find_triples, find_pairs, find_singles]
        if request.hand_on_table.is_empty:
            if self.randomize_leads:
                random.shuffle(finders)
            for finder in finders:
                hands = finder(request.cards, request.level_rank)
                if hands and can_play(hands[0], request.hand_on_table, number_of_decks=self.context.deck_count):
                    return hands[0]
            raise ValueError("no legal leading hand")

        finder_by_type = {
            HandType.PLATE: find_plates,
            HandType.TUBE: find_tubes,
            HandType.FULL_HOUSE: find_full_houses,
            HandType.STRAIGHT: find_straights,
            HandType.TRIPLE: find_triples,
            HandType.PAIR: find_pairs,
            HandType.SINGLE: find_singles,
        }
        finder = finder_by_type.get(request.hand_on_table.type)
        if finder:
            for hand in finder(request.cards, request.level_rank, find_all=True):
                if can_play(hand, request.hand_on_table, number_of_decks=self.context.deck_count):
                    return hand
        return Hand.empty_hand()

