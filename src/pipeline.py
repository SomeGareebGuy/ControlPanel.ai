"""
pipeline.py
------------
Wires the three checkers + policy layer into one call: `evaluate()`.

Latency model (illustrative, not a real profiler): the cheap
heuristic and the responsibility check are cheap enough to run
in parallel with generation / with each other (~5-15ms each in a
real deployment using an ANN index). The expensive multi-sample
performance check is the one that can blow the latency budget, so
it is the one gated by cost_check's escalation decision.

This is the "architecture" answer from the brief: pre-response gate
for responsibility + cheap performance signal (always on, low
latency), with the expensive tier only in the critical path when the
cheap tier already flagged uncertainty.
"""
import time
from dataclasses import dataclass, asdict

import mock_llm
import performance_check
import cost_check
import responsibility_check
import policy


@dataclass
class AuditRecord:
    query_id: str
    use_case: str
    query_text: str
    single_response: str
    escalated: bool
    cost_units: int
    latency_ms: float
    performance: dict
    responsibility: dict
    decision: str
    reasons: list


def evaluate(query: dict, n_samples_if_escalated: int = 5) -> AuditRecord:
    t0 = time.perf_counter()

    # 1. Always: one real generation, cheap heuristic + responsibility
    #    check run on it (conceptually in parallel).
    single_seed = (hash(query["id"] + "-single") & 0xFFFF)
    single_response = mock_llm.sample_responses(query, n=1, seed=single_seed)[0]
    cheap = cost_check.cheap_heuristic(single_response)
    resp_result = responsibility_check.check(single_response)

    # 2. Conditionally: escalate to expensive multi-sample performance
    #    check only if the cheap pass was itself uncertain.
    escalated = cheap.cheap_uncertain
    if escalated:
        samples = mock_llm.sample_responses(query, n=n_samples_if_escalated, seed=2)
        perf_result = performance_check.check(samples)
    else:
        # Cheap pass was confident enough -- treat as trivially agreeing,
        # no extra model calls spent.
        perf_result = performance_check.PerformanceResult(
            n_samples=1,
            agreement_score=1.0,
            majority_response=single_response,
            dispersion=0.0,
            confident=True,
        )

    decision = policy.decide(query["use_case"], perf_result, resp_result)
    units = cost_check.cost_units(escalated, n_samples_if_escalated)

    latency_ms = (time.perf_counter() - t0) * 1000

    return AuditRecord(
        query_id=query["id"],
        use_case=query["use_case"],
        query_text=query["text"],
        single_response=single_response,
        escalated=escalated,
        cost_units=units,
        latency_ms=round(latency_ms, 2),
        performance=asdict(perf_result),
        responsibility=asdict(resp_result),
        decision=decision.action,
        reasons=decision.reasons,
    )
