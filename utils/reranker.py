# Copyright (c) Microsoft. All rights reserved.

"""
Simple Reranker - Improves search result quality through keyword-based reranking.
Phase 3: Advanced RAG with Reranking
"""

import logging
from typing import List, Dict, Any
import re
from collections import Counter

logger = logging.getLogger(__name__)


class Reranker:
    """
    Simple reranker that scores results based on keyword overlap and position.
    No external ML models required - uses lightweight lexical matching.
    """
    
    def __init__(self):
        """Initialize the reranker."""
        logger.info("Reranker initialized with keyword overlap scoring")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text by removing common words and normalizing.
        
        Args:
            text: Input text
            
        Returns:
            List of normalized keywords
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Common stop words to ignore
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with',
            'to', 'for', 'of', 'as', 'by', 'from', 'this', 'that', 'these', 'those',
            'what', 'when', 'where', 'who', 'how', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
            'can', 'must', 'shall', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me',
            'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'
        }
        
        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_keyword_overlap(self, query: str, document: str) -> float:
        """
        Calculate keyword overlap score between query and document.
        
        Args:
            query: Search query
            document: Document text
            
        Returns:
            Overlap score between 0 and 1
        """
        query_keywords = self._extract_keywords(query)
        doc_keywords = self._extract_keywords(document)
        
        if not query_keywords:
            return 0.0
        
        # Count keyword frequencies
        query_counter = Counter(query_keywords)
        doc_counter = Counter(doc_keywords)
        
        # Calculate overlap
        overlap_count = 0
        for keyword, query_freq in query_counter.items():
            if keyword in doc_counter:
                # Give credit for keyword presence, with bonus for frequency
                overlap_count += min(query_freq, doc_counter[keyword])
        
        # Normalize by query length
        max_possible_overlap = sum(query_counter.values())
        overlap_score = overlap_count / max_possible_overlap if max_possible_overlap > 0 else 0.0
        
        return overlap_score
    
    def _calculate_position_score(self, position: int, total_results: int) -> float:
        """
        Calculate position-based score (earlier results get higher scores).
        
        Args:
            position: Position in original results (0-indexed)
            total_results: Total number of results
            
        Returns:
            Position score between 0 and 1
        """
        if total_results <= 1:
            return 1.0
        
        # Linear decay: first result gets 1.0, last gets 0.0
        position_score = 1.0 - (position / (total_results - 1))
        return position_score
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        keyword_weight: float = 0.7,
        position_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results based on keyword overlap and position.
        
        Args:
            query: Original search query
            results: List of search results with 'document' field
            keyword_weight: Weight for keyword overlap (default: 0.7)
            position_weight: Weight for position score (default: 0.3)
            
        Returns:
            Reranked results with added 'rerank_score' field
        """
        if not results:
            logger.warning("No results to rerank")
            return []
        
        if not query or not query.strip():
            logger.warning("Empty query provided for reranking")
            return results
        
        try:
            # Score each result
            scored_results = []
            total_results = len(results)
            
            for i, result in enumerate(results):
                document = result.get('document', '')
                
                # Calculate component scores
                keyword_score = self._calculate_keyword_overlap(query, document)
                position_score = self._calculate_position_score(i, total_results)
                
                # Calculate weighted final score
                final_score = (keyword_weight * keyword_score) + (position_weight * position_score)
                
                # Add score to result
                result_copy = result.copy()
                result_copy['rerank_score'] = round(final_score, 4)
                result_copy['keyword_score'] = round(keyword_score, 4)
                result_copy['position_score'] = round(position_score, 4)
                result_copy['original_position'] = i
                
                scored_results.append(result_copy)
            
            # Sort by rerank score (descending)
            reranked_results = sorted(
                scored_results,
                key=lambda x: x['rerank_score'],
                reverse=True
            )
            
            logger.info(
                f"Reranked {len(results)} results. "
                f"Top score: {reranked_results[0]['rerank_score']:.4f}"
            )
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error during reranking: {str(e)}")
            # Return original results on error
            return results


# Global instance
_reranker = None


def get_reranker() -> Reranker:
    """Get or create the global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
