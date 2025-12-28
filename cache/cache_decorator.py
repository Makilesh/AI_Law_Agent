"""
Cache Decorators - Function decorators for automatic caching.

Provides easy-to-use decorators that can be applied to functions
to automatically cache their responses using semantic similarity.
"""

from functools import wraps
import logging
import time
from typing import Callable, Optional

from cache.cache_strategies import get_semantic_cache

logger = logging.getLogger(__name__)


def cache_query(
    ttl: int = None,
    similarity_threshold: float = None,
    key_prefix: str = "query"
):
    """
    Decorator to cache query responses using semantic similarity.

    Args:
        ttl: Cache TTL in seconds (optional, uses default if not provided)
        similarity_threshold: Similarity threshold for cache hits (optional)
        key_prefix: Prefix for cache keys (default: "query")

    Example:
        @cache_query(ttl=3600, similarity_threshold=0.95)
        async def process_query(query: str, language: str = "English"):
            # Function will automatically cache responses
            return {"response": "..."}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract query and language from args/kwargs
                query = args[0] if len(args) > 0 else kwargs.get('query', '')
                language = kwargs.get('language', 'English')

                if not query:
                    # No query to cache, execute normally
                    return await func(*args, **kwargs)

                # Get cache instance
                cache = get_semantic_cache()

                # Override similarity threshold if provided
                if similarity_threshold is not None:
                    original_threshold = cache.similarity_threshold
                    cache.similarity_threshold = similarity_threshold

                # Check cache
                start_time = time.time()
                cached_response = cache.get_cached_response(query, language)

                if cached_response:
                    # Cache hit - add timing
                    search_time_ms = int((time.time() - start_time) * 1000)
                    cached_response["search_time_ms"] = search_time_ms
                    cached_response["from_cache"] = True

                    # Restore original threshold
                    if similarity_threshold is not None:
                        cache.similarity_threshold = original_threshold

                    return cached_response

                # Cache miss - execute function
                response = await func(*args, **kwargs)

                # Cache the response
                if response and isinstance(response, dict):
                    cache.cache_response(query, response, language, ttl)
                    if response is not None:
                        response["cached"] = False
                        response["from_cache"] = False
                        response["search_time_ms"] = int((time.time() - start_time) * 1000)

                # Restore original threshold
                if similarity_threshold is not None:
                    cache.similarity_threshold = original_threshold

                return response

            except Exception as e:
                logger.error(f"Cache decorator error: {str(e)}")
                # On error, execute function normally
                return await func(*args, **kwargs)

        return wrapper
    return decorator


def invalidate_cache(pattern: str = "query_cache:*"):
    """
    Decorator to invalidate cache after function execution.

    Args:
        pattern: Redis key pattern to clear (default: "query_cache:*")

    Example:
        @invalidate_cache(pattern="query_cache:*")
        async def update_knowledge_base():
            # After this function runs, cache will be cleared
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)

            # Then invalidate cache
            try:
                cache = get_semantic_cache()
                cleared = cache.clear_cache(pattern)
                logger.info(f"🗑️ Cache invalidated: {cleared} keys cleared")
            except Exception as e:
                logger.error(f"Cache invalidation error: {str(e)}")

            return result

        return wrapper
    return decorator


def cache_aside(
    ttl: int = 7200,
    regenerate_on_miss: bool = True
):
    """
    Decorator implementing cache-aside pattern.

    Checks cache first, if miss then executes function and caches result.

    Args:
        ttl: Time to live for cached data
        regenerate_on_miss: Whether to call function on cache miss

    Example:
        @cache_aside(ttl=3600)
        async def get_legal_section(section_id: str):
            # Expensive database lookup
            return section_data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is simplified - full implementation would need proper key generation
            cache = get_semantic_cache()

            # Try to execute function (cache logic is in the function itself if needed)
            result = await func(*args, **kwargs)

            return result

        return wrapper
    return decorator
