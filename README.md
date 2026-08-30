# ControlPlane.ai
### Live oversight for AI systems, borrowed from 70 years of coding theory
**Accenture Innovation Challenge 2026 — Round 2 · Team Finrod Felagund (Anubhav Dash, NIT Rourkela)**

## The problem

Every AI deployment carries the same hidden risk: it can be **confidently wrong**, **quietly expensive**,
or **subtly biased/unsafe**, and today this is usually discovered only after a user has already acted on
the output. There is no live layer watching AI behavior the way monitoring tools watch infrastructure.

## The idea

We treat every AI response as a message sent through a noisy channel and borrow classical coding-theory
techniques for detecting a corrupted message with minimal added cost:

| Dimension | Coding-theory analogy | Mechanism |
|---|---|---|
| **Performance** | Repetition code / majority vote | Sample the model N times for the same query; disagreement across samples is a cheap, model-agnostic proxy for hallucination risk (no ground truth needed) |
| **Cost** | Adaptive/rate-limited retransmission | A cheap heuristic runs on every response; the expensive multi-sample check only fires when the cheap pass is itself uncertain |
| **Responsibility** | Structured nearest-neighbour search | PII detection + similarity search against a governed "sensitive document" index to catch leaks and near-duplicates, without brute-force comparison |

All three checks feed a **configurable policy layer** that maps to one of four actions,
`allow / edit / flag_for_review / block` , with thresholds set *per use case*, because a customer-facing
chatbot, an internal copilot, and a regulated decision-support tool have very different risk tolerance and
latency budgets. Every decision is logged with a plain-language reason: a full audit trail, not a black box.

The result is oversight that is **live** rather than after-the-fact, **tunable in cost** rather than fixed, and
**model-agnostic**  it sits at the input/output layer, so it requires no retraining or access to model
internals, matching how most enterprises actually consume foundation models (via API, not by owning them).

## Architecture

```
                 ┌─────────────────────────────┐
  query ───────► │      Application layer       │
                 └──────────────┬───────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Foundation Model     │  (any vendor, via API)
                     └───────────┬────────────┘
                                 │ single response
              ┌──────────────────┼───────────────────┐
              ▼                                       ▼
   ┌─────────────────────┐               ┌──────────────────────────┐
   │  Cost-tier heuristic │               │  Responsibility check     │
   │  (always on, cheap)  │               │  (always on, parallel)    │
   └──────────┬───────────┘               │  PII regex + sensitive-doc│
              │ uncertain?                │  similarity search        │
        yes   ▼                           └──────────────┬────────────┘
   ┌─────────────────────┐                                │
   │ Multi-sample         │                                │
   │ Performance check    │                                │
   │ (expensive, gated)   │                                │
   └──────────┬───────────┘                                │
              └───────────────────┬────────────────────────┘
                                   ▼
                       ┌───────────────────────┐
                       │   Policy layer          │  per-use-case thresholds
                       │   (allow/edit/review/   │  + audit trail
                       │    block)               │
                       └───────────────────────┘
```

## Repo layout

```
controlplane-ai/
├── src/
│   ├── mock_llm.py            # deterministic stand-in for a real model API (swap for a real client)
│   ├── performance_check.py   # multi-sample agreement / hallucination-risk signal
│   ├── cost_check.py          # cheap heuristic + adaptive escalation logic
│   ├── responsibility_check.py# PII detection + sensitive-document similarity search
│   ├── policy.py              # per-use-case decision thresholds + audit reasons
│   ├── pipeline.py            # orchestrates the above into one evaluate() call
│   ├── demo.py                # runs the full demo over sample data, prints + logs results
│   └── build_dashboard.py     # renders audit_log.jsonl into docs/dashboard.html
├── data/
│   └── sample_queries.json    # 19 interactions across 3 use cases (customer-facing, internal, regulated)
├── docs/
│   └── dashboard.html         # generated monitoring dashboard (open in a browser)
├── audit_log.jsonl            # generated: full per-interaction audit trail
├── proposal/
│   └── business_proposal.md   # detailed business proposal
└── requirements.txt
```

## Running the prototype

```bash
git clone <this-repo>
cd controlplane-ai
pip install -r requirements.txt
cd src
python demo.py              # prints decisions, writes ../audit_log.jsonl
python build_dashboard.py   # renders ../docs/dashboard.html — open it in a browser
```

No API keys required, the model layer is a deterministic mock (`mock_llm.py`) so the demo is 100%
reproducible offline. Swapping in a real model API (e.g. calling a hosted LLM N times at temperature > 0)
requires changing only that one file; nothing downstream changes.

### What the demo shows

- 19 simulated interactions across three use cases with different policy configs (`policy.py`)
- Adaptive cost tiering: most interactions cost 1 model-call unit; only genuinely ambiguous ones escalate
  to a 5-sample check, the demo reports the aggregate cost savings vs. a naive "always multi-sample"
  baseline
- All four decision tiers exercised: `allow`, `edit`, `flag_for_review`, `block`
- Responsibility checks catching both a direct PII leak (email/phone) and a near-duplicate of a governed
  sensitive document (an unreleased-earnings snippet), each producing a different action under the
  regulated-use-case policy
- A full, human-readable audit trail per decision (`audit_log.jsonl`, and rendered in `docs/dashboard.html`)

## Known limitations of this prototype (honest scope)

- The "model" is a deterministic mock with hand-authored response pools, not a live API call, this
  isolates and demonstrates the *oversight mechanism* without requiring API budget/keys for a hackathon
  demo; the architecture is designed so swapping in a real model is a one-file change.
- The responsibility check's sensitive-document similarity search uses TF-IDF cosine similarity as a
  stand-in for a production approximate-nearest-neighbour index (e.g. FAISS/HNSW) over real embeddings.
- Bias detection specifically is not yet implemented as a separate signal in this prototype; the
  responsibility layer currently covers PII/sensitive-data leakage and near-duplication. See the roadmap
  in the business proposal for how a bias-detection module would be added (e.g. counterfactual fairness
  probes, protected-attribute-conditioned output comparison).
- Thresholds in `policy.py` are illustrative starting points, not calibrated against real production data.

## Team

**Finrod Felagund**

 Anubhav Dash, Integrated M.Sc. Mathematics, NIT Rourkela
