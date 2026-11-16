"""Repository functions — all database operations for AgentGuard.

Seamlessly supports both Supabase (PostgreSQL) and local SQLite.
All JSON fields are transparently handled.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.client import get_client_type, get_db, get_sqlite_conn
from app.models import ActionRequest, DecisionResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(val: Any) -> Any:
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def _row_to_action(row: dict) -> dict:
    data = dict(row)
    data["command"] = _parse_json(data.get("command"))
    data["parsed_action"] = _parse_json(data.get("parsed_action"))
    data["risk_factors"] = _parse_json(data.get("risk_factors"))
    return data


# ---------------------------------------------------------------------------
# action_requests
# ---------------------------------------------------------------------------

def create_action_request(
    response: DecisionResponse,
    request: ActionRequest,
) -> None:
    """Persist an action request and its risk assessment."""
    if get_client_type() == "supabase":
        db = get_db()
        db.table("projects").upsert(
            {"id": request.context.project_id, "name": request.context.project_id},
            on_conflict="id",
        ).execute()

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

        db.table("risk_assessments").insert({
            "request_id": response.request_id,
            "risk_level": response.risk_level.value,
            "risk_score": response.risk_score,
            "factors": response.risk_factors.model_dump(),
        }).execute()
        return

    # SQLite
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO projects (id, name) VALUES (?, ?)",
        (request.context.project_id, request.context.project_id),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO action_requests (
            request_id, user_id, project_id, agent_id, environment,
            original_task, command, parsed_action, decision, policy_id,
            risk_level, risk_score, risk_factors, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            response.request_id,
            request.context.user_id,
            request.context.project_id,
            request.context.agent_id,
            request.context.environment,
            request.context.original_task,
            json.dumps(request.command.model_dump()),
            json.dumps(request.parsed_action.model_dump(mode="json")),
            response.decision.value,
            response.policy_id,
            response.risk_level.value,
            response.risk_score,
            json.dumps(response.risk_factors.model_dump()),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO risk_assessments (
            id, request_id, risk_level, risk_score, factors, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            response.request_id,
            response.risk_level.value,
            response.risk_score,
            json.dumps(response.risk_factors.model_dump()),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_action_request(request_id: str) -> dict | None:
    """Fetch a full action request record by ID."""
    if get_client_type() == "supabase":
        db = get_db()
        result = (
            db.table("action_requests")
            .select("*")
            .eq("request_id", request_id)
            .maybe_single()
            .execute()
        )
        return _row_to_action(result.data) if result.data else None

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM action_requests WHERE request_id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_action(dict(row)) if row else None


def list_actions(
    environment: str | None = None,
    decision: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List action requests with optional filters and total count."""
    if get_client_type() == "supabase":
        db = get_db()
        q = db.table("action_requests").select("*", count="exact")
        if environment and environment != "all":
            q = q.eq("environment", environment)
        if decision and decision != "all":
            q = q.eq("decision", decision)
        res = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        actions = [_row_to_action(r) for r in (res.data or [])]
        total = res.count or len(actions)
        return actions, total

    conn = get_sqlite_conn()
    cur = conn.cursor()
    conditions = []
    params: list[Any] = []
    if environment and environment != "all":
        conditions.append("environment = ?")
        params.append(environment)
    if decision and decision != "all":
        conditions.append("decision = ?")
        params.append(decision)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cur.execute(f"SELECT COUNT(*) as cnt FROM action_requests {where_clause}", params)
    total = cur.fetchone()["cnt"]

    query = f"SELECT * FROM action_requests {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    cur.execute(query, params + [limit, offset])
    rows = cur.fetchall()
    conn.close()
    return [_row_to_action(dict(r)) for r in rows], total


# ---------------------------------------------------------------------------
# approval_requests
# ---------------------------------------------------------------------------

