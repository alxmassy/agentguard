"""Unit tests for the Decision Engine.

Tests the pure decision function per §15:
- BLOCK always wins (policy is absolute)
- Intent mismatch can only ESCALATE (ALLOW → REQUIRE_APPROVAL), never de-escalate
- Null intent works (LLM unavailable scenario)
- REQUIRE_HUMAN_APPROVAL passes through
"""
from __future__ import annotations

import pytest

from app.models import (
    Decision,
    IntentResult,
    PolicyVerdict,
    RiskAssessment,
    RiskFactors,
    RiskLevel,
)
from app.decision.engine import decide


# --- Fixtures ---

def _make_risk(level: RiskLevel = RiskLevel.HIGH, score: int = 10) -> RiskAssessment:
    """Helper to build a RiskAssessment."""
    return RiskAssessment(
        risk_level=level,
        risk_score=score,
        factors=RiskFactors(
            action_weight=3,
            environment_weight=4,
            blast_radius_weight=1,
            reversibility_weight=1,
            privilege_weight=1,
        ),
    )


def _make_policy(
    decision: Decision,
    reason: str = "Test reason",
    policy_id: str = "test-policy",
) -> PolicyVerdict:
    """Helper to build a PolicyVerdict."""
    return PolicyVerdict(
        decision=decision,
        reason=reason,
        policy_id=policy_id,
    )


def _make_intent(mismatch: bool = False) -> IntentResult:
    """Helper to build an IntentResult."""
    return IntentResult(
        intent="modify payment service",
        expected_environment="staging",
        observed_environment="production" if mismatch else "staging",
        mismatch=mismatch,
        confidence=0.9,
    )


# --- Tests ---


class TestBlockIsAbsolute:
    """Policy BLOCK must always produce BLOCK, regardless of risk or intent."""

    def test_block_with_no_intent(self):
        result = decide(_make_policy(Decision.BLOCK), _make_risk(), intent=None)
        assert result.decision == Decision.BLOCK

    def test_block_with_matching_intent(self):
        result = decide(
            _make_policy(Decision.BLOCK),
            _make_risk(),
            intent=_make_intent(mismatch=False),
        )
        assert result.decision == Decision.BLOCK

    def test_block_with_mismatched_intent(self):
        """Even if intent says mismatch, BLOCK stays BLOCK (doesn't escalate further)."""
        result = decide(
            _make_policy(Decision.BLOCK),
            _make_risk(),
            intent=_make_intent(mismatch=True),
        )
        assert result.decision == Decision.BLOCK

    def test_block_preserves_policy_id(self):
        result = decide(
            _make_policy(Decision.BLOCK, policy_id="prod-destroy-block"),
            _make_risk(),
        )
        assert result.policy_id == "prod-destroy-block"

    def test_block_preserves_reason(self):
        result = decide(
            _make_policy(Decision.BLOCK, reason="Destruction prohibited"),
            _make_risk(),
        )
        assert result.reason == "Destruction prohibited"


class TestIntentMismatchEscalation:
    """Intent mismatch can only ESCALATE (ALLOW → REQUIRE_APPROVAL), never de-escalate."""

    def test_allow_escalated_to_approval_on_mismatch(self):
        """ALLOW + mismatch → REQUIRE_HUMAN_APPROVAL."""
        result = decide(
            _make_policy(Decision.ALLOW),
            _make_risk(),
            intent=_make_intent(mismatch=True),
        )
        assert result.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_allow_stays_allow_without_mismatch(self):
        """ALLOW + no mismatch → ALLOW."""
        result = decide(
            _make_policy(Decision.ALLOW),
            _make_risk(),
            intent=_make_intent(mismatch=False),
        )
        assert result.decision == Decision.ALLOW

    def test_require_approval_stays_on_mismatch(self):
        """REQUIRE_APPROVAL + mismatch → still REQUIRE_APPROVAL (no double-escalation)."""
        result = decide(
            _make_policy(Decision.REQUIRE_HUMAN_APPROVAL),
            _make_risk(),
            intent=_make_intent(mismatch=True),
        )
        assert result.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_mismatch_reason_includes_environments(self):
        """Mismatch escalation reason should mention expected vs observed env."""
        result = decide(
            _make_policy(Decision.ALLOW),
            _make_risk(),
            intent=_make_intent(mismatch=True),
        )
        assert "staging" in result.reason
        assert "production" in result.reason


class TestNullIntent:
    """When LLM is unavailable, intent is None — system works on policy+risk only."""

    def test_allow_works_without_intent(self):
        result = decide(_make_policy(Decision.ALLOW), _make_risk(), intent=None)
        assert result.decision == Decision.ALLOW

    def test_require_approval_works_without_intent(self):
        result = decide(
            _make_policy(Decision.REQUIRE_HUMAN_APPROVAL),
            _make_risk(),
            intent=None,
        )
        assert result.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_block_works_without_intent(self):
        result = decide(_make_policy(Decision.BLOCK), _make_risk(), intent=None)
        assert result.decision == Decision.BLOCK


class TestRiskPassthrough:
    """Decision response must include risk information from the risk engine."""

    def test_risk_level_included(self):
        risk = _make_risk(RiskLevel.CRITICAL, score=20)
        result = decide(_make_policy(Decision.ALLOW), risk)
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.risk_score == 20

    def test_risk_factors_included(self):
        risk = _make_risk()
        result = decide(_make_policy(Decision.ALLOW), risk)
        assert result.risk_factors is not None
        assert result.risk_factors.action_weight == 3


class TestDecisionResponseCompleteness:
    """Every DecisionResponse must have all required fields."""

    def test_response_has_request_id(self):
        result = decide(_make_policy(Decision.ALLOW), _make_risk())
        assert result.request_id is not None
        assert result.request_id.startswith("AG-")

    def test_response_has_all_fields(self):
        result = decide(_make_policy(Decision.ALLOW), _make_risk())
        assert result.decision is not None
        assert result.reason is not None
        assert result.risk_level is not None
        assert result.risk_score is not None
        assert result.risk_factors is not None
