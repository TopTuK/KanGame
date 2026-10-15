"""
Prompts for the AI agent player. Rule numbers are generated from the same
constants the engine uses (cards.py / game_engine.WORK_RANGES) so the agent is
told exactly the rules a human player plays under — no more, no less.

`board_text` renders the board the way a human sees it on screen (cards grouped
by column, WIP usage, who works where, which drags are currently possible), so
even small models can play without decoding raw JSON.
"""
from typing import Optional

from app.data.cards import CARD_DEFINITIONS, INITIAL_BOARD, INITIAL_WIP, INITIAL_WORKERS, PULL_MOVES, WIP_GROUPS
from app.services.game_engine import WORK_RANGES, PULL_WIP_KEYS, can_pull_to, wip_count

ROLES = ("analyst", "developer", "tester")
STAGE_OF_COLUMN = {
    "analysis": 0, "exp_analysis": 0,
    "development": 1, "exp_development": 1,
    "test": 2, "exp_test": 2,
}
STAGE_NAMES = ("analysis", "development", "test")
SPECIALIST_OF_STAGE = {0: "analyst", 1: "developer", 2: "tester"}

STANDARD_LANE = [
    "backlog", "ready", "analysis", "analysis_done", "development",
    "dev_done", "test", "test_done", "deployed",
]
EXPEDITE_LANE = [
    "exp_backlog", "exp_ready", "exp_analysis", "exp_analysis_done", "exp_development",
    "exp_dev_done", "exp_test", "exp_test_done", "exp_deployed",
]
_COLUMN_HELP = {
    "backlog": "options not started; pull into ready",
    "ready": "committed, waiting; pull into analysis",
    "analysis": "WORKING column: assign workers (analysts best)",
    "analysis_done": "analysis finished; pull into development",
    "development": "WORKING column: assign workers (developers best)",
    "dev_done": "development finished; pull into test",
    "test": "WORKING column: assign workers (testers best)",
    "test_done": "finished; pull into deployed to start earning",
    "deployed": "done, earning money",
}
BACKLOG_PREVIEW = 8


def _avg(rng: tuple[int, int]) -> float:
    return (rng[0] + rng[1]) / 2


