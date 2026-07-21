from __future__ import annotations

from proxy_bot.inspect_state import _bomb_report, _straight_flush_report, inspect_state


def test_inspector_reports_unseen_pool_and_stale_exact_hands() -> None:
    state = {
        "session_id": "s1",
        "game_id": "g1",
        "deck_count": 2,
        "player": {"player_id": "p1", "seat": 1, "team": "redTeam"},
        "round": {
            "round_id": "R2",
            "level_rank": "3",
            "cards_on_hand": "2H 3H*",
            "players": [
                {"player_id": "p1", "seat": 1, "team": "redTeam", "played_cards": "4H"},
                {"player_id": "p2", "seat": 2, "team": "blueTeam", "played_cards": "5H"},
                {"player_id": "p3", "seat": 3, "team": "redTeam", "played_cards": ""},
                {"player_id": "p4", "seat": 4, "team": "blueTeam", "played_cards": ""},
            ],
            "turns": [],
        },
        "recent_events": [
            {"type": "iRoundResult", "round_id": "R1"},
            {
                "type": "iCardsOnHand",
                "cards_on_hand": {"p2": "", "p3": "AS", "p4": "RJ"},
            },
            {"type": "iNewRound", "round_id": "R2"},
        ],
    }

    report = inspect_state(state)

    assert report["other_seats"]["2"]["remaining_count"] == 26
    latest = report["other_seats"]["2"]["latest_exact_hand"]
    keys = ("known", "round_id", "current_round", "source", "count", "cards")
    assert {key: latest[key] for key in keys} == {
        "known": True,
        "round_id": "R1",
        "current_round": False,
        "source": "recent_events[1].iCardsOnHand",
        "count": 0,
        "cards": [],
    }
    assert report["unseen_card_pool"]["count"] == 104
    assert report["unseen_card_pool"]["expected_from_other_seat_counts"] == 80
    assert report["unseen_card_pool"]["counts_by_card"]["2H"] == 1
    assert report["unseen_card_pool"]["counts_by_card"]["3H"] == 1
    assert report["unseen_card_pool"]["counts_by_card"]["4H"] == 1
    assert report["unseen_card_pool"]["counts_by_card"]["5H"] == 1


def test_current_exact_hand_is_advanced_by_later_public_play() -> None:
    state = {
        "session_id": "s1",
        "game_id": "g1",
        "deck_count": 2,
        "player": {"player_id": "p1", "seat": 1, "team": "redTeam"},
        "round": {
            "round_id": "R1",
            "level_rank": "2",
            "cards_on_hand": "3H",
            "players": [
                {"player_id": "p1", "seat": 1, "team": "redTeam", "played_cards": ""},
                {
                    "player_id": "p2",
                    "seat": 2,
                    "team": "blueTeam",
                    "played_cards": "4H",
                },
                {"player_id": "p3", "seat": 3, "team": "redTeam", "played_cards": ""},
                {"player_id": "p4", "seat": 4, "team": "blueTeam", "played_cards": ""},
            ],
            "turns": [],
        },
        "recent_events": [
            {"type": "iNewRound", "round_id": "R1"},
            {"type": "iCardsOnHand", "cards_on_hand": {"p2": "4H 5H"}},
            {
                "type": "iHandPlayed",
                "round_id": "R1",
                "player_id": "p2",
                "seat": 2,
                "cards": "single-4 : 4H",
            },
        ],
    }

    report = inspect_state(state)

    latest = report["other_seats"]["2"]["latest_exact_hand"]
    keys = ("known", "round_id", "current_round", "source", "count", "cards")
    assert {key: latest[key] for key in keys} == {
        "known": True,
        "round_id": "R1",
        "current_round": True,
        "source": "recent_events[1].iCardsOnHand + later public events",
        "count": 1,
        "cards": ["5H"],
    }


def test_snapshot_uses_cumulative_played_delta_when_events_arrive_out_of_order() -> None:
    state = {
        "session_id": "s1",
        "game_id": "g1",
        "deck_count": 2,
        "player": {"player_id": "p1", "seat": 1, "team": "redTeam"},
        "round": {
            "round_id": "R1",
            "level_rank": "2",
            "cards_on_hand": "3H",
            "players": [
                {"player_id": "p1", "seat": 1, "team": "redTeam", "played_cards": ""},
                {
                    "player_id": "p2",
                    "seat": 2,
                    "team": "blueTeam",
                    "played_cards": "4H",
                },
                {"player_id": "p3", "seat": 3, "team": "redTeam", "played_cards": ""},
                {"player_id": "p4", "seat": 4, "team": "blueTeam", "played_cards": ""},
            ],
            "turns": [],
        },
        "recent_events": [
            {"type": "iNewRound", "round_id": "R1"},
            {
                "type": "iHandPlayed",
                "round_id": "R1",
                "player_id": "p2",
                "seat": 2,
                "cards": "single-4 : 4H",
            },
            {
                "type": "sPlayHandRequest",
                "round_id": "R1",
                "game_state_snapshot": {
                    "players": [
                        {
                            "player_id": "p2",
                            "seat": 2,
                            "played_cards": "",
                            "cards_on_hand": "4H 5H",
                        }
                    ]
                },
            },
        ],
    }

    latest = inspect_state(state)["other_seats"]["2"]["latest_exact_hand"]

    assert latest["cards"] == ["5H"]
    assert latest["source"].endswith(" + cumulative played-card delta")


