#!/usr/bin/env python3
"""OR-Tools CP-SAT backend for the guandan_smart_splitter exact-cover oracle.

Reads a JSON model from a file (or stdin) describing a weighted exact-cover /
set-partitioning instance, solves it with OR-Tools CP-SAT, and writes the
top-K solutions back as JSON.

Model schema (JSON):
{
  "numCards": int,
  "melds": [
    {
      "id": int,
      "cardMask": [int, ...],   // 0-based card indices used by this meld
      "weight": float,          // additive row weight
      "weightScale": int        // optional per-meld integer weight = round(weight*scale)
    }
  ],
  "scale": int,                  // global integer scale (default 1000)
  "topK": int,
  "timeBudgetMs": int,           // 0 = unlimited
  "diversityDistance": int,      // >=1 requires new sol to differ by >=d melds
  "noGoodCuts": bool
}

Output schema (JSON):
{
  "solutions": [
    {
      "meldIds": [int, ...],
      "additiveScore": float
    }
  ],
  "provenOptimal": bool,
  "status": str
}

If OR-Tools is unavailable the script prints an error object and exits 1 so the
Dart side can fall back to the in-package Algorithm X solver.
"""

import json
import sys

try:
    from ortools.sat.python import cp_model
except Exception as exc:  # pragma: no cover - environment-dependent
    print(json.dumps({"error": "ortools-unavailable", "detail": str(exc)}))
    sys.exit(1)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else None
    if model_path:
        with open(model_path, "r", encoding="utf-8") as fh:
            model = json.load(fh)
    else:
        model = json.load(sys.stdin)

    num_cards = model["numCards"]
    melds = model["melds"]
    scale = model.get("scale", 1000)
    top_k = model.get("topK", 5)
    time_budget_ms = model.get("timeBudgetMs", 0)
    diversity_distance = model.get("diversityDistance", 0)
    no_good_cuts = model.get("noGoodCuts", True)

    # Integer weights: round(float * scale). Deterministic.
    int_weights = {}
    for m in melds:
        w = m.get("weightScale") or int(round(m["weight"] * scale))
        int_weights[m["id"]] = w

    solutions = []
    proven_optimal = True
    solver = cp_model.CpSolver()
    if time_budget_ms and time_budget_ms > 0:
        solver.parameters.max_time_in_seconds = time_budget_ms / 1000.0
    solver.parameters.num_workers = 1

    accepted_blocks = []  # list of sorted meld-id lists already emitted
    status_name = "UNKNOWN"

    for _ in range(max(1, top_k)):
        mdl = cp_model.CpModel()
        x = {}
        for m in melds:
            x[m["id"]] = mdl.new_bool_var(f"x_{m['id']}")

        # Partition constraints: each card covered exactly once.
        card_melds = {}
        for m in melds:
            for card in m["cardMask"]:
                card_melds.setdefault(card, []).append(m["id"])
        for card in range(num_cards):
            mdl.add(sum(x[cid] for cid in card_melds.get(card, [])) == 1)

        # Objective: maximize weighted sum.
        mdl.maximize(sum(int_weights[mid] * x[mid] for mid in x))

        # No-good cuts for previously accepted solutions.
        if no_good_cuts:
            for block in accepted_blocks:
                mdl.add(sum(x[mid] for mid in block) <= len(block) - 1)
            if diversity_distance and diversity_distance > 1:
                for block in accepted_blocks:
                    mdl.add(sum(x[mid] for mid in block)
                            <= len(block) - diversity_distance)

        status = solver.solve(mdl)
        status_name = solver.status_name(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            proven_optimal = False
            break

        chosen = [mid for mid in x if solver.boolean_value(x[mid])]
        chosen.sort()
        # Structural diversity vs accepted blocks.
        if diversity_distance and diversity_distance > 0:
            blocked = False
            for block in accepted_blocks:
                overlap = len(set(chosen) & set(block))
                # Must differ by at least `diversity_distance` melds from each
                # accepted block (a structural-distance proxy, §15.3).
                if len(block) - overlap < diversity_distance:
                    blocked = True
                    break
            if blocked:
                # Add a no-good cut to exclude this exact solution and retry.
                accepted_blocks.append(chosen)
                continue

        additive = sum(int_weights[mid] for mid in chosen) / scale
        solutions.append({"meldIds": chosen, "additiveScore": additive})
        accepted_blocks.append(chosen)

        if status == cp_model.FEASIBLE and not proven_optimal:
            pass
        if len(solutions) >= top_k:
            break

    print(json.dumps({
        "solutions": solutions,
        "provenOptimal": proven_optimal,
        "status": status_name,
        "scale": scale,
    }))


if __name__ == "__main__":
    main()
