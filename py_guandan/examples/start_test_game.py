"""Start a one-round game containing a deployed Python bot."""

import os

from guandan_bot import Participant, TestGame, TestGameConfig


config = TestGameConfig(
    lobby_url=os.environ.get("LOBBY_URL", "https://www.zhiquguandan.com"),
    api_key=os.environ["AUTO_TEST_API_KEY"],
    participants=(
        Participant.deployed(1, os.environ["BOT_DEPLOYMENT_ID"]),
        Participant.builtin(2),
        Participant.builtin(3),
        Participant.builtin(4),
    ),
    num_rounds=1,
)

game = TestGame.start(config)
print(game.test_game_id, game.status, game.runtime.get("events_url"))

