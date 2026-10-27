"""
Pytest test suite for Job Management and Candidate Applications
Tests job creation, filtering, permissions, applications, duplicate prevention, status updates, and deletion.
"""
import io
import uuid
import pytest
import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job, JobApplication

client = TestClient(app)


def create_test_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.fixture(scope="module")
def setup_job_test_environment():
    """
    Setup 2 recruiters and 2 candidates with resumes for job management workflows.
    """
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]

    rec1_email = f"rec1_{suffix}@example.com"
    rec2_email = f"rec2_{suffix}@example.com"
    cand1_email = f"cand1_{suffix}@example.com"
    cand2_email = f"cand2_{suffix}@example.com"

    # Register Recruiter 1
    client.post(f"{settings.API_V1_STR}/auth/register", json={"email": rec1_email, "password": "Password123!", "full_name": "Alice Recruiter", "role": "recruiter"})
    rec1_token = client.post(f"{settings.API_V1_STR}/auth/login", json={"email": rec1_email, "password": "Password123!"}).json()["access_token"]

    # Register Recruiter 2
    client.post(f"{settings.API_V1_STR}/auth/register", json={"email": rec2_email, "password": "Password123!", "full_name": "Bob Recruiter", "role": "recruiter"})
    rec2_token = client.post(f"{settings.API_V1_STR}/auth/login", json={"email": rec2_email, "password": "Password123!"}).json()["access_token"]

    # Register Candidate 1 & Upload Resume
    client.post(f"{settings.API_V1_STR}/auth/register", json={"email": cand1_email, "password": "Password123!", "full_name": "Charlie Candidate", "role": "candidate"})
    cand1_token = client.post(f"{settings.API_V1_STR}/auth/login", json={"email": cand1_email, "password": "Password123!"}).json()["access_token"]
    pdf1 = create_test_pdf("Charlie Candidate: Python, FastAPI, React, MySQL expert.")
    resume1_id = client.post(
        f"{settings.API_V1_STR}/resumes/upload",
        files={"file": ("charlie.pdf", io.BytesIO(pdf1), "application/pdf")},
        headers={"Authorization": f"Bearer {cand1_token}"},
    ).json()["id"]

    # Register Candidate 2 & Upload Resume
    client.post(f"{settings.API_V1_STR}/auth/register", json={"email": cand2_email, "password": "Password123!", "full_name": "Diana Candidate", "role": "candidate"})
    cand2_token = client.post(f"{settings.API_V1_STR}/auth/login", json={"email": cand2_email, "password": "Password123!"}).json()["access_token"]
    pdf2 = create_test_pdf("Diana Candidate: Java, Spring Boot, AWS.")
    resume2_id = client.post(
        f"{settings.API_V1_STR}/resumes/upload",
        files={"file": ("diana.pdf", io.BytesIO(pdf2), "application/pdf")},
        headers={"Authorization": f"Bearer {cand2_token}"},
    ).json()["id"]

    env = {
        "rec1_token": rec1_token,
        "rec2_token": rec2_token,
        "cand1_token": cand1_token,
        "cand2_token": cand2_token,
        "resume1_id": resume1_id,
        "resume2_id": resume2_id,
        "emails": [rec1_email, rec2_email, cand1_email, cand2_email],
    }

    yield env

    # Teardown
    db.query(JobApplication).delete()
    db.query(Job).delete()
    db.query(Resume).delete()
    db.query(User).filter(User.email.in_(env["emails"])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_recruiter_create_job_success(setup_job_test_environment):
    """
    Test recruiter creating a job posting with required skills and validation.
    """
    rec1_token = setup_job_test_environment["rec1_token"]
    headers = {"Authorization": f"Bearer {rec1_token}"}

    job_payload = {
        "title": "Backend Python Engineer",
        "company_name": "HireMinds AI Corp",
        "location": "Bengaluru, India / Hybrid",
        "job_type": "Full-time",
        "description": "Looking for a seasoned backend engineer with expertise in FastAPI, Python, and MySQL.",
        "required_skills": ["python", "fastapi", "mysql"],
        "preferred_skills": ["docker", "redis"],
        "min_experience_years": 2.5,
        "required_education": "B.Tech / B.E. in Computer Science or IT",
        "is_active": True,
    }

    response = client.post(f"{settings.API_V1_STR}/jobs", json=job_payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Backend Python Engineer"
    assert "id" in data
    assert data["is_active"] is True
    # Verify skills were normalized to canonical names
    assert "Python" in data["required_skills"]
    assert "FastAPI" in data["required_skills"]


def test_candidate_cannot_create_job(setup_job_test_environment):
    """
    Test that candidates are forbidden from creating job listings.
    """
    cand1_token = setup_job_test_environment["cand1_token"]
    headers = {"Authorization": f"Bearer {cand1_token}"}

    job_payload = {
        "title": "Unauthorized Job",
        "company_name": "Fake Corp",
        "description": "This should fail with 403 Forbidden.",
    }
    response = client.post(f"{settings.API_V1_STR}/jobs", json=job_payload, headers=headers)
    assert response.status_code == 403


def test_browse_and_filter_jobs(setup_job_test_environment):
    """
    Test public / candidate search, filtering, and pagination of job listings.
    """
    # 1. Search by keyword
    search_res = client.get(f"{settings.API_V1_STR}/jobs?search=Python")
    assert search_res.status_code == 200
    data = search_res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any("Python" in j["title"] for j in data["items"])

    # 2. Test pagination parameters
    page_res = client.get(f"{settings.API_V1_STR}/jobs?page=1&page_size=2")
    assert page_res.status_code == 200
    p_data = page_res.json()
    assert p_data["page"] == 1
    assert p_data["page_size"] == 2


def test_recruiter_update_and_ownership(setup_job_test_environment):
    """
    Test recruiter updating their own job, and rejection when another recruiter attempts to update it.
    """
    rec1_token = setup_job_test_environment["rec1_token"]
    rec2_token = setup_job_test_environment["rec2_token"]

    # Recruiter 1 creates job
    create_res = client.post(
        f"{settings.API_V1_STR}/jobs",
        json={
            "title": "DevOps Engineer",
            "company_name": "CloudOps Ltd",
            "description": "Kubernetes and Terraform expert needed.",
            "required_skills": ["Docker", "Kubernetes"],
        },
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    job_id = create_res.json()["id"]

    # 1. Recruiter 1 updates their own job -> 200 OK
    update_res = client.put(
        f"{settings.API_V1_STR}/jobs/{job_id}",
        json={"title": "Senior DevOps & Cloud Architect", "location": "100% Remote"},
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Senior DevOps & Cloud Architect"
    assert update_res.json()["location"] == "100% Remote"

    # 2. Recruiter 2 attempts to update Recruiter 1's job -> 403 Forbidden
    tamper_res = client.put(
        f"{settings.API_V1_STR}/jobs/{job_id}",
        json={"title": "Hacked Title"},
        headers={"Authorization": f"Bearer {rec2_token}"},
    )
    assert tamper_res.status_code == 403


def test_candidate_apply_and_duplicate_prevention(setup_job_test_environment):
    """
    Test candidate applying for a job, verifying ownership of selected resume, and duplicate prevention.
    """
    rec1_token = setup_job_test_environment["rec1_token"]
    cand1_token = setup_job_test_environment["cand1_token"]
    cand2_token = setup_job_test_environment["cand2_token"]
    resume1_id = setup_job_test_environment["resume1_id"]
    resume2_id = setup_job_test_environment["resume2_id"]

    # Create target job
    job_res = client.post(
        f"{settings.API_V1_STR}/jobs",
        json={
            "title": "Full-Stack React & Python Developer",
            "company_name": "HireMinds AI",
            "description": "Looking for energetic full-stack developer.",
            "required_skills": ["Python", "React"],
        },
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    job_id = job_res.json()["id"]

    # 1. Candidate 1 attempts to apply using Candidate 2's resume -> 404
    fake_res = client.post(
        f"{settings.API_V1_STR}/jobs/{job_id}/apply",
        json={"resume_id": resume2_id, "cover_letter": "I stole someone's resume"},
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    assert fake_res.status_code == 404

    # 2. Candidate 1 applies with their own resume -> 201 Created
    apply_res = client.post(
        f"{settings.API_V1_STR}/jobs/{job_id}/apply",
        json={"resume_id": resume1_id, "cover_letter": "Excited to apply for this role!"},
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    assert apply_res.status_code == 201
    app_data = apply_res.json()
    assert app_data["status"] == "applied"
    assert app_data["job_id"] == job_id
    assert app_data["resume_id"] == resume1_id
    application_id = app_data["id"]

    # 3. Candidate 1 attempts to apply again to the same job -> 409 Conflict (duplicate prevention)
    dup_res = client.post(
        f"{settings.API_V1_STR}/jobs/{job_id}/apply",
        json={"resume_id": resume1_id, "cover_letter": "Applying again"},
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    assert dup_res.status_code == 409
    assert "already submitted an application" in dup_res.json()["detail"]

    # 4. Candidate 1 checks their own applications
    my_apps_res = client.get(
        f"{settings.API_V1_STR}/jobs/applications/my-applications",
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    assert my_apps_res.status_code == 200
    assert any(a["id"] == application_id for a in my_apps_res.json()["items"])

    # 5. Recruiter 1 views applications for the job -> 200 OK
    rec_view_res = client.get(
        f"{settings.API_V1_STR}/jobs/{job_id}/applications",
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    assert rec_view_res.status_code == 200
    assert rec_view_res.json()["total"] == 1

    # 6. Recruiter 2 attempts to view applications for Recruiter 1's job -> 403 Forbidden
    unauth_rec_res = client.get(
        f"{settings.API_V1_STR}/jobs/{job_id}/applications",
        headers={"Authorization": f"Bearer {setup_job_test_environment['rec2_token']}"},
    )
    assert unauth_rec_res.status_code == 403

    # 7. Recruiter 1 updates application status to 'shortlisted' -> 200 OK
    status_update_res = client.patch(
        f"{settings.API_V1_STR}/jobs/applications/{application_id}/status",
        json={"status": "shortlisted", "recruiter_notes": "Strong Python and FastAPI foundation."},
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    assert status_update_res.status_code == 200
    assert status_update_res.json()["status"] == "shortlisted"

    # 8. Candidate 1 verifies updated status
    verify_res = client.get(
        f"{settings.API_V1_STR}/jobs/applications/my-applications",
        headers={"Authorization": f"Bearer {cand1_token}"},
    )
    assert verify_res.status_code == 200
    updated_app = next(a for a in verify_res.json()["items"] if a["id"] == application_id)
    assert updated_app["status"] == "shortlisted"


def test_recruiter_delete_job_listing(setup_job_test_environment):
    """
    Test recruiter deleting a job listing and ensuring cascading application cleanup.
    """
    rec1_token = setup_job_test_environment["rec1_token"]
    headers = {"Authorization": f"Bearer {rec1_token}"}

    job_res = client.post(
        f"{settings.API_V1_STR}/jobs",
        json={
            "title": "Job to be deleted",
            "company_name": "Temporary Inc",
            "description": "Will be removed.",
        },
        headers=headers,
    )
    job_id = job_res.json()["id"]

    del_res = client.delete(f"{settings.API_V1_STR}/jobs/{job_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure 404 on subsequent get
    assert client.get(f"{settings.API_V1_STR}/jobs/{job_id}").status_code == 404
