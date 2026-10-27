"""
Resume upload, parsing, inspection, and correction endpoints for HireMinds AI
"""
import hashlib
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user, require_candidate, check_resource_owner
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeDetailResponse, ResumeCorrectionRequest
from app.services.pdf_parser import extract_text_from_pdf, PDFParsingError
from app.services.skill_extractor import extract_skills_from_text
from app.services.section_extractor import extract_education, extract_experience, extract_projects

router = APIRouter()

# Directory for secure local resume storage
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Parse PDF Resume",
    description="Uploads a candidate PDF resume, validates integrity, extracts text via PyMuPDF, and runs NLP skill extraction.",
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> Resume:
    # 1. Validate filename and extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported.",
        )

    # 2. Read file contents
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF file is empty.",
        )

    # Max size: 10MB
    max_size_bytes = 10 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 10MB limit.",
        )

    # 3. Extract text using PyMuPDF service
    try:
        raw_text = extract_text_from_pdf(contents)
    except PDFParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PDF Processing Error: {str(exc)}",
        )

    # 4. Compute SHA-256 hash
    content_hash = hashlib.sha256(contents).hexdigest()

    # 5. Extract structured metadata (skills, education, experience, projects)
    extracted_skills = extract_skills_from_text(raw_text)
    extracted_education = extract_education(raw_text)
    extracted_experience = extract_experience(raw_text)
    extracted_projects = extract_projects(raw_text)

    # 6. Save file to disk with unique collision-free filename
    safe_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}_{os.path.basename(file.filename)}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # 7. Store in database
    resume_record = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(contents),
        content_hash=content_hash,
        raw_text=raw_text,
        extracted_skills=extracted_skills,
        extracted_education=extracted_education,
        extracted_experience=extracted_experience,
        extracted_projects=extracted_projects,
        candidate_corrected_data=None,
        is_reviewed_by_candidate=False,
    )
    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    return resume_record


@router.get(
    "/my-resumes",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authenticated Candidate's Resumes",
)
def list_my_resumes(
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> List[Resume]:
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()


@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Resume Information",
)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Enforce access permissions:
    # Candidates can only access their own resume.
    # Recruiters and Admins can view resumes.
    if current_user.role == UserRole.CANDIDATE and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot view another candidate's private resume.",
        )

    return resume


@router.put(
    "/{resume_id}/correct",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Candidate Review and Correction of Extracted Resume Details",
    description="Allows candidates to refine, add, or override extracted skills and parsed metadata.",
)
def correct_resume_details(
    resume_id: int,
    correction: ResumeCorrectionRequest,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Ensure ownership: only owner or admin can update
    check_resource_owner(resource_owner_id=resume.user_id, current_user=current_user)

    # Update candidate corrections
    correction_data = correction.model_dump(exclude_unset=True)
    resume.candidate_corrected_data = correction_data
    resume.is_reviewed_by_candidate = True

    # If candidate supplied updated skills, merge or update the primary extracted_skills
    if correction.skills is not None:
        # Deduplicate and normalize
        unique_skills = []
        for s in correction.skills:
            clean_s = s.strip()
            if clean_s and clean_s not in unique_skills:
                unique_skills.append(clean_s)
        resume.extracted_skills = unique_skills

    db.commit()
    db.refresh(resume)
    return resume


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Resume",
)
def delete_resume(
    resume_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> dict:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    check_resource_owner(resource_owner_id=resume.user_id, current_user=current_user)

    # Remove file from disk if present
    if resume.file_path and os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except OSError:
            pass

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted successfully.", "id": resume_id}
