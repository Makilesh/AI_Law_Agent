# Copyright (c) Microsoft. All rights reserved.

"""
Main FastAPI server for AI Legal Engine with Agentic Architecture using Free Services.
"""

import os
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

from models.schemas import ChatRequest, ChatResponse, PDFUploadResponse
from agents.router import get_router_agent
from agents.pdf_processor import get_pdf_processor
from utils.vector_store import get_vector_store

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
    logger.info("Initializing AI Legal Engine (Free Tier)...")
    
    try:
        # Validate Gemini API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        logger.info("✅ Gemini API key found")
        
        # Initialize ChromaDB vector store
        vector_store = get_vector_store()
        logger.info(f"✅ ChromaDB initialized: {vector_store.get_stats()}")
        
        # Initialize agents (lazy loading on first use)
        logger.info("✅ Agents ready for lazy initialization")
        
        logger.info("=" * 60)
        logger.info("🚀 AI Legal Engine Ready!")
        logger.info("=" * 60)
        logger.info("Using FREE services:")
        logger.info("  - Google Gemini (gemini-2.5-flash)")
        logger.info("  - ChromaDB (local vector store)")
        logger.info("  - Sentence Transformers (local embeddings)")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Legal Engine...")


# Create FastAPI app
app = FastAPI(
    title="AI Legal Engine",
    description="Agentic Legal Assistant for Indian Criminal Law (Free Tier)",
    version="2.0.0",
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


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AI Legal Engine",
        "version": "2.0.0",
        "description": "Agentic Legal Assistant using Free Services",
        "services": {
            "llm": "Google Gemini 1.5 Flash",
            "vector_db": "ChromaDB (local)",
            "embeddings": "Sentence Transformers (local)"
        },
        "endpoints": {
            "/chat": "Chat with legal assistant",
            "/upload-pdf": "Upload legal PDF documents",
            "/document-stats": "Get document statistics",
            "/clear-documents": "Clear all documents",
            "/clear-history": "Clear conversation history",
            "/health": "Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return {
            "status": "healthy",
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
            "vector_store": stats
        }
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
