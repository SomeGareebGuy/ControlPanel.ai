"""
mock_llm.py
-----------
A stand-in for a real foundation-model API call.

In production, ControlPlane.ai sits BETWEEN the application and a real
model API (OpenAI/Anthropic/Azure/etc.) and calls that API multiple times
per query when a multi-sample performance check is needed. For this
prototype we simulate that behaviour deterministically so the demo is
100% reproducible without API keys or network calls.

Each query in data/sample_queries.json has a pre-authored pool of
candidate responses. When the pipeline "samples" the model N times, we
draw from that pool. Some pools are tight (model is confident/correct),
some are split (model is guessing -> hallucination risk), and some
contain an injected PII/sensitive-data leak.

Swapping this module for a real API client (e.g. Anthropic's Messages
API called N times at temperature > 0) requires no change to the rest
of the pipeline -- that's the point of the architecture.
"""
import random


def sample_responses(query: dict, n: int, seed: int = None) -> list[str]:
    """Draw n responses from a query's pre-authored candidate pool,
    weighted the way a real model's sampling distribution would be:
    the dominant answer is drawn most often, minority/divergent
    answers occasionally, mimicking real decoding variance."""
    rng = random.Random(seed if seed is not None else hash(query["id"]) & 0xFFFF)
    pool = query["response_pool"]  # list of (text, weight)
    texts, weights = zip(*pool)
    return list(rng.choices(texts, weights=weights, k=n))
