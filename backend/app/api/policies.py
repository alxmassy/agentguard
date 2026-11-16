"""Policy viewer endpoint.

GET /api/v1/policies — list active rules loaded from policies/default.yaml.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["policies"])


@router.get("/policies")
async def get_policies(request: Request):
    """Retrieve active deterministic safety policies."""
    policy_config = getattr(request.app.state, "policy_config", None)
    if not policy_config:
        return {"rules": [], "default": "REQUIRE_HUMAN_APPROVAL", "count": 0}

    rules = [
        {
            "id": r.id,
            "conditions": r.conditions.model_dump(exclude_none=True),
            "then": r.then,
            "reason": r.reason,
        }
        for r in policy_config.rules
    ]
    return {
        "rules": rules,
        "default": policy_config.default,
        "count": len(rules),
    }
