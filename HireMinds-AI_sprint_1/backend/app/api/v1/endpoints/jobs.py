"""
Job Management and Application endpoints for HireMinds AI
Supports recruiter job CRUD, candidate browsing/filtering, applications, and status updates.
"""
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.api.deps import (
    get_current_user,
    require_recruiter,
    require_candidate,
    check_resource_owner,
)
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.models.job import Job, JobApplication, ApplicationStatus
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    PaginatedJobsResponse,
    JobApplicationCreate,
    JobApplicationStatusUpdate,
    JobApplicationResponse,
    PaginatedApplicationsResponse,
)
from app.services.skill_extractor import extract_skills_from_text

router = APIRouter()


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Job Posting",
    description="Recruiters can create job listings with required skills, experience, and educational requirements.",
)
def create_job(
    job_in: JobCreate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> Job:
    # Normalize required and preferred skills
    normalized_req = extract_skills_from_text(" ".join(job_in.required_skills)) if job_in.required_skills else []
    normalized_pref = extract_skills_from_text(" ".join(job_in.preferred_skills)) if job_in.preferred_skills else []

    new_job = Job(
        recruiter_id=current_user.id,
        title=job_in.title.strip(),
        company_name=job_in.company_name.strip(),
        location=job_in.location.strip(),
        job_type=job_in.job_type.strip(),
        description=job_in.description.strip(),
        required_skills=normalized_req or job_in.required_skills,
        preferred_skills=normalized_pref or job_in.preferred_skills,
        min_experience_years=job_in.min_experience_years,
        required_education=job_in.required_education.strip(),
        is_active=job_in.is_active,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    status_code=status.HTTP_200_OK,
    summary="Browse and Filter Job Listings",
    description="Search active jobs by keyword, skills, location, job type, and experience with pagination.",
)
def list_jobs(
    search: Optional[str] = Query(None, description="Search in title, description, or company"),
    location: Optional[str] = Query(None, description="Filter by location"),
    job_type: Optional[str] = Query(None, description="Filter by job type (Full-time, Internship, etc.)"),
    min_exp: Optional[float] = Query(None, description="Maximum required years of experience"),
    is_active: bool = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
) -> PaginatedJobsResponse:
    query = db.query(Job).filter(Job.is_active == is_active)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_fmt),
                Job.description.ilike(search_fmt),
                Job.company_name.ilike(search_fmt),
            )
        )

    if location:
        query = query.filter(Job.location.ilike(f"%{location.strip()}%"))

    if job_type:
        query = query.filter(Job.job_type.ilike(f"%{job_type.strip()}%"))

    if min_exp is not None:
        query = query.filter(Job.min_experience_years <= min_exp)

    total = query.count()
    items = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedJobsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/my-postings",
    response_model=List[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="List Recruiter's Own Job Postings",
)
def list_my_job_postings(
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> List[Job]:
    return db.query(Job).filter(Job.recruiter_id == current_user.id).order_by(Job.created_at.desc()).all()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Details",
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found.",
        )
    return job


@router.put(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a Job Listing",
    description="Recruiters can update job listings they own.",
)
def update_job(
    job_id: int,
    job_update: JobUpdate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found.",
        )

    check_resource_owner(resource_owner_id=job.recruiter_id, current_user=current_user)

    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Job Listing",
    description="Recruiters can delete job listings they own.",
)
def delete_job(
    job_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found.",
        )

    check_resource_owner(resource_owner_id=job.recruiter_id, current_user=current_user)

    db.delete(job)
    db.commit()
    return {"message": "Job listing deleted successfully.", "id": job_id}


# ==========================================
# JOB APPLICATIONS WORKFLOW
# ==========================================

