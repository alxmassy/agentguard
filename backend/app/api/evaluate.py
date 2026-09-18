"""POST /api/v1/actions/evaluate — the core evaluation endpoint.

Orchestrates: re-validate → policy → risk → decision → persist → respond.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.db import repositories as repo
from app.decision.engine import decide
from app.models import ActionRequest, Decision, DecisionResponse
from app.parser.validator import validate_and_reclassify
from app.policy.engine import evaluate_policy
from app.risk.engine import assess_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["actions"])


@router.post("/actions/evaluate", response_model=DecisionResponse)
async def evaluate_action(
    request_body: ActionRequest,
    request: Request,
) -> DecisionResponse:
    """Evaluate a command for safety, persist the decision, return response.
    
    Pipeline:
        1. Server-side re-parse/validate (never trust client classification)
        2. Evaluate against policy rules
        3. Compute risk score
        4. Combine via Decision Engine
        5. Persist to database
        6. If REQUIRE_HUMAN_APPROVAL, create approval request
        7. Return decision to CLI
    """
    policy_config = request.app.state.policy_config
    db_available = getattr(request.app.state, "db_available", False)

    # 1. Server-side re-validation (security boundary)
    validated_request = validate_and_reclassify(request_body)

    logger.info(
        "Evaluating: tool=%s operation=%s env=%s action_type=%s",
        validated_request.parsed_action.tool,
        validated_request.parsed_action.operation,
        validated_request.context.environment,
        validated_request.parsed_action.action_type,
    )

    # 2. Policy evaluation
    policy_verdict = evaluate_policy(validated_request, policy_config)

    # 3. Risk assessment
    risk = assess_risk(validated_request)

    # 4. Decision
    response = decide(
        policy_verdict=policy_verdict,
        risk=risk,
        intent=None,  # LLM intent layer — Milestone 5
    )

    logger.info(
        "Decision: %s (policy=%s, risk=%s/%d)",
        response.decision,
        response.policy_id,
        response.risk_level,
        response.risk_score,
    )

    # 5. Persist to DB (if available — graceful degradation if DB is down)
    if db_available:
        try:
            repo.create_action_request(response=response, request=validated_request)
            repo.append_audit_event(
                request_id=response.request_id,
                event_type="decision_made",
                payload={
                    "decision": response.decision.value,
                    "policy_id": response.policy_id,
                    "risk_level": response.risk_level.value,
                    "risk_score": response.risk_score,
                },
            )

            # 6. Create approval request if needed
            if response.decision == Decision.REQUIRE_HUMAN_APPROVAL:
                approval_id = repo.create_approval_request(response.request_id)
                repo.append_audit_event(
                    request_id=response.request_id,
                    event_type="approval_requested",
                    payload={"approval_id": approval_id},
                )
                # Attach approval_id to response so CLI can poll
                response = response.model_copy(update={"approval_id": approval_id})

        except Exception as e:
            # DB write failure — log but don't fail the evaluation
            # The safety decision is already made; audit loss is bad but not a security failure
            logger.error("DB write failed (non-fatal): %s", e)
    else:
        logger.warning("DB not available — evaluation result not persisted")

    return response
