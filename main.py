# Copyright (c) Microsoft. All rights reserved.

"""
Main FastAPI server for AI Legal Engine with Agentic Architecture.

Enhanced with:
- Redis-based semantic caching
- Rate limiting and IP blocking
- Request validation
- Comprehensive security middleware
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile

from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import uvicorn

from models.schemas import ChatRequest, ChatResponse, PDFUploadResponse
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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for legal queries.
    
    Routes queries to appropriate specialized agents.
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
        
        # Process query with router
        result = await router.process_query(
            query=request.query,
            language=request.language,
            context={"history": conversation_history}
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
            "metadata": result.get("routing", {})
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
                    "burst": rate_limiter.burst_limit
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


def main():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()
