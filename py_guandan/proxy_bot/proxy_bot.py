"""HTTP proxy bot that lets an external agent make Guandan decisions."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from guandan_bot.protocol import (
    BotError,
    BotMessage,
    GameMessageEnvelope,
    SessionEnd,
    SessionEnded,
    SessionStart,
    SessionStarted,
)
from guandan_core import (
    Card,
    Hand,
    MessageType,
    PlayerPayTributeRequest,
    PlayerPlayHandRequest,
    PlayerReturnCardRequest,
    PokerCardList,
    ServerPlayHandRequest,
    ServerReturnCardRequest,
    ServerTributeRequest,
)
from guandan_core.hand_validator import (
    validate_play,
    validate_return_card,
    validate_tribute_card,
)


class ProxyError(ValueError):
    """An invalid public API request or action."""


@dataclass
class PendingRequest:
    envelope: GameMessageEnvelope
    response: GameMessageEnvelope | None = None
    error: str | None = None
    ready: threading.Event = field(default_factory=threading.Event)


@dataclass
class ProxySession:
    session_id: str
    player_id: str
    seat: int
    team: str
    rule_set: str
    deck_count: int
    deployment_id: str | None = None
    bot_definition_id: str | None = None
    room_id: str = ""
    game_id: str = ""
    round_id: str = ""
    level_rank: str = "2"
    initial_cards: str = ""
    cards_on_hand: str = ""
    players: list[dict[str, Any]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    game_state_snapshot: dict[str, Any] | None = None
    pending: PendingRequest | None = None
    ended: bool = False


class ProxyBotApplication:
    """Owns independent proxy state for every platform bot session."""

    def __init__(self, *, bot_code: str = "httpProxyBot", action_timeout: float = 600.0) -> None:
        self.bot_code = bot_code
        self.action_timeout = action_timeout
        self._sessions: dict[str, ProxySession] = {}
        self._lock = threading.RLock()

    @property
    def session_count(self) -> int:
        with self._lock:
            return sum(not session.ended for session in self._sessions.values())

    def handle(self, message: BotMessage) -> BotMessage | None:
        if isinstance(message, SessionStart):
            return self._start(message)
        if isinstance(message, SessionEnd) and not isinstance(message, SessionEnded):
            return self._end(message.session_id)
        if isinstance(message, GameMessageEnvelope):
            return self._game_message(message)
        return BotError(message.session_id, "unsupported_message_type", message.type)

    def _start(self, message: SessionStart) -> SessionStarted:
        seat = message.seat or 1
        with self._lock:
            self._sessions[message.session_id] = ProxySession(
                session_id=message.session_id,
                player_id=message.player_id or f"proxy-bot-{seat}",
                seat=seat,
                team="redTeam" if seat % 2 else "blueTeam",
                rule_set=message.rule_set or "guandan-standard-v1",
                deck_count=message.deck_count or 2,
                deployment_id=message.deployment_id,
                bot_definition_id=message.bot_definition_id,
            )
        print(f"[proxy] session started: {message.session_id} seat={seat}", flush=True)
        return SessionStarted(message.session_id, True)

    def _end(self, session_id: str) -> SessionEnded:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.ended = True
                if session.pending is not None:
                    session.pending.error = "session ended"
                    session.pending.ready.set()
        print(f"[proxy] session ended: {session_id}", flush=True)
        return SessionEnded(session_id)

    def _game_message(self, envelope: GameMessageEnvelope) -> BotMessage | None:
        with self._lock:
            session = self._sessions.get(envelope.session_id)
            if session is None or session.ended:
                return BotError(envelope.session_id, "unknown_session", "bot session has not been started")

            payload = envelope.payload
            raw = payload.to_json()
            self._update_state(session, raw)
            if not isinstance(payload, (ServerPlayHandRequest, ServerTributeRequest, ServerReturnCardRequest)):
                return None
            if payload.available_cards is None or payload.available_cards.is_empty:
                return None
            if session.pending is not None and not session.pending.ready.is_set():
                # A newer request supersedes the stale one — cancel the old
                # pending request so the agent only sees the most recent.
                session.pending.error = "superseded by newer request"
                session.pending.ready.set()
                print(
                    f"[proxy] superseded stale {_request_kind(session.pending.envelope.payload)}: "
                    f"session={envelope.session_id} "
                    f"old_request={session.pending.envelope.request_id}",
                    flush=True,
                )
            pending = PendingRequest(envelope)
            session.pending = pending

        kind = _request_kind(envelope.payload)
        print(
            f"[proxy] pending {kind}: session={envelope.session_id} "
            f"game={getattr(envelope.payload, 'game_id', '')} "
            f"request={envelope.request_id}",
            flush=True,
        )
        timeout = self._wait_timeout(envelope)
        if not pending.ready.wait(timeout):
            with self._lock:
                if session.pending is pending:
                    session.pending = None
            print(f"[proxy] action timed out: session={envelope.session_id}", flush=True)
            return BotError(envelope.session_id, "proxy_action_timeout", "no action was submitted in time")

        with self._lock:
            if session.pending is pending:
                session.pending = None
        if pending.response is not None:
            return pending.response
        return BotError(envelope.session_id, "proxy_action_failed", pending.error or "action failed")

    def _wait_timeout(self, envelope: GameMessageEnvelope) -> float:
        if envelope.deadline_millis:
            remaining = (envelope.deadline_millis / 1000) - time.time() - 0.15
            return max(0.05, min(self.action_timeout, remaining))
        return self.action_timeout

    def _update_state(self, session: ProxySession, raw: dict[str, Any]) -> None:
        message_type = raw.get("type", "")
        session.room_id = raw.get("room_id", session.room_id)
        session.game_id = raw.get("game_id", session.game_id)
        session.round_id = raw.get("round_id", session.round_id)
        session.events.append(raw)
        if len(session.events) > 500:
            del session.events[:-500]

        if message_type == MessageType.I_NEW_ROUND.value:
            session.round_id = raw.get("round_id", "")
            session.level_rank = raw.get("level_rank", "2")
            session.initial_cards = raw.get("hand", "")
            session.cards_on_hand = session.initial_cards
            session.players = raw.get("players", [])
            session.turns = []
            session.game_state_snapshot = None
        elif message_type == MessageType.I_HAND_PLAYED.value:
            session.turns.append(
                {
                    "turn_id": raw.get("turn_id"),
                    "phase_id": raw.get("phase_id"),
                    "player_id": raw.get("player_id"),
                    "seat": raw.get("seat"),
                    "cards": raw.get("cards", "empty-0 :"),
                    "bot_code": raw.get("bot_code"),
                }
            )
            if raw.get("player_id") == session.player_id and raw.get("cards"):
                self._remove_played_cards(session, raw["cards"])
        elif message_type == MessageType.I_CARDS_ON_HAND.value:
            self._update_player_card_counts(session, raw.get("cards_on_hand", {}))
        elif message_type == MessageType.I_TRIBUTE_RESULT.value:
            self._apply_tribute_result(session, raw)
        elif message_type == MessageType.S_PLAY_HAND_REQUEST.value:
            session.level_rank = raw.get("level_rank", session.level_rank)
            session.cards_on_hand = raw.get("available_cards", session.cards_on_hand)
            session.game_state_snapshot = raw.get("game_state_snapshot")
            if session.game_state_snapshot:
                session.players = session.game_state_snapshot.get("players", session.players)
        elif message_type in (
            MessageType.S_TRIBUTE_CARD_REQUEST.value,
            MessageType.S_RETURN_CARD_REQUEST.value,
        ):
            session.cards_on_hand = raw.get("available_cards", session.cards_on_hand)

    def _remove_played_cards(self, session: ProxySession, hand_string: str) -> None:
        try:
            cards = PokerCardList.from_string(session.cards_on_hand, session.level_rank)
            cards.remove_cards(Hand.parse(hand_string).cards)
            session.cards_on_hand = str(cards)
        except (ValueError, KeyError):
            pass

    def _update_player_card_counts(self, session: ProxySession, values: dict[str, Any]) -> None:
        for player in session.players:
            player_id = player.get("player_id")
            if player_id not in values:
                continue
            cards = values[player_id]
            player["cards_on_hand"] = cards
            player["cards_on_hand_count"] = len(cards.split()) if isinstance(cards, str) else None

    def _apply_tribute_result(self, session: ProxySession, raw: dict[str, Any]) -> None:
        try:
            cards = PokerCardList.from_string(session.cards_on_hand, session.level_rank)
            for tribute in raw.get("tribute_result", {}).get("tributes", []):
                tribute_card = tribute.get("tribute_card")
                return_card = tribute.get("return_card")
                if tribute.get("receiver_id") == session.player_id:
                    if tribute_card:
                        cards.add(Card.parse(tribute_card))
                    if return_card:
                        cards.remove_card(Card.parse(return_card))
                if tribute.get("payer_id") == session.player_id:
                    if tribute_card:
                        cards.remove_card(Card.parse(tribute_card))
                    if return_card:
                        cards.add(Card.parse(return_card))
            session.cards_on_hand = str(cards)
        except (ValueError, KeyError):
            pass

    def requests(self, *, session_id: str | None = None, game_id: str | None = None) -> Any:
        with self._lock:
            sessions = self._select(session_id=session_id, game_id=game_id, pending_only=False)
            values = [self._request_view(session) for session in sessions]
        if session_id or game_id:
            return values[0]
        return values

    def states(self, *, session_id: str | None = None, game_id: str | None = None) -> Any:
        with self._lock:
            sessions = self._select(session_id=session_id, game_id=game_id, pending_only=False)
            values = [self._state_view(session) for session in sessions]
        if session_id or game_id:
            return values[0]
        return values

    def submit_action(
        self,
        action: str,
        *,
        session_id: str | None = None,
        game_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            sessions = self._select(session_id=session_id, game_id=game_id, pending_only=True)
            if not sessions:
                raise ProxyError("no action request is pending")
            if len(sessions) != 1:
                raise ProxyError("multiple requests are pending; specify session_id or game_id")
            session = sessions[0]
            pending = session.pending
            assert pending is not None
            response = self._build_response(session, pending.envelope, action.strip())
            pending.response = response
            pending.ready.set()
            result = response.to_dict()
        print(
            f"[proxy] submitted {_request_kind(pending.envelope.payload)}: "
            f"session={session.session_id} action={action!r}",
            flush=True,
        )
        return result

    def _select(
        self,
        *,
        session_id: str | None,
        game_id: str | None,
        pending_only: bool,
    ) -> list[ProxySession]:
        sessions = [session for session in self._sessions.values() if not session.ended]
        if session_id:
            sessions = [session for session in sessions if session.session_id == session_id]
        if game_id:
            sessions = [session for session in sessions if session.game_id == game_id]
        if pending_only:
            sessions = [
                session
                for session in sessions
                if session.pending is not None and not session.pending.ready.is_set()
            ]
        if (session_id or game_id) and not sessions:
            raise ProxyError("no matching active session")
        if (session_id or game_id) and len(sessions) > 1:
            raise ProxyError("selector is ambiguous; use session_id")
        return sorted(sessions, key=lambda session: session.session_id)

    def _request_view(self, session: ProxySession) -> dict[str, Any]:
        value: dict[str, Any] = {
            "session_id": session.session_id,
            "game_id": session.game_id or None,
            "seat": session.seat,
            "pending": False,
        }
        pending = session.pending
        if pending is not None and not pending.ready.is_set():
            payload = pending.envelope.payload.to_json()
            value.update(
                {
                    "pending": True,
                    "request_id": pending.envelope.request_id,
                    "deadline_millis": pending.envelope.deadline_millis,
                    "request": _request_kind(pending.envelope.payload),
                    "payload": payload,
                }
            )
        return value

    def _state_view(self, session: ProxySession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "game_id": session.game_id or None,
            "room_id": session.room_id or None,
            "player": {
                "player_id": session.player_id,
                "seat": session.seat,
                "team": session.team,
            },
            "rule_set": session.rule_set,
            "deck_count": session.deck_count,
            "round": {
                "round_id": session.round_id or None,
                "level_rank": session.level_rank,
                "initial_cards": session.initial_cards,
                "cards_on_hand": session.cards_on_hand,
                "players": session.players,
                "turns": session.turns,
            },
            "pending_request": self._request_view(session),
            "game_state_snapshot": session.game_state_snapshot,
            "recent_events": session.events[-40:],
        }

    def _build_response(
        self,
        session: ProxySession,
        envelope: GameMessageEnvelope,
        action: str,
    ) -> GameMessageEnvelope:
        payload = envelope.payload
        cards = payload.available_cards
        assert cards is not None
        if isinstance(payload, ServerPlayHandRequest):
            normalized = "" if action.lower() in {"", "pass", "empty", "[]"} else action
            table = payload.hand_on_table or Hand.empty_hand()
            valid, reason = validate_play(normalized, cards, table, payload.level_rank)
            if not valid:
                raise ProxyError(reason)
            response = PlayerPlayHandRequest(
                room_id=payload.room_id,
                game_id=payload.game_id,
                player_id=session.player_id,
                cards=PokerCardList.from_string(normalized, payload.level_rank),
                round_id=payload.round_id,
                turn_id=payload.turn_id,
                bot_code=self.bot_code,
            )
        elif isinstance(payload, ServerTributeRequest):
            valid, reason = validate_tribute_card(action, cards)
            if not valid:
                raise ProxyError(reason)
            response = PlayerPayTributeRequest(
                room_id=payload.room_id,
                game_id=payload.game_id,
                player_id=session.player_id,
                tribute=Card.parse(action),
                round_id=payload.round_id,
                bot_code=self.bot_code,
            )
        elif isinstance(payload, ServerReturnCardRequest):
            valid, reason = validate_return_card(action, cards)
            if not valid:
                raise ProxyError(reason)
            response = PlayerReturnCardRequest(
                room_id=payload.room_id,
                game_id=payload.game_id,
                player_id=session.player_id,
                return_card=Card.parse(action),
                round_id=payload.round_id,
                bot_code=self.bot_code,
            )
        else:
            raise ProxyError("unsupported pending request")
        return GameMessageEnvelope(session.session_id, response, envelope.request_id)


def _request_kind(payload: Any) -> str:
    if isinstance(payload, ServerPlayHandRequest):
        return "play"
    if isinstance(payload, ServerTributeRequest):
        return "tribute"
    if isinstance(payload, ServerReturnCardRequest):
        return "return"
    return "unknown"
