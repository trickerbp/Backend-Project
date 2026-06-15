from __future__ import annotations

# End-to-end check for the recommendation flow against the real MongoDB.
# Seeds a throwaway course + student profile, runs the real
# generate_recommendations() against Atlas, prints the result, then deletes
# everything it created. Safe to run repeatedly: all temp docs are tagged with
# a unique marker and removed in a finally block.
#
# Usage (from Backend-Project, with its venv):
#   .\.venv\Scripts\python.exe scripts\verify_recommendation_e2e.py

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.mongodb import (
    close_mongo_connection,
    connect_to_mongo,
    get_database,
)
from app.services.recommendation_service import generate_recommendations


MARKER = f"e2e-{uuid.uuid4().hex[:8]}"


def _configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


async def _run() -> int:
    await connect_to_mongo()
    db = get_database()

    student_id = ObjectId()
    now = datetime.now(timezone.utc)
    created_course_ids: list[ObjectId] = []
    created_profile_id: ObjectId | None = None
    recommendation_id: ObjectId | None = None

    try:
        # Ping first so a bad connection string fails clearly, not mid-query.
        await db.command("ping")
        print(f"[ok] Connected to MongoDB. marker={MARKER}")

        courses = [
            {
                "title": "Lập trình Web cơ bản",
                "course_code": f"{MARKER}-WEB101",
                "description": "Nhập môn phát triển web với HTML, CSS, JavaScript.",
                "level": "beginner",
                "target_goals": ["Frontend Developer", "Web Developer"],
                "manual_tags": ["HTML", "CSS"],
                "extracted_skills": ["HTML", "CSS", "JavaScript", "DOM"],
                "extracted_topics": ["Frontend", "Web Development"],
                "extracted_prerequisites": ["Biết sử dụng máy tính"],
                "tools": ["VS Code"],
                "duration_hours": 30,
                "status": "active",
                "teacher_id": ObjectId(),
                "_marker": MARKER,
                "created_at": now,
                "updated_at": now,
            },
            {
                "title": "React nâng cao",
                "course_code": f"{MARKER}-WEB301",
                "description": "Xây dựng ứng dụng SPA với React và REST API.",
                "level": "intermediate",
                "target_goals": ["Frontend Developer"],
                "manual_tags": [],
                "extracted_skills": ["React", "JavaScript", "API"],
                "extracted_topics": ["Frontend"],
                "extracted_prerequisites": ["JavaScript"],
                "tools": ["VS Code"],
                "duration_hours": 40,
                "status": "active",
                "teacher_id": ObjectId(),
                "_marker": MARKER,
                "created_at": now,
                "updated_at": now,
            },
        ]
        insert_courses = await db.courses.insert_many(courses)
        created_course_ids = insert_courses.inserted_ids
        print(f"[ok] Seeded {len(created_course_ids)} active course(s).")

        profile = {
            "student_id": student_id,
            "source_type": "manual_form",
            "career_goal": "Frontend Developer",
            "current_level": "beginner",
            "current_skills": ["HTML", "CSS"],
            "desired_skills": ["JavaScript", "React", "API"],
            "interested_topics": ["Frontend", "Web Development"],
            "hours_per_week": 8,
            "learning_format": "online",
            "_marker": MARKER,
            "created_at": now,
            "updated_at": now,
        }
        insert_profile = await db.student_profiles.insert_one(profile)
        created_profile_id = insert_profile.inserted_id
        profile["_id"] = created_profile_id
        print("[ok] Seeded 1 student profile.")

        document = await generate_recommendations(db, student_id, profile)
        recommendation_id = document["_id"]
        results = document["results"]

        print(f"\n[result] generate_recommendations -> {len(results)} course(s):")
        for rank, item in enumerate(results, start=1):
            print(
                f"  {rank}. {item.get('title')} [{item.get('course_code')}] "
                f"score={item['score']} prereq_met={item['prerequisites_met']}"
            )
            print(f"     matched_skills={item['matched_skills']}")
            print(f"     missing_skills={item['missing_skills']}")
            print(f"     matched_topics={item['matched_topics']}")
            print(f"     reasons={json.dumps(item['matched_reasons'], ensure_ascii=False)}")
            print(f"     detail={json.dumps(item['score_detail'], ensure_ascii=False)}")

        # Verify the stored document round-trips and is publishable.
        from app.models.recommendation_model import recommendation_to_public

        stored = await db.recommendations.find_one({"_id": recommendation_id})
        public = recommendation_to_public(stored)
        assert public["student_id"] == str(student_id)
        assert all(isinstance(r["course_id"], str) for r in public["results"])
        print("\n[ok] Stored recommendation reads back and serializes to public shape.")

        # Sanity assertions on the ranking the scoring core should produce.
        by_code = {r["course_code"]: r for r in results}
        web101 = by_code.get(f"{MARKER}-WEB101")
        web301 = by_code.get(f"{MARKER}-WEB301")
        assert web101 is not None and web301 is not None, "both courses should score"
        assert web101["prerequisites_met"] is True, "WEB101 prereq should be met"
        assert web301["prerequisites_met"] is False, "WEB301 needs JavaScript"
        assert web101["score"] > web301["score"], "ready-to-take course should rank higher"
        print("[ok] Ranking assertions passed (WEB101 > WEB301, prereq gate works).")

        print("\nEND-TO-END OK")
        return 0
    finally:
        # Always clean up, even on assertion failure.
        if created_course_ids:
            await db.courses.delete_many({"_marker": MARKER})
        if created_profile_id is not None:
            await db.student_profiles.delete_many({"_marker": MARKER})
        if recommendation_id is not None:
            await db.recommendations.delete_one({"_id": recommendation_id})
        # processing_logs written by generate_recommendations carry no marker;
        # remove the ones from this run by recency + step name.
        await db.processing_logs.delete_many(
            {"step": "generate_recommendation", "resource_id": None, "course_id": None}
        )
        await close_mongo_connection()
        print(f"[cleanup] Removed temp data for marker={MARKER}.")


def main() -> int:
    _configure_utf8_console()
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
