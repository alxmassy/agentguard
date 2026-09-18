"""Approval workflow endpoints.

GET  /api/v1/approvals          — list approvals (filterable by status)
GET  /api/v1/approvals/{id}     — single approval detail
POST /api/v1/approvals/{id}/approve — approve a pending request
POST /api/v1/approvals/{id}/reject  — reject a pending request

No auth in Milestone 2. Auth added in Milestone 3.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import repositories as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["approvals"])


class ApproveBody(BaseModel):
    comment: Optional[str] = None


class RejectBody(BaseModel):
    reason: str


@router.get("/approvals")
async def list_approvals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected")
):
    """List approval requests, optionally filtered by status."""
    try:
        approvals = repo.list_approvals(status=status)
        return {"approvals": approvals, "count": len(approvals)}
    except Exception as e:
        logger.error("Error listing approvals: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/{approval_id}")
async def get_approval(approval_id: str):
    """Get a single approval request by ID.
    
    Used by the CLI polling loop to check current status.
    """
    approval = repo.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")
    return approval


@router.post("/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, body: ApproveBody):
    """Approve a pending action request.
    
    Returns 409 Conflict if already resolved (prevents double-execution).
    """
    try:
        result = repo.resolve_approval(
            approval_id=approval_id,
            new_status="approved",
            comment=body.comment,
        )
        repo.append_audit_event(
            request_id=result.get("request_id", ""),
            event_type="approval_resolved",
            payload={"status": "approved", "comment": body.comment},
        )
        logger.info("Approval %s approved", approval_id)
        return {"ok": True, "approval_id": approval_id, "status": "approved"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Error approving %s: %s", approval_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, body: RejectBody):
    """Reject a pending action request.
    
    Returns 409 Conflict if already resolved.
    """
    try:
        result = repo.resolve_approval(
            approval_id=approval_id,
            new_status="rejected",
            comment=body.reason,
        )
        repo.append_audit_event(
            request_id=result.get("request_id", ""),
            event_type="approval_resolved",
            payload={"status": "rejected", "reason": body.reason},
        )
        logger.info("Approval %s rejected", approval_id)
        return {"ok": True, "approval_id": approval_id, "status": "rejected"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Error rejecting %s: %s", approval_id, e)
        raise HTTPException(status_code=500, detail=str(e))