def create_approval_request(request_id: str) -> str:
    """Create a pending approval request for an action."""
    approval_id = str(uuid.uuid4())
    if get_client_type() == "supabase":
        db = get_db()
        db.table("approval_requests").insert({
            "id": approval_id,
            "request_id": request_id,
            "status": "pending",
        }).execute()
        return approval_id

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO approval_requests (id, request_id, status, created_at)
        VALUES (?, ?, 'pending', ?)
        """,
        (approval_id, request_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return approval_id


def get_approval(approval_id: str) -> dict | None:
    """Fetch an approval request by its UUID."""
    if get_client_type() == "supabase":
        db = get_db()
        result = (
            db.table("approval_requests")
            .select("*, action_requests(*)")
            .eq("id", approval_id)
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        data = dict(result.data)
        if "action_requests" in data and data["action_requests"]:
            data["action_requests"] = _row_to_action(data["action_requests"])
        return data

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM approval_requests WHERE id = ?", (approval_id,))
    app_row = cur.fetchone()
    if not app_row:
        conn.close()
        return None

    data = dict(app_row)
    cur.execute("SELECT * FROM action_requests WHERE request_id = ?", (data["request_id"],))
    action_row = cur.fetchone()
    conn.close()

    data["action_requests"] = _row_to_action(dict(action_row)) if action_row else None
    return data


def list_approvals(status: str | None = None) -> list[dict]:
    """List approval requests, optionally filtered by status."""
    if get_client_type() == "supabase":
        db = get_db()
        query = db.table("approval_requests").select("*, action_requests(*)")
        if status and status != "all":
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).execute()
        items = []
        for r in (result.data or []):
            item = dict(r)
            if "action_requests" in item and item["action_requests"]:
                item["action_requests"] = _row_to_action(item["action_requests"])
            items.append(item)
        return items

    conn = get_sqlite_conn()
    cur = conn.cursor()
    if status and status != "all":
        cur.execute(
            """
            SELECT ap.*, ar.request_id as ar_id, ar.environment, ar.project_id,
                   ar.agent_id, ar.original_task, ar.command, ar.parsed_action,
                   ar.decision, ar.policy_id, ar.risk_level, ar.risk_score,
                   ar.risk_factors, ar.created_at as ar_created_at
            FROM approval_requests ap
            LEFT JOIN action_requests ar ON ap.request_id = ar.request_id
            WHERE ap.status = ?
            ORDER BY ap.created_at DESC
            """,
            (status,),
        )
    else:
        cur.execute(
            """
            SELECT ap.*, ar.request_id as ar_id, ar.environment, ar.project_id,
                   ar.agent_id, ar.original_task, ar.command, ar.parsed_action,
                   ar.decision, ar.policy_id, ar.risk_level, ar.risk_score,
                   ar.risk_factors, ar.created_at as ar_created_at
            FROM approval_requests ap
            LEFT JOIN action_requests ar ON ap.request_id = ar.request_id
            ORDER BY ap.created_at DESC
            """
        )
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        row_dict = dict(r)
        action_data = None
        if row_dict.get("ar_id"):
            action_data = {
                "request_id": row_dict["ar_id"],
                "environment": row_dict["environment"],
                "project_id": row_dict["project_id"],
                "agent_id": row_dict["agent_id"],
                "original_task": row_dict["original_task"],
                "command": _parse_json(row_dict["command"]),
                "parsed_action": _parse_json(row_dict["parsed_action"]),
                "decision": row_dict["decision"],
                "policy_id": row_dict["policy_id"],
                "risk_level": row_dict["risk_level"],
                "risk_score": row_dict["risk_score"],
                "risk_factors": _parse_json(row_dict["risk_factors"]),
                "created_at": row_dict["ar_created_at"],
            }
        results.append({
            "id": row_dict["id"],
            "request_id": row_dict["request_id"],
            "status": row_dict["status"],
            "comment": row_dict["comment"],
            "approver_id": row_dict["approver_id"],
            "created_at": row_dict["created_at"],
            "resolved_at": row_dict["resolved_at"],
            "action_requests": action_data,
        })
    return results


def resolve_approval(
    approval_id: str,
    new_status: str,  # "approved" or "rejected"
    comment: str | None = None,
    approver_id: str | None = None,
) -> dict:
    """Resolve a pending approval request atomically."""
    resolved_at = datetime.now(timezone.utc).isoformat()

    if get_client_type() == "supabase":
        db = get_db()
        existing = get_approval(approval_id)
        if not existing:
            raise LookupError(f"Approval {approval_id} not found")
        if existing["status"] != "pending":
            raise ValueError(f"Approval {approval_id} is already {existing['status']}")

        result = (
            db.table("approval_requests")
            .update({
                "status": new_status,
                "comment": comment,
                "approver_id": approver_id,
                "resolved_at": resolved_at,
            })
            .eq("id", approval_id)
            .eq("status", "pending")
            .execute()
        )
        if not result.data:
            raise ValueError(f"Approval {approval_id} was resolved by another process.")
        return result.data[0]

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM approval_requests WHERE id = ?", (approval_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise LookupError(f"Approval {approval_id} not found")
    if row["status"] != "pending":
        conn.close()
        raise ValueError(f"Approval {approval_id} is already {row['status']}")

    cur.execute(
        """
        UPDATE approval_requests
        SET status = ?, comment = ?, approver_id = ?, resolved_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (new_status, comment, approver_id, resolved_at, approval_id),
    )
    if cur.rowcount == 0:
        conn.close()
        raise ValueError(f"Approval {approval_id} was resolved concurrently.")

    conn.commit()
    cur.execute("SELECT * FROM approval_requests WHERE id = ?", (approval_id,))
    updated = dict(cur.fetchone())
    conn.close()
    return updated


