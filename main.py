# Copyright (c) Microsoft. All rights reserved.

"""
Main FastAPI server for AI Legal Engine with Agentic Architecture.

Enhanced with:
- Redis-based semantic caching
- Rate limiting and IP blocking
- Request validation
- Comprehensive security middleware
- Voice I/O with WebSocket (Phase 5)
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Body, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import uvicorn

from models.schemas import (
    ChatRequest, ChatResponse, PDFUploadResponse,
    UserRegisterRequest, UserLoginRequest, TokenResponse, RefreshTokenRequest, UserInfoResponse,
    ConversationListResponse, ConversationDetailResponse,
    DocumentStartRequest, DocumentStartResponse, DocumentUpdateRequest, DocumentUpdateResponse,
    DocumentPreviewResponse, DocumentGenerateResponse, DocumentListResponse
)
from agents.router import get_router_agent
from agents.pdf_processor import get_pdf_processor
from utils.vector_store import get_vector_store

# Phase 1 Imports: Caching and Security
from cache.redis_cache import get_redis_cache
from cache.cache_strategies import get_semantic_cache
from security.security_middleware import SecurityMiddleware
from security.rate_limiter import get_rate_limiter
from security.ip_blocker import get_ip_blocker
from security.request_validator import get_request_validator

# Phase 2 Imports: Authentication and Database
from auth.user_manager import get_user_manager
from auth.jwt_handler import get_jwt_handler

# Phase 3 Imports: Advanced RAG with Reranking
from utils.reranker import get_reranker
from database.sqlite_db import get_database
from document_templates import (
    FIRTemplate, BailTemplate, AffidavitTemplate, 
    ComplaintTemplate, LegalNoticeTemplate
)

# Phase 4 Imports: Export and Engagement Features
from utils.export_handler import get_export_handler

# Phase 5 Imports: Voice I/O (lazy loaded)
voice_assistant = None

def get_voice_assistant():
    """Lazy load voice assistant to avoid startup overhead."""
    global voice_assistant
    if voice_assistant is None:
        try:
            from voice.voice_assistant import VoiceAssistant
            voice_assistant = VoiceAssistant()
            logger.info("Voice assistant initialized")
        except ImportError as e:
            logger.warning(f"Voice I/O not available: {e}")
    return voice_assistant

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
router_agent = None
pdf_processor = None
conversation_history: List[Dict[str, str]] = []

# Phase 2: Document generation sessions (in-memory for now)
# Format: {document_id: {template: BaseTemplate, created_at: datetime, user_id: int}}
active_documents: Dict[str, Dict[str, Any]] = {}

# HTTP Bearer for JWT authentication
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global router_agent, pdf_processor

    # Startup
    logger.info("Initializing AI Legal Engine with Enhanced Security...")

    try:
        # Validate Gemini API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")

        logger.info("✅ Gemini API key found")

        # Initialize ChromaDB vector store
        vector_store = get_vector_store()
        logger.info(f"✅ ChromaDB initialized: {vector_store.get_stats()}")

        # Initialize Redis cache
        try:
            redis_cache = get_redis_cache()
            cache_stats = redis_cache.get_stats()
            logger.info(f"✅ Redis cache initialized: {cache_stats.get('cache_size', 0)} keys")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache unavailable: {str(e)}")
            logger.warning("   Continuing without caching...")

        # Initialize security components
        try:
            rate_limiter = get_rate_limiter()
            ip_blocker = get_ip_blocker()
            request_validator = get_request_validator()
            logger.info("✅ Security components initialized")
        except Exception as e:
            logger.warning(f"⚠️ Security initialization warning: {str(e)}")

        # Initialize agents (lazy loading on first use)
        logger.info("✅ Agents ready for lazy initialization")

        logger.info("=" * 60)
        logger.info("🚀 AI Legal Engine Ready!")
        logger.info("=" * 60)
        logger.info("Core Services:")
        logger.info("  - Google Gemini (gemini-2.5-flash)")
        logger.info("  - ChromaDB (local vector store)")
        logger.info("  - Sentence Transformers (local embeddings)")
        logger.info("Phase 1 Enhancements:")
        logger.info("  - Redis Semantic Caching")
        logger.info("  - Rate Limiting (30/min, 500/hour)")
        logger.info("  - IP Blocking & Whitelisting")
        logger.info("  - Request Validation")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down AI Legal Engine...")

    # Close Redis connection
    try:
        redis_cache = get_redis_cache()
        if redis_cache.client:
            redis_cache.client.close()
            logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="AI Legal Engine",
    description="Enhanced Agentic Legal Assistant with Caching & Security",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (Phase 1)
enable_rate_limiting = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
enable_ip_blocking = os.getenv("ENABLE_IP_BLOCKING", "true").lower() == "true"
enable_request_validation = os.getenv("ENABLE_REQUEST_VALIDATION", "true").lower() == "true"

app.add_middleware(
    SecurityMiddleware,
    enable_rate_limiting=enable_rate_limiting,
    enable_ip_blocking=enable_ip_blocking,
    enable_request_validation=enable_request_validation
)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AI Legal Engine",
        "version": "3.0.0",
        "description": "Enhanced Agentic Legal Assistant with Caching & Security",
        "services": {
            "llm": "Google Gemini 2.5 Flash",
            "vector_db": "ChromaDB (local)",
            "embeddings": "Sentence Transformers (local)",
            "cache": "Redis (semantic similarity)",
            "security": "Rate limiting + IP blocking"
        },
        "endpoints": {
            "core": {
                "/chat": "Chat with legal assistant (cached)",
                "/upload-pdf": "Upload legal PDF documents",
                "/health": "Health check"
            },
            "documents": {
                "/document-stats": "Get document statistics",
                "/vector-store/stats": "Get vector store statistics",
                "/clear-documents": "Clear all documents",
                "/clear-history": "Clear conversation history"
            },
            "cache": {
                "/cache/stats": "Get cache statistics",
                "/cache/clear": "Clear cache (pattern optional)"
            },
            "security": {
                "/security/stats": "Get security statistics",
                "/security/block-ip": "Block an IP address",
                "/security/unblock-ip": "Unblock an IP address",
                "/security/whitelist-ip": "Add IP to whitelist",
                "/security/blocked-ips": "List blocked IPs"
            }
        },
        "features": {
            "semantic_caching": "92% similarity threshold",
            "rate_limiting": "30/min, 500/hour",
            "parallel_seeding": "4 workers",
            "knowledge_base": "500+ legal documents"
        }
    }


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with cache and security status."""
    try:
        health_status = {
            "status": "healthy",
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        }

        # Vector store health
        try:
            vector_store = get_vector_store()
            health_status["vector_store"] = vector_store.get_stats()
        except Exception as e:
            health_status["vector_store"] = {"error": str(e), "status": "unhealthy"}

        # Redis cache health
        try:
            redis_cache = get_redis_cache()
            cache_stats = redis_cache.get_stats()
            health_status["cache"] = {
                "status": "healthy" if redis_cache.client else "unavailable",
                "stats": cache_stats
            }
        except Exception as e:
            health_status["cache"] = {"status": "unavailable", "error": str(e)}

        # Security components health
        try:
            rate_limiter = get_rate_limiter()
            health_status["security"] = {
                "rate_limiting": "enabled" if enable_rate_limiting else "disabled",
                "ip_blocking": "enabled" if enable_ip_blocking else "disabled",
                "request_validation": "enabled" if enable_request_validation else "disabled"
            }
        except Exception as e:
            health_status["security"] = {"error": str(e)}

        return health_status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/search-test")
