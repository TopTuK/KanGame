from typing import Optional

from pydantic import BaseModel


class RulesWorker(BaseModel):
    id: str
    role: str
    active_at_start: bool


class RulesCard(BaseModel):
    key: str
    type: str
    title: str
    analysis: int
    development: int
    test: int
    value: int
    start_column: str
    due_day: Optional[int] = None
    buff: Optional[str] = None


class RulesRank(BaseModel):
    min_revenue: int
    rank: str


class RulesOut(BaseModel):
    start_day: int
    total_days: int
    work_ranges: dict[str, dict[str, list[int]]]
    initial_wip: dict[str, int]
    wip_groups: dict[str, list[str]]
    pull_moves: dict[str, str]
    workers: list[RulesWorker]
    cards: list[RulesCard]
    ranks: list[RulesRank]
