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


# Phase 2: Authentication and User Management Schemas

class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


class UserInfoResponse(BaseModel):
    """Response model for user information."""
    user_id: int
    username: str
    email: str
    created_at: str
    is_active: bool


# Phase 2: Conversation Management Schemas

class ConversationListResponse(BaseModel):
    """Response model for conversation list."""
    conversations: List[Dict[str, Any]]
    total_count: int


class ConversationDetailResponse(BaseModel):
    """Response model for conversation details."""
    conversation_id: int
    title: str
    created_at: str
    last_message_at: str
    messages: List[Dict[str, Any]]


# Phase 2: Document Generation Schemas

class DocumentStartRequest(BaseModel):
    """Request model to start document generation."""
    document_type: str = Field(..., description="Type of document: fir, bail, affidavit, complaint, legal_notice")
    user_id: Optional[int] = Field(None, description="User ID (if authenticated)")


class DocumentStartResponse(BaseModel):
    """Response model for starting document generation."""
    document_id: str
    document_type: str
    next_field: str
    field_prompt: str
    completion_percentage: float


class DocumentUpdateRequest(BaseModel):
    """Request model to update document field."""
    field_name: str
    field_value: Any


class DocumentUpdateResponse(BaseModel):
    """Response model for document field update."""
    success: bool
    document_id: str
    next_field: Optional[str]
    field_prompt: Optional[str]
    completion_percentage: float
    is_complete: bool
    error: Optional[str] = None


class DocumentPreviewResponse(BaseModel):
    """Response model for document preview."""
    document_id: str
    document_type: str
    preview_text: str
    completion_percentage: float
    is_complete: bool
    missing_fields: List[str]


class DocumentGenerateResponse(BaseModel):
    """Response model for document generation."""
    success: bool
    document_id: str
    filename: str
    download_url: Optional[str] = None
    message: str


class DocumentListResponse(BaseModel):
    """Response model for user documents list."""
    documents: List[Dict[str, Any]]
    total_count: int