@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a Job",
    description="Candidates apply for a specific job listing using one of their uploaded resumes.",
)
def apply_for_job(
    job_id: int,
    app_in: JobApplicationCreate,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> JobApplicationResponse:
    # 1. Verify job exists and is active
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found.",
        )
    if not job.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job listing is closed and no longer accepting applications.",
        )

    # 2. Verify resume belongs to the candidate
    resume = db.query(Resume).filter(Resume.id == app_in.resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected resume was not found or does not belong to you.",
        )

    # 3. Check for duplicate application
    existing_app = db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.candidate_id == current_user.id,
    ).first()
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted an application for this job.",
        )

    # 4. Create application
    application = JobApplication(
        job_id=job_id,
        candidate_id=current_user.id,
        resume_id=resume.id,
        cover_letter=app_in.cover_letter.strip() if app_in.cover_letter else None,
        status=ApplicationStatus.APPLIED,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return JobApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        resume_id=application.resume_id,
        cover_letter=application.cover_letter,
        status=application.status,
        recruiter_notes=application.recruiter_notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        job_title=job.title,
        company_name=job.company_name,
        candidate_name=current_user.full_name,
        candidate_email=current_user.email,
    )


@router.get(
    "/applications/my-applications",
    response_model=PaginatedApplicationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Track Candidate's Own Job Applications",
)
def list_my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> PaginatedApplicationsResponse:
    query = db.query(JobApplication).filter(JobApplication.candidate_id == current_user.id)
    total = query.count()
    apps = query.order_by(JobApplication.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    items = []
    for app in apps:
        items.append(
            JobApplicationResponse(
                id=app.id,
                job_id=app.job_id,
                candidate_id=app.candidate_id,
                resume_id=app.resume_id,
                cover_letter=app.cover_letter,
                status=app.status,
                recruiter_notes=app.recruiter_notes,
                created_at=app.created_at,
                updated_at=app.updated_at,
                job_title=app.job.title if app.job else None,
                company_name=app.job.company_name if app.job else None,
                candidate_name=current_user.full_name,
                candidate_email=current_user.email,
            )
        )

    return PaginatedApplicationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{job_id}/applications",
    response_model=PaginatedApplicationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Recruiter View Applications for a Job",
    description="Recruiter can view all candidates who applied for their job listing.",
)
def list_job_applicants(
    job_id: int,
    status_filter: Optional[ApplicationStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> PaginatedApplicationsResponse:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found.",
        )

    check_resource_owner(resource_owner_id=job.recruiter_id, current_user=current_user)

    query = db.query(JobApplication).filter(JobApplication.job_id == job_id)
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)

    total = query.count()
    apps = query.order_by(JobApplication.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    items = []
    for app in apps:
        items.append(
            JobApplicationResponse(
                id=app.id,
                job_id=app.job_id,
                candidate_id=app.candidate_id,
                resume_id=app.resume_id,
                cover_letter=app.cover_letter,
                status=app.status,
                recruiter_notes=app.recruiter_notes,
                created_at=app.created_at,
                updated_at=app.updated_at,
                job_title=job.title,
                company_name=job.company_name,
                candidate_name=app.candidate.full_name if app.candidate else None,
                candidate_email=app.candidate.email if app.candidate else None,
            )
        )

    return PaginatedApplicationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/applications/{application_id}/status",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application Status",
    description="Recruiter updates application status (shortlisted, rejected, interview scheduled, etc.).",
)
def update_application_status(
    application_id: int,
    status_in: JobApplicationStatusUpdate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> JobApplicationResponse:
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found.",
        )

    # Check that current recruiter owns the job for which the application was submitted
    check_resource_owner(resource_owner_id=application.job.recruiter_id, current_user=current_user)

    application.status = status_in.status
    if status_in.recruiter_notes is not None:
        application.recruiter_notes = status_in.recruiter_notes

    db.commit()
    db.refresh(application)

    return JobApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        resume_id=application.resume_id,
        cover_letter=application.cover_letter,
        status=application.status,
        recruiter_notes=application.recruiter_notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        job_title=application.job.title,
        company_name=application.job.company_name,
        candidate_name=application.candidate.full_name if application.candidate else None,
        candidate_email=application.candidate.email if application.candidate else None,
    )
