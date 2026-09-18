"""Unit tests for the Risk Engine.

Tests weighted risk scoring against the design doc §13.
Pure function tests — no HTTP, no database.
"""
from __future__ import annotations

import pytest

from app.models import (
    ActionRequest,
    ActionType,
    CommandInfo,
    ParsedAction,
    RequestContext,
    RiskLevel,
)
from app.risk.engine import assess_risk


def _make_request(
    tool: str,
    operation: str,
    action_type: ActionType,
    environment: str,
    is_destructive: bool = False,
    is_read_only: bool = False,
    flags: dict | None = None,
    raw_args: list[str] | None = None,
) -> ActionRequest:
    """Helper to build an ActionRequest for testing."""
    return ActionRequest(
        command=CommandInfo(raw=f"{tool} {operation}", argv=[tool, operation]),
        parsed_action=ParsedAction(
            tool=tool,
            operation=operation,
            action_type=action_type,
            is_destructive=is_destructive,
            is_read_only=is_read_only,
            flags=flags or {},
            raw_args=raw_args or [],
        ),
        context=RequestContext(
            project_id="test-project",
            environment=environment,
        ),
    )


class TestRiskScoring:
    """Test risk score computation."""

    def test_terraform_destroy_production_is_critical(self):
        """terraform destroy + production = score 20 → CRITICAL (§13 worked example)."""
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "production",
            is_destructive=True,
        )
        result = assess_risk(request)

        # Per §13: action=6 + env=4 + blast=5 + reversibility=5 + privilege=0 = 20
        assert result.risk_score == 20
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.factors.action_weight == 6
        assert result.factors.environment_weight == 4
        assert result.factors.blast_radius_weight == 5
        assert result.factors.reversibility_weight == 5
        assert result.factors.privilege_weight == 0

    def test_terraform_plan_staging_is_low(self):
        """terraform plan + staging = low risk."""
        request = _make_request(
            "terraform", "plan", ActionType.INFRASTRUCTURE_READ, "staging",
            is_read_only=True,
        )
        result = assess_risk(request)

        # action=0 + env=1 + blast=0 + reversibility=0 + privilege=0 = 1
        assert result.risk_score == 1
        assert result.risk_level == RiskLevel.LOW

    def test_terraform_apply_production_is_high(self):
        """terraform apply + production = high risk."""
        request = _make_request(
            "terraform", "apply", ActionType.INFRASTRUCTURE_MODIFY, "production",
        )
        result = assess_risk(request)

        # action=3 + env=4 + blast=3 + reversibility=1 + privilege=0 = 11
        assert result.risk_score == 11
        assert result.risk_level == RiskLevel.HIGH

    def test_terraform_plan_local_is_low(self):
        """terraform plan + local = minimal risk."""
        request = _make_request(
            "terraform", "plan", ActionType.INFRASTRUCTURE_READ, "local",
            is_read_only=True,
        )
        result = assess_risk(request)

        # action=0 + env=0 + blast=0 + reversibility=0 + privilege=0 = 0
        assert result.risk_score == 0
        assert result.risk_level == RiskLevel.LOW

    def test_auto_approve_adds_privilege_weight(self):
        """Using -auto-approve should add privilege weight."""
        request = _make_request(
            "terraform", "apply", ActionType.INFRASTRUCTURE_MODIFY, "production",
            flags={"-auto-approve": True},
        )
        result = assess_risk(request)

        assert result.factors.privilege_weight == 3
        # action=3 + env=4 + blast=3 + reversibility=1 + privilege=3 = 14
        assert result.risk_score == 14
        assert result.risk_level == RiskLevel.CRITICAL

    def test_database_destructive_production_is_critical(self):
        """DROP TABLE + production = critical risk."""
        request = _make_request(
            "psql", "query", ActionType.DATABASE_DESTRUCTIVE, "production",
            is_destructive=True,
        )
        result = assess_risk(request)

        # action=6 + env=4 + blast=5 + reversibility=5 + privilege=0 = 20
        assert result.risk_score == 20
        assert result.risk_level == RiskLevel.CRITICAL

    def test_database_read_production_is_medium(self):
        """SELECT + production = low-medium risk."""
        request = _make_request(
            "psql", "query", ActionType.DATABASE_READ, "production",
            is_read_only=True,
        )
        result = assess_risk(request)

        # action=0 + env=4 + blast=0 + reversibility=0 + privilege=0 = 4
        assert result.risk_score == 4
        assert result.risk_level == RiskLevel.MEDIUM


class TestRiskLevelThresholds:
    """Test the score-to-level mapping boundaries."""

    def test_low_boundary(self):
        """Score 3 should be LOW."""
        request = _make_request(
            "terraform", "apply", ActionType.INFRASTRUCTURE_MODIFY, "local",
        )
        result = assess_risk(request)
        # action=3 + env=0 + blast=3 + reversibility=1 = 7 → MEDIUM
        # Need a different combo for exactly 3
        # Actually let's just check the function directly
        from app.risk.engine import _score_to_level
        assert _score_to_level(3) == RiskLevel.LOW
        assert _score_to_level(4) == RiskLevel.MEDIUM

    def test_medium_boundary(self):
        from app.risk.engine import _score_to_level
        assert _score_to_level(7) == RiskLevel.MEDIUM
        assert _score_to_level(8) == RiskLevel.HIGH

    def test_high_boundary(self):
        from app.risk.engine import _score_to_level
        assert _score_to_level(12) == RiskLevel.HIGH
        assert _score_to_level(13) == RiskLevel.CRITICAL


class TestRiskFactorsExplainability:
    """Test that risk output includes all factor weights for explainability."""

    def test_all_factors_present(self):
        """Every RiskAssessment must include all factor weights."""
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "production",
        )
        result = assess_risk(request)

        # All factor fields must be present (not None)
        assert result.factors.action_weight is not None
        assert result.factors.environment_weight is not None
        assert result.factors.blast_radius_weight is not None
        assert result.factors.reversibility_weight is not None
        assert result.factors.privilege_weight is not None

        # Score must equal sum of factors
        total = (
            result.factors.action_weight
            + result.factors.environment_weight
            + result.factors.blast_radius_weight
            + result.factors.reversibility_weight
            + result.factors.privilege_weight
        )
        assert result.risk_score == total
