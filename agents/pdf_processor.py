# Copyright (c) Microsoft. All rights reserved.

"""
PDF Processor Agent - Processes legal PDFs and stores them in ChromaDB using Gemini.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from utils.vector_store import get_vector_store
from utils.model_manager import GeminiChatAgent

load_dotenv()
logger = logging.getLogger(__name__)


class PDFProcessorAgent:
    """
    Processes PDF documents and stores them in ChromaDB for retrieval.
    Uses free local vector storage.
    """
    
    def __init__(self):
        """Initialize the PDF processor agent."""
        # Get vector store
        self.vector_store = get_vector_store()
        
        # Initialize Gemini agent for Q&A
        self.agent = GeminiChatAgent(
            name="PDFProcessor",
            instructions=self._get_system_instruction(),
            model_name="gemini-2.0-flash",
            temperature=0.7
        )
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        logger.info("PDFProcessorAgent initialized")
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for document Q&A."""
        return """You are a legal document analysis assistant.

Your role is to answer questions about legal documents that have been provided to you.

When answering questions:
1. Only use information from the provided document context
2. Quote relevant sections when possible
3. Be precise and accurate
4. If the answer is not in the context, say so clearly
5. Provide section or page references when available

Always be factual and cite the document content."""
    
    async def process_pdf(
        self,
        pdf_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF file and store it in the vector database.
        
        Args:
            pdf_path: Path to the PDF file
            metadata: Optional metadata to store with the document
            
        Returns:
            Processing result with stats
        """
        try:
            # Check if file exists
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Load PDF
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            # Split into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Prepare data for ChromaDB
            texts = [chunk.page_content for chunk in chunks]
            metadatas = []
            ids = []
            
            filename = Path(pdf_path).name
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "source": filename,
                    "chunk_id": i,
                    "page": chunk.metadata.get("page", 0)
                }
                
                # Add custom metadata if provided
                if metadata:
                    chunk_metadata.update(metadata)
                
                metadatas.append(chunk_metadata)
                ids.append(f"{filename}_chunk_{i}")
            
            # Add to vector store
            self.vector_store.add_documents(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully processed {len(chunks)} chunks from {filename}")
            
            return {
                "success": True,
                "filename": filename,
                "total_chunks": len(chunks),
                "total_pages": len(documents),
                "message": f"Successfully processed {filename}"
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to process PDF: {str(e)}"
            }
    
    async def query_documents(
        self,
        query: str,
        language: str = "English",
        n_results: int = 5
    ) -> str:
        """
        Query the processed documents.
        
        Args:
            query: User's question about the documents
            language: Language for the response
            n_results: Number of relevant chunks to retrieve
            
        Returns:
            Answer based on the documents
        """
        try:
            # Search vector store
            results = self.vector_store.query(query, n_results=n_results)
            
            if not results:
                return f"I couldn't find any relevant information in the documents to answer your question."
            
            # Build context from results
            context = "\n\n".join([
                f"[From {result['metadata'].get('source', 'unknown')} - Page {result['metadata'].get('page', 'unknown')}]\n{result['document']}"
                for result in results
            ])
            
            # Generate answer using Gemini
            prompt = f"""
Based on the following document excerpts, answer this question:

Question: {query}

Document Context:
{context}

Provide a comprehensive answer in {language}. Quote relevant sections and cite sources.
If the answer is not in the provided context, say so clearly.
"""
            
            response = await self.agent.run([
                {"role": "user", "content": prompt}
            ])
            return response["text"]
            
        except Exception as e:
            logger.error(f"Error querying documents: {str(e)}")
            return f"I encountered an error while searching the documents: {str(e)}"
    
    async def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the PDF processor agent (compatible with workflow executor).
        
        Args:
            query: The user's query about documents
            context: Optional context dict
            
        Returns:
            Result dict with answer
        """
        language = context.get("language", "English") if context else "English"
        
        answer = await self.query_documents(query, language)
        
        return {
            "query": query,
            "answer": answer,
            "language": language
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about processed documents."""
        return self.vector_store.get_stats()
    
    def clear_all_documents(self) -> None:
        """Clear all documents from the vector store."""
        self.vector_store.delete_all()
        logger.info("Cleared all documents from vector store")


# Create global instance
_pdf_processor = None


def get_pdf_processor() -> PDFProcessorAgent:
    """Get or create the global PDF processor instance."""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessorAgent()
    return _pdf_processor
