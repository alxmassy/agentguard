"""Action detail and execution result endpoints.

GET  /api/v1/actions/{id}         — full detail for one action
POST /api/v1/actions/{id}/execute — CLI reports execution result
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import repositories as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["actions"])


class ExecuteResultBody(BaseModel):
    exit_code: int
    stdout_meta: Optional[str] = None
    stderr_meta: Optional[str] = None


@router.get("/actions/{request_id}")
async def get_action(request_id: str):
    """Get full detail for a single action request.
    
    Returns the action_request row. Used by the dashboard Action Detail page.
    """
    action = repo.get_action_request(request_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action {request_id} not found")
    return action


@router.post("/actions/{request_id}/execute")
async def report_execution(request_id: str, body: ExecuteResultBody):
    """CLI reports the result of executing an approved command.
    
    Called after subprocess.run() completes. Completes the audit trail.
    """
    action = repo.get_action_request(request_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action {request_id} not found")

    try:
        repo.create_execution_record(
            request_id=request_id,
            exit_code=body.exit_code,
            stdout_meta=body.stdout_meta,
            stderr_meta=body.stderr_meta,
        )
        repo.append_audit_event(
            request_id=request_id,
            event_type="execution_completed",
            payload={"exit_code": body.exit_code},
        )
        logger.info("Execution recorded for %s (exit_code=%d)", request_id, body.exit_code)
        return {"ok": True}
    except Exception as e:
        logger.error("Error recording execution for %s: %s", request_id, e)
        raise HTTPException(status_code=500, detail=str(e))
