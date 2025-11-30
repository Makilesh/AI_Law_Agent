# Copyright (c) Microsoft. All rights reserved.

"""
Pydantic models for request/response schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User's message")
    language: str = Field(default="English", description="Response language")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="AI assistant's response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class PDFUploadResponse(BaseModel):
    """Response model for PDF upload endpoint."""
    total_pages: int
    total_chunks: int
    message: str = Field(default="PDF processed successfully")
    vectors_after: Optional[int] = None


class QueryDecision(BaseModel):
    """Model for query classification decision."""
    query_type: str = Field(..., description="Type of query: 'law' or 'section'")
    confidence: float = Field(..., description="Confidence score")
    reasoning: str = Field(..., description="Reasoning for classification")


class LegalClassification(BaseModel):
    """Model for legal classification results."""
    offense_type: str
    applicable_sections: List[str]
    severity: str
    legal_procedure: str
    analysis: str


class SectionInfo(BaseModel):
    """Model for legal section information."""
    section_number: str
    act_name: str
    summary: str
    punishment: Optional[str] = None
    key_points: List[str]