def _productivity_table() -> str:
    lines = [
        "| worker type | in Analysis | in Development | in Test |",
        "|---|---|---|---|",
    ]
    for role in ROLES:
        cells = []
        for bar in (0, 1, 2):
            lo, hi = WORK_RANGES[bar][role]
            mark = " (specialist)" if SPECIALIST_OF_STAGE[bar] == role else ""
            cells.append(f"{lo}-{hi}, avg {_avg((lo, hi)):g}{mark}")
        lines.append(f"| {role} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _pull_table() -> str:
    lines = []
    for src, dst in PULL_MOVES.items():
        wip = PULL_WIP_KEYS.get(src)
        lanes = " + ".join(WIP_GROUPS.get(wip, [wip])) if wip else ""
        lines.append(
            f"- {src} -> {dst}" + (f"   (needs a free slot in WIP '{wip}' = {lanes})" if wip else "   (no WIP limit)")
        )
    return "\n".join(lines)


def _special_cards() -> str:
    lines = []
    for c in CARD_DEFINITIONS:
        if c["type"] == "fixed_date":
            effect = f"bonus +{c['val']} if deployed by end of day {c['due_day']}" if c["val"] > 0 \
                else f"penalty {c['val']} if not deployed by end of day {c['due_day']}"
            lines.append(f"- {c['key']} (fixed-date, work A/D/T {c['analysis']}/{c['dev']}/{c['test']}): {effect}")
        elif c["type"] == "intangible":
            lines.append(
                f"- {c['key']} (intangible, work A/D/T {c['analysis']}/{c['dev']}/{c['test']}): "
                f"no revenue; when deployed every {c['buff']} gets +1 on all future work rolls"
            )
    return "\n".join(lines)


def _specialist_avg(stage: int) -> float:
    return _avg(WORK_RANGES[stage][SPECIALIST_OF_STAGE[stage]])


_START_COLUMN = {key: col for col, keys in INITIAL_BOARD.items() for key in keys}


def _card_catalog() -> str:
    """Every standard card with its daily value and A/D/T estimate (the numbers printed on the cards)."""
    items = []
    for c in CARD_DEFINITIONS:
        if c["type"] != "standard":
            continue
        where = _START_COLUMN.get(c["key"])
        items.append(
            f"{c['key']} {c['val']}/day A{c['analysis']} D{c['dev']} T{c['test']}"
            + (f" (starts in {where})" if where else "")
        )
    return "\n".join("; ".join(items[i:i + 4]) for i in range(0, len(items), 4))


def _team_roster() -> str:
    lines = []
    for role in ROLES:
        ids = [w["id"] for w in INITIAL_WORKERS if w["type"] == role]
        active = [w["id"] for w in INITIAL_WORKERS if w["type"] == role and w["active"]]
        lines.append(f"- {role}s: {', '.join(ids)} (active at the start: {', '.join(active) or 'none'})")
    return "\n".join(lines)


def _starting_capacity() -> str:
    """Expected points per day of the starting team if every worker stays in their own stage."""
    parts = []
    for bar in (0, 1, 2):
        role = SPECIALIST_OF_STAGE[bar]
        n = sum(1 for w in INITIAL_WORKERS if w["type"] == role and w["active"])
        parts.append(f"{STAGE_NAMES[bar]} about {n} x {_specialist_avg(bar):g} = {n * _specialist_avg(bar):g} points/day")
    return "; ".join(parts)


KANBAN_INSTRUCTIONS = f"""
You are playing a Kanban team-management simulation (based on the getKanban board game)
exactly like a human player does in the web UI. You manage a software team's board from
day 9 to the final day. Objective: **maximise total revenue by the end of the game.**
Money only comes from cards that reach **deployed** — a card stuck anywhere else earns nothing.

# 1. Your actions (the same 4 actions a human has, plus looking)
- `get_game_state()` — show the board (read-only, free). The board is also given to you at
  the start of every day.
- `pull_card(card_key, reason)` — move ONE card ONE column to the right (a human drags it).
- `assign_worker(worker_id, card_key, reason)` — put one team member on one card for today
  (a human drags a worker chip onto a card).
- `start_work(reason)` — all assigned workers roll dice and do today's work.
- `end_day(reason)` — finish the day; the day's event is revealed.
Every `reason` is one short sentence explaining *why* — it is logged for analysis.

# 2. The board: columns and stages
Standard lane, left to right:
backlog -> ready -> [analysis -> analysis_done] -> [development -> dev_done] -> [test -> test_done] -> deployed
Each stage has a WORKING column (analysis, development, test) where people do work, and a
DONE column (analysis_done, dev_done, test_done) where finished cards wait to be pulled.
Expedite lane (urgent E* cards, appear during the game) works the same with exp_ columns:
exp_backlog -> exp_ready -> exp_analysis -> exp_analysis_done -> exp_development -> exp_dev_done
-> exp_test -> exp_test_done -> exp_deployed.

# 3. How cards move (VERY IMPORTANT)
There are exactly two ways a card moves:
a) **Automatically, during start_work**: a card in a WORKING column whose remaining work for
   that stage drops to 0 moves to the matching DONE column
   (analysis -> analysis_done, development -> dev_done, test -> test_done).
b) **Only when YOU pull it**: every other move. A card in a DONE column, in ready or in backlog
   stays there FOREVER until you call `pull_card`. Nobody else moves cards for you.
Allowed pulls (one column per pull; you may pull many cards per day):
{_pull_table()}
**Pulls are only possible BEFORE start_work.** After start_work the board is frozen until the
next day, so do all pulls first. A card finished today is pulled tomorrow morning.

# 4. WIP limits
Initial limits: {INITIAL_WIP}. A stage's limit counts its WORKING and DONE columns together:
'analysis' = analysis + analysis_done, 'development' = development + dev_done,
'test' = test + test_done. 'ready' counts the ready column; 'expedite' counts exp_ready.
A pull into a full stage is rejected. To make room in a stage you must first pull a card OUT
of that stage's DONE column into the next stage. That is why you always pull from RIGHT to LEFT.
Events can change limits; the board always shows current limits and usage.

# 5. Work, workers and how to assign them
A card has three amounts of work: analysis / development / test points. The board shows the
points left for the stage the card is currently in ("left: N").
During start_work each assigned worker rolls a random whole number of points for the stage of
the card they are on (uniform in the range; "avg" is the expected value):
{_productivity_table()}
Rules:
- Workers can only be assigned to cards in WORKING columns (analysis, development, test,
  exp_analysis, exp_development, exp_test). Assigning to a card in ready / *_done / backlog fails.
- One worker works on one card per day. Several workers may work on the same card (their points add up).
  Points beyond what a stage needs are lost (they do not carry over to another card or stage).
- Assigning a worker to a card they are ALREADY on UNASSIGNS them (it is a toggle). Assigning
  them to a different card moves them. So assign each worker exactly once per day.
- Inactive workers (sick, on vacation, quit, not hired yet) cannot be assigned. The board lists who is active.
- All assignments are cleared after start_work: assign everyone again every day.
- Blocked cards cannot progress: each worker assigned to a blocked card rolls 1d6 against the
  blocker instead; once the blocker reaches 0, leftover points go into the card's work.
- Buffs: each deployed intangible card adds +1 to every future roll of one role (shown on the board).

# 6. The team and its capacity
The roster has 12 workers; worker ids never change:
{_team_roster()}
Workers join or leave only through day events (hired, sick, vacation, conference, quit,
restructure); the board always shows who is active today.
Expected capacity of the starting team with everyone in their own stage:
{_starting_capacity()}.
How to assign well:
- Put every active worker on some card — an idle worker is wasted capacity.
- Specialists first: testers on test cards, developers on development cards, analysts on analysis cards.
- Concentrate: put enough people on a card to FINISH its stage soon, instead of one person per
  card everywhere. Days to finish a stage = points left / sum of the assigned workers' averages.
  Example: a card with 9 test points left needs about 2 testers ({_specialist_avg(2):g} each) to finish in one day.
- Prefer cards closest to deployment (test before development before analysis) and cards with deadlines.
- If a stage has no card for a specialist, send them to help the most downstream stage that has
  work (e.g. a developer helps test). Cross-role help is slower but better than idle.

# 7. Card types (classes of service) and money
- Standard cards (S*) earn their value **every day** once deployed. Revenue is counted during
  start_work, so a card pulled into deployed before start_work earns money that same day.
  The earlier a card is deployed, the more days it earns — finishing cards beats starting cards.
- Fixed-date cards (F*) earn nothing per day; they have a deadline (end of the due day). A
  positive value is a one-off bonus if deployed on time (nothing if late); a negative value is a
  fine charged if the card is not deployed on time:
{_special_cards()}
- Expedite cards (E*) appear in exp_backlog when a day event announces them, with a deadline and
  a large one-off value: positive = payment if deployed on time, negative = fine if NOT deployed
  on time (deploying on time costs nothing). They use the expedite lane (exp_ready WIP limit 1).
  Treat them as top priority.
- Intangible cards (I*) earn no money; deploying one gives a permanent +1 buff to every future
  roll of one role. Worth it early in the game, rarely worth it late.
- Overdue: a fixed-date or expedite card still on the board (ready..test_done, or anywhere in the
  expedite lane) at the end of its due day is removed; a negative-value card then charges its fine.
  Fixed-date cards never pulled out of backlog are not removed.

# 8. Card catalog: standard cards, value per day and A/D/T estimate in points
{_card_catalog()}

# 9. Daily routine (follow it every day, in this order)
1. Read the board (it is in the day message; call get_game_state again after changes if needed).
2. DEPLOY: pull every card in test_done (and exp_test_done) — no WIP limit, always do it.
3. PULL RIGHT TO LEFT, one stage at a time, as long as the board says the pull is possible:
   dev_done -> test, then analysis_done -> development, then ready -> analysis, then backlog -> ready.
   Also move expedite cards forward first whenever possible.
4. ASSIGN every active worker (section 5) to cards now in working columns.
5. start_work once.
6. end_day once.
7. Reply with a short note (1-3 sentences): what you did, why, and what to do tomorrow.
   Earlier days stay in this conversation (older days are condensed into a "Game memory"
   summary), so use them to plan ahead.

# 10. Worked example (the opening board)
Board: test has S1, S2, S3 (test 3/3 FULL); dev_done has S4, S5; development has S6, S7
(development 4/5, 1 free); analysis_done has S8; analysis has S9, S10 (analysis 3/3 FULL);
ready is full. Active: a1, a2 (analysts), d1, d2 (developers), t1, t2, t3 (testers).
- Deploy: test_done is empty, nothing to deploy.
- dev_done -> test: test is FULL, so S4 and S5 must wait.
- analysis_done -> development: 1 slot free -> pull_card("S8"). Now analysis has a free slot.
- ready -> analysis: pull_card("S11") to use the freed analysis slot.
- Assign: t1 -> S1, t2 -> S2, t3 -> S3 (testers on test); d1 -> S6, d2 -> S7 (developers on
  development); a1 -> S9, a2 -> S10 (analysts on analysis). Nobody is idle.
- start_work, then end_day.
Next morning: S1-S3 will probably be in test_done -> deploy them first, which frees the test
stage -> pull S4 and S5 from dev_done into test -> that frees development -> pull from
analysis_done, and so on, always right to left.

# 11. Common mistakes to avoid
- Forgetting to pull cards out of analysis_done / dev_done / test_done (the card stays there and
  blocks the WIP of its stage). Check those columns first every day.
- Trying to pull after start_work (always rejected).
- Assigning a worker twice to the same card (that unassigns them).
- Assigning workers to cards in ready or *_done columns (rejected — those are not working columns).
- Spreading workers one-per-card so nothing ever finishes.
- Calling end_day without start_work (the day's work is lost).
If a tool returns ERROR, read it, fix the cause and continue. If a tool answers with "STOP",
stop calling tools and write your note.
""".strip()


# --- board rendering -----------------------------------------------------------

def _worker_names_by_card(game) -> dict[str, list[str]]:
    by_card: dict[str, list[str]] = {}
    for w in game.team_config.get("workers", []):
        if w.get("assigned_card_id"):
            by_card.setdefault(str(w["assigned_card_id"]), []).append(w["id"])
    return by_card


def _card_line(card, workers_on: dict[str, list[str]]) -> str:
    parts = [card.card_key]
    if card.card_type == "standard":
        parts.append(f"(earns {card.val}/day)")
    elif card.card_type in ("fixed_date", "expedite"):
        parts.append(f"({card.card_type}, value {card.val}, due end of day {card.due_day})")
    elif card.card_type == "intangible":
        parts.append(f"(intangible, buff +1 {card.buff})")
    stage = STAGE_OF_COLUMN.get(card.column)
    remaining = (card.analysis_remaining, card.dev_remaining, card.test_remaining)
    if stage is not None:
        parts.append(f"left: {remaining[stage]:g} {STAGE_NAMES[stage]} points")
    elif card.column not in ("deployed", "exp_deployed"):
        parts.append(f"work A/D/T {remaining[0]:g}/{remaining[1]:g}/{remaining[2]:g}")
    if card.is_blocked:
        parts.append(f"BLOCKED (blocker {card.blocker_remaining} points left)")
    names = workers_on.get(str(card.id))
    if names:
        parts.append("workers: " + ", ".join(names))
    return "  - " + " ".join(parts)


def _wip_line(game) -> str:
    items = []
    for key, limit in game.wip_limits.items():
        count = wip_count(game, key)
        lanes = "+".join(WIP_GROUPS.get(key, [key]))
        state = "FULL" if count >= limit else f"{limit - count} free"
        items.append(f"{key} {count}/{limit} [{lanes}] {state}")
    return "WIP: " + "; ".join(items)


# Expedite lane first, then right-most columns first (deploy before starting new work).
_PULL_PRIORITY = {col: i for i, col in enumerate([*reversed(EXPEDITE_LANE), *reversed(STANDARD_LANE)])}


def _possible_pulls(game) -> list[str]:
    """Pulls the WIP limits allow right now — the drags a human could make on screen."""
    moves = []
    backlog_listed = 0
    for card in sorted(game.cards, key=lambda c: c.sort_order):
        target = PULL_MOVES.get(card.column)
        if not target:
            continue
        wip_key = PULL_WIP_KEYS.get(card.column)
        if wip_key and not can_pull_to(game, wip_key):
            continue
        if card.column == "backlog":
            backlog_listed += 1
            if backlog_listed > BACKLOG_PREVIEW:
                continue
        moves.append((_PULL_PRIORITY.get(card.column, 99), card.sort_order, f"{card.card_key}: {card.column} -> {target}"))
    return [text for _, _, text in sorted(moves)]


def board_text(game) -> str:
    """The board as a human sees it, as plain text."""
    workers_on = _worker_names_by_card(game)
    status = game.status.value if hasattr(game.status, "value") else str(game.status)
    lines = [
        f"DAY {game.current_day} of {game.total_days} | status: {status} | "
        f"work started today: {'yes' if game.work_done else 'no'} | total revenue: {game.total_revenue}",
        _wip_line(game),
    ]
    buffs = {k: v for k, v in game.team_config.get("buffs", {}).items() if v}
    if buffs:
        lines.append("Buffs (+points per roll): " + ", ".join(f"{k} +{v}" for k, v in buffs.items()))

    cards_by_col: dict[str, list] = {}
    for card in sorted(game.cards, key=lambda c: c.sort_order):
        cards_by_col.setdefault(card.column, []).append(card)

    lanes = [("STANDARD LANE", STANDARD_LANE)]
    if any(cards_by_col.get(col) for col in EXPEDITE_LANE):
        lanes.append(("EXPEDITE LANE (urgent)", EXPEDITE_LANE))
    for title, columns in lanes:
        lines.append(f"\n{title}")
        for col in columns:
            cards = cards_by_col.get(col, [])
            help_text = _COLUMN_HELP.get(col.removeprefix("exp_"), "")
            lines.append(f"{col} ({len(cards)}) — {help_text}")
            if col in ("deployed", "exp_deployed"):
                if cards:
                    lines.append("  - " + ", ".join(c.card_key for c in cards))
                continue
            shown = cards[:BACKLOG_PREVIEW] if col == "backlog" else cards
            lines.extend(_card_line(c, workers_on) for c in shown)
            if len(cards) > len(shown):
                lines.append(f"  - ... and {len(cards) - len(shown)} more")

    lines.append("\nTEAM")
    active, inactive = [], []
    by_id = {str(c.id): c.card_key for c in game.cards}
    for w in game.team_config.get("workers", []):
        if w.get("active"):
            on = by_id.get(str(w.get("assigned_card_id"))) if w.get("assigned_card_id") else None
            active.append(f"{w['id']} {w['type']}" + (f" -> on {on}" if on else " (not assigned yet)"))
        else:
            inactive.append(w["id"])
    lines.append("Active workers: " + "; ".join(active))
    if inactive:
        lines.append("Unavailable (cannot be assigned): " + ", ".join(inactive))

    if not game.work_done:
        pulls = _possible_pulls(game)
        lines.append("\nPULLS POSSIBLE RIGHT NOW (WIP allows them; right-most first):")
        lines.extend(f"  - {m}" for m in pulls or ["none"])
    else:
        lines.append("\nWork already started today: no more pulls or assignments; call end_day.")
    return "\n".join(lines)


def day_prompt(
    day: int,
    total_days: int,
    last_modal: Optional[dict] = None,
    last_note: Optional[str] = None,
    deadlines: Optional[list[str]] = None,
    board: Optional[str] = None,
) -> str:
    """`last_modal` is the engine's end-of-day modal — the same dialog a human reads."""
    parts = [f"Day {day} of {total_days}. Play this day following the daily routine "
             f"(deploy, pull right to left, assign every active worker, start_work, end_day)."]
    if last_modal:
        parts.append(
            f"Yesterday's end-of-day event: {last_modal.get('title', '')}\n{last_modal.get('description', '')}".strip()
        )
        for o in last_modal.get("overdue") or []:
            parts.append(f"Overdue and removed: {o.get('card_key')} (due day {o.get('due_day')}, value {o.get('val')}).")
    if deadlines:
        parts.append("Open deadlines: " + "; ".join(deadlines))
    if last_note:
        parts.append(f"Your note from yesterday: {last_note}")
    if day >= total_days:
        parts.append("This is the final day — after end_day the game is over.")
    if board:
        parts.append("Current board:\n" + board)
    return "\n\n".join(parts)
