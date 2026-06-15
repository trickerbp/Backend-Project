from __future__ import annotations

# Hand-built evaluation dataset (gold set) for the course recommender.
#
# WHY THIS EXISTS: tuning weights against a metric is only honest if the metric
# is computed against relevance labels that were decided BEFORE seeing any
# score. The labels below follow the fixed rubric in `RELEVANCE_RUBRIC` so they
# are reproducible and not reverse-engineered from the engine's output.
#
# GRADED RELEVANCE (used by nDCG; collapsed to binary "relevant if gain >= 1"
# for P@k / R@k / MAP / MRR):
#   2 = strong fit   : course teaches the student's desired/gap skills AND
#                      matches their career goal or interested topic, and the
#                      level is reachable (same or one step up).
#   1 = partial fit  : course is in the student's area (topic or goal overlaps)
#                      OR teaches some desired skill, but is weaker on the rest
#                      (e.g. wrong level, only tangential skills).
#   0 = not relevant : different domain; teaches nothing the student wants.
#
# Labels were assigned by reading each (student, course) pair against the rubric
# only. The engine's numeric score was NOT consulted when labeling.

RELEVANCE_RUBRIC = (
    "2=strong: teaches desired/gap skills AND matches goal or topic, level reachable; "
    "1=partial: same area OR some desired skill, weaker elsewhere; "
    "0=none: different domain, teaches nothing wanted."
)


