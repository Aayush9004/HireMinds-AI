"""
Health check response schemas
"""
from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Schema for health check endpoint responses
    """
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    project: str = Field(..., json_schema_extra={"example": "HireMinds AI"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: Dict[str, Any] = Field(default_factory=dict)
