"""Audit trail events endpoint.

GET /api/v1/audit — query lifecycle audit events.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.db import repositories as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit")
async def list_audit_events(
    request_id: Optional[str] = Query(None, description="Filter by request ID (AG-xxxxxxxx)"),
    limit: int = Query(100, ge=1, le=500),
):
    """Retrieve audit events in chronological order."""
    try:
        events = repo.list_audit_events(request_id=request_id, limit=limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error("Error retrieving audit events: %s", e)
        return {"events": [], "count": 0}