# ---------------------------------------------------------------------------
# execution_records
# ---------------------------------------------------------------------------

def create_execution_record(
    request_id: str,
    exit_code: int,
    stdout_meta: str | None,
    stderr_meta: str | None,
) -> None:
    """Record execution outcome."""
    if get_client_type() == "supabase":
        db = get_db()
        db.table("execution_records").insert({
            "request_id": request_id,
            "exit_code": exit_code,
            "stdout_meta": (stdout_meta or "")[:4096],
            "stderr_meta": (stderr_meta or "")[:4096],
        }).execute()
        return

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO execution_records (
            id, request_id, exit_code, stdout_meta, stderr_meta, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            request_id,
            exit_code,
            (stdout_meta or "")[:4096],
            (stderr_meta or "")[:4096],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# audit_events
# ---------------------------------------------------------------------------

def append_audit_event(
    request_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a lifecycle event to the audit trail."""
    payload_data = payload or {}
    if get_client_type() == "supabase":
        db = get_db()
        db.table("audit_events").insert({
            "request_id": request_id,
            "event_type": event_type,
            "payload": payload_data,
        }).execute()
        return

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_events (id, request_id, event_type, payload, occurred_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            request_id,
            event_type,
            json.dumps(payload_data),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def list_audit_events(request_id: str | None = None, limit: int = 100) -> list[dict]:
    """List audit events."""
    if get_client_type() == "supabase":
        db = get_db()
        q = db.table("audit_events").select("*")
        if request_id:
            q = q.eq("request_id", request_id)
        res = q.order("occurred_at", desc=True).limit(limit).execute()
        return [dict(r, payload=_parse_json(r.get("payload"))) for r in (res.data or [])]

    conn = get_sqlite_conn()
    cur = conn.cursor()
    if request_id:
        cur.execute(
            "SELECT * FROM audit_events WHERE request_id = ? ORDER BY occurred_at DESC LIMIT ?",
            (request_id, limit),
        )
    else:
        cur.execute("SELECT * FROM audit_events ORDER BY occurred_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r, payload=_parse_json(r["payload"])) for r in rows]


# ---------------------------------------------------------------------------
# stats & aggregates
# ---------------------------------------------------------------------------

def get_stats() -> dict[str, Any]:
    """Compute aggregate dashboard metrics."""
    if get_client_type() == "supabase":
        db = get_db()
        actions = db.table("action_requests").select("decision, risk_level").execute().data or []
        pending = db.table("approval_requests").select("id").eq("status", "pending").execute().data or []
        recent = db.table("action_requests").select("*").order("created_at", desc=True).limit(5).execute().data or []

        total = len(actions)
        allowed = sum(1 for a in actions if a.get("decision") == "ALLOW")
        blocked = sum(1 for a in actions if a.get("decision") == "BLOCK")
        req_approval = sum(1 for a in actions if a.get("decision") == "REQUIRE_HUMAN_APPROVAL")
        critical = sum(1 for a in actions if a.get("risk_level") == "CRITICAL")
        high = sum(1 for a in actions if a.get("risk_level") == "HIGH")

        return {
            "total_evaluations": total,
            "allowed_count": allowed,
            "blocked_count": blocked,
            "require_approval_count": req_approval,
            "pending_approvals": len(pending),
            "critical_risk_count": critical,
            "high_risk_count": high,
            "recent_actions": [_row_to_action(r) for r in recent],
        }

    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT decision, risk_level FROM action_requests")
    rows = cur.fetchall()
    total = len(rows)
    allowed = sum(1 for r in rows if r["decision"] == "ALLOW")
    blocked = sum(1 for r in rows if r["decision"] == "BLOCK")
    req_approval = sum(1 for r in rows if r["decision"] == "REQUIRE_HUMAN_APPROVAL")
    critical = sum(1 for r in rows if r["risk_level"] == "CRITICAL")
    high = sum(1 for r in rows if r["risk_level"] == "HIGH")

    cur.execute("SELECT COUNT(*) as pending_cnt FROM approval_requests WHERE status = 'pending'")
    pending_cnt = cur.fetchone()["pending_cnt"]

    cur.execute("SELECT * FROM action_requests ORDER BY created_at DESC LIMIT 5")
    recent_rows = cur.fetchall()
    conn.close()

    return {
        "total_evaluations": total,
        "allowed_count": allowed,
        "blocked_count": blocked,
        "require_approval_count": req_approval,
        "pending_approvals": pending_cnt,
        "critical_risk_count": critical,
        "high_risk_count": high,
        "recent_actions": [_row_to_action(dict(r)) for r in recent_rows],
    }
