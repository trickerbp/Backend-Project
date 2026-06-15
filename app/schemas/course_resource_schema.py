from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CourseResourceResponse(BaseModel):
    id: str
    course_id: str
    uploaded_by: str
    file_name: str
    original_file_name: str
    file_type: str
    mime_type: str
    file_path: str
    file_size: int
    processing_status: str
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    extracted_title: Optional[str] = None
    extracted_description: Optional[str] = None
    extracted_level: Optional[str] = None
    extracted_skills: list[str] = []
    extracted_topics: list[str] = []
    extracted_objectives: list[str] = []
    extracted_prerequisites: list[str] = []
    extracted_tools: list[str] = []
    extracted_duration_hours: Optional[int] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
