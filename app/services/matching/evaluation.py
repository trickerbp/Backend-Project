from __future__ import annotations

# Pure ranking-evaluation metrics for the course recommender. No I/O, no app
# deps -- takes a ranked list of course ids and a relevance judgment, returns
# the standard information-retrieval metrics so we can measure (not guess)
# whether the ranking is good.
#
# Two relevance conventions are supported:
#   * binary: a set/iterable of "relevant" course ids.
#   * graded: a dict {course_id: gain} where gain >= 0 (e.g. 2 = strong match,
#     1 = partial, 0 = irrelevant). Used by nDCG.

import math
from typing import Iterable, Mapping, Sequence


__all__ = [
    "precision_at_k",
    "recall_at_k",
    "average_precision",
    "reciprocal_rank",
    "dcg_at_k",
    "ndcg_at_k",
    "evaluate_ranking",
    "aggregate_metrics",
]


def _binary_relevant(relevant: Iterable[str]) -> set[str]:
    return {str(r) for r in relevant}


def precision_at_k(
    ranked_ids: Sequence[str],
    relevant: Iterable[str],
    k: int,
) -> float:
    """Fraction of the top-k results that are relevant.

    Denominator is k (or the list length if shorter), the standard convention:
    a system that returns fewer than k items is not rewarded for padding.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = _binary_relevant(relevant)
    top_k = list(ranked_ids)[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for cid in top_k if str(cid) in relevant_set)
    return hits / min(k, len(top_k))


def recall_at_k(
    ranked_ids: Sequence[str],
    relevant: Iterable[str],
    k: int,
) -> float:
    """Fraction of all relevant items that appear in the top-k."""
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = _binary_relevant(relevant)
    if not relevant_set:
        return 0.0
    top_k = {str(cid) for cid in list(ranked_ids)[:k]}
    return len(top_k & relevant_set) / len(relevant_set)


def average_precision(
    ranked_ids: Sequence[str],
    relevant: Iterable[str],
) -> float:
    """Average of precision values taken at each relevant hit position.

    AP rewards placing relevant items early. Zero when there are no relevant
    items or none are retrieved. This is the per-query term of MAP.
    """
    relevant_set = _binary_relevant(relevant)
    if not relevant_set:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for index, cid in enumerate(ranked_ids, start=1):
        if str(cid) in relevant_set:
            hits += 1
            precision_sum += hits / index
    if hits == 0:
        return 0.0
    return precision_sum / len(relevant_set)


def reciprocal_rank(
    ranked_ids: Sequence[str],
    relevant: Iterable[str],
) -> float:
    """1 / rank of the first relevant item; 0 if none retrieved. (MRR term.)"""
    relevant_set = _binary_relevant(relevant)
    for index, cid in enumerate(ranked_ids, start=1):
        if str(cid) in relevant_set:
            return 1.0 / index
    return 0.0


def dcg_at_k(
    ranked_ids: Sequence[str],
    gains: Mapping[str, float],
    k: int,
) -> float:
    """Discounted cumulative gain over the top-k.

    Uses the standard log2(rank+1) discount and raw graded gains. Unknown ids
    contribute zero gain.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    total = 0.0
    for index, cid in enumerate(list(ranked_ids)[:k], start=1):
        gain = float(gains.get(str(cid), 0.0))
        if gain:
            total += gain / math.log2(index + 1)
    return total


def ndcg_at_k(
    ranked_ids: Sequence[str],
    gains: Mapping[str, float],
    k: int,
) -> float:
    """DCG@k normalized by the ideal DCG@k, in [0, 1].

    The ideal ranking sorts all known gains descending. Returns 0 when there is
    no positive gain to be had (so an empty/irrelevant catalogue is not a
    free 1.0).
    """
    actual = dcg_at_k(ranked_ids, gains, k)
    ideal_gains = sorted(
        (float(g) for g in gains.values() if g > 0), reverse=True
    )
    ideal = 0.0
    for index, gain in enumerate(ideal_gains[:k], start=1):
        ideal += gain / math.log2(index + 1)
    if ideal == 0.0:
        return 0.0
    return actual / ideal


def evaluate_ranking(
    ranked_ids: Sequence[str],
    relevant: Iterable[str],
    *,
    gains: Mapping[str, float] | None = None,
    ks: Sequence[int] = (1, 3, 5),
) -> dict[str, float]:
    """All metrics for one query (one student).

    ``relevant`` drives the binary metrics (P@k, R@k, MAP, MRR). ``gains`` (graded
    relevance) drives nDCG; when omitted, relevant items are treated as gain 1.
    """
    relevant_set = _binary_relevant(relevant)
    if gains is None:
        gains = {cid: 1.0 for cid in relevant_set}

    result: dict[str, float] = {
        "map": average_precision(ranked_ids, relevant_set),
        "mrr": reciprocal_rank(ranked_ids, relevant_set),
    }
    for k in ks:
        result[f"precision_at_{k}"] = precision_at_k(ranked_ids, relevant_set, k)
        result[f"recall_at_{k}"] = recall_at_k(ranked_ids, relevant_set, k)
        result[f"ndcg_at_{k}"] = ndcg_at_k(ranked_ids, gains, k)
    return result


def aggregate_metrics(
    per_query: Sequence[Mapping[str, float]],
) -> dict[str, float]:
    """Macro-average each metric across queries (students).

    Macro (mean of per-student scores) is the right aggregation here: every
    student counts equally regardless of how many courses match them.
    """
    if not per_query:
        return {}
    keys = set()
    for row in per_query:
        keys.update(row.keys())
    return {
        key: sum(row.get(key, 0.0) for row in per_query) / len(per_query)
        for key in sorted(keys)
    }
