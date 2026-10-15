"""
AgentMemory on its own (no database, no model): conversation layout, the token
budget, day-boundary summarization and the deterministic fallback.
"""
from agent_framework import Content, Message

from app.services.agent_memory import AgentMemory, estimate_tokens, message_text


def _memory(**kwargs) -> AgentMemory:
    defaults = dict(window_tokens=10_000, threshold=0.5, keep_recent_days=1, base_tokens=1_000)
    return AgentMemory(**{**defaults, **kwargs})


def _play(memory: AgentMemory, day: int, board_chars: int = 2_000) -> None:
    prompt = Message("user", [f"Day {day} of 35. Event: quiet.\n\nCurrent board:\n" + "x" * board_chars])
    call = Message("assistant", [Content.from_function_call(call_id=f"c{day}", name="pull_card",
                                                            arguments={"card_key": "S8", "reason": "r"})])
    result = Message("tool", [Content.from_function_result(call_id=f"c{day}", result="OK: S8 moved to development.")])
    note = Message("assistant", [f"Note for day {day}."])
    memory.append_day(day, prompt, [call, result, note], journal=f"Day {day}: journal line.")


def test_messages_for_puts_summary_first_and_today_last():
    memory = _memory()
    _play(memory, 9)
    messages = memory.messages_for("Day 10 prompt")
    assert [m.role for m in messages] == ["user", "assistant", "tool", "assistant", "user"]
    assert messages[-1].text == "Day 10 prompt"

    memory.summary, memory.summary_first_day, memory.summary_until_day = "S", 9, 9
    assert memory.messages_for("p")[0].text.startswith("Game memory (your own summary of days 9-9)")


def test_message_text_includes_tool_calls_and_results():
    call = Message("assistant", [Content.from_function_call(call_id="1", name="end_day", arguments='{"reason":"done"}')])
    result = Message("tool", [Content.from_function_result(call_id="1", result={"event": "Quiet Day"})])
    assert message_text(call) == '[call end_day({"reason":"done"})]'
    assert message_text(result) == '[result {"event": "Quiet Day"}]'


def test_budget_triggers_only_above_threshold_and_with_old_days():
    memory = _memory()
    assert not memory.needs_summary("x" * 40_000)  # nothing old to summarize yet
    _play(memory, 9)
    assert not memory.needs_summary("x" * 20_000)  # the only day is a "recent" one and stays verbatim
    _play(memory, 10)
    assert not memory.needs_summary("short")
    assert memory.needs_summary("x" * 20_000)  # 1000 base + two days + ~5.7k-token prompt > 5000
    assert memory.estimated_tokens() > 1_000 + estimate_tokens("x" * 2_000)


async def test_compact_summarizes_old_days_and_keeps_recent_ones_whole():
    memory = _memory(keep_recent_days=1)
    for day in (9, 10, 11):
        _play(memory, day)
    received = {}

    async def summarize(instructions, transcript):
        received["instructions"], received["transcript"] = instructions, transcript
        return "Deployed S8 twice. Keep pulling right to left."

    before = memory.estimated_tokens()
    stats = await memory.compact(summarize)

    assert stats["days_summarized"] == [9, 10] and stats["fallback"] is False
    assert stats["tokens_before"] == before and stats["tokens_after"] < before
    assert [r.day for r in memory.days] == [11]
    assert len(memory.days[0].messages) == 4  # call and result still together
    assert memory.summary.startswith("Deployed S8") and (memory.summary_first_day, memory.summary_until_day) == (9, 10)
    # The transcript drops the repeated boards but keeps the tool activity.
    assert "Current board" not in received["transcript"] and "xxxx" not in received["transcript"]
    assert "=== Day 10 ===" in received["transcript"] and "[call pull_card(" in received["transcript"]
    assert "Do not invent facts" in received["instructions"]


async def test_second_compaction_folds_in_the_previous_summary():
    memory = _memory(keep_recent_days=1)
    for day in (9, 10):
        _play(memory, day)

    async def first(instructions, transcript):
        return "FIRST"

    await memory.compact(first)
    _play(memory, 11)
    received = {}

    async def second(instructions, transcript):
        received["transcript"] = transcript
        return "SECOND"

    await memory.compact(second)
    assert received["transcript"].startswith("Earlier summary (days 9-9):\nFIRST")
    assert memory.summary == "SECOND" and (memory.summary_first_day, memory.summary_until_day) == (9, 10)


async def test_failed_or_empty_summary_falls_back_to_journal():
    memory = _memory(keep_recent_days=1)
    for day in (9, 10, 11):
        _play(memory, day)

    async def broken(instructions, transcript):
        raise RuntimeError("provider down")

    stats = await memory.compact(broken)
    assert stats["fallback"] is True
    assert memory.summary == "Day 9: journal line.\nDay 10: journal line."

    async def empty(instructions, transcript):
        return "   "

    _play(memory, 12)
    stats = await memory.compact(empty)
    assert stats["fallback"] is True and memory.summary.endswith("Day 11: journal line.")


async def test_compact_is_a_no_op_with_only_recent_days():
    memory = _memory(keep_recent_days=2)
    _play(memory, 9)
    _play(memory, 10)

    async def never(instructions, transcript):
        raise AssertionError("should not be called")

    assert await memory.compact(never) is None
    assert len(memory.days) == 2