# --- Course catalogue (already-normalized shape: matches course_model) -------
COURSES: list[dict] = [
    {
        "course_id": "WEB101",
        "title": "Lập trình Web cơ bản",
        "course_code": "WEB101",
        "description": "HTML, CSS, JavaScript, responsive design, thao tác DOM.",
        "level": "beginner",
        "target_goals": ["Frontend Developer", "Web Developer"],
        "extracted_skills": ["HTML", "CSS", "JavaScript", "Responsive Design", "DOM"],
        "extracted_topics": ["Web Development", "Frontend"],
        "extracted_prerequisites": ["Biết sử dụng máy tính"],
        "duration_hours": 30,
    },
    {
        "course_id": "WEB201",
        "title": "React và Frontend hiện đại",
        "course_code": "WEB201",
        "description": "React, component, state management, gọi REST API.",
        "level": "intermediate",
        "target_goals": ["Frontend Developer"],
        "extracted_skills": ["React", "JavaScript", "REST API", "Responsive Design"],
        "extracted_topics": ["Frontend", "Web Development"],
        "extracted_prerequisites": ["HTML", "CSS", "JavaScript"],
        "duration_hours": 40,
    },
    {
        "course_id": "WEB301",
        "title": "Kiến trúc Frontend nâng cao",
        "course_code": "WEB301",
        "description": "Performance, testing, design system, TypeScript.",
        "level": "advanced",
        "target_goals": ["Frontend Developer"],
        "extracted_skills": ["TypeScript", "React", "Clean Architecture"],
        "extracted_topics": ["Frontend"],
        "extracted_prerequisites": ["React", "JavaScript"],
        "duration_hours": 36,
    },
    {
        "course_id": "BE101",
        "title": "Lập trình Backend với Node.js",
        "course_code": "BE101",
        "description": "Node.js, Express, REST API, JWT, MongoDB.",
        "level": "intermediate",
        "target_goals": ["Backend Developer"],
        "extracted_skills": ["Node.js", "Express", "REST API", "JWT", "MongoDB"],
        "extracted_topics": ["Backend", "Web Development"],
        "extracted_prerequisites": ["JavaScript"],
        "duration_hours": 45,
    },
    {
        "course_id": "BE201",
        "title": "Java Spring Boot",
        "course_code": "BE201",
        "description": "Java, Spring Boot, REST API, OOP.",
        "level": "intermediate",
        "target_goals": ["Backend Developer"],
        "extracted_skills": ["Java", "Spring Boot", "REST API", "OOP"],
        "extracted_topics": ["Backend"],
        "extracted_prerequisites": ["OOP"],
        "duration_hours": 50,
    },
    {
        "course_id": "MOB101",
        "title": "Lập trình Flutter",
        "course_code": "MOB101",
        "description": "Dart, Flutter, state management, gọi REST API.",
        "level": "beginner",
        "target_goals": ["Mobile Developer"],
        "extracted_skills": ["Dart", "Flutter", "REST API"],
        "extracted_topics": ["Mobile Development"],
        "extracted_prerequisites": ["Biết lập trình hướng đối tượng cơ bản"],
        "duration_hours": 40,
    },
    {
        "course_id": "MOB201",
        "title": "iOS với SwiftUI",
        "course_code": "MOB201",
        "description": "Swift, SwiftUI, xây dựng app iOS native.",
        "level": "intermediate",
        "target_goals": ["Mobile Developer"],
        "extracted_skills": ["Swift", "SwiftUI"],
        "extracted_topics": ["Mobile Development"],
        "extracted_prerequisites": ["Biết lập trình cơ bản"],
        "duration_hours": 40,
    },
    {
        "course_id": "DATA101",
        "title": "Phân tích dữ liệu với Python",
        "course_code": "DATA101",
        "description": "Python, pandas, NumPy, phân tích dữ liệu, trực quan hóa.",
        "level": "beginner",
        "target_goals": ["Data Analyst"],
        "extracted_skills": ["Python", "Pandas", "NumPy", "Data Analysis"],
        "extracted_topics": ["Data Science", "Data Analysis"],
        "extracted_prerequisites": [],
        "duration_hours": 35,
    },
    {
        "course_id": "DATA201",
        "title": "Machine Learning nhập môn",
        "course_code": "DATA201",
        "description": "scikit-learn, hồi quy, phân loại, đánh giá mô hình.",
        "level": "intermediate",
        "target_goals": ["Machine Learning Engineer", "Data Scientist"],
        "extracted_skills": [
            "Machine Learning",
            "Scikit-learn",
            "Regression",
            "Classification",
            "Python",
        ],
        "extracted_topics": ["Machine Learning", "Data Science"],
        "extracted_prerequisites": ["Python"],
        "duration_hours": 45,
    },
    {
        "course_id": "DATA301",
        "title": "Data Engineering với Spark & Airflow",
        "course_code": "DATA301",
        "description": "ETL, Apache Spark, Apache Airflow, Kafka, data pipeline.",
        "level": "advanced",
        "target_goals": ["Data Engineer"],
        "extracted_skills": ["ETL", "Apache Spark", "Apache Airflow", "Kafka", "Python"],
        "extracted_topics": ["Data Engineering"],
        "extracted_prerequisites": ["Python", "SQL"],
        "duration_hours": 60,
    },
    {
        "course_id": "DB101",
        "title": "Cơ sở dữ liệu MongoDB",
        "course_code": "DB101",
        "description": "MongoDB, NoSQL, thiết kế schema, truy vấn.",
        "level": "intermediate",
        "target_goals": [],
        "extracted_skills": ["MongoDB", "NoSQL"],
        "extracted_topics": ["Database"],
        "extracted_prerequisites": [],
        "duration_hours": 24,
    },
    {
        "course_id": "DB201",
        "title": "SQL và PostgreSQL",
        "course_code": "DB201",
        "description": "SQL, PostgreSQL, tối ưu truy vấn.",
        "level": "beginner",
        "target_goals": [],
        "extracted_skills": ["SQL", "PostgreSQL"],
        "extracted_topics": ["Database"],
        "extracted_prerequisites": [],
        "duration_hours": 20,
    },
    {
        "course_id": "DEVOPS101",
        "title": "Docker & Kubernetes",
        "course_code": "DEVOPS101",
        "description": "Docker, Kubernetes, CI/CD pipeline.",
        "level": "intermediate",
        "target_goals": ["DevOps Engineer"],
        "extracted_skills": ["Docker", "Kubernetes", "CI/CD"],
        "extracted_topics": ["DevOps", "Cloud"],
        "extracted_prerequisites": [],
        "duration_hours": 30,
    },
    {
        "course_id": "DESIGN101",
        "title": "Thiết kế UI/UX với Figma",
        "course_code": "DESIGN101",
        "description": "Figma, nguyên tắc thiết kế, prototyping.",
        "level": "beginner",
        "target_goals": ["UI/UX Designer"],
        "extracted_skills": ["Figma", "UI/UX"],
        "extracted_topics": ["UI/UX Design"],
        "extracted_prerequisites": [],
        "duration_hours": 25,
    },
]


