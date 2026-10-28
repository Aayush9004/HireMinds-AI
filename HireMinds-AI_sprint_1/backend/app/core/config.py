"""
Core configuration module for HireMinds AI
"""
from typing import Dict, List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings powered by Pydantic Settings.
    Reads values from environment variables or .env file.
    """
    PROJECT_NAME: str = "HireMinds AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # CORS origins allowed to communicate with backend
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "hireminds_ai"
    DATABASE_URL: Union[str, None] = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Security & JWT Authentication
    SECRET_KEY: str = "hireminds_super_secret_jwt_key_development_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Phase 7: ATS scoring weights (must sum to 1.0)
    # These are initial assumptions, not validated hiring criteria.
    ATS_WEIGHT_SKILL: float = 0.40
    ATS_WEIGHT_EXPERIENCE: float = 0.25
    ATS_WEIGHT_EDUCATION: float = 0.15
    ATS_WEIGHT_PROJECT: float = 0.10
    ATS_WEIGHT_SEMANTIC: float = 0.10
    ATS_SCORING_VERSION: str = "ats-v1.0"

    # ------------------------------------------------------------------
    # Phase 8: Technical assessments
    # ------------------------------------------------------------------
    # LLM provider used for assessment generation: "gemini" or "deepseek".
    LLM_PROVIDER: str = "gemini"

    @field_validator("LLM_PROVIDER")
    @classmethod
    def _validate_llm_provider(cls, v: str) -> str:
        provider = (v or "gemini").strip().lower()
        if provider not in {"gemini", "deepseek"}:
            raise ValueError(
                "LLM_PROVIDER must be 'gemini' or 'deepseek'; "
                f"got {v!r}."
            )
        return provider

    # Gemini API (key is intentionally empty by default; generation is
    # unavailable until the deployment supplies a key).
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    # Legacy REST base URL. The official SDK appends its own API version, so
    # the trailing version segment is stripped when this value is supplied.
    GEMINI_API_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    # Gemini can take well over a minute under load; keep this generous and
    # lower it only if the deployment needs faster failure.
    GEMINI_TIMEOUT_SECONDS: float = 180.0
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_TEMPERATURE: float = 0.4

    # DeepSeek API (OpenAI-compatible chat completions).
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_API_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_TIMEOUT_SECONDS: float = 60.0
    DEEPSEEK_MAX_OUTPUT_TOKENS: int = 8192
    DEEPSEEK_TEMPERATURE: float = 0.4

    ASSESSMENT_PROMPT_VERSION: str = "assessment-v1"
    ASSESSMENT_MAX_MCQ_QUESTIONS: int = 20
    ASSESSMENT_MAX_CODING_QUESTIONS: int = 5
    ASSESSMENT_DEFAULT_DURATION_MINUTES: int = 60
    ASSESSMENT_DEFAULT_PASSING_SCORE: float = 60.0

    # ------------------------------------------------------------------
    # Phase 9: AI mock interviews
    # ------------------------------------------------------------------
    INTERVIEW_PROMPT_VERSION: str = "interview-v1"
    INTERVIEW_RUBRIC_VERSION: str = "interview-rubric-v1"
    INTERVIEW_DEFAULT_QUESTION_COUNT: int = 5
    INTERVIEW_MIN_QUESTION_COUNT: int = 3
    INTERVIEW_MAX_QUESTION_COUNT: int = 10
    INTERVIEW_MAX_FOLLOW_UPS: int = 3
    INTERVIEW_MAX_ANSWER_LENGTH: int = 10000
    INTERVIEW_MAX_TOTAL_QUESTIONS: int = 15

    # Coding execution is DISABLED by default. Candidate code is never
    # executed inside the FastAPI process. When enabled, only the Docker
    # backend is supported and the container must run with network and
    # filesystem restrictions (see docs/PHASE8_TECHNICAL_ASSESSMENTS.md).
    CODE_EXECUTION_ENABLED: bool = False
    CODE_EXECUTION_BACKEND: str = "disabled"
    CODE_EXECUTION_DOCKER_BINARY: str = "docker"
    CODE_EXECUTION_DOCKER_IMAGE: str = "python:3.12-slim"
    CODE_EXECUTION_TIMEOUT_SECONDS: int = 10
    CODE_EXECUTION_STARTUP_GRACE_SECONDS: float = 5.0
    CODE_EXECUTION_MEMORY_MB: int = 256
    CODE_EXECUTION_CPU_LIMIT: float = 0.5
    CODE_EXECUTION_PIDS_LIMIT: int = 64
    CODE_EXECUTION_MAX_OUTPUT_BYTES: int = 10000

    @model_validator(mode="after")
    def _validate_ats_weights(self) -> "Settings":
        total = (
            self.ATS_WEIGHT_SKILL
            + self.ATS_WEIGHT_EXPERIENCE
            + self.ATS_WEIGHT_EDUCATION
            + self.ATS_WEIGHT_PROJECT
            + self.ATS_WEIGHT_SEMANTIC
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "ATS weights must sum to 1.0; "
                f"got {total:.6f}. Check ATS_WEIGHT_* environment variables."
            )
        return self

    @property
    def ATS_WEIGHTS(self) -> Dict[str, float]:
        """Current ATS component weights keyed by component name."""
        return {
            "skills": self.ATS_WEIGHT_SKILL,
            "experience": self.ATS_WEIGHT_EXPERIENCE,
            "education": self.ATS_WEIGHT_EDUCATION,
            "projects": self.ATS_WEIGHT_PROJECT,
            "semantic": self.ATS_WEIGHT_SEMANTIC,
        }

    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
