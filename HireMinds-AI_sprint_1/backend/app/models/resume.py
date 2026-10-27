"""
Resume database model for storing candidate resume uploads and extracted metadata.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Resume(Base):
    """
    Resume entity holding parsed textual content, extracted NLP metadata,
    and candidate correction history.
    """
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text(length=4294967295), nullable=False)

    # Structured metadata extracted by NLP & heuristic pipelines
    extracted_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_education: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    extracted_experience: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    extracted_projects: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Candidate review & corrections
    candidate_corrected_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_reviewed_by_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, user_id={self.user_id}, filename='{self.filename}')>"
