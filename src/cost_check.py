"""
cost_check.py
--------------
Implements the "don't run the expensive check on everything" tier.

Real-world constraint from the brief: different use cases have very
different latency/cost budgets, and over-checking everything at
maximum rigor doesn't scale to tens of thousands of interactions/week.

Design: a cheap, single-pass heuristic (near-zero latency, no extra
model calls) runs on EVERY response. Only when that heuristic is
itself uncertain do we pay for the expensive multi-sample
performance_check. This mirrors how repetition codes are used in
real systems -- you don't triple-transmit every packet, only the
ones where a single cheap parity check already smells wrong.

Cost is tracked in "model-call units" so the demo can report the
concrete savings vs. a naive "always multi-sample" baseline.
"""
import re
from dataclasses import dataclass

HEDGE_PATTERNS = re.compile(
    r"\b(i think|might be|not (entirely )?sure|possibly|could be|"
    r"as far as i (know|recall)|i believe|approximately|around \d)\b",
    re.IGNORECASE,
)


@dataclass
class CheapSignal:
    hedge_count: int
    length_chars: int
    cheap_uncertain: bool


def cheap_heuristic(single_response: str) -> CheapSignal:
    hedges = len(HEDGE_PATTERNS.findall(single_response))
    length = len(single_response)
    # Very short "I don't know"-style answers or heavily hedged answers
    # are themselves a signal worth a closer, more expensive look.
    uncertain = hedges >= 1 or length < 25
    return CheapSignal(hedge_count=hedges, length_chars=length, cheap_uncertain=uncertain)


def cost_units(escalated: bool, n_samples_if_escalated: int) -> int:
    """1 unit for the cheap pass; +n_samples units only if escalated."""
    return 1 + (n_samples_if_escalated if escalated else 0)
