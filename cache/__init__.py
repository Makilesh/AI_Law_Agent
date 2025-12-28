"""
Cache Package - Redis-based caching with semantic similarity support.

This package provides:
- Redis cache operations (redis_cache.py)
- Semantic similarity caching (cache_strategies.py)
- Function decorators for caching (cache_decorator.py)
"""

from cache.redis_cache import RedisCache, get_redis_cache
from cache.cache_strategies import SemanticCacheStrategy, get_semantic_cache

__all__ = [
    'RedisCache',
    'get_redis_cache',
    'SemanticCacheStrategy',
    'get_semantic_cache'
]
