# Copyright (c) Microsoft. All rights reserved.

"""
Azure Search client utilities for legal document retrieval.
"""

import os
from typing import List
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizableTextQuery
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class LegalSearchClient:
    """Client for searching legal documents using Azure Cognitive Search."""
    
    def __init__(self):
        """Initialize the Azure Search client."""
        self.search_client = SearchClient(
            endpoint=os.getenv('AZURE_SEARCH_ENDPOINT'),
            index_name=os.getenv('AZURE_SEARCH_INDEX'),
            credential=AzureKeyCredential(os.getenv('AZURE_SEARCH_KEY'))
        )
        logger.info("Azure Search client initialized")
    
    async def search_documents(self, query: str, top_k: int = 10) -> str:
        """
        Search for relevant legal documents.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            Combined context from search results
        """
        try:
            logger.info(f"Searching for: {query}")
            
            # Create vector query
            vector_query = VectorizableTextQuery(
                text=query,
                k_nearest_neighbors=5,
                fields="embedding",
                exhaustive=True
            )
            
            # Execute search
            results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                select=['id', 'content', 'metadata_page'],
                top=top_k
            )
            
            # Collect results
            results_list = list(results)
            logger.info(f"Found {len(results_list)} search results")
            
            if not results_list:
                return ""
            
            # Combine context from search results
            context = "\n".join([result['content'] for result in results_list])
            logger.info(f"Combined context length: {len(context)} characters")
            
            return context
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return ""


# Global instance
_search_client = None


def get_search_client() -> LegalSearchClient:
    """Get or create the global search client instance."""
    global _search_client
    if _search_client is None:
        _search_client = LegalSearchClient()
    return _search_client


async def search_legal_context(query: str) -> str:
    """
    Convenience function to search for legal context.
    
    Args:
        query: Search query
        
    Returns:
        Combined context from search results
    """
    client = get_search_client()
    return await client.search_documents(query)
