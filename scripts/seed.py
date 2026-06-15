from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.mongodb import create_indexes  # noqa: E402


DEFAULT_PASSWORD = "123456"

ADMIN_EMAIL = "admin@gmail.com"
TEACHER_EMAIL = "teacher@gmail.com"
STUDENT_EMAIL = "student@gmail.com"


async def upsert_user(
    db: AsyncIOMotorDatabase,
    name: str,
    email: str,
    role: str,
) -> Any:
    now = datetime.now(timezone.utc)
    password_hash = hash_password(DEFAULT_PASSWORD)

    existing_user = await db.users.find_one({"email": email})
    if existing_user is not None:
        await db.users.update_one(
            {"_id": existing_user["_id"]},
            {
                "$set": {
                    "name": name,
                    "password_hash": password_hash,
                    "role": role,
                    "updated_at": now,
                }
            },
        )
        return existing_user["_id"]

    result = await db.users.insert_one(
        {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "created_at": now,
            "updated_at": now,
        }
    )
    return result.inserted_id


def sample_courses(teacher_id: Any) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "title": "Lập trình Web cơ bản",
            "course_code": "WEB101",
            "instructor": "ThS. Nguyễn Văn Bình",
            "description": (
                "Khóa học nhập môn phát triển web, trang bị nền tảng "
                "HTML, CSS và JavaScript để xây dựng giao diện website "
                "tĩnh và tương tác cơ bản. Học viên thực hành dựng layout, "
                "xử lý sự kiện DOM và làm quen quy trình phát triển frontend."
            ),
            "level": "beginner",
            "target_goals": ["Frontend Developer", "Web Developer"],
            "manual_tags": ["HTML", "CSS", "JavaScript", "Frontend"],
            "tools": ["VS Code", "Chrome DevTools", "Git"],
            "extracted_skills": [
                "HTML",
                "CSS",
                "JavaScript",
                "Responsive Design",
                "DOM Manipulation",
            ],
            "extracted_topics": [
                "Cấu trúc HTML",
                "Bố cục CSS và Flexbox",
                "Thao tác DOM với JavaScript",
                "Xử lý sự kiện trên trình duyệt",
            ],
            "duration_hours": 30,
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "title": "Cơ sở dữ liệu MongoDB",
            "course_code": "DB201",
            "instructor": "ThS. Trần Thị Cúc",
            "description": (
                "Khóa học cung cấp kiến thức thiết kế dữ liệu NoSQL với "
                "MongoDB, từ mô hình document, truy vấn, đến lập chỉ mục và "
                "tối ưu hiệu năng. Học viên thực hành thiết kế schema và "
                "viết truy vấn aggregation cho ứng dụng thực tế."
            ),
            "level": "intermediate",
            "target_goals": ["Backend Developer", "Data Engineer"],
            "manual_tags": ["MongoDB", "NoSQL", "Database"],
            "tools": ["MongoDB Compass", "mongosh", "MongoDB Atlas"],
            "extracted_skills": [
                "MongoDB",
                "NoSQL",
                "Database Design",
                "Aggregation Pipeline",
                "Indexing",
            ],
            "extracted_topics": [
                "Mô hình dữ liệu document",
                "Truy vấn CRUD",
                "Aggregation Pipeline",
                "Lập chỉ mục và tối ưu truy vấn",
            ],
            "duration_hours": 25,
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "title": "Lập trình Python ứng dụng",
            "course_code": "PY150",
            "instructor": "ThS. Lê Văn Dũng",
            "description": (
                "Khóa học lập trình Python hướng ứng dụng thực tế, tập "
                "trung vào xử lý dữ liệu, đọc ghi file, gọi API và tự động "
                "hóa công việc. Học viên xây dựng các script backend nhỏ và "
                "làm quen lập trình hướng đối tượng."
            ),
            "level": "beginner",
            "target_goals": ["Python Developer", "Automation Engineer"],
            "manual_tags": ["Python", "OOP", "Automation"],
            "tools": ["Python 3", "VS Code", "Jupyter Notebook"],
            "extracted_skills": [
                "Python",
                "OOP",
                "File I/O",
                "REST API",
                "Automation",
            ],
            "extracted_topics": [
                "Cú pháp và kiểu dữ liệu Python",
                "Lập trình hướng đối tượng",
                "Đọc ghi file và xử lý dữ liệu",
                "Gọi API và tự động hóa",
            ],
            "duration_hours": 35,
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "title": "Phân tích dữ liệu với SQL",
            "course_code": "SQL220",
            "instructor": "ThS. Phạm Thị Hà",
            "description": (
                "Khóa học phân tích dữ liệu quan hệ bằng SQL, từ truy vấn "
                "cơ bản đến JOIN nhiều bảng, hàm tổng hợp và window function. "
                "Học viên thực hành phân tích doanh thu và xây dựng báo cáo "
                "phục vụ ra quyết định kinh doanh."
            ),
            "level": "intermediate",
            "target_goals": ["Data Analyst", "BI Developer"],
            "manual_tags": ["SQL", "Data Analysis", "Database"],
            "tools": ["PostgreSQL", "DBeaver", "MySQL Workbench"],
            "extracted_skills": [
                "SQL",
                "Data Analysis",
                "JOIN",
                "Aggregation",
                "Window Functions",
            ],
            "extracted_topics": [
                "Truy vấn SELECT và lọc dữ liệu",
                "JOIN nhiều bảng",
                "Hàm tổng hợp và GROUP BY",
                "Window function và phân tích doanh thu",
            ],
            "duration_hours": 28,
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "title": "Nhập môn Machine Learning",
            "course_code": "ML300",
            "instructor": "TS. Hoàng Minh Quân",
            "description": (
                "Khóa học nền tảng học máy với Python và scikit-learn, bao "
                "gồm quy trình train/test split, hồi quy, phân loại và đánh "
                "giá mô hình. Học viên thực hành xây dựng pipeline ML cơ bản "
                "và lưu ý về sử dụng mô hình có trách nhiệm."
            ),
            "level": "advanced",
            "target_goals": ["ML Engineer", "Data Scientist"],
            "manual_tags": ["Machine Learning", "Python", "Data Science"],
            "tools": ["Python 3", "scikit-learn", "Jupyter Notebook"],
            "extracted_skills": [
                "Machine Learning",
                "scikit-learn",
                "Regression",
                "Classification",
                "Model Evaluation",
            ],
            "extracted_topics": [
                "Train/test split",
                "Hồi quy tuyến tính",
                "Phân loại và đánh giá mô hình",
                "Pipeline học máy cơ bản",
            ],
            "duration_hours": 40,
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ]


