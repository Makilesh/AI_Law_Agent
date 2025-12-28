"""
Cache Strategies - Semantic similarity-based caching.

Implements intelligent caching that matches similar queries even if not identical,
using sentence embeddings and cosine similarity.
"""

import hashlib
import numpy as np
from typing import Optional, Dict, Any, List
from sentence_transformers import SentenceTransformer
import logging
import os
import time

from cache.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)


class SemanticCacheStrategy:
    """
    Semantic similarity-based caching strategy.

    Caches queries based on embedding similarity rather than exact matches.
    Example: "What is IPC 420?" and "Tell me about IPC Section 420" would match.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = None
    ):
        """
        Initialize semantic cache strategy.

        Args:
            embedding_model: Sentence transformer model name
            similarity_threshold: Minimum similarity to consider cache hit (0.0-1.0)
        """
        self.cache = get_redis_cache()

        # Load embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"✅ Embedding model loaded: {embedding_model}")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            self.embedding_model = None

        self.similarity_threshold = similarity_threshold or float(
            os.getenv("CACHE_SIMILARITY_THRESHOLD", 0.92)
        )

        logger.info(f"SemanticCache initialized (threshold: {self.similarity_threshold})")

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if not self.embedding_model:
            # Fallback: use hash of text
            return np.array([hash(text) % 1000])

        return self.embedding_model.encode(text)

    def _embedding_to_hash(self, embedding: np.ndarray) -> str:
        """Convert embedding to hash string."""
        # Round to reduce cache misses from tiny variations
        rounded = np.round(embedding, decimals=4)
        return hashlib.md5(rounded.tobytes()).hexdigest()

    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

    def get_cached_response(
        self,
        query: str,
        language: str = "English"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query if similar query exists.

        Args:
            query: User query
            language: Response language

        Returns:
            Cached response dict or None
        """
        if not self.cache.client:
            return None

        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            embedding_hash = self._embedding_to_hash(query_embedding)

            # Check for exact embedding match
            cache_key = f"query_cache:{embedding_hash}:{language}"
            cached = self.cache.get(cache_key)

            if cached:
                logger.info(f"✅ Cache HIT (exact): {query[:50]}...")
                return {
                    **cached,
                    "cached": True,
                    "cache_similarity": 1.0
                }

            # Check for similar queries (semantic search)
            similar_response = self._find_similar_cached_query(
                query_embedding,
                language
            )

            if similar_response:
                logger.info(
                    f"✅ Cache HIT (similar): {query[:50]}... "
                    f"(similarity: {similar_response.get('cache_similarity', 0):.3f})"
                )
                return similar_response

            logger.debug(f"❌ Cache MISS: {query[:50]}...")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def _find_similar_cached_query(
        self,
        query_embedding: np.ndarray,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar cached query using semantic search.

        Args:
            query_embedding: Query embedding vector
            language: Response language

        Returns:
            Cached response if similar query found, else None
        """
        if not self.cache.client:
            return None

        try:
            # Get all cached query keys for this language
            pattern = f"query_cache:*:{language}"
            cache_keys = self.cache.client.keys(pattern)

            if not cache_keys:
                return None

            # For each cached query, check similarity
            best_match = None
            best_similarity = 0.0

            # Limit to recent 50 for performance
            for cache_key in cache_keys[:50]:
                try:
                    # Get cached embedding from metadata
                    metadata_key = cache_key.replace("query_cache:", "metadata:")
                    metadata = self.cache.get(metadata_key)

                    if not metadata or "embedding" not in metadata:
                        continue

                    # Calculate similarity
                    cached_embedding = np.array(metadata["embedding"])
                    similarity = self._cosine_similarity(query_embedding, cached_embedding)

                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        response = self.cache.get(cache_key)
                        if response:
                            best_match = {
                                **response,
                                "cached": True,
                                "cache_similarity": float(similarity)
                            }

                except Exception as e:
                    logger.warning(f"Error checking similarity for {cache_key}: {str(e)}")
                    continue

            return best_match

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return None

    def cache_response(
        self,
        query: str,
        response: Dict[str, Any],
        language: str = "English",
        ttl: int = None
    ) -> bool:
        """
        Cache query response with embeddings.

        Args:
            query: User query
            response: Response to cache
            language: Response language
            ttl: Cache TTL in seconds

        Returns:
            Success status
        """
        if not self.cache.client:
            return False

        try:
            # Generate embedding
            query_embedding = self._generate_embedding(query)
            embedding_hash = self._embedding_to_hash(query_embedding)

            # Cache key
            cache_key = f"query_cache:{embedding_hash}:{language}"
            metadata_key = f"metadata:{embedding_hash}:{language}"

            # Store response
            success = self.cache.set(cache_key, response, ttl)

            # Store metadata with embedding
            metadata = {
                "query": query,
                "embedding": query_embedding.tolist(),
                "language": language,
                "timestamp": time.time()
            }
            self.cache.set(metadata_key, metadata, ttl)

            if success:
                logger.debug(f"💾 Cached response for: {query[:50]}...")

            return success

        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
            return False

    def clear_cache(self, pattern: str = "query_cache:*") -> int:
        """Clear cached queries matching pattern."""
        try:
            cleared = self.cache.clear_pattern(pattern)
            # Also clear metadata
            metadata_cleared = self.cache.clear_pattern("metadata:*")
            logger.info(f"🗑️ Cleared {cleared} cached queries and {metadata_cleared} metadata entries")
            return cleared
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        stats = self.cache.get_stats()

        # Add semantic cache specific stats
        if self.cache.client:
            try:
                metadata_count = len(self.cache.client.keys("metadata:*"))
                stats["metadata_entries"] = metadata_count
                stats["similarity_threshold"] = self.similarity_threshold
            except:
                pass

        return stats


# Global instance
_semantic_cache = None


def get_semantic_cache() -> SemanticCacheStrategy:
    """Get or create global semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCacheStrategy()
    return _semantic_cache
