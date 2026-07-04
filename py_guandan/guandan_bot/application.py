"""Transport-independent bot session dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from guandan_core import (
    Card,
    Hand,
    PlayerPayTributeRequest,
    PlayerPlayHandRequest,
    PlayerReturnCardRequest,
    PokerCardList,
    ServerPlayHandRequest,
    ServerReturnCardRequest,
    ServerTributeRequest,
)
from guandan_core.hand_validator import validate_play, validate_return_card, validate_tribute_card

from .bot import Bot, BotContext, PlayRequest, ReturnCardRequest, TributeRequest
from .protocol import BotError, BotMessage, GameMessageEnvelope, SessionEnd, SessionEnded, SessionStart, SessionStarted


class InvalidBotDecision(ValueError):
    """Raised when a bot returns a malformed or illegal decision."""


@dataclass
class _Session:
    bot: Bot
    context: BotContext


class BotApplication:
    """Own bot sessions and turn protocol requests into bot decisions."""

    def __init__(self, bot_factory: Callable[[], Bot], *, deck_count: int = 2, bot_code: str | None = None) -> None:
        self.bot_factory = bot_factory
        self.deck_count = deck_count
        self.bot_code = bot_code or getattr(bot_factory, "__name__", "PythonBot")
        self._sessions: dict[str, _Session] = {}

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def handle(self, message: BotMessage) -> BotMessage | None:
        if isinstance(message, SessionStart):
            return self._start(message)
        if isinstance(message, SessionEnd) and not isinstance(message, SessionEnded):
            self._sessions.pop(message.session_id, None)
            return SessionEnded(message.session_id)
        if isinstance(message, GameMessageEnvelope):
            return self._game_message(message)
        return BotError(message.session_id, "unsupported_message_type", f"unsupported message type: {message.type}")

    def _start(self, message: SessionStart) -> SessionStarted:
        seat = message.seat or 1
        context = BotContext(
            session_id=message.session_id,
            player_id=message.player_id or f"python-bot-{seat}",
            seat=seat,
            team="redTeam" if seat % 2 else "blueTeam",
            deck_count=message.deck_count or self.deck_count,
            rule_set=message.rule_set or "guandan-standard-v1",
        )
        bot = self.bot_factory()
        if not isinstance(bot, Bot):
            raise TypeError("bot_factory must return a Bot instance")
        bot._bind(context)
        self._sessions[message.session_id] = _Session(bot, context)
        return SessionStarted(message.session_id, True)

    def _game_message(self, envelope: GameMessageEnvelope) -> BotMessage | None:
        session = self._sessions.get(envelope.session_id)
        if session is None:
            return BotError(envelope.session_id, "unknown_session", "bot session has not been started")
        payload = envelope.payload
        if isinstance(payload, (ServerPlayHandRequest, ServerTributeRequest, ServerReturnCardRequest)):
            if payload.available_cards is None or payload.available_cards.is_empty:
                return None  # request was broadcast, but targets another player
            cards = PokerCardList.from_list(payload.available_cards.cards)
            session.bot.cards_on_hand = PokerCardList.from_list(cards.cards)
            if isinstance(payload, ServerPlayHandRequest):
                response = self._play(session, payload, cards)
            elif isinstance(payload, ServerTributeRequest):
                response = self._tribute(session, payload, cards)
            else:
                response = self._return_card(session, payload, cards)
            return GameMessageEnvelope(envelope.session_id, response, envelope.request_id)
        session.bot._receive(payload)
        return None

    def _play(
        self,
        session: _Session,
        payload: ServerPlayHandRequest,
        cards: PokerCardList,
    ) -> PlayerPlayHandRequest:
        table = payload.hand_on_table or Hand.empty_hand()
        request = PlayRequest(
            cards=cards,
            hand_on_table=table,
            level_rank=payload.level_rank,
            room_id=payload.room_id,
            game_id=payload.game_id,
            round_id=payload.round_id,
            turn_id=payload.turn_id,
            seat_of_hand_on_table=payload.seat_of_hand_on_table,
            game_state_snapshot=payload.game_state_snapshot,
        )
        hand = session.bot.play_hand(request)
        if not isinstance(hand, Hand):
            raise InvalidBotDecision("play_hand() must return a Hand")
        card_string = " ".join(map(str, hand.cards))
        valid, reason = validate_play(card_string, cards, table, request.level_rank)
        if not valid:
            raise InvalidBotDecision(reason)
        return PlayerPlayHandRequest(
            room_id=payload.room_id,
            game_id=payload.game_id,
            player_id=session.context.player_id,
            cards=PokerCardList.from_string(card_string, payload.level_rank),
            round_id=payload.round_id,
            turn_id=request.turn_id,
            bot_code=self.bot_code,
        )

    def _tribute(
        self,
        session: _Session,
        payload: ServerTributeRequest,
        cards: PokerCardList,
    ) -> PlayerPayTributeRequest:
        request = TributeRequest(cards, payload.room_id, payload.game_id, payload.round_id)
        card = session.bot.tribute_card(request)
        self._validate_card(card, cards, validate_tribute_card)
        return PlayerPayTributeRequest(
            room_id=payload.room_id,
            game_id=payload.game_id,
            player_id=session.context.player_id,
            tribute=card,
            round_id=payload.round_id,
            bot_code=self.bot_code,
        )

    def _return_card(
        self,
        session: _Session,
        payload: ServerReturnCardRequest,
        cards: PokerCardList,
    ) -> PlayerReturnCardRequest:
        request = ReturnCardRequest(cards, payload.room_id, payload.game_id, payload.round_id)
        card = session.bot.return_card(request)
        self._validate_card(card, cards, validate_return_card)
        return PlayerReturnCardRequest(
            room_id=payload.room_id,
            game_id=payload.game_id,
            player_id=session.context.player_id,
            return_card=card,
            round_id=payload.round_id,
            bot_code=self.bot_code,
        )

    @staticmethod
    def _validate_card(card: Card, cards: PokerCardList, validator: Callable[..., tuple[bool, str]]) -> None:
        if not isinstance(card, Card):
            raise InvalidBotDecision("card decision must return a Card")
        valid, reason = validator(str(card), cards)
        if not valid:
            raise InvalidBotDecision(reason)
