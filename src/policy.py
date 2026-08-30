"""
policy.py
----------
The governance layer: turns raw signals from the three checkers into
one of four tiered actions -- allow / edit / flag_for_review / block --
and, critically, makes that mapping CONFIGURABLE per use case rather
than hard-coded, because a one-size-fits-all threshold is exactly
what the brief calls out as failing in practice (customer-facing vs.
internal vs. regulated decision-support have very different risk
tolerance and latency budgets).

Every decision returns a `reasons` list -- this is the audit trail.
Nothing is flagged or blocked silently.
"""
from dataclasses import dataclass, field

# Per-use-case policy: how much dispersion (model disagreement) is
# tolerated before we act, and how PII/sensitive-data hits are
# handled. Tuned deliberately asymmetric: it is always cheaper to
# over-flag than to silently ship a leak or a hallucinated claim into
# a regulated decision.
USE_CASE_POLICIES = {
    "customer_facing_chatbot": {
        "dispersion_edit_threshold": 0.35,
        "dispersion_review_threshold": 0.55,
        "pii_action": "block",
        "latency_budget_ms": 300,
    },
    "internal_knowledge_assistant": {
        "dispersion_edit_threshold": 0.45,
        "dispersion_review_threshold": 0.65,
        "pii_action": "flag_for_review",
        "latency_budget_ms": 800,
    },
    "decision_support_regulated": {
        "dispersion_edit_threshold": 0.20,
        "dispersion_review_threshold": 0.35,
        "pii_action": "block",
        "latency_budget_ms": 1500,
    },
}


@dataclass
class Decision:
    action: str  # allow | edit | flag_for_review | block
    reasons: list = field(default_factory=list)


def decide(use_case: str, perf, resp) -> Decision:
    policy = USE_CASE_POLICIES[use_case]
    reasons = []

    # Responsibility dimension takes priority -- a leak or bias hit
    # is never "averaged away" by a confident performance score.
    if resp.flagged:
        action = policy["pii_action"]
        if resp.has_pii:
            reasons.append(f"PII/sensitive pattern detected: {list(resp.pii_hits.keys())}")
        if resp.near_duplicate_of_sensitive_doc:
            reasons.append(
                f"Near-duplicate of governed sensitive document "
                f"(similarity={resp.max_sensitive_similarity})"
            )
        return Decision(action=action, reasons=reasons)

    # Performance dimension: use disagreement across samples as the
    # hallucination-risk proxy.
    if perf.dispersion >= policy["dispersion_review_threshold"]:
        reasons.append(
            f"High sample disagreement ({perf.dispersion}) -- model likely guessing"
        )
        return Decision(action="flag_for_review", reasons=reasons)
    if perf.dispersion >= policy["dispersion_edit_threshold"]:
        reasons.append(
            f"Moderate sample disagreement ({perf.dispersion}) -- hedge/caveat before showing user"
        )
        return Decision(action="edit", reasons=reasons)

    reasons.append(f"High agreement across samples ({perf.agreement_score})")
    return Decision(action="allow", reasons=reasons)
