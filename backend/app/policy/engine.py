"""Policy Engine — deterministic, rule-ordered evaluation.

Evaluates rules in precedence order (BLOCK > REQUIRE_APPROVAL > ALLOW > default).
This is the core authorization logic. No ML, no LLM, no probabilistic decisions.

Precedence (highest to lowest):
    1. Explicit BLOCK — safety-critical, cannot be overridden
    2. REQUIRE_HUMAN_APPROVAL — cannot be silently downgraded to ALLOW  
    3. Explicit ALLOW
    4. Default policy — REQUIRE_HUMAN_APPROVAL for anything unmatched
"""
from __future__ import annotations

from app.models import ActionRequest, Decision, PolicyVerdict
from app.policy.loader import PolicyConfig, PolicyRule


# Precedence weights: lower number = higher priority
_DECISION_PRECEDENCE: dict[str, int] = {
    "BLOCK": 0,
    "REQUIRE_HUMAN_APPROVAL": 1,
    "ALLOW": 2,
}


def _rule_matches(rule: PolicyRule, request: ActionRequest) -> bool:
    """Check if all conditions in a rule match the request.
    
    A rule matches only if ALL specified (non-None) conditions match.
    Conditions that are None (not specified) are treated as wildcards.
    """
    cond = rule.conditions

    if cond.environment is not None:
        if cond.environment != request.context.environment:
            return False

    if cond.action_type is not None:
        if cond.action_type != request.parsed_action.action_type.value:
            return False

    if cond.is_read_only is not None:
        if cond.is_read_only != request.parsed_action.is_read_only:
            return False

    if cond.is_destructive is not None:
        if cond.is_destructive != request.parsed_action.is_destructive:
            return False

    if cond.tool is not None:
        if cond.tool != request.parsed_action.tool:
            return False

    return True


def evaluate_policy(request: ActionRequest, config: PolicyConfig) -> PolicyVerdict:
    """Evaluate all matching policy rules and return the highest-precedence verdict.
    
    All matching rules are collected, then the one with the highest precedence
    (BLOCK > REQUIRE_HUMAN_APPROVAL > ALLOW) wins. This is NOT first-match-wins,
    which would be sensitive to rule ordering bugs.
    
    If no rules match, the default policy applies (REQUIRE_HUMAN_APPROVAL).
    
    Args:
        request: The action request to evaluate.
        config: The loaded policy configuration.
        
    Returns:
        PolicyVerdict with the decision, reason, and matched policy_id.
    """
    matching_rules: list[PolicyRule] = []

    for rule in config.rules:
        if _rule_matches(rule, request):
            matching_rules.append(rule)

    if not matching_rules:
        # No rules matched — apply default policy (fail safe: never ALLOW)
        return PolicyVerdict(
            decision=Decision(config.default),
            reason="No matching policy rule; default policy applied",
            policy_id="default",
        )

    # Sort by precedence (BLOCK=0 < REQUIRE=1 < ALLOW=2), take highest priority
    matching_rules.sort(key=lambda r: _DECISION_PRECEDENCE.get(r.then, 99))
    winner = matching_rules[0]

    return PolicyVerdict(
        decision=Decision(winner.then),
        reason=winner.reason,
        policy_id=winner.id,
    )
