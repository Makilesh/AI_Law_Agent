# Copyright (c) Microsoft. All rights reserved.

"""
Pydantic models for request/response schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., description="User's query")
    language: str = Field(default="English", description="Response language")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="AI assistant's response")
    confidence: float = Field(default=0.9, description="Confidence score")
    source: str = Field(default="gemini", description="Source model")
    language: str = Field(default="English", description="Response language")


class ClassifierResult(BaseModel):
    """Result model for query classification."""
    category: str = Field(..., description="Query category")
    confidence: float = Field(..., description="Confidence score")
    reasoning: str = Field(..., description="Reasoning for classification")
    extracted_info: Dict[str, Any] = Field(default_factory=dict, description="Extracted information")


class PDFUploadResponse(BaseModel):
    """Response model for PDF upload endpoint."""
    success: bool = Field(..., description="Upload success status")
    filename: str = Field(..., description="Uploaded filename")
    message: str = Field(..., description="Status message")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    pages_processed: int = Field(default=0, description="Number of pages processed")


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
