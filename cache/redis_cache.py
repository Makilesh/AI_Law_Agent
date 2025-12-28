"""
Redis Cache - Core caching functionality for AI Legal Engine.

Provides Redis-based caching with connection pooling, error handling,
and statistics tracking.
"""

import redis
import json
import logging
from typing import Any, Optional
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()
logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-based caching with semantic similarity support."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: str = None,
        decode_responses: bool = True
    ):
        """
        Initialize Redis cache connection.

        Args:
            host: Redis host (default from env)
            port: Redis port (default from env)
            db: Redis database number
            password: Redis password (optional)
            decode_responses: Decode byte responses to strings
        """
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.db = db or int(os.getenv("REDIS_DB", 0))
        self.password = password or os.getenv("REDIS_PASSWORD")

        # Connect to Redis
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )

            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis connected: {self.host}:{self.port}")

        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            logger.warning("⚠️ Running without cache - performance will be degraded")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                # Increment hit counter
                self.client.incr("cache_stats:hits")
                return json.loads(value) if isinstance(value, str) else value
            else:
                # Increment miss counter
                self.client.incr("cache_stats:misses")
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default from env)

        Returns:
            Success status
        """
        if not self.client:
            return False

        try:
            ttl = ttl or int(os.getenv("CACHE_TTL", 3600))

            # Serialize value
            serialized = json.dumps(value) if not isinstance(value, str) else value

            # Set with TTL
            result = self.client.setex(key, ttl, serialized)
            return result

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False

        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            return False

        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "query_cache:*")

        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error for pattern {pattern}: {str(e)}")
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self.client:
            return {
                "status": "disconnected",
                "total_hits": 0,
                "total_misses": 0,
                "hit_rate": 0.0,
                "cache_size": 0,
                "memory_usage_mb": 0.0
            }

        try:
            hits = int(self.client.get("cache_stats:hits") or 0)
            misses = int(self.client.get("cache_stats:misses") or 0)
            total = hits + misses
            hit_rate = (hits / total) if total > 0 else 0

            # Get cache size
            cache_size = len(self.client.keys("query_cache:*"))

            # Get memory usage
            info = self.client.info("memory")
            memory_mb = info.get("used_memory", 0) / (1024 * 1024)

            return {
                "status": "connected",
                "total_hits": hits,
                "total_misses": misses,
                "hit_rate": round(hit_rate, 3),
                "cache_size": cache_size,
                "memory_usage_mb": round(memory_mb, 2)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def health_check(self) -> bool:
        """Check if Redis is healthy."""
        if not self.client:
            return False

        try:
            return self.client.ping()
        except:
            return False

    def flush_all(self) -> bool:
        """Flush all keys from current database. Use with caution!"""
        if not self.client:
            return False

        try:
            self.client.flushdb()
            logger.warning("⚠️ Cache flushed - all keys deleted")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {str(e)}")
            return False


# Global instance
_redis_cache = None


def get_redis_cache() -> RedisCache:
    """Get or create global Redis cache instance."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
