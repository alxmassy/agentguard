"""Repository functions — all database operations for AgentGuard.

All functions use the Supabase client from db.client.
The API layer calls these functions; it never accesses Supabase directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.client import get_db
from app.models import ActionRequest, DecisionResponse


# ---------------------------------------------------------------------------
# action_requests
# ---------------------------------------------------------------------------

def create_action_request(
    response: DecisionResponse,
    request: ActionRequest,
) -> None:
    """Persist an action request and its risk assessment.
    
    Called immediately after the Decision Engine produces a response.
    Inserts into action_requests (one row per evaluation).
    
    Args:
        response: The DecisionResponse from the Decision Engine.
        request: The original ActionRequest from the CLI.
    """
    db = get_db()

    # Upsert project record (ignore if exists)
    db.table("projects").upsert(
        {"id": request.context.project_id, "name": request.context.project_id},
        on_conflict="id",
    ).execute()

    # Insert action_request row
    db.table("action_requests").insert({
        "request_id": response.request_id,
        "user_id": request.context.user_id,
        "project_id": request.context.project_id,
        "agent_id": request.context.agent_id,
        "environment": request.context.environment,
        "original_task": request.context.original_task,
        "command": request.command.model_dump(),
        "parsed_action": request.parsed_action.model_dump(mode="json"),
        "decision": response.decision.value,
        "policy_id": response.policy_id,
        "risk_level": response.risk_level.value,
        "risk_score": response.risk_score,
        "risk_factors": response.risk_factors.model_dump(),
    }).execute()

    # Insert risk_assessment row (one-to-one)
    db.table("risk_assessments").insert({
        "request_id": response.request_id,
        "risk_level": response.risk_level.value,
        "risk_score": response.risk_score,
        "factors": response.risk_factors.model_dump(),
    }).execute()


def get_action_request(request_id: str) -> dict | None:
    """Fetch a full action request record by ID."""
    db = get_db()
    result = (
        db.table("action_requests")
        .select("*")
        .eq("request_id", request_id)
        .maybe_single()
        .execute()
    )
    return result.data


# ---------------------------------------------------------------------------
# approval_requests
# ---------------------------------------------------------------------------

def create_approval_request(request_id: str) -> str:
    """Create a pending approval request for an action.
    
    Args:
        request_id: The action_requests.request_id this approval is for.
    
    Returns:
        The new approval UUID as a string.
    """
    db = get_db()
    approval_id = str(uuid.uuid4())

    db.table("approval_requests").insert({
        "id": approval_id,
        "request_id": request_id,
        "status": "pending",
    }).execute()

    return approval_id


def get_approval(approval_id: str) -> dict | None:
    """Fetch an approval request by its UUID."""
    db = get_db()
    result = (
        db.table("approval_requests")
        .select("*, action_requests(*)")
        .eq("id", approval_id)
        .maybe_single()
        .execute()
    )
    return result.data


def list_approvals(status: str | None = None) -> list[dict]:
    """List approval requests, optionally filtered by status."""
    db = get_db()
    query = db.table("approval_requests").select("*, action_requests(*)")
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


def resolve_approval(
    approval_id: str,
    new_status: str,  # "approved" or "rejected"
    comment: str | None = None,
    approver_id: str | None = None,
) -> dict:
    """Resolve a pending approval request.
    
    Raises:
        ValueError: If the approval doesn't exist or is already resolved (409).
    
    Args:
        approval_id: UUID of the approval_requests row.
        new_status: 'approved' or 'rejected'.
        comment: Optional comment/reason from the approver.
        approver_id: Optional UUID of the approver user.
    
    Returns:
        The updated approval row.
    """
    db = get_db()

    # Fetch current state
    existing = get_approval(approval_id)
    if not existing:
        raise LookupError(f"Approval {approval_id} not found")

    if existing["status"] != "pending":
        raise ValueError(
            f"Approval {approval_id} is already {existing['status']} — cannot modify"
        )

    result = (
        db.table("approval_requests")
        .update({
            "status": new_status,
            "comment": comment,
            "approver_id": approver_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", approval_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ---------------------------------------------------------------------------
# execution_records
# ---------------------------------------------------------------------------

def create_execution_record(
    request_id: str,
    exit_code: int,
    stdout_meta: str | None,
    stderr_meta: str | None,
) -> None:
    """Record the result of executing an approved command.
    
    Args:
        request_id: The action_requests.request_id.
        exit_code: The subprocess exit code.
        stdout_meta: First 4KB of stdout (truncated).
        stderr_meta: First 4KB of stderr (truncated).
    """
    db = get_db()
    db.table("execution_records").insert({
        "request_id": request_id,
        "exit_code": exit_code,
        "stdout_meta": (stdout_meta or "")[:4096],
        "stderr_meta": (stderr_meta or "")[:4096],
    }).execute()


# ---------------------------------------------------------------------------
# audit_events
# ---------------------------------------------------------------------------

def append_audit_event(
    request_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a lifecycle event to the audit trail.
    
    event_type values: request_created, decision_made, approval_requested,
    approval_resolved, execution_started, execution_completed
    
    Args:
        request_id: The action_requests.request_id.
        event_type: The event type string.
        payload: Optional additional data for this event.
    """
    db = get_db()
    db.table("audit_events").insert({
        "request_id": request_id,
        "event_type": event_type,
        "payload": payload or {},
    }).execute()
