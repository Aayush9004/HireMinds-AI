"""
Pydantic schemas for Resume upload, retrieval, and candidate correction workflows.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ResumeCorrectionRequest(BaseModel):
    """
    Schema allowing candidates to correct, refine, or add extracted skills and details.
    """
    skills: Optional[List[str]] = Field(None, description="Corrected or added technical skills")
    education: Optional[List[Dict[str, Any]]] = Field(None, description="Corrected education records")
    experience: Optional[Dict[str, Any]] = Field(None, description="Corrected experience summary")
    projects: Optional[List[Dict[str, Any]]] = Field(None, description="Corrected projects list")
    notes: Optional[str] = Field(None, description="Candidate remarks on the corrections")


class ResumeResponse(BaseModel):
    """
    Summary schema for resume metadata and parsed NLP outputs.
    """
    id: int
    user_id: int
    filename: str
    file_size: int
    content_hash: str
    extracted_skills: List[str]
    extracted_education: List[Dict[str, Any]]
    extracted_experience: Dict[str, Any]
    extracted_projects: List[Dict[str, Any]]
    candidate_corrected_data: Optional[Dict[str, Any]] = None
    is_reviewed_by_candidate: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeDetailResponse(ResumeResponse):
    """
    Detailed resume schema including the complete extracted raw text.
    """
    raw_text: str
