"""
The AI agent's conversation memory across game days, kept within a token budget.

The whole game is one conversation: each day appends the day prompt plus the
messages the agent produced (its tool calls, tool results and its note). Before
a new day, if the estimated context would pass `threshold x window` tokens, the
older days are condensed into a single "Game memory" summary written by the
model itself; the most recent days stay verbatim. Cuts happen only at day
boundaries, so a tool call is never separated from its result. If the model
cannot summarize, a deterministic summary built from the daily journal is used
instead, so memory pressure can never fail a run.

Within a single day the chat client's own compaction (see agent_runner) guards
the window; this module manages the growth across days.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from agent_framework import Message

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 3.5
TOOL_RESULT_PREVIEW = 400
SUMMARY_MAX_WORDS = 800

SUMMARY_INSTRUCTIONS = f"""
You are condensing your own memory of a Kanban simulation game you are playing.
Write a summary for yourself (at most {SUMMARY_MAX_WORDS} words, plain text) of the days below.
Keep what matters for the rest of the game:
- revenue trend and which cards were deployed (and when);
- fixed-date and expedite deadlines: which were met, which are still open and how far along they are;
- team changes (who is unavailable or back), blockers, WIP-limit changes, active buffs;
- mistakes and rejected actions to avoid, and what worked well;
- your plan for the coming days.
Do not invent facts. Do not include tool-call syntax.
""".strip()

Summarizer = Callable[[str, str], Awaitable[str]]


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1


def _content_text(content: Any) -> str:
    ctype = getattr(content, "type", None)
    if ctype == "text":
        return getattr(content, "text", "") or ""
    if ctype == "function_call":
        args = getattr(content, "arguments", None)
        if not isinstance(args, str):
            args = json.dumps(args, ensure_ascii=False) if args else ""
        return f"[call {getattr(content, 'name', '?')}({args})]"
    if ctype == "function_result":
        result = getattr(content, "result", None)
        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
        return f"[result {text}]"
    return ""


def message_text(message: Any) -> str:
    """Everything in a message that reaches the model, as plain text (for estimates and transcripts)."""
    contents = getattr(message, "contents", None)
    if contents is None:
        return str(getattr(message, "text", "") or message)
    return " ".join(t for t in (_content_text(c) for c in contents) if t)


def message_tokens(message: Any) -> int:
    # Small fixed overhead per message for role/ids/JSON framing.
    return estimate_tokens(message_text(message)) + 8


@dataclass
class DayRecord:
    day: int
    messages: list
    journal: str
    tokens: int = 0


@dataclass
class AgentMemory:
    window_tokens: int
    threshold: float
    keep_recent_days: int
    base_tokens: int = 0  # instructions + tool schemas, sent with every call
    days: list[DayRecord] = field(default_factory=list)
    summary: Optional[str] = None
    summary_until_day: Optional[int] = None
    summary_first_day: Optional[int] = None

    # --- building the conversation -----------------------------------------

    def _summary_message(self) -> Optional[Message]:
        if not self.summary:
            return None
        return Message("user", [
            f"Game memory (your own summary of days {self.summary_first_day}-{self.summary_until_day}):\n"
            f"{self.summary}"
        ])

    def messages_for(self, prompt: str) -> list:
        """The full conversation for today's run: memory summary, earlier days, today's prompt."""
        out: list = []
        if summary := self._summary_message():
            out.append(summary)
        for record in self.days:
            out.extend(record.messages)
        out.append(Message("user", [prompt]))
        return out

    def append_day(self, day: int, prompt_message: Any, response_messages: list, journal: str) -> None:
        messages = [prompt_message, *response_messages]
        self.days.append(DayRecord(
            day=day, messages=messages, journal=journal,
            tokens=sum(message_tokens(m) for m in messages),
        ))

    # --- budget ----------------------------------------------------------------

    def estimated_tokens(self, next_prompt: str = "") -> int:
        total = self.base_tokens + sum(r.tokens for r in self.days)
        if self.summary:
            total += estimate_tokens(self.summary) + 30
        if next_prompt:
            total += estimate_tokens(next_prompt) + 8
        return total

    @property
    def trigger_tokens(self) -> int:
        return int(self.window_tokens * self.threshold)

    def needs_summary(self, next_prompt: str = "") -> bool:
        return len(self.days) > self.keep_recent_days and self.estimated_tokens(next_prompt) > self.trigger_tokens

    # --- summarization -----------------------------------------------------------

    def _transcript(self, records: list[DayRecord]) -> str:
        parts = []
        if self.summary:
            parts.append(
                f"Earlier summary (days {self.summary_first_day}-{self.summary_until_day}):\n{self.summary}"
            )
        for record in records:
            lines = [f"=== Day {record.day} ==="]
            for i, m in enumerate(record.messages):
                role = getattr(m, "role", "?")
                if i == 0 and role == "user":
                    # The day prompt repeats the whole board; the event and deadlines at its top are what matter.
                    text = message_text(m).split("Current board:")[0].strip()
                else:
                    text = message_text(m)
                if role == "tool" and len(text) > TOOL_RESULT_PREVIEW:
                    text = text[:TOOL_RESULT_PREVIEW] + "…"
                if text:
                    lines.append(f"{role}: {text}")
            parts.append("\n".join(lines))
        transcript = "\n\n".join(parts)
        # Never send the summarizer more than half the window.
        limit = int(self.window_tokens * 0.5 * CHARS_PER_TOKEN)
        return transcript if len(transcript) <= limit else "…" + transcript[-limit:]

    def _fallback_summary(self, records: list[DayRecord]) -> str:
        lines = []
        if self.summary:
            lines.append(self.summary)
        lines.extend(r.journal for r in records if r.journal)
        return "\n".join(lines)

    async def compact(self, summarize: Summarizer) -> Optional[dict]:
        """Summarize every day except the most recent ones. Returns stats for the run log, or None."""
        if len(self.days) <= self.keep_recent_days:
            return None
        cut = len(self.days) - self.keep_recent_days
        old, recent = self.days[:cut], self.days[cut:]
        before = self.estimated_tokens()
        fallback = False
        try:
            summary = (await summarize(SUMMARY_INSTRUCTIONS, self._transcript(old)) or "").strip()
            if not summary:
                raise ValueError("empty summary")
        except Exception as exc:  # noqa: BLE001 — memory must never fail the run
            logger.warning("Agent memory summarization failed, using journal fallback: %s", type(exc).__name__)
            summary = self._fallback_summary(old)
            fallback = True
        if self.summary_first_day is None:
            self.summary_first_day = old[0].day
        self.summary = summary
        self.summary_until_day = old[-1].day
        self.days = recent
        return {
            "tokens_before": before,
            "tokens_after": self.estimated_tokens(),
            "days_summarized": [r.day for r in old],
            "fallback": fallback,
        }