async def search_test(query: str = "What is BNS 103?"):
    """
    Test endpoint to compare vector search vs reranked results.
    Shows the impact of reranking on search result quality.
    
    Args:
        query: Search query (default: "What is BNS 103?")
        
    Returns:
        Comparison of original and reranked results
    """
    try:
        vector_store = get_vector_store()
        reranker = get_reranker()
        
        # Perform vector search
        vector_results = vector_store.query(query, n_results=10)
        
        # Rerank the results
        reranked_results = reranker.rerank(query, vector_results)
        
        # Format for comparison
        original_top_5 = []
        for i, result in enumerate(vector_results[:5]):
            original_top_5.append({
                "position": i + 1,
                "document_preview": result['document'][:200] + "...",
                "distance": result.get('distance', 0.0),
                "metadata": result.get('metadata', {})
            })
        
        reranked_top_5 = []
        for i, result in enumerate(reranked_results[:5]):
            reranked_top_5.append({
                "position": i + 1,
                "original_position": result.get('original_position', -1) + 1,
                "document_preview": result['document'][:200] + "...",
                "rerank_score": result.get('rerank_score', 0.0),
                "keyword_score": result.get('keyword_score', 0.0),
                "position_score": result.get('position_score', 0.0),
                "metadata": result.get('metadata', {})
            })
        
        return {
            "query": query,
            "total_results": len(vector_results),
            "original_top_5": original_top_5,
            "reranked_top_5": reranked_top_5,
            "reranking_impact": {
                "position_changes": sum(
                    1 for r in reranked_results[:5] 
                    if r.get('original_position', 0) != reranked_results.index(r)
                ),
                "top_result_changed": (
                    reranked_results[0].get('original_position', 0) != 0
                    if reranked_results else False
                )
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search test failed: {str(e)}"
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for legal queries.
    
    Routes queries to appropriate specialized agents.
    Supports multi-turn dialogue with context awareness.
    """
    try:
        global conversation_history
        
        # Get router agent
        router = get_router_agent()
        
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": request.query,
            "language": request.language
        })
        
        # Process query with router (now includes dialogue management)
        result = await router.process_query(
            query=request.query,
            language=request.language,
            context={"history": conversation_history},
            history=conversation_history  # Pass history for dialogue manager
        )
        
        # Extract response
        if "response" in result:
            response_text = result["response"]
        elif "explanation" in result:
            response_text = result["explanation"]
        elif "answer" in result:
            response_text = result["answer"]
        else:
            response_text = str(result)
        
        # Add assistant response to history
        conversation_history.append({
            "role": "assistant",
            "content": response_text,
            "metadata": {
                "routing": result.get("routing", {}),
                "dialogue_context": result.get("dialogue_context"),
                "needs_clarification": result.get("needs_clarification", False)
            }
        })
        
        # Keep last 10 messages
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]
        
        return ChatResponse(
            response=response_text,
            confidence=result.get("confidence", 0.9),
            source="gemini-2.5-flash",
            language=request.language
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    
    Stores document chunks in ChromaDB for later retrieval.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        logger.info(f"Processing uploaded PDF: {file.filename}")
        
        # Get PDF processor
        processor = get_pdf_processor()
        
        # Process PDF
        result = await processor.process_pdf(
            pdf_path=tmp_path,
            metadata={"original_filename": file.filename}
        )
        
        # Clean up temp file
        Path(tmp_path).unlink()
        
        if result["success"]:
            return PDFUploadResponse(
                success=True,
                filename=file.filename,
                message=result["message"],
                chunks_created=result["total_chunks"],
                pages_processed=result["total_pages"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.get("/document-stats")
async def get_document_stats():
    """Get statistics about processed documents."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/vector-store/stats")
async def get_vector_store_stats():
    """Get vector store statistics (alias for frontend compatibility)."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/clear-documents")
async def clear_documents():
    """Clear all documents from the vector store."""
    try:
        processor = get_pdf_processor()
        processor.clear_all_documents()
        
        return {
            "success": True,
            "message": "All documents cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {str(e)}")


@app.post("/clear-history")
async def clear_history():
    """Clear conversation history."""
    global conversation_history
    conversation_history = []

    return {
        "success": True,
        "message": "Conversation history cleared"
    }


# ============================================================================
# CACHE ENDPOINTS (Phase 1)
# ============================================================================

@app.get("/cache/stats")
async def get_cache_stats():
    """Get Redis cache statistics."""
    try:
        redis_cache = get_redis_cache()
        stats = redis_cache.get_stats()

        return {
            "success": True,
            "cache": stats
        }
    except Exception as e:
        logger.error(f"Cache stats error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Cache unavailable"
        }


@app.post("/cache/clear")
async def clear_cache(pattern: str = Body("query_cache:*", embed=True)):
    """
    Clear Redis cache.

    Args:
        pattern: Redis key pattern to clear (default: "query_cache:*")
    """
    try:
        semantic_cache = get_semantic_cache()
        cleared = semantic_cache.clear_cache(pattern)

        return {
            "success": True,
            "message": f"Cache cleared: {cleared} keys removed",
            "keys_cleared": cleared
        }
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# ============================================================================
# SECURITY ENDPOINTS (Phase 1)
# ============================================================================

@app.get("/security/stats")
async def get_security_stats(request: Request):
    """Get security statistics and current request info."""
    try:
        rate_limiter = get_rate_limiter()
        ip_blocker = get_ip_blocker()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get rate limit stats for current IP
        minute_key = f"rate_limit:{client_ip}:minute"
        hour_key = f"rate_limit:{client_ip}:hour"

        redis_cache = get_redis_cache()
        minute_count = 0
        hour_count = 0

        if redis_cache.client:
            try:
                minute_count = int(redis_cache.client.get(minute_key) or 0)
                hour_count = int(redis_cache.client.get(hour_key) or 0)
            except Exception:
                pass

        return {
            "success": True,
            "client_ip": client_ip,
            "rate_limits": {
                "requests_this_minute": minute_count,
                "requests_this_hour": hour_count,
                "limits": {
                    "per_minute": rate_limiter.rate_per_minute,
                    "per_hour": rate_limiter.rate_per_hour,
                    "burst": rate_limiter.burst
                }
            },
            "status": {
                "is_blocked": ip_blocker.is_blocked(client_ip),
                "is_whitelisted": ip_blocker.is_whitelisted(client_ip)
            },
            "features": {
                "rate_limiting": enable_rate_limiting,
                "ip_blocking": enable_ip_blocking,
                "request_validation": enable_request_validation
            }
        }
    except Exception as e:
        logger.error(f"Security stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get security stats: {str(e)}")


@app.post("/security/block-ip")
async def block_ip(
    ip_address: str = Body(..., embed=True),
    reason: str = Body("abuse", embed=True),
    duration_hours: int = Body(24, embed=True)
):
    """
    Block an IP address.

    Args:
        ip_address: IP to block
        reason: Reason for blocking (default: "abuse")
        duration_hours: Block duration in hours, 0 for permanent (default: 24)
    """
    try:
        ip_blocker = get_ip_blocker()
        success = ip_blocker.block_ip(ip_address, reason, duration_hours)

        if success:
            return {
                "success": True,
                "message": f"IP {ip_address} blocked for {duration_hours} hours" if duration_hours > 0 else f"IP {ip_address} blocked permanently",
                "ip_address": ip_address,
                "reason": reason,
                "duration_hours": duration_hours
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to block IP")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Block IP error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to block IP: {str(e)}")


@app.post("/security/unblock-ip")
async def unblock_ip(ip_address: str = Body(..., embed=True)):
    """
    Unblock an IP address.

    Args:
        ip_address: IP to unblock
    """
    try:
        ip_blocker = get_ip_blocker()
        success = ip_blocker.unblock_ip(ip_address)

        if success:
            return {
                "success": True,
                "message": f"IP {ip_address} unblocked",
                "ip_address": ip_address
            }
        else:
            return {
                "success": False,
                "message": f"IP {ip_address} was not blocked"
            }

    except Exception as e:
        logger.error(f"Unblock IP error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to unblock IP: {str(e)}")


@app.post("/security/whitelist-ip")
async def whitelist_ip(ip_address: str = Body(..., embed=True)):
    """
    Add IP to whitelist (bypasses all rate limiting and blocking).

    Args:
        ip_address: IP to whitelist
    """
    try:
        ip_blocker = get_ip_blocker()
        success = ip_blocker.add_to_whitelist(ip_address)

        if success:
            return {
                "success": True,
                "message": f"IP {ip_address} added to whitelist",
                "ip_address": ip_address
            }
        else:
            return {
                "success": False,
                "message": f"IP {ip_address} may already be whitelisted"
            }

    except Exception as e:
        logger.error(f"Whitelist IP error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to whitelist IP: {str(e)}")


@app.get("/security/blocked-ips")
async def get_blocked_ips():
    """Get list of all blocked IPs."""
    try:
        ip_blocker = get_ip_blocker()
        blocked_ips = ip_blocker.get_blocked_ips()

        return {
            "success": True,
            "blocked_ips": blocked_ips,
            "count": len(blocked_ips)
        }
    except Exception as e:
        logger.error(f"Get blocked IPs error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get blocked IPs: {str(e)}")


# ============================================================================
# PHASE 2: AUTHENTICATION ENDPOINTS
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user from JWT token."""
    try:
        jwt_handler = get_jwt_handler()
        token = credentials.credentials

        # Verify and decode token (returns tuple: is_valid, payload)
        is_valid, payload = jwt_handler.verify_token(token)

        if not is_valid or not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return payload
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@app.post("/auth/register", response_model=UserInfoResponse)
async def register_user(request: UserRegisterRequest):
    """Register a new user."""
    try:
        user_manager = get_user_manager()
        db = get_database()

        # Register user (validate and prepare user data)
        success, message, user_data = user_manager.register_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name if hasattr(request, 'full_name') else None,
            phone=request.phone if hasattr(request, 'phone') else None
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Insert user into database
        db_success, db_message, user_id = db.create_user(user_data)

        if not db_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=db_message
            )

        logger.info(f"New user registered: {request.username} (ID: {user_id})")

        return UserInfoResponse(
            user_id=user_id,
            username=user_data["username"],
            email=user_data["email"],
            created_at=user_data["created_at"],
            is_active=user_data["is_active"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest):
    """Login user and return JWT tokens."""
    try:
        user_manager = get_user_manager()
        jwt_handler = get_jwt_handler()
        db = get_database()

        # Get user from database to retrieve password hash and user_id
        user_record = db.get_user_by_username(request.username)

        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        password_handler = user_manager.password_handler
        if not password_handler.verify_password(request.password, user_record["password_hash"]):
            logger.warning(f"Failed login attempt for: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Generate tokens with actual user_id
        access_token = jwt_handler.create_access_token(
            user_id=str(user_record["id"]),  # Convert to string for JWT
            username=user_record["username"]
        )

        refresh_token = jwt_handler.create_refresh_token(
            user_id=str(user_record["id"]),
            username=user_record["username"]
        )

        logger.info(f"User logged in: {user_record['username']} (ID: {user_record['id']})")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600  # 1 hour
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    try:
        jwt_handler = get_jwt_handler()
        
        # Verify refresh token
        payload = jwt_handler.verify_token(request.refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Generate new access token
        access_token = jwt_handler.create_access_token(
            {"user_id": payload["user_id"], "username": payload["username"]}
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,
            token_type="bearer",
            expires_in=3600
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


@app.post("/auth/logout")
async def logout_user(current_user: Dict = Depends(get_current_user)):
    """Logout user (client should discard tokens)."""
    logger.info(f"User logged out: {current_user.get('username')}")
    return {"success": True, "message": "Logged out successfully"}


@app.get("/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current user information."""
    try:
        db = get_database()

        # Get user_id from JWT payload (sub claim)
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Fetch user from database
        user = db.get_user_by_id(int(user_id))

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserInfoResponse(
            user_id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


# ============================================================================
# PHASE 2: CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/conversations/list", response_model=ConversationListResponse)
async def list_conversations(current_user: Dict = Depends(get_current_user)):
    """List all conversations for authenticated user."""
    try:
        db = get_database()

        # Get user_id from JWT payload (sub claim)
        user_id = int(current_user.get("sub"))
        conversations = db.get_user_conversations(user_id)

        return ConversationListResponse(
            conversations=conversations,
            total_count=len(conversations)
        )
    
    except Exception as e:
        logger.error(f"List conversations error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@app.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: int, current_user: Dict = Depends(get_current_user)):
    """Get conversation details with messages."""
    try:
        db = get_database()
        conversation = db.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Verify ownership
        user_id = int(current_user.get("sub"))
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        messages = db.get_conversation_messages(conversation_id)
        
        return ConversationDetailResponse(
            conversation_id=conversation["conversation_id"],
            title=conversation["title"],
            created_at=conversation["created_at"],
            last_message_at=conversation["last_message_at"],
            messages=messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@app.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: int, current_user: Dict = Depends(get_current_user)):
    """Archive a conversation."""
    try:
        db = get_database()
        conversation = db.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        user_id = int(current_user.get("sub"))
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Archive conversation (set is_active = 0)
        db.execute(
            "UPDATE conversations SET is_active = 0 WHERE conversation_id = ?",
            (conversation_id,)
        )
        
        return {"success": True, "message": "Conversation archived"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Archive conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to archive conversation: {str(e)}")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, current_user: Dict = Depends(get_current_user)):
    """Delete a conversation permanently."""
    try:
        db = get_database()
        conversation = db.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        user_id = int(current_user.get("sub"))
        if conversation["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete messages first
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        # Delete conversation
        db.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
        
        return {"success": True, "message": "Conversation deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


# ============================================================================
# PHASE 2: DOCUMENT GENERATION ENDPOINTS
# ============================================================================

def get_template_by_type(document_type: str):
    """Factory function to get template by type."""
    templates = {
        "fir": FIRTemplate,
        "bail": BailTemplate,
        "affidavit": AffidavitTemplate,
        "complaint": ComplaintTemplate,
        "legal_notice": LegalNoticeTemplate
    }
    
    template_class = templates.get(document_type.lower())
    if not template_class:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Available types: {', '.join(templates.keys())}"
        )
    
    return template_class()


@app.post("/documents/start", response_model=DocumentStartResponse)
async def start_document_generation(request: DocumentStartRequest):
    """Start a new document generation session."""
    try:
        # Create template instance
        template = get_template_by_type(request.document_type)
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Store in active documents
        active_documents[document_id] = {
            "template": template,
            "created_at": datetime.now(),
            "user_id": request.user_id,
            "document_type": request.document_type
        }
        
        # Get first field
        next_field = template.get_next_required_field()
        field_prompts = template.get_field_prompts()
        field_prompt = field_prompts.get(next_field, "Please provide the required information")
        
        logger.info(f"Started document generation: {document_id} (type: {request.document_type})")
        
        return DocumentStartResponse(
            document_id=document_id,
            document_type=request.document_type,
            next_field=next_field,
            field_prompt=field_prompt,
            completion_percentage=template.get_completion_percentage()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start document: {str(e)}")


@app.post("/documents/{document_id}/update", response_model=DocumentUpdateResponse)
async def update_document_field(document_id: str, request: DocumentUpdateRequest):
    """Update a field in the document."""
    try:
        # Get document from active documents
        if document_id not in active_documents:
            raise HTTPException(status_code=404, detail="Document not found or session expired")
        
        template = active_documents[document_id]["template"]
        
        # Set field value (with validation)
        success, error = template.set_field(request.field_name, request.field_value)
        
        if not success:
            return DocumentUpdateResponse(
                success=False,
                document_id=document_id,
                next_field=request.field_name,
                field_prompt=template.get_field_prompts().get(request.field_name, "Please provide valid input"),
                completion_percentage=template.get_completion_percentage(),
                is_complete=False,
                error=error
            )
        
        # Get next field
        next_field = template.get_next_required_field()
        field_prompts = template.get_field_prompts()
        field_prompt = field_prompts.get(next_field) if next_field else None
        
        is_complete = template.is_complete()
        
        return DocumentUpdateResponse(
            success=True,
            document_id=document_id,
            next_field=next_field,
            field_prompt=field_prompt,
            completion_percentage=template.get_completion_percentage(),
            is_complete=is_complete,
            error=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


@app.get("/documents/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(document_id: str):
    """Preview the current state of the document."""
    try:
        if document_id not in active_documents:
            raise HTTPException(status_code=404, detail="Document not found or session expired")
        
        template = active_documents[document_id]["template"]
        document_type = active_documents[document_id]["document_type"]
        
        preview_text = template.get_preview()
        
        return DocumentPreviewResponse(
            document_id=document_id,
            document_type=document_type,
            preview_text=preview_text,
            completion_percentage=template.get_completion_percentage(),
            is_complete=template.is_complete(),
            missing_fields=template.get_missing_fields()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to preview document: {str(e)}")


@app.post("/documents/{document_id}/generate", response_model=DocumentGenerateResponse)
async def generate_document(document_id: str):
    """Generate final DOCX document."""
    try:
        if document_id not in active_documents:
            raise HTTPException(status_code=404, detail="Document not found or session expired")
        
        template = active_documents[document_id]["template"]
        document_type = active_documents[document_id]["document_type"]
        
        # Check if complete
        if not template.is_complete():
            raise HTTPException(
                status_code=400,
                detail=f"Document incomplete. Missing fields: {', '.join(template.get_missing_fields())}"
            )
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type}_{timestamp}.docx"
        output_path = Path(tempfile.gettempdir()) / filename
        
        # Generate DOCX
        success = template.generate_docx(str(output_path))
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate document")
        
        logger.info(f"Generated document: {filename}")
        
        # TODO: Save to database for authenticated users
        # if active_documents[document_id].get("user_id"):
        #     db = get_database()
        #     db.save_generated_document(...)
        
        return DocumentGenerateResponse(
            success=True,
            document_id=document_id,
            filename=filename,
            download_url=f"/documents/{document_id}/download",
            message="Document generated successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@app.get("/documents/{document_id}/download")
async def download_document(document_id: str):
    """Download generated document."""
    try:
        if document_id not in active_documents:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document_type = active_documents[document_id]["document_type"]
        
        # Find the generated file
        temp_dir = Path(tempfile.gettempdir())
        files = list(temp_dir.glob(f"{document_type}_*.docx"))
        
        if not files:
            raise HTTPException(status_code=404, detail="Document file not found")
        
        # Get the most recent file
        latest_file = max(files, key=lambda p: p.stat().st_mtime)
        
        return FileResponse(
            path=str(latest_file),
            filename=latest_file.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")


@app.get("/documents/list", response_model=DocumentListResponse)
async def list_user_documents(current_user: Dict = Depends(get_current_user)):
    """List all generated documents for authenticated user."""
    try:
        db = get_database()

        # Get user_id from JWT payload (sub claim)
        user_id = int(current_user.get("sub"))
        documents = db.get_user_documents(user_id)
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )
    
    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


# ============================================================================
# PHASE 4: EXPORT & ENGAGEMENT ENDPOINTS
# ============================================================================

@app.post("/export/response")
async def export_response(
    response_data: Dict[str, Any] = Body(...),
    format: str = Body("json", embed=True)
):
    """
    Export a single response to specified format.
    
    Formats: json, txt, md
    """
    try:
        export_handler = get_export_handler()
        
        if format == "json":
            content = export_handler.export_response_to_json(response_data)
            media_type = "application/json"
            filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        elif format == "txt":
            content = export_handler.export_response_to_txt(response_data)
            media_type = "text/plain"
            filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        elif format == "md":
            content = export_handler.export_response_to_markdown(response_data)
            media_type = "text/markdown"
            filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use: json, txt, or md")
        
        return JSONResponse(
            content={
                "success": True,
                "filename": filename,
                "content": content,
                "format": format
            }
        )
        
    except Exception as e:
        logger.error(f"Export response error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/export/conversation")
async def export_conversation(
    conversation_id: str = Body(..., embed=True),
    format: str = Body("json", embed=True),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Export a full conversation to specified format.
    Requires authentication.
    
    Formats: json, txt, md
    """
    try:
        # Verify token
        user_manager = get_user_manager()
        user_info = user_manager.verify_access_token(credentials.credentials)
        
        # Get conversation from database
        db = get_database()
        messages = db.get_conversation_messages(conversation_id, limit=1000)
        
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get conversation metadata
        conversation_data = {
            "id": conversation_id,
            "title": f"Conversation {conversation_id}",
            "created_at": messages[0].get("created_at") if messages else datetime.now().isoformat(),
            "status": "active"
        }
        
        export_handler = get_export_handler()
        
        if format == "json":
            content = export_handler.export_conversation_to_json(conversation_data, messages)
            media_type = "application/json"
            filename = f"conversation_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        elif format == "txt":
            content = export_handler.export_conversation_to_txt(conversation_data, messages)
            media_type = "text/plain"
            filename = f"conversation_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        elif format == "md":
            content = export_handler.export_conversation_to_markdown(conversation_data, messages)
            media_type = "text/markdown"
            filename = f"conversation_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use: json, txt, or md")
        
        return JSONResponse(
            content={
                "success": True,
                "filename": filename,
                "content": content,
                "format": format,
                "message_count": len(messages)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/bookmarks/create")
async def create_bookmark(
    conversation_id: Optional[str] = Body(None),
    message_id: Optional[str] = Body(None),
    title: str = Body(...),
    notes: Optional[str] = Body(None),
    category: Optional[str] = Body("general"),
    metadata: Optional[Dict[str, Any]] = Body(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a bookmark for a conversation, specific message, or general legal topic.
    Requires authentication.
    """
    try:
        # Verify token
        user_manager = get_user_manager()
        user_info = user_manager.verify_access_token(credentials.credentials)
        user_id = user_info["user_id"]
        
        # Create bookmark in database
        db = get_database()
        
        bookmark_data = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "title": title,
            "notes": notes,
            "category": category,
            "metadata": metadata or {}
        }
        
        # Insert bookmark using database method
        bookmark_id = db.create_bookmark(user_id, bookmark_data)
        
        if not bookmark_id:
            raise HTTPException(status_code=500, detail="Failed to create bookmark")
        
        return JSONResponse(
            content={
                "success": True,
                "bookmark_id": bookmark_id,
                "message": "Bookmark created successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create bookmark error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create bookmark: {str(e)}")


@app.get("/bookmarks/list")
async def list_bookmarks(
    category: Optional[str] = None,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    List all bookmarks for the authenticated user.
    Optional category filter.
    """
    try:
        # Verify token
        user_manager = get_user_manager()
        user_info = user_manager.verify_access_token(credentials.credentials)
        user_id = user_info["user_id"]
        
        # Get bookmarks from database
        db = get_database()
        
        # Get user bookmarks with optional category filter
        bookmarks = db.get_user_bookmarks(user_id, category=category, limit=limit)
        
        return JSONResponse(
            content={
                "success": True,
                "bookmarks": bookmarks,
                "total": len(bookmarks)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List bookmarks error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list bookmarks: {str(e)}")


@app.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Delete a bookmark by ID.
    Requires authentication.
    """
    try:
        # Verify token
        user_manager = get_user_manager()
        user_info = user_manager.verify_access_token(credentials.credentials)
        user_id = user_info["user_id"]
        
        # Delete bookmark from database
        db = get_database()
        
        # Delete bookmark (checks user ownership)
        success, message = db.delete_bookmark(bookmark_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=message)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Bookmark deleted successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete bookmark error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete bookmark: {str(e)}")


# =============================================================================
# PHASE 5: VOICE I/O ENDPOINTS
# =============================================================================

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice chat.
    
    Protocol:
    - Client sends: {"type": "start_listening"} to begin STT
    - Client sends: {"type": "stop_listening"} to stop STT
    - Client sends: {"type": "text", "content": "query", "language": "English"}
    - Client sends: {"type": "speak", "content": "text to speak"}
    - Client sends: {"type": "stop_speaking"} to stop TTS
    - Server sends: {"type": "transcript", "content": "..."} for STT result
    - Server sends: {"type": "response", "content": "...", "metadata": {...}}
    - Server sends: {"type": "status", "content": "listening|processing|speaking|ready"}
    - Server sends: {"type": "error", "content": "error message"}
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    # Define chat handler that uses the existing chat logic
    async def chat_handler(query: str, language: str) -> dict:
        global router_agent
        try:
            if router_agent is None:
                router_agent = get_router_agent()
            result = router_agent.process_query(query, language)
            return {
                "response": result.get("response", "I couldn't process that query."),
                "confidence": result.get("confidence", 0.0),
                "source": result.get("source", "unknown")
            }
        except Exception as e:
            logger.error(f"Chat handler error: {e}")
            return {"response": f"Error processing query: {str(e)}", "confidence": 0.0}
    
    assistant = get_voice_assistant()
    if assistant is None:
        await websocket.send_json({
            "type": "error",
            "content": "Voice I/O not available. Install RealtimeSTT and RealtimeTTS."
        })
        await websocket.close()
        return
        
    assistant.chat_handler = chat_handler
    
    try:
        await assistant.handle_websocket(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
    finally:
        assistant.cleanup()


@app.get("/voice/status")
async def voice_status():
    """Check voice I/O availability and status."""
    voice_available = False
    stt_available = False
    tts_available = False
    
    try:
        from voice.speech_to_text import SpeechToText
        stt_available = True
    except ImportError:
        pass
        
    try:
        from voice.text_to_speech import TextToSpeech
        tts_available = True
    except ImportError:
        pass
        
    voice_available = stt_available and tts_available
    
    return {
        "success": True,
        "voice_available": voice_available,
        "components": {
            "speech_to_text": stt_available,
            "text_to_speech": tts_available,
            "websocket_endpoint": "/ws/voice"
        },
        "instructions": {
            "connect": "Connect to WebSocket at /ws/voice",
            "start_listening": "Send {\"type\": \"start_listening\"} to begin voice input",
            "send_text": "Send {\"type\": \"text\", \"content\": \"your query\", \"language\": \"English\"}",
            "speak": "Send {\"type\": \"speak\", \"content\": \"text to speak\"}"
        }
    }


def main():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Disable reload for Windows compatibility with multiprocessing
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Disabled for compatibility
        log_level="info"
    )


if __name__ == "__main__":
    main()
