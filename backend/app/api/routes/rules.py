from fastapi import APIRouter

from app.schemas.rules import RulesOut
from app.services.rules import rules_payload

router = APIRouter()


@router.get("", response_model=RulesOut)
async def get_rules():
    """Public: the rule numbers (productivity, WIP, team, card catalog, ranks) the engine uses."""
    return rules_payload()