async def upsert_courses(
    db: AsyncIOMotorDatabase,
    courses: list[dict[str, Any]],
) -> None:
    for course_doc in courses:
        update_payload = {
            key: value
            for key, value in course_doc.items()
            if key != "created_at"
        }
        await db.courses.update_one(
            {"course_code": course_doc["course_code"]},
            {
                "$set": {
                    **update_payload,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": course_doc["created_at"]},
            },
            upsert=True,
        )


async def upsert_student_profile(
    db: AsyncIOMotorDatabase,
    student_id: Any,
) -> None:
    now = datetime.now(timezone.utc)
    profile = {
        "student_id": student_id,
        "source_type": "manual_form",
        "career_goal": "Frontend Developer",
        "current_level": "beginner",
        "current_skills": ["HTML", "CSS"],
        "desired_skills": ["React", "JavaScript", "API"],
        "interested_topics": ["Frontend", "Web Development"],
        "hours_per_week": 8,
        "learning_format": "online",
        "uploaded_file_name": None,
        "file_path": None,
        "raw_text": None,
        "cleaned_text": None,
        "updated_at": now,
    }
    await db.student_profiles.update_one(
        {"student_id": student_id},
        {
            "$set": profile,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def seed() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]

    try:
        await create_indexes(db)

        await upsert_user(
            db,
            name="Admin EduMatch",
            email=ADMIN_EMAIL,
            role="admin",
        )
        teacher_id = await upsert_user(
            db,
            name="Teacher Demo",
            email=TEACHER_EMAIL,
            role="teacher",
        )
        student_id = await upsert_user(
            db,
            name="Student Demo",
            email=STUDENT_EMAIL,
            role="student",
        )

        await upsert_courses(db, sample_courses(teacher_id))
        await upsert_student_profile(db, student_id)

        print("Seed completed successfully.")
        print(f"Admin account:   {ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
        print(f"Teacher account: {TEACHER_EMAIL} / {DEFAULT_PASSWORD}")
        print(f"Student account: {STUDENT_EMAIL} / {DEFAULT_PASSWORD}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed())
