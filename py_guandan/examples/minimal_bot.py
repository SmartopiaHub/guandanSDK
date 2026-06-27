"""The smallest useful custom bot, runnable as a WebSocket deployment."""

import os

from guandan_bot import Bot, BotApplication, PlayRequest, ReturnCardRequest, TributeRequest, run_websocket_bot
from guandan_core import Card, Hand
from guandan_core.utility import find_singles


class MyBot(Bot):
    def play_hand(self, request: PlayRequest) -> Hand:
        if not request.hand_on_table.is_empty:
            candidates = find_singles(request.cards, request.level_rank, target_power=request.hand_on_table.power)
            return candidates[0] if candidates else Hand.empty_hand()
        return find_singles(request.cards, request.level_rank)[0]

    def tribute_card(self, request: TributeRequest) -> Card:
        return max((card for card in request.cards if not card.is_wild), key=lambda card: card.power_rank)

    def return_card(self, request: ReturnCardRequest) -> Card:
        return min(request.cards, key=lambda card: card.power_rank)


if __name__ == "__main__":
    run_websocket_bot(
        BotApplication(MyBot),
        game_server_url=os.environ["GAME_SERVER_URL"],
        deployment_key=os.environ["WEBSOCKET_BOT_DEPLOYMENT_KEY"],
    )

