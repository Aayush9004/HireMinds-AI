"""
Pytest test suite for Resume Processing, PyMuPDF Parsing, and Skill Extraction
Tests valid PDF extraction, malformed PDFs, empty PDFs, candidate review/correction, RBAC, and ownership.
"""
import io
import uuid
import pytest
import fitz  # PyMuPDF
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.resume import Resume

client = TestClient(app)


def create_sample_pdf(text_content: str) -> bytes:
    """
    Helper function to generate a valid, in-memory PDF document using PyMuPDF.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture(scope="module")
def setup_users():
    """
    Create candidate 1, candidate 2, and a recruiter for resume tests.
    """
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    cand1_email = f"cand1_res_{suffix}@example.com"
    cand2_email = f"cand2_res_{suffix}@example.com"
    rec_email = f"rec_res_{suffix}@example.com"

    # Register Candidate 1
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": cand1_email, "password": "Password123!", "full_name": "Candidate One", "role": "candidate"},
    )
    token1 = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": cand1_email, "password": "Password123!"},
    ).json()["access_token"]

    # Register Candidate 2
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": cand2_email, "password": "Password123!", "full_name": "Candidate Two", "role": "candidate"},
    )
    token2 = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": cand2_email, "password": "Password123!"},
    ).json()["access_token"]

    # Register Recruiter
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": rec_email, "password": "Password123!", "full_name": "Recruiter One", "role": "recruiter"},
    )
    rec_token = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": rec_email, "password": "Password123!"},
    ).json()["access_token"]

    user_data = {
        "token1": token1,
        "token2": token2,
        "rec_token": rec_token,
        "emails": [cand1_email, cand2_email, rec_email],
    }

    yield user_data

    # Cleanup
    db.query(Resume).delete()
    db.query(User).filter(User.email.in_(user_data["emails"])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_resume_upload_and_extraction_success(setup_users):
    """
    Test uploading a valid PDF resume and extracting skills, education, experience, and projects.
    """
    token1 = setup_users["token1"]

    sample_resume_text = """
    Aayush Sharma
    Email: aayush@example.com | Phone: +91 9876543210

    PROFESSIONAL SUMMARY
    Full-Stack Developer with 2+ years of experience building scalable applications using Python, FastAPI, and React.

    TECHNICAL SKILLS
    Languages: Python, TypeScript, JavaScript, SQL
    Frameworks & Tools: FastAPI, React, Node.js, Docker, Kubernetes, Git, Tailwind CSS
    Databases: MySQL, PostgreSQL, MongoDB, Redis
    AI & ML: Machine Learning, Scikit-Learn, PyTorch, spaCy

    EDUCATION
    B.Tech in Information Technology
    ABC Institute of Technology, 2024
    CGPA: 8.8 / 10

    EXPERIENCE
    Software Engineer at TechCorp Solutions (2022 - Present)
    - Developed REST APIs using FastAPI and MySQL.
    - Containerized microservices with Docker and Kubernetes.

    PROJECTS
    HireMinds AI
    Built an AI-powered resume screening and mock interview assessment platform using FastAPI, React, and MySQL.
    """

    pdf_bytes = create_sample_pdf(sample_resume_text)
    files = {"file": ("aayush_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    headers = {"Authorization": f"Bearer {token1}"}

    response = client.post(f"{settings.API_V1_STR}/resumes/upload", files=files, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "aayush_resume.pdf"
    assert data["file_size"] > 0
    assert "content_hash" in data

    # Verify extracted skills
    skills = data["extracted_skills"]
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "React" in skills
    assert "TypeScript" in skills
    assert "Docker" in skills
    assert "MySQL" in skills

    # Verify education
    education = data["extracted_education"]
    assert len(education) > 0
    assert any("B.Tech" in str(edu) for edu in education)

    # Verify experience
    exp = data["extracted_experience"]
    assert exp["estimated_years"] == 2.0


def test_invalid_file_extension_rejection(setup_users):
    """
    Test that uploading non-PDF files is rejected with HTTP 400.
    """
    token1 = setup_users["token1"]
    files = {"file": ("resume.docx", io.BytesIO(b"dummy word doc content"), "application/vnd.openxmlformats")}
    headers = {"Authorization": f"Bearer {token1}"}

    response = client.post(f"{settings.API_V1_STR}/resumes/upload", files=files, headers=headers)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_malformed_and_empty_pdf_rejection(setup_users):
    """
    Test that corrupt or empty PDFs return HTTP 422 Unprocessable Entity.
    """
    token1 = setup_users["token1"]
    headers = {"Authorization": f"Bearer {token1}"}

    # 1. Corrupted PDF
    corrupt_bytes = b"%PDF-1.4\ncorrupted bytes that cannot be opened as pdf"
    files_corrupt = {"file": ("corrupt.pdf", io.BytesIO(corrupt_bytes), "application/pdf")}
    res_corrupt = client.post(f"{settings.API_V1_STR}/resumes/upload", files=files_corrupt, headers=headers)
    assert res_corrupt.status_code == 422

    # 2. Empty PDF (0 pages / 0 text)
    empty_doc = fitz.open()
    empty_doc.new_page()  # Blank page with no text
    empty_pdf_bytes = empty_doc.tobytes()
    empty_doc.close()

    files_empty = {"file": ("empty.pdf", io.BytesIO(empty_pdf_bytes), "application/pdf")}
    res_empty = client.post(f"{settings.API_V1_STR}/resumes/upload", files=files_empty, headers=headers)
    assert res_empty.status_code == 422
    assert "No selectable text" in res_empty.json()["detail"]


def test_candidate_review_and_correction(setup_users):
    """
    Test that candidates can review, add missing skills, and correct extracted information.
    """
    token1 = setup_users["token1"]
    headers = {"Authorization": f"Bearer {token1}"}

    # Upload baseline resume
    pdf_bytes = create_sample_pdf("Software Developer with Python and SQL experience.")
    upload_res = client.post(
        f"{settings.API_V1_STR}/resumes/upload",
        files={"file": ("skills.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # Candidate submits corrections adding additional skills
    correction_payload = {
        "skills": ["Python", "SQL", "FastAPI", "Next.js", "Docker"],
        "notes": "Added unlisted freelance skills",
    }
    correct_res = client.put(
        f"{settings.API_V1_STR}/resumes/{resume_id}/correct",
        json=correction_payload,
        headers=headers,
    )
    assert correct_res.status_code == 200

    corrected_data = correct_res.json()
    assert corrected_data["is_reviewed_by_candidate"] is True
    assert "FastAPI" in corrected_data["extracted_skills"]
    assert "Next.js" in corrected_data["extracted_skills"]
    assert corrected_data["candidate_corrected_data"]["notes"] == "Added unlisted freelance skills"


def test_resume_privacy_and_access_control(setup_users):
    """
    Test that candidates cannot access another candidate's resume, while recruiters can view it.
    """
    token1 = setup_users["token1"]
    token2 = setup_users["token2"]
    rec_token = setup_users["rec_token"]

    # Candidate 1 uploads resume
    pdf_bytes = create_sample_pdf("Candidate One Private Resume with React and Node.js.")
    upload_res = client.post(
        f"{settings.API_V1_STR}/resumes/upload",
        files={"file": ("cand1.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    resume_id = upload_res.json()["id"]

    # 1. Candidate 1 accesses own resume -> 200 OK
    res_own = client.get(
        f"{settings.API_V1_STR}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res_own.status_code == 200
    assert "React" in res_own.json()["raw_text"]

    # 2. Candidate 2 attempts to view Candidate 1's resume -> 403 Forbidden
    res_other = client.get(
        f"{settings.API_V1_STR}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res_other.status_code == 403
    assert "Access denied" in res_other.json()["detail"]

    # 3. Candidate 2 attempts to correct Candidate 1's resume -> 403 Forbidden
    res_tamper = client.put(
        f"{settings.API_V1_STR}/resumes/{resume_id}/correct",
        json={"skills": ["HackedSkill"]},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res_tamper.status_code == 403

    # 4. Recruiter can view candidate's resume -> 200 OK
    res_recruiter = client.get(
        f"{settings.API_V1_STR}/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {rec_token}"},
    )
    assert res_recruiter.status_code == 200


def test_resume_deletion(setup_users):
    """
    Test that candidates can delete their uploaded resumes.
    """
    token1 = setup_users["token1"]
    headers = {"Authorization": f"Bearer {token1}"}

    pdf_bytes = create_sample_pdf("Resume to be deleted shortly.")
    upload_res = client.post(
        f"{settings.API_V1_STR}/resumes/upload",
        files={"file": ("to_delete.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    resume_id = upload_res.json()["id"]

    # Delete resume
    del_res = client.delete(f"{settings.API_V1_STR}/resumes/{resume_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure resume no longer exists -> 404
    get_res = client.get(f"{settings.API_V1_STR}/resumes/{resume_id}", headers=headers)
    assert get_res.status_code == 404
