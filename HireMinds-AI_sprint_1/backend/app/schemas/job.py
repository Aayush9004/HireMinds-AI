"""
Pydantic schemas for Job Listings, Filtering, Applications, and Status Tracking.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.job import ApplicationStatus


class JobBase(BaseModel):
    """
    Base schema shared across Job creation and responses.
    """
    title: str = Field(..., min_length=3, max_length=200, json_schema_extra={"example": "Senior Full-Stack Engineer"})
    company_name: str = Field(..., min_length=2, max_length=200, json_schema_extra={"example": "HireMinds Technologies"})
    location: str = Field("Remote", max_length=150, json_schema_extra={"example": "Bengaluru, India / Remote"})
    job_type: str = Field("Full-time", max_length=50, json_schema_extra={"example": "Full-time"})
    description: str = Field(..., min_length=10, json_schema_extra={"example": "We are looking for an experienced developer with Python & React..."})
    required_skills: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Python", "FastAPI", "React", "MySQL"]})
    preferred_skills: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Docker", "TypeScript", "AWS"]})
    min_experience_years: float = Field(0.0, ge=0.0, json_schema_extra={"example": 2.0})
    required_education: str = Field("Bachelor's Degree", max_length=200, json_schema_extra={"example": "B.Tech in Computer Science / IT"})
    is_active: bool = Field(True, description="Whether the job listing is open for applications")


class JobCreate(JobBase):
    """Schema for recruiter job posting."""
    pass


class JobUpdate(BaseModel):
    """Schema for updating an existing job listing."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    location: Optional[str] = Field(None, max_length=150)
    job_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, min_length=10)
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience_years: Optional[float] = Field(None, ge=0.0)
    required_education: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class JobResponse(JobBase):
    """Response schema for public or recruiter job representations."""
    id: int
    recruiter_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    """Paginated list of jobs."""
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobApplicationCreate(BaseModel):
    """Schema for candidate submitting a job application."""
    resume_id: int = Field(..., description="ID of the candidate's uploaded resume")
    cover_letter: Optional[str] = Field(None, description="Optional candidate statement or cover letter")


class JobApplicationStatusUpdate(BaseModel):
    """Schema for recruiter updating application review status."""
    status: ApplicationStatus = Field(..., description="New lifecycle status")
    recruiter_notes: Optional[str] = Field(None, description="Private evaluation remarks from recruiter")


class JobApplicationResponse(BaseModel):
    """Response schema for candidate and recruiter application tracking."""
    id: int
    job_id: int
    candidate_id: int
    resume_id: int
    cover_letter: Optional[str] = None
    status: ApplicationStatus
    recruiter_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Denormalized context fields for UI convenience
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedApplicationsResponse(BaseModel):
    """Paginated list of job applications."""
    items: List[JobApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
