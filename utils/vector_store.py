# Copyright (c) Microsoft. All rights reserved.

"""
ChromaDB Vector Store - Free local alternative to Pinecone.
"""

import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Local vector database using ChromaDB (completely free).
    """
    
    def __init__(
        self,
        collection_name: str = "legal_documents",
        persist_directory: str = None
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist data
        """
        if persist_directory is None:
            persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embedding model (free, runs locally)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info(f"ChromaDB initialized with collection: {collection_name}")
        logger.info(f"Persist directory: {persist_directory}")
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dicts
            ids: List of document IDs
        """
        try:
            # Generate embeddings
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # Generate IDs if not provided
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to ChromaDB")
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    def query(
        self,
        query_text: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store.
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            
        Returns:
            List of result dicts with 'id', 'document', 'metadata', 'distance'
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text]).tolist()
            
            # Query collection
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })
            
            logger.info(f"Query returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying documents: {str(e)}")
            return []
    
    def delete_all(self) -> None:
        """Delete all documents from the collection."""
        try:
            # Get all IDs
            all_docs = self.collection.get()
            if all_docs['ids']:
                self.collection.delete(ids=all_docs['ids'])
                logger.info(f"Deleted {len(all_docs['ids'])} documents")
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {"total_documents": 0}


# Global instance
_vector_store = None


def get_vector_store(collection_name: str = "legal_documents") -> ChromaVectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore(collection_name=collection_name)
    return _vector_store


async def search_legal_context(query: str, n_results: int = 5) -> str:
    """
    Search for legal context in the vector store.
    
    Args:
        query: Search query
        n_results: Number of results
        
    Returns:
        Combined context text
    """
    try:
        vector_store = get_vector_store()
        results = vector_store.query(query, n_results=n_results)
        
        if not results:
            return ""
        
        # Combine documents into context
        context = "\n\n".join([
            f"[Document {i+1}]\n{result['document']}"
            for i, result in enumerate(results)
        ])
        
        return context
        
    except Exception as e:
        logger.error(f"Error searching legal context: {str(e)}")
        return ""
