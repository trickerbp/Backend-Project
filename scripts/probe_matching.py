from __future__ import annotations

# Throwaway probe: exercise extraction + scoring edge cases with concrete
# inputs and print results so we can review each dimension's real behavior.
# Run: .\.venv\Scripts\python.exe scripts\probe_matching.py

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.matching import scoring
from app.services.matching.engine import match_student_to_courses
from app.services.matching.normalize import (
    normalize_course,
    normalize_student_profile,
    parse_duration_hours,
    parse_hours_per_week,
)
from app.services.matching.skill_taxonomy import extract_skills, extract_topics


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


hr("A. parse_duration_hours")
for s in [
    "40 giờ, gồm 14 buổi",
    "14 buổi",
    "Thời lượng: 36 tiết",
    "khoảng 2 tháng",
    "120",
    "",
    None,
    "3 giờ/buổi, 10 buổi",
]:
    print(f"  {s!r:35} -> {parse_duration_hours(s)}")

hr("B. parse_hours_per_week")
for s in [
    "Thứ Ba và Thứ Năm, 19:00-21:00",
    "8 giờ/tuần",
    "tối Thứ Hai, Thứ Tư và Thứ Sáu từ 18:30 đến 21:00; chiều Chủ Nhật",
    "cuối tuần",
    "rảnh cả tuần",
    "",
]:
    print(f"  {s!r:55} -> {parse_hours_per_week(s)}")

hr("C. extract_skills / extract_topics on messy text")
for s in [
    "Đã dùng React, Node.js và Express; biết Docker cơ bản.",
    "Tôi muốn học Java và Spring Boot",
    "khóa học C++ và C#",  # not in taxonomy
    "Học máy, hồi quy, phân loại với scikit-learn",
    "REST API, RESTful, API design",
    "Node.js",  # the earlier false-positive case
]:
    print(f"  {s!r:55}")
    print(f"    skills: {extract_skills(s)}")
    print(f"    topics: {extract_topics(s)}")

hr("D. normalize_student_profile (RAW extractor output)")
raw_profile = {
    "ho_ten": "Nguyễn Minh Anh",
    "kien_thuc_nen_tang": "Sinh viên năm 3 CNTT; đã làm React, Node.js, MySQL.",
    "muc_tieu_hoc_tap": "Học Flutter và Machine Learning để làm Mobile Developer.",
    "hinh_thuc_hoc": "Online; TP. Hồ Chí Minh",
    "thoi_gian_hoc": "Thứ Ba và Thứ Năm, 19:00-21:00",
}
np = normalize_student_profile(raw_profile)
for k, v in np.items():
    print(f"  {k:18}: {v}")

hr("E. normalize_course (RAW extractor output)")
raw_course = {
    "ten_khoa_hoc": "Lập trình Flutter",
    "noi_dung_dao_tao": "Dart, Flutter, state management, gọi REST API.",
    "yeu_cau_dau_vao": "Biết lập trình hướng đối tượng cơ bản.",
    "thoi_luong_lich_hoc": "40 giờ, gồm 14 buổi",
    "hinh_thuc_to_chuc": "Hybrid",
}
nc = normalize_course(raw_course)
for k, v in nc.items():
    print(f"  {k:22}: {v}")

hr("F. SCORING dimension probes")


def score(profile, course, label):
    m = scoring.score_course_for_student(profile, course)
    d = m.score_detail
    print(f"\n  [{label}] total={round(m.score,4)} prereq_met={m.prerequisites_met}")
    print(
        f"    skill_gap={d.skill_gap} semantic={d.semantic} behavior={d.behavior} "
        f"topic={d.topic} level={d.level} goal={d.goal} dur={d.duration} "
        f"sim={round(d.text_similarity,4)}"
    )
    print(f"    matched_skills={m.matched_skills} missing={m.missing_skills}")
    return m


