"""Stats and dashboard summary endpoint.

GET /api/v1/stats — aggregate counts for overview metrics.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter

from app.db import repositories as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats")
async def get_stats():
    """Retrieve aggregate counts and recent activity for the dashboard overview."""
    try:
        return repo.get_stats()
    except Exception as e:
        logger.error("Error computing stats: %s", e)
        return {
            "total_evaluations": 0,
            "allowed_count": 0,
            "blocked_count": 0,
            "require_approval_count": 0,
            "pending_approvals": 0,
            "critical_risk_count": 0,
            "high_risk_count": 0,
            "recent_actions": [],
        }
