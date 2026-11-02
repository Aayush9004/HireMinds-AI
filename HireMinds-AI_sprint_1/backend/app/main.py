"""
HireMinds AI - FastAPI Application Entrypoint
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HireMinds AI - Intelligent recruitment, resume matching, and candidate assessment platform.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root_redirect():
    """
    Redirect root path to interactive API documentation.
    """
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")


@app.get("/recruiter/{path:path}", include_in_schema=False)
@app.get("/recruiter", include_in_schema=False)
@app.get("/candidate/{path:path}", include_in_schema=False)
@app.get("/candidate", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def frontend_fallback(request: Request, path: str = ""):
    """
    If a user accesses frontend routes on the backend port (8000), redirect to Vite dev server on port 5173.
    """
    host = request.headers.get("host", "127.0.0.1:8000")
    frontend_host = host.split(":")[0] + ":5173" if ":" in host else host
    return RedirectResponse(url=f"http://{frontend_host}{request.url.path}")

