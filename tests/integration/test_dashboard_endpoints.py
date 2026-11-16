"""Integration tests for the dashboard endpoints.

Tests /stats, /audit, /policies, and /actions list.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_get_stats(client: TestClient):
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_evaluations" in data
    assert "allowed_count" in data
    assert "blocked_count" in data
    assert "pending_approvals" in data


def test_get_policies(client: TestClient):
    response = client.get("/api/v1/policies")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert len(data["rules"]) > 0
    assert data["default"] == "REQUIRE_HUMAN_APPROVAL"


def test_get_actions_list(client: TestClient):
    response = client.get("/api/v1/actions")
    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert "total" in data


def test_get_audit_events(client: TestClient):
    response = client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "count" in data


def test_demo_seed(client: TestClient):
    response = client.post("/api/v1/demo/seed")
    assert response.status_code == 200
    assert response.json()["ok"] is True
