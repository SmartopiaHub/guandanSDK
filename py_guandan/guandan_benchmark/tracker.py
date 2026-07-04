"""Game state tracker — round results, team scores, win rates."""

from typing import Any


class GameTracker:
    """Tracks round results, team scores, and win rates across a test game."""

    def __init__(self, total_rounds: int):
        self.total_rounds = total_rounds
        self.rounds_completed = 0
        # Cumulative scores per team
        self.red_score = 0
        self.blue_score = 0
        # Rounds won per team
        self.red_wins = 0
        self.blue_wins = 0
        # Per-round details
        self.round_details: list[dict] = []

    def record_round_result(
        self,
        round_result: dict,
        seat_map: dict[str, int],
    ) -> None:
        """Parse a round result and update team scores + win counts.

        Scoring (Guandan convention):
            The team with the banker (1st) wins the round (no draws).

            Winning team:
                banker + follower  (1st + 2nd)  → +3  (double-down)
                banker + third     (1st + 3rd)  → +2
                banker + dweller   (1st + 4th)  → +1

            Losing team:
                follower + third   (2nd + 3rd)  → -1
                follower + dweller (2nd + 4th)  → -2
                two dwellers       (3rd + 4th)  → -3  (double-down)
        """
        self.rounds_completed += 1

        # Collect team + seat assignments from rankings
        rankings: dict[str, dict] = {}  # rank_name → {team, seat}
        seat_team: dict[int, str] = {
            1: "red", 3: "red",
            2: "blue", 4: "blue",
        }

        def _pid(entry: Any) -> str:
            if isinstance(entry, dict):
                return entry.get("player_id", entry.get("id", ""))
            return entry if isinstance(entry, str) else ""

        def _team(entry: Any, pid: str) -> str:
            if isinstance(entry, dict):
                team = entry.get("team", "")
                if team in ("red", "redTeam"):
                    return "red"
                if team in ("blue", "blueTeam"):
                    return "blue"
            seat = seat_map.get(pid)
            return seat_team.get(seat, "unknown") if seat is not None else "unknown"

        def _seat(entry: Any, pid: str) -> object:
            """Extract seat from the entry itself first, then fall back to seat_map."""
            if isinstance(entry, dict):
                s = entry.get("seat")
                if s is not None:
                    return s
            return seat_map.get(pid)

        rank_entries: dict[str, Any] = {
            "first": round_result.get("first", round_result.get("banker")),
            "second": round_result.get("second", round_result.get("follower")),
            "third": round_result.get("third"),
            "fourth": round_result.get("fourth"),
        }
        if rank_entries["fourth"] is None:
            dwellers = round_result.get("dwellers")
            if isinstance(dwellers, list) and dwellers:
                rank_entries["fourth"] = dwellers[0]

        for rank_key, entry in rank_entries.items():
            pid = _pid(entry)
            if pid:
                s = _seat(entry, pid)
                rankings[rank_key] = {
                    "team": _team(entry, pid),
                    "seat": s if s is not None else "?",
                }

        # Determine winner: the team holding first place (banker)
        first_entry = rankings.get("first", {})
        winner_team = first_entry.get("team", "unknown") if isinstance(first_entry, dict) else first_entry
        if winner_team not in ("red", "blue"):
            return

        loser_team = "blue" if winner_team == "red" else "red"

        # Score based on what ranks the WINNING team holds
        winner_ranks = {
            r for r, info in rankings.items()
            if (info.get("team") if isinstance(info, dict) else info) == winner_team
        }
        loser_ranks = {
            r for r, info in rankings.items()
            if (info.get("team") if isinstance(info, dict) else info) == loser_team
        }

        # Winning team scoring
        if {"first", "second"}.issubset(winner_ranks):
            winner_pts = 3   # banker + follower (double-down)
        elif "first" in winner_ranks and "third" in winner_ranks:
            winner_pts = 2   # banker + third
        elif "first" in winner_ranks and "fourth" in winner_ranks:
            winner_pts = 1   # banker + dweller
        else:
            winner_pts = 0   # unexpected

        # Losing team scoring (determined by which ranks they hold)
        if {"third", "fourth"}.issubset(loser_ranks):
            loser_pts = -3   # two dwellers (double-down)
        elif {"second", "fourth"}.issubset(loser_ranks):
            loser_pts = -2   # follower + dweller
        elif {"second", "third"}.issubset(loser_ranks):
            loser_pts = -1   # follower + third
        else:
            loser_pts = 0    # unexpected

        if winner_team == "red":
            red_round_pts = winner_pts
            blue_round_pts = loser_pts
            self.red_wins += 1
            winner = "red"
        else:
            red_round_pts = loser_pts
            blue_round_pts = winner_pts
            self.blue_wins += 1
            winner = "blue"

        self.red_score += red_round_pts
        self.blue_score += blue_round_pts

        detail = {
            "round": self.rounds_completed,
            "rankings": rankings,
            "red_pts": red_round_pts,
            "blue_pts": blue_round_pts,
            "winner": winner,
        }
        self.round_details.append(detail)

    @property
    def red_win_rate(self) -> str:
        return f"{self.red_wins}/{self.total_rounds}"

    @property
    def blue_win_rate(self) -> str:
        return f"{self.blue_wins}/{self.total_rounds}"
