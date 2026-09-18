"""Integration tests for the /api/v1/actions/evaluate endpoint.

Tests the full pipeline via HTTP: request → re-validate → policy → risk → decide → respond.
Uses FastAPI TestClient — no real server needed.

Covers the §27 test matrix end-to-end.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


def _make_evaluate_payload(
    tool: str,
    operation: str,
    action_type: str,
    environment: str,
    is_destructive: bool = False,
    is_read_only: bool = False,
    raw_command: str | None = None,
    argv: list[str] | None = None,
) -> dict:
    """Build a JSON payload for POST /api/v1/actions/evaluate."""
    if raw_command is None:
        raw_command = f"{tool} {operation}"
    if argv is None:
        argv = [tool, operation]

    return {
        "command": {
            "raw": raw_command,
            "argv": argv,
        },
        "parsed_action": {
            "tool": tool,
            "operation": operation,
            "raw_args": [],
            "flags": {},
            "action_type": action_type,
            "target_resource": None,
            "is_destructive": is_destructive,
            "is_read_only": is_read_only,
        },
        "context": {
            "agent_id": "test-agent",
            "user_id": None,
            "project_id": "test-project",
            "environment": environment,
            "original_task": None,
            "working_directory": "/workspace/test",
            "git_branch": "main",
        },
    }


class TestHealthCheck:
    """Basic health check."""

    def test_health(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestTerraformEvaluation:
    """Test terraform commands through the full pipeline."""

    def test_terraform_plan_staging_allow(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "plan", "infrastructure_read", "staging",
            is_read_only=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "ALLOW"

    def test_terraform_plan_production_allow(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "plan", "infrastructure_read", "production",
            is_read_only=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "ALLOW"

    def test_terraform_apply_staging_allow(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "apply", "infrastructure_modify", "staging",
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "ALLOW"

    def test_terraform_apply_production_require_approval(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "apply", "infrastructure_modify", "production",
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REQUIRE_HUMAN_APPROVAL"
        assert data["policy_id"] == "prod-apply-approval"

    def test_terraform_destroy_staging_require_approval(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "destroy", "infrastructure_destroy", "staging",
            is_destructive=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "REQUIRE_HUMAN_APPROVAL"

    def test_terraform_destroy_production_block(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "destroy", "infrastructure_destroy", "production",
            is_destructive=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "BLOCK"
        assert data["policy_id"] == "prod-destroy-block"
        assert data["risk_level"] == "CRITICAL"
        assert data["risk_score"] == 20


class TestDatabaseEvaluation:
    """Test database commands through the full pipeline."""

    def test_select_production_allow(self, client: TestClient):
        payload = _make_evaluate_payload(
            "psql", "query", "database_read", "production",
            is_read_only=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "ALLOW"

    def test_drop_table_production_block(self, client: TestClient):
        payload = _make_evaluate_payload(
            "psql", "query", "database_destructive", "production",
            is_destructive=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_level"] == "CRITICAL"


class TestShellEvaluation:
    """Test generic shell commands through the full pipeline."""

    def test_unknown_command_require_approval(self, client: TestClient):
        payload = _make_evaluate_payload(
            "shell", "some-cmd", "shell_unknown", "staging",
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "REQUIRE_HUMAN_APPROVAL"

    def test_high_risk_shell_production_block(self, client: TestClient):
        payload = _make_evaluate_payload(
            "shell", "rm", "shell_high_risk", "production",
            is_destructive=True,
            raw_command="rm -rf /",
            argv=["rm", "-rf", "/"],
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"] == "BLOCK"


class TestResponseStructure:
    """Test that response includes all required fields."""

    def test_response_has_all_fields(self, client: TestClient):
        payload = _make_evaluate_payload(
            "terraform", "destroy", "infrastructure_destroy", "production",
            is_destructive=True,
        )
        response = client.post("/api/v1/actions/evaluate", json=payload)
        data = response.json()

        assert "request_id" in data
        assert data["request_id"].startswith("AG-")
        assert "decision" in data
        assert "reason" in data
        assert "policy_id" in data
        assert "risk_level" in data
        assert "risk_score" in data
        assert "risk_factors" in data
        assert "approval_id" in data

        # Risk factors must be complete
        factors = data["risk_factors"]
        assert "action_weight" in factors
        assert "environment_weight" in factors
        assert "blast_radius_weight" in factors
        assert "reversibility_weight" in factors
        assert "privilege_weight" in factors

    def test_malformed_request_returns_422(self, client: TestClient):
        """Malformed request body should return 422, not 500."""
        response = client.post(
            "/api/v1/actions/evaluate",
            json={"bad": "data"},
        )
        assert response.status_code == 422
