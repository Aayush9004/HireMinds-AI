"""
API v1 Router Aggregator
Combines all domain routers for API version 1.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, resumes, jobs, matching

api_router = APIRouter()

# System endpoints
api_router.include_router(health.router, prefix="", tags=["System"])

# Authentication & User Management
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Resume Upload, Parsing & Skill Extraction
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])

# Job Management & Candidate Applications
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs & Applications"])

# Resume-Job Matching Algorithms
api_router.include_router(matching.router, prefix="/matching", tags=["Matching"])

