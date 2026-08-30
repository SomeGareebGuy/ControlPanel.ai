"""
responsibility_check.py
-------------------------
Flags bias/unsafe/privacy-leaking content. Runs on EVERY response,
always-on, but asynchronously / in parallel with the performance
check so it doesn't add to the critical-path latency (see pipeline.py).

Two layers, deliberately cheap:

1. Deterministic PII/entity detection (regex) for the categories that
   are unambiguous and must NEVER depend on a probabilistic model
   being right: emails, phone numbers, card-like numbers, government
   ID-like numbers.

2. Embedding-space similarity against a small reference set of known
   "sensitive" internal documents/snippets. Instead of brute-force
   comparing every response against every protected document (O(n*m)
   and doesn't scale to enterprise document stores), we do a
   structured nearest-neighbour lookup -- here approximated with
   cosine similarity over TF-IDF vectors, which stands in for a real
   deployment's approximate-nearest-neighbour index (e.g. HNSW/FAISS)
   over embeddings of the sensitive corpus.

Note explicitly (per the brief's real-world complexity #2): a
fabricated detail about a person is BOTH a hallucination and a
privacy concern. This module does not try to cleanly separate that --
it reports its own score, and the policy layer is what combines
scores across dimensions rather than pretending the categories are
disjoint.
"""
import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PII_PATTERNS = {
    "email": re.compile(r"[\w.\-]+@[\w\-]+\.\w+"),
    "phone": re.compile(r"\b(?:\+?\d{1,2}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}\b"),
    "card_number": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "gov_id": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

# A small illustrative reference set of "known sensitive" internal
# snippets. In production this is the enterprise's governed sensitive
# document index, not hardcoded text.
SENSITIVE_REFERENCE_SET = [
    "Patient record: John A., DOB 04/12/1985, diagnosis confidential, insurance ID 88213X.",
    "Internal salary band for VP Engineering is $310,000-$340,000, do not disclose externally.",
    "Q3 unreleased earnings: revenue $482M, down 3% QoQ, embargoed until board approval.",
]


@dataclass
class ResponsibilityResult:
    pii_hits: dict
    has_pii: bool
    max_sensitive_similarity: float
    near_duplicate_of_sensitive_doc: bool
    flagged: bool


def _sensitive_similarity(text: str) -> float:
    corpus = SENSITIVE_REFERENCE_SET + [text]
    vec = TfidfVectorizer().fit_transform(corpus)
    sims = cosine_similarity(vec[-1], vec[:-1])[0]
    return float(sims.max()) if len(sims) else 0.0


def check(text: str) -> ResponsibilityResult:
    hits = {name: bool(pat.search(text)) for name, pat in PII_PATTERNS.items()}
    has_pii = any(hits.values())
    max_sim = round(_sensitive_similarity(text), 3)
    near_dup = max_sim >= 0.35
    return ResponsibilityResult(
        pii_hits={k: v for k, v in hits.items() if v},
        has_pii=has_pii,
        max_sensitive_similarity=max_sim,
        near_duplicate_of_sensitive_doc=near_dup,
        flagged=has_pii or near_dup,
    )