# --- Students (already-normalized shape: matches student_profile_model) ------
# Each entry: profile + graded relevance labels {course_id: gain}. Courses not
# listed are implicitly gain 0 (not relevant).
STUDENTS: list[dict] = [
    {
        "profile": {
            "student_id": "S1",
            "career_goal": "Frontend Developer",
            "current_level": "beginner",
            "current_skills": ["HTML", "CSS"],
            "desired_skills": ["JavaScript", "React", "Responsive Design"],
            "interested_topics": ["Frontend", "Web Development"],
            "hours_per_week": 8,
            "learning_format": "online",
        },
        # WEB101 teaches JS+Responsive at reachable level + Frontend goal -> 2.
        # WEB201 teaches React (top desired) + goal, one step up -> 2.
        # WEB301 Frontend goal but advanced + needs React first -> 1.
        # BE101 shares JS/web area but backend goal -> 1.
        "labels": {"WEB101": 2, "WEB201": 2, "WEB301": 1, "BE101": 1},
    },
    {
        "profile": {
            "student_id": "S2",
            "career_goal": "Frontend Developer",
            "current_level": "intermediate",
            "current_skills": ["HTML", "CSS", "JavaScript"],
            "desired_skills": ["React", "TypeScript", "REST API"],
            "interested_topics": ["Frontend"],
            "hours_per_week": 10,
            "learning_format": "online",
        },
        # WEB201 React+REST at matching level + goal -> 2.
        # WEB301 TypeScript+React, advanced is one step up, goal -> 2.
        # WEB101 frontend area but below current level / already-known skills -> 1.
        # BE101 teaches REST API (a desired skill) but backend -> 1.
        "labels": {"WEB201": 2, "WEB301": 2, "WEB101": 1, "BE101": 1},
    },
    {
        "profile": {
            "student_id": "S3",
            "career_goal": "Backend Developer",
            "current_level": "intermediate",
            "current_skills": ["JavaScript", "SQL"],
            "desired_skills": ["Node.js", "Express", "MongoDB", "REST API"],
            "interested_topics": ["Backend"],
            "hours_per_week": 12,
            "learning_format": "hybrid",
        },
        # BE101 Node/Express/Mongo/REST + backend goal -> 2.
        # BE201 backend goal + REST, different stack (Java) -> 1.
        # DB101 MongoDB (desired) + DB area -> 1.
        "labels": {"BE101": 2, "BE201": 1, "DB101": 1},
    },
    {
        "profile": {
            "student_id": "S4",
            "career_goal": "Mobile Developer",
            "current_level": "beginner",
            "current_skills": ["Java"],
            "desired_skills": ["Flutter", "Dart"],
            "interested_topics": ["Mobile Development"],
            "hours_per_week": 6,
            "learning_format": "online",
        },
        # MOB101 Flutter+Dart at beginner + mobile goal -> 2.
        # MOB201 mobile goal + topic, different stack/level -> 1.
        "labels": {"MOB101": 2, "MOB201": 1},
    },
    {
        "profile": {
            "student_id": "S5",
            "career_goal": "Data Analyst",
            "current_level": "beginner",
            "current_skills": ["Excel", "SQL"],
            "desired_skills": ["Python", "Pandas", "Data Analysis"],
            "interested_topics": ["Data Science", "Data Analysis"],
            "hours_per_week": 8,
            "learning_format": "online",
        },
        # DATA101 Python/pandas/analysis + analyst goal + topic -> 2.
        # DATA201 ML, data science area, one step up -> 1.
        # DB201 SQL area (already known) tangential -> 1.
        "labels": {"DATA101": 2, "DATA201": 1, "DB201": 1},
    },
    {
        "profile": {
            "student_id": "S6",
            "career_goal": "Machine Learning Engineer",
            "current_level": "intermediate",
            "current_skills": ["Python", "Pandas", "NumPy"],
            "desired_skills": ["Machine Learning", "Scikit-learn", "Classification"],
            "interested_topics": ["Machine Learning", "Data Science"],
            "hours_per_week": 10,
            "learning_format": "online",
        },
        # DATA201 ML/sklearn/classification + ML goal + topic at level -> 2.
        # DATA301 data eng, advanced, data area -> 1.
        # DATA101 foundational python/analysis (mostly known) -> 1.
        "labels": {"DATA201": 2, "DATA301": 1, "DATA101": 1},
    },
    {
        "profile": {
            "student_id": "S7",
            "career_goal": "Data Engineer",
            "current_level": "advanced",
            "current_skills": ["Python", "SQL", "Pandas"],
            "desired_skills": ["Apache Spark", "Apache Airflow", "ETL", "Kafka"],
            "interested_topics": ["Data Engineering"],
            "hours_per_week": 14,
            "learning_format": "hybrid",
        },
        # DATA301 Spark/Airflow/ETL/Kafka + DE goal + topic + level -> 2.
        # DATA201 data area, ML (some overlap) -> 1.
        "labels": {"DATA301": 2, "DATA201": 1},
    },
    {
        "profile": {
            "student_id": "S8",
            "career_goal": "DevOps Engineer",
            "current_level": "intermediate",
            "current_skills": ["Git", "Python"],
            "desired_skills": ["Docker", "Kubernetes", "CI/CD"],
            "interested_topics": ["DevOps", "Cloud"],
            "hours_per_week": 8,
            "learning_format": "online",
        },
        # DEVOPS101 Docker/K8s/CI-CD + DevOps goal + topic at level -> 2.
        "labels": {"DEVOPS101": 2},
    },
]


def binary_relevant(labels: dict[str, int]) -> set[str]:
    """Course ids with graded gain >= 1 count as relevant for binary metrics."""
    return {cid for cid, gain in labels.items() if gain >= 1}
