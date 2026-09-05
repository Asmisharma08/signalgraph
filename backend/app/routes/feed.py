"""
SignalGraph — Feed Route (Milestone 6, + Milestone 11's brief refresh)
========================================================================
Endpoint:
  GET /api/feed — returns the personalized relevance feed for the calling user.

Response shape matches Validation and Acceptance in the ExecPlan.

Milestone 11: after build_feed() returns (already carrying whatever
market_brief is currently cached — see app/relevance/feed.py), this
handler compares the response's items hash against the cache and, if
it differs, schedules a FastAPI BackgroundTasks call to regenerate the
brief for the *next* poll to pick up. The AI call never sits in this
request's critical path.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from app.auth import get_current_user_id
from app.ai.brief import generate_brief
from app.relevance.feed import build_feed, compute_items_hash, mark_seen, _brief_cache

router = APIRouter(prefix="/api", tags=["feed"])


def _regenerate_brief(user_id: str, items: list[dict], items_hash: str) -> None:
    brief = generate_brief(items)
    _brief_cache[user_id] = {"brief": brief, "items_hash": items_hash}


@router.get("/feed")
async def get_feed(background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user_id)):
    result = build_feed(user_id)

    items_hash = compute_items_hash(result["items"])
    cached = _brief_cache.get(user_id)
    if cached is None or cached["items_hash"] != items_hash:
        background_tasks.add_task(_regenerate_brief, user_id, result["items"], items_hash)

    return result


@router.post("/feed/seen/{instrument_id}", status_code=204)
async def post_mark_seen(instrument_id: str, user_id: str = Depends(get_current_user_id)):
    mark_seen(user_id, instrument_id)
    return None
