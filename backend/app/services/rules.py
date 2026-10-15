"""
The game's rule numbers, built from the same constants the engine plays with,
so the public rules page can never drift from the actual mechanics.
Expedite cards are left out on purpose: a player only learns about them when
a day event announces them.
"""
from app.data.cards import CARD_DEFINITIONS, INITIAL_BOARD, INITIAL_WIP, INITIAL_WORKERS, PULL_MOVES, WIP_GROUPS
from app.data.scoring import RANKS
from app.services.game_engine import WORK_RANGES

START_DAY = 9
TOTAL_DAYS = 35
STAGE_KEYS = ("analysis", "development", "test")

_START_COLUMN = {key: col for col, keys in INITIAL_BOARD.items() for key in keys}


def rules_payload() -> dict:
    return {
        "start_day": START_DAY,
        "total_days": TOTAL_DAYS,
        "work_ranges": {
            STAGE_KEYS[bar]: {role: list(rng) for role, rng in roles.items()}
            for bar, roles in WORK_RANGES.items()
        },
        "initial_wip": dict(INITIAL_WIP),
        "wip_groups": {k: list(v) for k, v in WIP_GROUPS.items()},
        "pull_moves": dict(PULL_MOVES),
        "workers": [
            {"id": w["id"], "role": w["type"], "active_at_start": w["active"]} for w in INITIAL_WORKERS
        ],
        "cards": [
            {
                "key": c["key"], "type": c["type"], "title": c["title_en"],
                "analysis": c["analysis"], "development": c["dev"], "test": c["test"],
                "value": c["val"], "start_column": _START_COLUMN.get(c["key"], "backlog"),
                "due_day": c.get("due_day"), "buff": c.get("buff"),
            }
            for c in CARD_DEFINITIONS if c["type"] != "expedite"
        ],
        "ranks": [{"min_revenue": threshold, "rank": rank} for threshold, rank in RANKS],
    }