def test_straight_flush_windows_distinguish_natural_and_heart_level_wild() -> None:
    windows = _straight_flush_report(
        [
            "5D",
            "6D",
            "7D*",
            "8D",
            "9D",
            "6C",
            "7C*",
            "8C",
            "TC",
            "7H*",
        ],
        "7",
    )

    natural = next(
        window
        for window in windows["natural"]
        if window["ranks"] == ["5", "6", "7", "8", "9"] and window["suit"] == "D"
    )
    assisted = next(
        window
        for window in windows["wildcard_assisted"]
        if window["ranks"] == ["6", "7", "8", "9", "T"] and window["suit"] == "C"
    )

    assert natural == {
        "ranks": ["5", "6", "7", "8", "9"],
        "suit": "D",
        "cards": ["5D", "6D", "7D*", "8D", "9D"],
        "wildcards_needed": 0,
    }
    assert assisted["ranks"] == ["6", "7", "8", "9", "T"]
    assert assisted["suit"] == "C"
    assert assisted["wildcards_needed"] == 1
    assert set(assisted["cards"]) == {"6C", "7C*", "8C", "7H*", "TC"}


def test_known_exact_hand_output_includes_straight_flush_windows() -> None:
    state = {
        "session_id": "s1",
        "game_id": "g1",
        "deck_count": 2,
        "player": {"player_id": "p1", "seat": 1, "team": "redTeam"},
        "round": {
            "round_id": "R1",
            "level_rank": "7",
            "cards_on_hand": "",
            "players": [
                {"player_id": "p1", "seat": 1, "team": "redTeam", "played_cards": ""},
                {
                    "player_id": "p2",
                    "seat": 2,
                    "team": "blueTeam",
                    "played_cards": "",
                    "cards_on_hand": "TH JH QH KH AH",
                },
            ],
            "turns": [],
        },
        "recent_events": [{"type": "iNewRound", "round_id": "R1", "level_rank": "7"}],
    }

    windows = inspect_state(state)["other_seats"]["2"]["latest_exact_hand"][
        "straight_flush_windows"
    ]

    assert windows["level_rank"] == "7"
    assert windows["natural"] == [
        {
            "ranks": ["T", "J", "Q", "K", "A"],
            "suit": "H",
            "cards": ["TH", "JH", "QH", "KH", "AH"],
            "wildcards_needed": 0,
        }
    ]
    assert windows["wildcard_assisted"] == []


def test_bomb_inventory_covers_rank_wildcard_and_joker_bombs() -> None:
    bombs = _bomb_report(
        [
            "9H",
            "9D",
            "9C",
            "9S",
            "7H*",
            "BJ",
            "BJ",
            "RJ",
            "RJ",
        ],
        "7",
        2,
    )

    assert bombs["natural"] == [
        {
            "kind": "rank_bomb",
            "size": 4,
            "rank": "9",
            "cards": ["9H", "9D", "9C", "9S"],
            "wildcards_needed": 0,
        },
        {
            "kind": "joker_bomb",
            "size": 4,
            "rank": "BJ+RJ",
            "cards": ["RJ", "RJ", "BJ", "BJ"],
            "wildcards_needed": 0,
        },
    ]
    assert bombs["wildcard_assisted"] == [
        {
            "kind": "rank_bomb",
            "size": 5,
            "rank": "9",
            "cards": ["9H", "9D", "9C", "9S", "7H*"],
            "wildcards_needed": 1,
        }
    ]


def test_nonheart_level_cards_are_natural_in_bombs() -> None:
    bombs = _bomb_report(
        ["7D*", "7D*", "7C*", "7C*", "7H*"],
        "7",
        2,
    )

    assert bombs == {
        "natural": [
            {
                "kind": "rank_bomb",
                "size": 4,
                "rank": "7",
                "cards": ["7D*", "7D*", "7C*", "7C*"],
                "wildcards_needed": 0,
            }
        ],
        "wildcard_assisted": [
            {
                "kind": "rank_bomb",
                "size": 5,
                "rank": "7",
                "cards": ["7D*", "7D*", "7C*", "7C*", "7H*"],
                "wildcards_needed": 1,
            }
        ],
    }


def test_exact_hand_output_includes_bomb_inventory() -> None:
    state = {
        "session_id": "s1",
        "game_id": "g1",
        "deck_count": 2,
        "player": {"player_id": "p1", "seat": 1, "team": "redTeam"},
        "round": {
            "round_id": "R1",
            "level_rank": "7",
            "cards_on_hand": "",
            "players": [
                {"player_id": "p1", "seat": 1, "team": "redTeam", "played_cards": ""},
                {
                    "player_id": "p2",
                    "seat": 2,
                    "team": "blueTeam",
                    "played_cards": "",
                    "cards_on_hand": "TC TD TS 7H*",
                },
            ],
            "turns": [],
        },
        "recent_events": [{"type": "iNewRound", "round_id": "R1", "level_rank": "7"}],
    }

    bombs = inspect_state(state)["other_seats"]["2"]["latest_exact_hand"]["bombs"]

    assert bombs == {
        "level_rank": "7",
        "natural": [],
        "wildcard_assisted": [
            {
                "kind": "rank_bomb",
                "size": 4,
                "rank": "T",
                "cards": ["TC", "TD", "TS", "7H*"],
                "wildcards_needed": 1,
            }
        ],
    }
