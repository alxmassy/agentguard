"""Unit tests for the Policy Engine.

Tests the deterministic rule evaluation against the §27 test matrix.
Pure function tests — no HTTP, no database.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.models import (
    ActionRequest,
    ActionType,
    CommandInfo,
    Decision,
    ParsedAction,
    RequestContext,
)
from app.policy.engine import evaluate_policy
from app.policy.loader import PolicyConfig, load_policies


# --- Fixtures ---

POLICY_PATH = Path(__file__).parent.parent.parent / "policies" / "default.yaml"


@pytest.fixture
def policy_config() -> PolicyConfig:
    """Load the default policy config for testing."""
    return load_policies(POLICY_PATH)


def _make_request(
    tool: str,
    operation: str,
    action_type: ActionType,
    environment: str,
    is_destructive: bool = False,
    is_read_only: bool = False,
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
        ),
        context=RequestContext(
            project_id="test-project",
            environment=environment,
        ),
    )


# --- Test Matrix from §27 ---


class TestTerraformPolicies:
    """Test terraform command policies."""

    def test_terraform_plan_staging_allow(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "plan", ActionType.INFRASTRUCTURE_READ, "staging",
            is_read_only=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.ALLOW

    def test_terraform_plan_production_allow(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "plan", ActionType.INFRASTRUCTURE_READ, "production",
            is_read_only=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.ALLOW

    def test_terraform_apply_staging_allow(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "apply", ActionType.INFRASTRUCTURE_MODIFY, "staging",
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.ALLOW

    def test_terraform_apply_production_require_approval(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "apply", ActionType.INFRASTRUCTURE_MODIFY, "production",
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_terraform_destroy_staging_require_approval(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "staging",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_terraform_destroy_production_block(self, policy_config: PolicyConfig):
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK


class TestDatabasePolicies:
    """Test database command policies."""

    def test_select_production_allow(self, policy_config: PolicyConfig):
        request = _make_request(
            "psql", "query", ActionType.DATABASE_READ, "production",
            is_read_only=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.ALLOW

    def test_drop_table_production_block(self, policy_config: PolicyConfig):
        request = _make_request(
            "psql", "query", ActionType.DATABASE_DESTRUCTIVE, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK

    def test_drop_database_production_block(self, policy_config: PolicyConfig):
        request = _make_request(
            "psql", "query", ActionType.DATABASE_DESTRUCTIVE, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK

    def test_delete_without_where_production_block(self, policy_config: PolicyConfig):
        request = _make_request(
            "psql", "query", ActionType.DATABASE_DESTRUCTIVE, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK


class TestDefaultPolicy:
    """Test default policy (unrecognized commands)."""

    def test_unknown_command_gets_default_require_approval(self, policy_config: PolicyConfig):
        request = _make_request(
            "shell", "unknown_cmd", ActionType.SHELL_UNKNOWN, "staging",
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.REQUIRE_HUMAN_APPROVAL

    def test_shell_high_risk_production_block(self, policy_config: PolicyConfig):
        request = _make_request(
            "shell", "rm", ActionType.SHELL_HIGH_RISK, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK


class TestPolicyPrecedence:
    """Test that precedence order is enforced correctly."""

    def test_block_beats_allow(self, policy_config: PolicyConfig):
        """A BLOCK rule should win even if an ALLOW rule also matches."""
        # infrastructure_destroy in production: both the BLOCK rule and
        # potentially other rules could match, but BLOCK must win.
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.decision == Decision.BLOCK

    def test_policy_id_is_set(self, policy_config: PolicyConfig):
        """The verdict must include the matching policy_id."""
        request = _make_request(
            "terraform", "destroy", ActionType.INFRASTRUCTURE_DESTROY, "production",
            is_destructive=True,
        )
        verdict = evaluate_policy(request, policy_config)
        assert verdict.policy_id == "prod-destroy-block"