# F1: goal partial-match false positive via shared token "developer"
prof = {
    "career_goal": "Frontend Developer",
    "current_level": "beginner",
    "current_skills": [],
    "desired_skills": [],
    "interested_topics": [],
    "hours_per_week": 8,
}
score(
    prof,
    {"title": "Backend Java", "target_goals": ["Backend Developer"], "level": "beginner", "duration_hours": 40},
    "F1 goal: Frontend Dev vs target Backend Dev (should NOT be a real match)",
)

# F2: empty-desired student -> skill dimension dead, duration carries
prof2 = {
    "career_goal": "",
    "current_level": "beginner",
    "current_skills": ["HTML"],
    "desired_skills": [],
    "interested_topics": [],
    "hours_per_week": 6,
}
score(
    prof2,
    {"title": "ML intro", "extracted_skills": ["Python", "Machine Learning"], "level": "advanced", "duration_hours": 30},
    "F2 empty-desired vs unrelated ML course (should be ~0, is it?)",
)

# F3: duration noise - course totally irrelevant but duration fits
score(
    prof2,
    {"title": "Random", "extracted_skills": [], "extracted_topics": [], "level": "beginner", "duration_hours": 20},
    "F3 totally irrelevant course w/ fitting duration (should be ~0)",
)

# F4: real good match
prof4 = {
    "career_goal": "Mobile Developer",
    "current_level": "beginner",
    "current_skills": ["React", "JavaScript"],
    "desired_skills": ["Flutter", "Dart", "REST API"],
    "interested_topics": ["Mobile Development"],
    "hours_per_week": 8,
}
score(
    prof4,
    {
        "title": "Flutter",
        "extracted_skills": ["Flutter", "Dart", "REST API"],
        "extracted_topics": ["Mobile Development"],
        "target_goals": ["Mobile Developer"],
        "level": "beginner",
        "duration_hours": 40,
        "extracted_prerequisites": ["Biết lập trình hướng đối tượng"],
    },
    "F4 strong match (should be high)",
)

# F5: prereq penalty coarseness - 1 of 3 unmet halves whole score
score(
    prof4,
    {
        "title": "Adv Flutter",
        "extracted_skills": ["Flutter", "Dart"],
        "extracted_topics": ["Mobile Development"],
        "target_goals": ["Mobile Developer"],
        "level": "intermediate",
        "duration_hours": 40,
        "extracted_prerequisites": ["Kotlin", "Swift", "Biết Flutter"],
    },
    "F5 prereq: 2 unknown-skill prereqs (Kotlin/Swift not in taxonomy) + 1 known",
)

hr("G. FULL ranking: empty-desired student against a mixed catalogue")
courses = [
    {"course_id": "WEB101", "title": "Web cơ bản", "extracted_skills": ["HTML", "CSS", "JavaScript"], "extracted_topics": ["Web Development", "Frontend"], "target_goals": ["Frontend Developer"], "level": "beginner", "duration_hours": 30},
    {"course_id": "ML300", "title": "Machine Learning", "extracted_skills": ["Python", "Machine Learning"], "extracted_topics": ["Machine Learning"], "level": "advanced", "duration_hours": 30},
    {"course_id": "DB201", "title": "MongoDB", "extracted_skills": ["MongoDB", "NoSQL"], "level": "intermediate", "duration_hours": 24},
]
# uploaded-style profile: career goal empty, no desired skills extracted
res = match_student_to_courses(
    {"kien_thuc_nen_tang": "Biết HTML, CSS cơ bản.", "muc_tieu_hoc_tap": "Muốn làm web đẹp hơn.", "thoi_gian_hoc": "cuối tuần", "hinh_thuc_hoc": "online"},
    courses,
)
print(f"  normalized desired_skills: {res['profile']['desired_skills']}")
print(f"  normalized interested:     {res['profile']['interested_topics']}")
print(f"  career_goal:               {res['profile']['career_goal']}")
for r in res["recommendations"]:
    print(f"    {r['course_id']:8} score={r['score']:.4f}  detail={r['score_detail']}")
