"""Demo simulation and seed endpoint for presentations.

POST /api/v1/demo/seed — seed sample evaluated actions for demonstration.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter

from app.db import repositories as repo
from app.models import (
    ActionRequest,
    ActionType,
    CommandInfo,
    Decision,
    DecisionResponse,
    ParsedAction,
    RequestContext,
    RiskFactors,
    RiskLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo_data():
    """Seed sample data to demonstrate the system during college presentation."""
    scenarios = [
        # Scenario 1: Allowed plan
        (
            CommandInfo(raw="terraform plan", argv=["terraform", "plan"]),
            ParsedAction(
                tool="terraform",
                operation="plan",
                action_type=ActionType.INFRASTRUCTURE_READ,
                is_read_only=True,
            ),
            RequestContext(
                agent_id="claude-code",
                project_id="payment-service",
                environment="staging",
                original_task="Inspect planned infrastructure changes",
            ),
            DecisionResponse(
                request_id="AG-1001",
                decision=Decision.ALLOW,
                reason="Staging infrastructure reads are allowed",
                policy_id="staging-plan-allow",
                risk_level=RiskLevel.LOW,
                risk_score=1,
                risk_factors=RiskFactors(action_weight=0, environment_weight=1, blast_radius_weight=0, reversibility_weight=0, privilege_weight=0),
            ),
            0,
            "Plan: 2 to add, 0 to change, 0 to destroy.",
        ),
        # Scenario 2: Blocked destroy in production
        (
            CommandInfo(raw="terraform destroy -auto-approve", argv=["terraform", "destroy", "-auto-approve"]),
            ParsedAction(
                tool="terraform",
                operation="destroy",
                action_type=ActionType.INFRASTRUCTURE_DESTROY,
                is_destructive=True,
                flags={"-auto-approve": True},
            ),
            RequestContext(
                agent_id="claude-code",
                project_id="payment-service",
                environment="production",
                original_task="Clean up unused instances",
            ),
            DecisionResponse(
                request_id="AG-1002",
                decision=Decision.BLOCK,
                reason="Production infrastructure destruction is prohibited",
                policy_id="prod-destroy-block",
                risk_level=RiskLevel.CRITICAL,
                risk_score=20,
                risk_factors=RiskFactors(action_weight=6, environment_weight=4, blast_radius_weight=5, reversibility_weight=5, privilege_weight=0),
            ),
            None,
            None,
        ),
        # Scenario 3: Blocked destructive database command in production
        (
            CommandInfo(raw="psql -d production -c 'DROP TABLE users CASCADE;'", argv=["psql", "-d", "production", "-c", "DROP TABLE users CASCADE;"]),
            ParsedAction(
                tool="psql",
                operation="query",
                action_type=ActionType.DATABASE_DESTRUCTIVE,
                is_destructive=True,
            ),
            RequestContext(
                agent_id="claude-code",
                project_id="payment-service",
                environment="production",
                original_task="Reset database schema",
            ),
            DecisionResponse(
                request_id="AG-1003",
                decision=Decision.BLOCK,
                reason="Production destructive database operations are prohibited",
                policy_id="prod-db-drop-block",
                risk_level=RiskLevel.CRITICAL,
                risk_score=20,
                risk_factors=RiskFactors(action_weight=6, environment_weight=4, blast_radius_weight=5, reversibility_weight=5, privilege_weight=0),
            ),
            None,
            None,
        ),
        # Scenario 4: Pending human approval
        (
            CommandInfo(raw="terraform apply -auto-approve", argv=["terraform", "apply", "-auto-approve"]),
            ParsedAction(
                tool="terraform",
                operation="apply",
                action_type=ActionType.INFRASTRUCTURE_MODIFY,
                is_destructive=False,
                flags={"-auto-approve": True},
            ),
            RequestContext(
                agent_id="claude-code",
                project_id="payment-service",
                environment="production",
                original_task="Deploy database replica to production",
            ),
            DecisionResponse(
                request_id="AG-1004",
                decision=Decision.REQUIRE_HUMAN_APPROVAL,
                reason="Production infrastructure modification requires approval",
                policy_id="prod-apply-approval",
                risk_level=RiskLevel.HIGH,
                risk_score=11,
                risk_factors=RiskFactors(action_weight=3, environment_weight=4, blast_radius_weight=3, reversibility_weight=1, privilege_weight=0),
            ),
            None,
            None,
        ),
    ]

    for cmd, action, ctx, resp, exit_code, stdout in scenarios:
        req = ActionRequest(command=cmd, parsed_action=action, context=ctx)
        repo.append_audit_event(
            request_id=resp.request_id,
            event_type="request_created",
            payload={"command": cmd.raw, "environment": ctx.environment, "agent_id": ctx.agent_id},
        )
        repo.create_action_request(response=resp, request=req)
        repo.append_audit_event(
            request_id=resp.request_id,
            event_type="decision_made",
            payload={"decision": resp.decision.value, "policy_id": resp.policy_id, "risk_level": resp.risk_level.value},
        )
        if resp.decision == Decision.REQUIRE_HUMAN_APPROVAL:
            app_id = repo.create_approval_request(resp.request_id)
            repo.append_audit_event(
                request_id=resp.request_id,
                event_type="approval_requested",
                payload={"approval_id": app_id},
            )
        if exit_code is not None:
            repo.create_execution_record(resp.request_id, exit_code, stdout, "")
            repo.append_audit_event(
                request_id=resp.request_id,
                event_type="execution_completed",
                payload={"exit_code": exit_code},
            )

    return {"ok": True, "message": "Demo data successfully seeded!"}
