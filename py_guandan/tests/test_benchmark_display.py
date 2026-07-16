from guandan_benchmark import display
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


def _blue_double_down() -> dict:
    return {
        "banker": _player(4),
        "follower": _player(2),
        "third": None,
        "fourth": None,
        "dwellers": [_player(1), _player(3)],
    }


def test_round_end_displays_both_double_down_dwellers(monkeypatch) -> None:
    messages = []
    monkeypatch.setattr(
        display,
        "log",
        lambda level, message: messages.append((level, message)),
    )

    display._print_round_end(
        {"round_id": "R1", "round_result": _blue_double_down()},
        _seat_map(),
    )

    assert len(messages) == 1
    level, message = messages[0]
    assert level == "INFO"
    assert "first=S4(blue)" in message
    assert "second=S2(blue)" in message
    assert "dwellers=S1(red),S3(red)" in message
    assert "third=" not in message
    assert "fourth=" not in message


def test_tracker_summary_displays_both_double_down_dwellers() -> None:
    tracker = GameTracker(total_rounds=1)
    tracker.record_round_result(_blue_double_down(), _seat_map())

    summary = display._format_round_detail_rankings(tracker.round_details[0])

    assert "first: 4 (blue)" in summary
    assert "second: 2 (blue)" in summary
    assert "dwellers: 1 (red), 3 (red)" in summary
