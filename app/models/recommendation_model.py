from __future__ import annotations

from typing import Any


RECOMMENDATIONS_COLLECTION = "recommendations"


def recommendation_to_public(rec: dict[str, Any]) -> dict[str, Any]:
    results = []
    for item in rec.get("results", []):
        results.append(
            {
                "course_id": str(item["course_id"]),
                'title': item.get('title'),
                'course_code': item.get('course_code'),
                'level': item.get('level'),
                "score": item.get("score"),
                "matched_reasons": item.get("matched_reasons", []),
                "matched_skills": item.get("matched_skills", []),
                "missing_skills": item.get("missing_skills", []),
                "matched_topics": item.get("matched_topics", []),
                "matched_resource_ids": [
                    str(rid) for rid in item.get("matched_resource_ids", [])
                ],
                "prerequisites_met": item.get("prerequisites_met", True),
                "unmet_prerequisites": item.get("unmet_prerequisites", []),
                "score_detail": item.get("score_detail", {}),
            }
        )
    return {
        "id": str(rec["_id"]),
        "student_id": str(rec["student_id"]),
        "student_profile_id": str(rec["student_profile_id"]),
        "results": results,
        "created_at": rec.get("created_at"),
    }
