"""Transport-independent bot session dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from guandan_core import Card, Hand, PokerCardList
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
        payload_type = payload.get("type")
        available_raw = payload.get("available_cards")
        if payload_type in {"sPlayHandRequest", "sTributeCardRequest", "sReturnCardRequest"}:
            if not available_raw:
                return None  # request was broadcast, but targets another player
            cards = PokerCardList.parse(available_raw, payload.get("level_rank", "2"))
            session.bot.cards_on_hand = PokerCardList.from_list(cards.cards)
            if payload_type == "sPlayHandRequest":
                response = self._play(session, payload, cards)
            elif payload_type == "sTributeCardRequest":
                response = self._tribute(session, payload, cards)
            else:
                response = self._return_card(session, payload, cards)
            return GameMessageEnvelope(envelope.session_id, response, envelope.request_id)
        session.bot._receive(payload)
        return None

    def _play(self, session: _Session, payload: dict[str, Any], cards: PokerCardList) -> dict[str, Any]:
        table = Hand.parse(payload.get("hand_on_table", ""))
        request = PlayRequest(
            cards=cards,
            hand_on_table=table,
            level_rank=payload.get("level_rank", "2"),
            room_id=payload.get("room_id", ""),
            game_id=payload.get("game_id", ""),
            round_id=payload.get("round_id", ""),
            turn_id=payload.get("turn_id", ""),
            seat_of_hand_on_table=payload.get("seat_of_hand_on_table"),
            game_state_snapshot=payload.get("game_state_snapshot"),
        )
        hand = session.bot.play_hand(request)
        if not isinstance(hand, Hand):
            raise InvalidBotDecision("play_hand() must return a Hand")
        card_string = " ".join(map(str, hand.cards))
        valid, reason = validate_play(card_string, cards, table, request.level_rank)
        if not valid:
            raise InvalidBotDecision(reason)
        return self._response(payload, session, "pPlayHandRequest", cards=card_string, turn_id=request.turn_id)

    def _tribute(self, session: _Session, payload: dict[str, Any], cards: PokerCardList) -> dict[str, Any]:
        request = TributeRequest(cards, payload.get("room_id", ""), payload.get("game_id", ""), payload.get("round_id", ""))
        card = session.bot.tribute_card(request)
        self._validate_card(card, cards, validate_tribute_card)
        return self._response(payload, session, "pPayTributeRequest", tribute_card=str(card))

    def _return_card(self, session: _Session, payload: dict[str, Any], cards: PokerCardList) -> dict[str, Any]:
        request = ReturnCardRequest(cards, payload.get("room_id", ""), payload.get("game_id", ""), payload.get("round_id", ""))
        card = session.bot.return_card(request)
        self._validate_card(card, cards, validate_return_card)
        return self._response(payload, session, "pReturnCardRequest", return_card=str(card))

    @staticmethod
    def _validate_card(card: Card, cards: PokerCardList, validator: Callable[..., tuple[bool, str]]) -> None:
        if not isinstance(card, Card):
            raise InvalidBotDecision("card decision must return a Card")
        valid, reason = validator(str(card), cards)
        if not valid:
            raise InvalidBotDecision(reason)

    def _response(self, payload: dict[str, Any], session: _Session, message_type: str, **fields: Any) -> dict[str, Any]:
        return {
            "type": message_type,
            "room_id": payload.get("room_id", ""),
            "game_id": payload.get("game_id", ""),
            "player_id": session.context.player_id,
            "round_id": payload.get("round_id", ""),
            "bot_code": self.bot_code,
            **fields,
        }

