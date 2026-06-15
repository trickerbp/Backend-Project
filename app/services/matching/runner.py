from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.services.matching.engine import match_student_to_courses
from app.services.matching.scoring import ScoreWeights


__all__ = ["run", "main"]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_record_list(payload: Any, *, source: str) -> list[dict[str, Any]]:
    """Accept either a bare JSON list or a wrapper object.

    Supports the extractor pipeline output ({"documents": [...]}) as well as a
    plain list, so both lab fixtures and run_pipeline output work.
    """
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        for key in ("documents", "courses", "student_profiles", "profiles", "items"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
        else:
            records = [payload]
    else:
        raise ValueError(f"Unexpected JSON shape in {source}: {type(payload).__name__}")

    flattened: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("data"), dict):
            # run_pipeline wraps fields under "data"; lift them up but keep
            # identifying metadata alongside.
            merged = {**record, **record["data"]}
            flattened.append(merged)
        elif isinstance(record, dict):
            flattened.append(record)
    return flattened


def run(
    courses_path: Path,
    profiles_path: Path,
    output_path: Path,
    *,
    weights: ScoreWeights | None = None,
    min_score: float = 0.0,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Read course + profile JSON, match every student, write recommendations."""
    course_sources = _as_record_list(
        _load_json(courses_path), source=str(courses_path)
    )
    profile_sources = _as_record_list(
        _load_json(profiles_path), source=str(profiles_path)
    )

    students: list[dict[str, Any]] = []
    for index, profile_source in enumerate(profile_sources):
        result = match_student_to_courses(
            profile_source,
            course_sources,
            weights=weights,
            min_score=min_score,
            top_k=top_k,
        )
        if result.get("student_id") is None:
            result["student_id"] = f"student_{index + 1:02d}"
        students.append(result)

    payload = {
        "course_count": len(course_sources),
        "student_count": len(students),
        "students": students,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Match student profiles against courses and write ranked "
            "recommendations to JSON."
        )
    )
    parser.add_argument(
        "--courses",
        type=Path,
        default=Path("course_features.json"),
        help="Path to course features JSON (default: course_features.json)",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("student_profiles.json"),
        help="Path to student profiles JSON (default: student_profiles.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("recommendations.json"),
        help="Where to write recommendations (default: recommendations.json)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Keep only the top K courses per student (default: all)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Drop courses scoring at or below this value (default: 0.0)",
    )
    args = parser.parse_args(argv)

    payload = run(
        args.courses,
        args.profiles,
        args.output,
        min_score=args.min_score,
        top_k=args.top_k,
    )

    print(
        f"Matched {payload['student_count']} student(s) against "
        f"{payload['course_count']} course(s)."
    )
    for student in payload["students"]:
        top = student["recommendations"][:3]
        print(f"\n- {student['student_id']}:")
        if not top:
            print("    (no matching course)")
        for rank, item in enumerate(top, start=1):
            print(
                f"    {rank}. {item.get('title') or item.get('course_id')} "
                f"[{item['score']}]"
            )
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
