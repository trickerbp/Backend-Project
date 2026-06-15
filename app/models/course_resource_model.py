from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COURSE_RESOURCES_COLLECTION = "course_resources"

VALID_FILE_TYPES = {"pdf", "pptx", "docx"}
VALID_PROCESSING_STATUSES = {
    "pending",
    "processing",
    "completed",
    "failed",
    "needs_ocr",
}

MIME_TYPE_BY_FILE_TYPE = {
    "pdf": "application/pdf",
    "pptx": (
        "application/vnd.openxmlformats-officedocument."
        "presentationml.presentation"
    ),
    "docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
}


def create_resource_document(
    course_id: ObjectId,
    uploaded_by: ObjectId,
    file_name: str,
    original_file_name: str,
    file_type: str,
    file_path: str,
    file_size: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "course_id": course_id,
        "uploaded_by": uploaded_by,
        "file_name": file_name,
        "original_file_name": original_file_name,
        "file_type": file_type,
        "mime_type": MIME_TYPE_BY_FILE_TYPE.get(file_type, "application/octet-stream"),
        "file_path": file_path,
        "file_size": file_size,
        "processing_status": "pending",
        'raw_text': '',
        'cleaned_text': '',
        "extracted_title": None,
        "extracted_description": None,
        "extracted_level": None,
        "extracted_skills": [],
        "extracted_topics": [],
        "extracted_objectives": [],
        "extracted_prerequisites": [],
        "extracted_tools": [],
        "extracted_duration_hours": None,
        "summary": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }


def resource_to_public(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(resource["_id"]),
        "course_id": str(resource["course_id"]),
        "uploaded_by": str(resource["uploaded_by"]),
        "file_name": resource.get("file_name"),
        "original_file_name": resource.get("original_file_name"),
        "file_type": resource.get("file_type"),
        "mime_type": resource.get("mime_type"),
        "file_path": resource.get("file_path"),
        "file_size": resource.get("file_size"),
        "processing_status": resource.get("processing_status"),
        "raw_text": resource.get("raw_text"),
        "cleaned_text": resource.get("cleaned_text"),
        "extracted_title": resource.get("extracted_title"),
        "extracted_description": resource.get("extracted_description"),
        "extracted_level": resource.get("extracted_level"),
        "extracted_skills": resource.get("extracted_skills", []),
        "extracted_topics": resource.get("extracted_topics", []),
        "extracted_objectives": resource.get("extracted_objectives", []),
        "extracted_prerequisites": resource.get("extracted_prerequisites", []),
        "extracted_tools": resource.get("extracted_tools", []),
        "extracted_duration_hours": resource.get("extracted_duration_hours"),
        "summary": resource.get("summary"),
        "error_message": resource.get("error_message"),
        "created_at": resource.get("created_at"),
        "updated_at": resource.get("updated_at"),
    }
