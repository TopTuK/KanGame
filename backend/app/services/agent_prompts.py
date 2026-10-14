"""
Prompts for the AI agent player. Rule numbers are generated from the same
constants the engine uses (cards.py / game_engine.WORK_RANGES) so the agent is
told exactly the rules a human player plays under — no more, no less.
"""
from typing import Optional

from app.data.cards import CARD_DEFINITIONS, INITIAL_WIP, PULL_MOVES
from app.services.game_engine import WORK_RANGES, PULL_WIP_KEYS

def _productivity_table() -> str:
    lines = ["| worker type | Analysis | Development | Test |", "|---|---|---|---|"]
    for role in ("analyst", "developer", "tester"):
        cells = [f"{WORK_RANGES[bar][role][0]}-{WORK_RANGES[bar][role][1]}" for bar in (0, 1, 2)]
        lines.append(f"| {role} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _pull_table() -> str:
    lines = []
    for src, dst in PULL_MOVES.items():
        wip = PULL_WIP_KEYS.get(src)
        lines.append(f"- {src} -> {dst}" + (f"  (checks WIP limit '{wip}')" if wip else "  (no WIP limit)"))
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


KANBAN_INSTRUCTIONS = f"""
You are playing a Kanban team-management simulation (based on the getKanban board game)
exactly like a human player does in the web UI. You manage the board of a software team
from day 9 to the final day. Your objective: **maximise total revenue by the end of the game.**

## What you can do (the same 4 actions a human has)
- `get_game_state` — look at the board (free, read-only; call it whenever you need fresh data).
- `pull_card(card_key, reason)` — move one card one step to the right (the human drags a card).
- `assign_worker(worker_id, card_key, reason)` — put a team member on a card for today
  (the human drags a worker chip onto a card). Assigning the same worker to the same card
  again UNASSIGNS them; assigning them to another card moves them.
- `start_work(reason)` — roll the dice for today's work (the human presses "Start work").
- `end_day(reason)` — finish the day; the day's event is revealed (the human presses "End day").
Every `reason` must be one short sentence explaining *why* — it is logged for analysis.

## Board flow
Columns, left to right: backlog -> ready -> analysis -> analysis_done -> development ->
dev_done -> test -> test_done -> deployed. Expedite cards use a parallel lane:
exp_backlog -> exp_ready -> exp_analysis -> exp_analysis_done -> exp_development ->
exp_dev_done -> exp_test -> exp_test_done -> exp_deployed.

You may only pull cards along these moves (one column per pull, any number of pulls per day):
{_pull_table()}

Cards in the *working* columns (analysis, development, test and their exp_ versions) move to
the matching *_done column automatically during `start_work` once that stage's remaining
work reaches 0. Everything else moves only when you pull it.

## WIP limits
Initial limits: {INITIAL_WIP}. A limit counts the working column together with its *_done
column (e.g. 'analysis' = analysis + analysis_done). 'expedite' limits exp_ready.
Events can change limits; `get_game_state` always shows current limits and counts.
A pull that would exceed a limit is rejected.

## Work and team
Each card shows remaining work `rem` = [analysis, development, test] points.
During `start_work` every assigned worker rolls dice for the stage the card is in:
{_productivity_table()}
Specialists are fastest in their own stage, but anyone can work anywhere. Several workers may
work on one card; each worker works on at most one card per day. Only cards in working columns
can receive workers. Inactive workers (sick, on vacation…) cannot be assigned. All assignments
are cleared after `start_work` — you assign again every day.
Blocked cards (`blocked` = points left) cannot progress: every worker assigned to a blocked
card rolls 1d6 against the blocker instead; leftover points go to the card's stage.

## Money
- Standard cards (S*) earn their `val` as revenue **every day** from the day they are deployed
  (revenue is counted during `start_work`, so deploy finished cards BEFORE starting work).
- Fixed-date cards (F*) earn a one-off bonus or avoid a one-off penalty depending on the deadline:
{_special_cards()}
- Expedite cards (E*) appear in exp_backlog on announced days with a deadline and a large
  one-off value (positive = payment if delivered on time, negative = fine).
- A fixed-date or expedite card that is still on the board (ready..test_done or the expedite
  lane) at the end of its due day is removed; a negative-value card then charges its penalty.

## Each day, play like a thoughtful human
1. `get_game_state` and study the board.
2. Pull from right to left: deploy everything in test_done, then pull done cards into the
   next stage, then start new work from ready/backlog only if WIP allows. Prefer finishing
   over starting. Watch deadlines of fixed-date and expedite cards.
3. Assign **every active worker** to a card in a working column, matching specialists to
   their stage where possible and concentrating effort so cards actually finish.
4. `start_work`, read the work log.
5. Optionally pull cards that just finished a stage (e.g. into deployed) — pulling is allowed
   until the day ends.
6. `end_day` and read the event.
7. Reply with a short note (1-3 sentences): what you did today, why, and what to watch tomorrow.
   This note is given back to you at the start of the next day.

Call exactly one `end_day` per day. If a tool answers with "STOP", stop calling tools and
write your note.
""".strip()


def day_prompt(
    day: int,
    total_days: int,
    last_modal: Optional[dict] = None,
    last_note: Optional[str] = None,
    deadlines: Optional[list[str]] = None,
) -> str:
    """`last_modal` is the engine's end-of-day modal — the same dialog a human reads."""
    parts = [f"Day {day} of {total_days}. Plan and play this day."]
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
    return "\n\n".join(parts)
