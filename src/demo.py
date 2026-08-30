"""
demo.py
--------
Entry point for the prototype demo. Run with:

    python src/demo.py

Loads data/sample_queries.json (18 interactions spanning three use
cases with different risk/latency profiles), runs each through the
ControlPlane.ai pipeline, prints a human-readable decision table,
writes a full audit trail to audit_log.jsonl, and reports the
adaptive-cost savings vs. a naive baseline that multi-samples every
single response.
"""
import json
import os
from pipeline import evaluate

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_queries.json")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "audit_log.jsonl")

N_SAMPLES_IF_ESCALATED = 5

DECISION_ICON = {
    "allow": "ALLOW ",
    "edit": "EDIT  ",
    "flag_for_review": "REVIEW",
    "block": "BLOCK ",
}


def main():
    with open(DATA_PATH) as f:
        queries = json.load(f)

    records = [evaluate(q, n_samples_if_escalated=N_SAMPLES_IF_ESCALATED) for q in queries]

    print(f"{'ID':6} {'Use case':28} {'Decision':8} {'Escl.':6} {'Units':6} Reason")
    print("-" * 110)
    for r in records:
        print(
            f"{r.query_id:6} {r.use_case:28} {DECISION_ICON[r.decision]:8} "
            f"{'yes' if r.escalated else 'no':6} {r.cost_units:<6} {r.reasons[0][:60]}"
        )

    with open(LOG_PATH, "w") as f:
        for r in records:
            f.write(json.dumps(r.__dict__) + "\n")

    total_naive_cost = len(records) * (1 + N_SAMPLES_IF_ESCALATED)
    total_actual_cost = sum(r.cost_units for r in records)
    savings_pct = 100 * (1 - total_actual_cost / total_naive_cost)

    decision_counts = {}
    for r in records:
        decision_counts[r.decision] = decision_counts.get(r.decision, 0) + 1

    print("\n--- Summary ---")
    print(f"Total interactions evaluated : {len(records)}")
    print(f"Decisions                    : {decision_counts}")
    print(f"Escalated to multi-sample    : {sum(r.escalated for r in records)}/{len(records)}")
    print(f"Model-call cost units used   : {total_actual_cost} "
          f"(vs. {total_naive_cost} if every response were multi-sampled)")
    print(f"Adaptive-cost savings        : {savings_pct:.1f}%")
    print(f"Avg. pipeline latency        : "
          f"{sum(r.latency_ms for r in records) / len(records):.2f} ms/interaction (simulated)")
    print(f"\nFull audit trail written to: {os.path.abspath(LOG_PATH)}")


if __name__ == "__main__":
    main()
