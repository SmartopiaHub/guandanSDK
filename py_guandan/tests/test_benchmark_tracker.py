import pytest

from guandan_benchmark.tracker import GameTracker


def _player(seat: int) -> dict:
    team = "redTeam" if seat in (1, 3) else "blueTeam"
    return {
        "player_id": f"player-{seat}",
        "seat": seat,
        "team": team,
    }


def _seat_map() -> dict[str, int]:
    return {f"player-{seat}": seat for seat in range(1, 5)}


@pytest.mark.parametrize(
    ("first_seats", "dweller_seats", "red_pts", "blue_pts", "winner"),
    [
        ((4, 2), (1, 3), -3, 3, "blue"),
        ((1, 3), (2, 4), 3, -3, "red"),
    ],
)
def test_double_down_scores_both_teams_and_preserves_both_dwellers(
    first_seats: tuple[int, int],
    dweller_seats: tuple[int, int],
    red_pts: int,
    blue_pts: int,
    winner: str,
) -> None:
    tracker = GameTracker(total_rounds=1)
    round_result = {
        "banker": _player(first_seats[0]),
        "follower": _player(first_seats[1]),
        "third": None,
        "fourth": None,
        "dwellers": [_player(seat) for seat in dweller_seats],
    }

    tracker.record_round_result(round_result, _seat_map())

    assert tracker.rounds_completed == 1
    assert tracker.red_score == red_pts
    assert tracker.blue_score == blue_pts
    assert tracker.red_wins == (1 if winner == "red" else 0)
    assert tracker.blue_wins == (1 if winner == "blue" else 0)

    detail = tracker.round_details[0]
    assert detail["red_pts"] == red_pts
    assert detail["blue_pts"] == blue_pts
    assert detail["winner"] == winner
    assert set(detail["rankings"]) == {"first", "second"}
    assert {info["seat"] for info in detail["dwellers"]} == set(dweller_seats)
    represented_seats = {
        info["seat"] for info in detail["rankings"].values()
    } | {
        info["seat"] for info in detail["dwellers"]
    }
    assert represented_seats == {1, 2, 3, 4}


def test_single_dweller_round_keeps_existing_scoring() -> None:
    tracker = GameTracker(total_rounds=1)
    round_result = {
        "banker": _player(1),
        "follower": _player(2),
        "third": _player(3),
        "fourth": None,
        "dwellers": [_player(4)],
    }

    tracker.record_round_result(round_result, _seat_map())

    detail = tracker.round_details[0]
    assert detail["red_pts"] == 2
    assert detail["blue_pts"] == -2
    assert detail["rankings"]["third"]["seat"] == 3
    assert detail["rankings"]["fourth"]["seat"] == 4
