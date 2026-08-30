"""
performance_check.py
---------------------
Detects "confidently wrong" outputs using a repetition-code-style
majority vote, borrowed directly from classical coding theory: send
the same message (query) through the noisy channel (the model)
multiple times, and check whether the received symbols (responses)
agree.

- High agreement across samples  -> high confidence, likely correct.
- Low agreement / no clear majority cluster -> the model is guessing,
  which is exactly the situation in which hallucination happens. We
  cannot check the claim against ground truth (there usually isn't
  one available in real time), but internal *disagreement* is a
  strong, cheap, model-agnostic proxy signal for it.

We measure agreement with TF-IDF + cosine similarity clustering
(no external embedding API needed -- keeps the checker decoupled
from any one vendor, consistent with "enterprises consume a
foundation model via API, not own it").
"""
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


@dataclass
class PerformanceResult:
    n_samples: int
    agreement_score: float       # 0-1, size of largest agreement cluster / n
    majority_response: str
    dispersion: float            # 0-1, how spread out the responses are
    confident: bool


def _cluster_by_similarity(texts: list[str], threshold: float = 0.55):
    """Greedy single-link clustering on cosine similarity of TF-IDF
    vectors. Cheap (no GPU, no external call), good enough to tell
    'the model keeps saying basically the same thing' from
    'the model is all over the place'."""
    if len(texts) == 1:
        return [[0]]
    vec = TfidfVectorizer().fit_transform(texts)
    sim = cosine_similarity(vec)
    n = len(texts)
    assigned = [-1] * n
    clusters = []
    for i in range(n):
        if assigned[i] != -1:
            continue
        cluster = [i]
        assigned[i] = len(clusters)
        for j in range(i + 1, n):
            if assigned[j] == -1 and sim[i, j] >= threshold:
                cluster.append(j)
                assigned[j] = len(clusters)
        clusters.append(cluster)
    return clusters


def check(responses: list[str]) -> PerformanceResult:
    clusters = _cluster_by_similarity(responses)
    clusters.sort(key=len, reverse=True)
    majority_idx = clusters[0][0]
    agreement = len(clusters[0]) / len(responses)
    dispersion = 1 - agreement
    return PerformanceResult(
        n_samples=len(responses),
        agreement_score=round(agreement, 3),
        majority_response=responses[majority_idx],
        dispersion=round(dispersion, 3),
        confident=agreement >= 0.6,
    )
