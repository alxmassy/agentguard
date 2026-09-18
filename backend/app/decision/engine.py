"""Decision Engine — pure function combining policy, risk, and intent.

Hard constraint: the LLM/intent layer can NEVER produce or override ALLOW/BLOCK.
It can only ESCALATE (turn ALLOW → REQUIRE_HUMAN_APPROVAL on mismatch).
Policy BLOCK is absolute and cannot be overridden by anything.

This function is deliberately simple and must remain a pure function with no I/O.
"""
from __future__ import annotations

from app.models import (
    Decision,
    DecisionResponse,
    IntentResult,
    PolicyVerdict,
    RiskAssessment,
)


def decide(
    policy_verdict: PolicyVerdict,
    risk: RiskAssessment,
    intent: IntentResult | None = None,
) -> DecisionResponse:
    """Combine policy verdict, risk assessment, and optional intent into a final decision.
    
    Precedence:
        1. Policy BLOCK → always BLOCK (absolute, nothing overrides)
        2. Intent mismatch + policy ALLOW → escalate to REQUIRE_HUMAN_APPROVAL
        3. Policy REQUIRE_HUMAN_APPROVAL → REQUIRE_HUMAN_APPROVAL
        4. Policy ALLOW → ALLOW
    
    Args:
        policy_verdict: Output of the policy engine (deterministic).
        risk: Output of the risk engine (deterministic).
        intent: Output of the LLM intent layer (advisory, optional).
        
    Returns:
        DecisionResponse ready to send to the CLI.
    """
    # 1. Policy BLOCK is absolute
    if policy_verdict.decision == Decision.BLOCK:
        return DecisionResponse(
            decision=Decision.BLOCK,
            reason=policy_verdict.reason,
            policy_id=policy_verdict.policy_id,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.factors,
        )

    # 2. Intent mismatch can only ESCALATE, never de-escalate
    if (
        intent is not None
        and intent.mismatch
        and policy_verdict.decision == Decision.ALLOW
    ):
        reason = (
            f"Task/action mismatch: expected {intent.expected_environment}, "
            f"observed {intent.observed_environment}"
        )
        return DecisionResponse(
            decision=Decision.REQUIRE_HUMAN_APPROVAL,
            reason=reason,
            policy_id=policy_verdict.policy_id,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.factors,
        )

    # 3. Policy REQUIRE_HUMAN_APPROVAL
    if policy_verdict.decision == Decision.REQUIRE_HUMAN_APPROVAL:
        return DecisionResponse(
            decision=Decision.REQUIRE_HUMAN_APPROVAL,
            reason=policy_verdict.reason,
            policy_id=policy_verdict.policy_id,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.factors,
        )

    # 4. Policy ALLOW
    return DecisionResponse(
        decision=Decision.ALLOW,
        reason=policy_verdict.reason,
        policy_id=policy_verdict.policy_id,
        risk_level=risk.risk_level,
        risk_score=risk.risk_score,
        risk_factors=risk.factors,
    )
