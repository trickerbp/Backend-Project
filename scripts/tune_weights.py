from __future__ import annotations

# Tune the scoring weights against the gold set using a held-out metric so the
# reported number is not an overfit-to-the-tuning-set figure.
#
# Method:
#   1. Grid-search candidate ScoreWeights over the gold set.
#   2. Primary objective = mean nDCG@5 under LEAVE-ONE-STUDENT-OUT cross
#      validation: for each candidate, for each student s, "train" means pick
#      the candidate; we measure on s while s was never used to pick it. Because
#      a grid is fixed (not fit per fold), LOSO here means: the selected weight
#      must be the argmax of the AVERAGE over the other 7 students, then scored
#      on the held-out student. We aggregate those held-out scores.
#   3. Report both the in-sample best (optimistic) and the LOSO best (honest),
#      and print the winning weights to paste into scoring.py.
#
# Run: .\.venv\Scripts\python.exe scripts\tune_weights.py

import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")

from app.services.matching.engine import rank_courses_for_student
from app.services.matching.eval_data import COURSES, STUDENTS, binary_relevant
from app.services.matching.evaluation import aggregate_metrics, evaluate_ranking
from app.services.matching.normalize import normalize_course
from app.services.matching.scoring import ScoreWeights

KS = (1, 3, 5)
PRIMARY = "ndcg_at_5"

# Pre-normalize the catalogue once (engine expects normalized courses).
NORM_COURSES = [normalize_course(c) for c in COURSES]


def per_student_metrics(weights: ScoreWeights) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for student in STUDENTS:
        matches = rank_courses_for_student(
            student["profile"], NORM_COURSES, weights=weights, min_score=-1.0
        )
        ranked_ids = [m.course_id for m in matches]
        labels = student["labels"]
        rows.append(
            evaluate_ranking(
                ranked_ids,
                binary_relevant(labels),
                gains={cid: float(g) for cid, g in labels.items()},
                ks=KS,
            )
        )
    return rows


def candidate_grid() -> list[ScoreWeights]:
    # Relevance weights vary; context weights stay small. Steps chosen coarse to
    # keep the search honest (fine-tuning a tiny gold set invites overfitting).
    skill_opts = (0.30, 0.40, 0.50, 0.60)
    topic_opts = (0.10, 0.20, 0.30)
    goal_opts = (0.10, 0.20, 0.30)
    level_opts = (0.08, 0.12)
    dur_opts = (0.04, 0.08)
    bonus_opts = (0.05, 0.10, 0.20)

    grid: list[ScoreWeights] = []
    for skill, topic, goal, level, dur, bonus in product(
        skill_opts, topic_opts, goal_opts, level_opts, dur_opts, bonus_opts
    ):
        grid.append(
            ScoreWeights(
                skill_gap=skill,
                semantic=0.55,
                topic=topic,
                goal=goal,
                level=level,
                duration=dur,
                text_similarity_bonus=bonus,
            )
        )
    return grid


def mean_primary(rows: list[dict[str, float]]) -> float:
    return aggregate_metrics(rows).get(PRIMARY, 0.0)


def main() -> int:
    grid = candidate_grid()
    print(f"Grid size: {len(grid)} candidates, {len(STUDENTS)} students")

    # Precompute per-student metric rows for every candidate.
    cand_rows: list[list[dict[str, float]]] = [per_student_metrics(w) for w in grid]
    cand_primary_per_student: list[list[float]] = [
        [row.get(PRIMARY, 0.0) for row in rows] for rows in cand_rows
    ]

    # In-sample best (optimistic upper bound).
    in_sample = [mean_primary(rows) for rows in cand_rows]
    best_in_idx = max(range(len(grid)), key=lambda i: in_sample[i])

    # Leave-one-student-out: for each held-out student h, pick the candidate that
    # maximizes mean PRIMARY over the OTHER students, then record its score on h.
    n = len(STUDENTS)
    held_out_scores: list[float] = []
    for h in range(n):
        def others_mean(i: int) -> float:
            vals = [
                cand_primary_per_student[i][s] for s in range(n) if s != h
            ]
            return sum(vals) / len(vals)

        picked = max(range(len(grid)), key=others_mean)
        held_out_scores.append(cand_primary_per_student[picked][h])
    loso_mean = sum(held_out_scores) / n

    # For deploying a single weight vector, use the in-sample argmax (standard
    # practice once LOSO has confirmed the method generalizes).
    best = grid[best_in_idx]
    baseline_rows = per_student_metrics(ScoreWeights())
    baseline = aggregate_metrics(baseline_rows)
    best_agg = aggregate_metrics(cand_rows[best_in_idx])

    print(f"\nLOSO mean {PRIMARY}: {loso_mean:.4f}  (honest, held-out)")
    print(f"In-sample best {PRIMARY}: {in_sample[best_in_idx]:.4f}  (optimistic)")

    print("\n--- metric: default weights vs tuned (in-sample) ---")
    for key in sorted(best_agg):
        print(f"  {key:18} {baseline.get(key, 0.0):.4f} -> {best_agg[key]:.4f}")

    print("\n--- winning weights ---")
    print(
        f"  ScoreWeights(semantic={best.semantic}, behavior={best.behavior}, "
        f"skill_gap={best.skill_gap}, topic={best.topic}, goal={best.goal}, "
        f"level={best.level}, duration={best.duration}, "
        f"text_similarity_bonus={best.text_similarity_bonus})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
