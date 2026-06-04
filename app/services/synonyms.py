"""Curated job-title synonym dictionary for query expansion.

The requirement is that searching 'programmer' or 'coder' should still return
'software engineer' jobs. pg_trgm handles typos; this handles synonyms.

Each frozenset below is a *synset* — all terms within it are treated as
equivalent. When a search query token matches any term in a synset, the query
is expanded to OR-match every term in that synset.

This is intentionally a small curated starter list, not a comprehensive
thesaurus. Add synsets as your real users start typing things we miss.

To extend: append a new frozenset of lowercase synonyms.
"""
from __future__ import annotations

from typing import Iterable

_SYNSETS: list[frozenset[str]] = [
    # Engineering / software
    frozenset({
        "software engineer", "software developer", "developer", "programmer",
        "coder", "swe", "dev", "engineer",
    }),
    frozenset({
        "backend engineer", "backend developer", "backend", "server engineer",
        "back-end engineer", "back end engineer", "api engineer",
    }),
    frozenset({
        "frontend engineer", "frontend developer", "frontend",
        "front-end engineer", "front end engineer", "ui engineer",
        "ui developer", "client-side engineer",
    }),
    frozenset({
        "full stack engineer", "full-stack engineer", "fullstack engineer",
        "full stack developer", "full-stack developer", "fullstack developer",
    }),
    frozenset({
        "mobile engineer", "mobile developer", "ios developer",
        "android developer", "ios engineer", "android engineer",
    }),
    frozenset({
        "devops engineer", "devops", "sre", "site reliability engineer",
        "platform engineer", "infrastructure engineer", "infra engineer",
    }),
    frozenset({
        "data engineer", "data infrastructure engineer", "etl engineer",
    }),
    frozenset({
        "ml engineer", "machine learning engineer", "ai engineer",
        "applied scientist", "ml researcher",
    }),
    # Data / analytics
    frozenset({
        "data analyst", "business analyst", "bi analyst",
        "business intelligence analyst", "analytics analyst",
    }),
    frozenset({
        "data scientist", "research scientist", "applied data scientist",
    }),
    # Design
    frozenset({
        "designer", "ux designer", "ui designer", "ux/ui designer",
        "product designer", "interaction designer", "visual designer",
    }),
    frozenset({"graphic designer", "graphic artist", "visual artist"}),
    # Product / management
    frozenset({"product manager", "pm", "product owner", "po"}),
    frozenset({
        "project manager", "program manager", "delivery manager", "tpm",
        "technical program manager",
    }),
    frozenset({
        "engineering manager", "em", "tech lead", "team lead",
    }),
    # Marketing / growth
    frozenset({
        "marketing manager", "growth manager", "marketing specialist",
        "growth marketer",
    }),
    frozenset({
        "content writer", "copywriter", "technical writer", "content creator",
    }),
    # Sales / customer
    frozenset({
        "sales representative", "sales rep", "account executive", "ae",
        "salesperson",
    }),
    frozenset({
        "customer success manager", "csm", "customer success",
        "account manager",
    }),
    # QA / testing
    frozenset({
        "qa engineer", "quality assurance engineer", "qa", "tester",
        "test engineer", "sdet",
    }),
    # Ops
    frozenset({
        "operations manager", "ops manager", "operations specialist",
    }),
]

# Reverse index: term → synset for O(1) lookup.
_TERM_TO_SYNSET: dict[str, frozenset[str]] = {
    term: synset for synset in _SYNSETS for term in synset
}


def expand(query: str) -> set[str]:
    """Expand a search query to include all known synonyms.

    Tries to match the WHOLE query first (catches multi-word titles like
    'data analyst'). Falls back to per-token expansion. Always includes the
    original query so we never *lose* matches.
    """
    q = (query or "").strip().lower()
    if not q:
        return set()

    expanded: set[str] = {q}

    # Whole-query synset match first — "data analyst" → all data-analyst synonyms
    if q in _TERM_TO_SYNSET:
        expanded |= _TERM_TO_SYNSET[q]

    # Per-token expansion catches single-word matches like "programmer"
    for token in q.split():
        if token in _TERM_TO_SYNSET:
            expanded |= _TERM_TO_SYNSET[token]

    return expanded


def to_tsquery_or(expansions: Iterable[str]) -> str:
    """Build a Postgres to_tsquery() input from a set of expansion terms.

    Each multi-word expansion becomes a phrase match (`<->` operator);
    expansions are OR-joined. Special characters are stripped to avoid
    tsquery syntax errors.
    """
    parts = []
    for term in expansions:
        clean = "".join(c if c.isalnum() or c.isspace() else " " for c in term)
        tokens = clean.split()
        if not tokens:
            continue
        if len(tokens) == 1:
            parts.append(tokens[0])
        else:
            parts.append("(" + " <-> ".join(tokens) + ")")
    return " | ".join(parts)
