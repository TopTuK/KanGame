import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.agent import AgentRun, AgentRunStatus, GameAction, ACTIVE_RUN_STATUSES
from app.models.game import Game
from app.models.user import User
from app.schemas.agent import (
    AgentConfigOut, AgentRunCreate, AgentRunOut, AgentRunDetail, AgentGameSummary, GameActionOut,
)
from app.schemas.game import MetricResponse
from app.services import game_engine, action_log, agent_runner

router = APIRouter()

DETAIL_ACTIONS = 50


def _run_out(run: AgentRun, game: Optional[Game]) -> AgentRunOut:
    return AgentRunOut(
        id=run.id, game_id=run.game_id, name=run.name, model=run.model, base_url=run.base_url,
        status=run.status.value, error=run.error,
        tool_calls=run.tool_calls or 0, llm_turns=run.llm_turns or 0,
        input_tokens=run.input_tokens or 0, output_tokens=run.output_tokens or 0,
        created_at=run.created_at, started_at=run.started_at, finished_at=run.finished_at,
        game=AgentGameSummary(
            id=game.id, name=game.name, status=game.status.value, current_day=game.current_day,
            total_days=game.total_days, total_revenue=game.total_revenue,
        ) if game else None,
    )


async def _get_run(db: AsyncSession, run_id: uuid.UUID, user: User) -> tuple[AgentRun, Optional[Game]]:
    result = await db.execute(
        select(AgentRun, Game)
        .join(Game, Game.id == AgentRun.game_id, isouter=True)
        .where(AgentRun.id == run_id, AgentRun.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return row[0], row[1]


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def _resolve_api_key(payload: AgentRunCreate, base_url: str) -> str:
    """User key if given; otherwise the server key, which only ever goes to the default provider."""
    user_key = payload.api_key.get_secret_value().strip() if payload.api_key else ""
    if user_key:
        return user_key
    if settings.AGENT_DEFAULT_API_KEY and base_url == _normalize_url(settings.AGENT_DEFAULT_BASE_URL):
        return settings.AGENT_DEFAULT_API_KEY
    raise HTTPException(status_code=400, detail="API key is required")


@router.get("/config", response_model=AgentConfigOut)
async def get_config(current_user: User = Depends(get_current_user)):
    return AgentConfigOut(
        enabled=settings.AGENT_ENABLED,
        default_base_url=_normalize_url(settings.AGENT_DEFAULT_BASE_URL),
        default_model=settings.AGENT_DEFAULT_MODEL,
        has_server_key=bool(settings.AGENT_DEFAULT_API_KEY),
    )


@router.post("/runs", response_model=AgentRunOut, status_code=201)
async def create_run(
    payload: AgentRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.AGENT_ENABLED:
        raise HTTPException(status_code=503, detail="AI agent mode is disabled")
    base_url = _normalize_url(str(payload.base_url) if payload.base_url else settings.AGENT_DEFAULT_BASE_URL)
    model = (payload.model or "").strip() or settings.AGENT_DEFAULT_MODEL
    api_key = _resolve_api_key(payload, base_url)

    active = await db.execute(
        select(AgentRun.id).where(AgentRun.user_id == current_user.id, AgentRun.status.in_(ACTIVE_RUN_STATUSES))
    )
    if active.first():
        raise HTTPException(status_code=409, detail="You already have an agent run in progress")

    name = payload.name.strip()
    game = await game_engine.create_game(db, f"🤖 {name}", name, current_user.id, is_agent=True)
    run = AgentRun(
        id=uuid.uuid4(), user_id=current_user.id, game_id=game.id,
        name=name, model=model, base_url=base_url, status=AgentRunStatus.pending,
    )
    db.add(run)
    await db.commit()
    await action_log.record_day_start(db, game, run_id=run.id)

    agent_runner.start(run.id, game.id, current_user.id, api_key, base_url, model)
    return _run_out(run, game)


@router.get("/runs", response_model=list[AgentRunOut])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentRun, Game)
        .join(Game, Game.id == AgentRun.game_id, isouter=True)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
    )
    return [_run_out(run, game) for run, game in result.all()]


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def get_run(
    run_id: uuid.UUID,
    after_seq: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run detail. Without `after_seq`: the latest actions; with it: actions newer than that seq (for polling)."""
    run, game = await _get_run(db, run_id, current_user)
    query = select(GameAction).where(GameAction.game_id == run.game_id)
    if after_seq is not None:
        query = query.where(GameAction.seq > after_seq).order_by(GameAction.seq).limit(500)
        actions = list((await db.execute(query)).scalars().all())
    else:
        query = query.order_by(GameAction.seq.desc()).limit(DETAIL_ACTIONS)
        actions = list(reversed((await db.execute(query)).scalars().all()))
    return AgentRunDetail(
        **_run_out(run, game).model_dump(),
        actions=[GameActionOut.model_validate(a) for a in actions],
    )


@router.get("/runs/{run_id}/actions", response_model=list[GameActionOut])
async def list_run_actions(
    run_id: uuid.UUID,
    before_seq: Optional[int] = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Older actions for paging back through the feed, returned oldest first."""
    run, _ = await _get_run(db, run_id, current_user)
    query = select(GameAction).where(GameAction.game_id == run.game_id)
    if before_seq is not None:
        query = query.where(GameAction.seq < before_seq)
    rows = (await db.execute(query.order_by(GameAction.seq.desc()).limit(limit))).scalars().all()
    return list(reversed(rows))


@router.get("/runs/{run_id}/log")
async def download_run_log(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full run log as a JSON file: run metadata, every action, and per-day metrics."""
    run, game = await _get_run(db, run_id, current_user)
    actions = (await db.execute(
        select(GameAction).where(GameAction.game_id == run.game_id).order_by(GameAction.seq)
    )).scalars().all()
    full_game = await game_engine.get_game(db, run.game_id, current_user.id)
    metrics = sorted(full_game.metrics, key=lambda m: m.day) if full_game else []
    body = {
        "run": _run_out(run, game).model_dump(mode="json"),
        "actions": [GameActionOut.model_validate(a).model_dump(mode="json") for a in actions],
        "metrics": [MetricResponse.model_validate(m).model_dump(mode="json") for m in metrics],
    }
    filename = f"agent-run-{run.id}.json"
    return Response(
        content=json.dumps(body, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/runs/{run_id}/cancel", response_model=AgentRunOut)
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run, game = await _get_run(db, run_id, current_user)
    if run.status not in ACTIVE_RUN_STATUSES:
        raise HTTPException(status_code=400, detail="Run is not active")
    if not agent_runner.cancel(run.id):
        # No live task (e.g. a different worker process) — close the row directly.
        run.status = AgentRunStatus.cancelled
        run.finished_at = datetime.utcnow()
        await db.commit()
    return _run_out(run, game)
