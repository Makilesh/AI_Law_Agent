"""
Rate Limiter - Token bucket algorithm for API rate limiting.

Implements per-IP and per-endpoint rate limiting using Redis
to prevent abuse and ensure fair usage.
"""

import time
import logging
from typing import Optional, Dict, Tuple
from cache.redis_cache import get_redis_cache
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter using Redis.

    Supports per-IP and per-endpoint rate limiting with
    minute-based and hour-based limits.
    """

    def __init__(
        self,
        rate_per_minute: int = None,
        rate_per_hour: int = None,
        burst: int = None
    ):
        """
        Initialize rate limiter.

        Args:
            rate_per_minute: Requests allowed per minute
            rate_per_hour: Requests allowed per hour
            burst: Maximum burst size
        """
        self.cache = get_redis_cache()
        self.rate_per_minute = rate_per_minute or int(
            os.getenv("RATE_LIMIT_PER_MINUTE", 30)
        )
        self.rate_per_hour = rate_per_hour or int(
            os.getenv("RATE_LIMIT_PER_HOUR", 500)
        )
        self.burst = burst or int(os.getenv("RATE_LIMIT_BURST", 10))

        logger.info(
            f"RateLimiter initialized: {self.rate_per_minute}/min, "
            f"{self.rate_per_hour}/hour, burst: {self.burst}"
        )

    def is_allowed(
        self,
        identifier: str,
        endpoint: str = "global"
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            endpoint: Endpoint being accessed

        Returns:
            (is_allowed: bool, info: dict with remaining, reset_time)
        """
        if not self.cache.client:
            # If Redis unavailable, allow request (fail open)
            return True, {"remaining": 999, "reset_at": int(time.time()) + 60}

        try:
            # Minute-based limit
            minute_key = f"rate_limit:{identifier}:{endpoint}:minute"
            minute_allowed, minute_info = self._check_limit(
                minute_key,
                self.rate_per_minute,
                60  # 1 minute window
            )

            if not minute_allowed:
                return False, minute_info

            # Hour-based limit
            hour_key = f"rate_limit:{identifier}:{endpoint}:hour"
            hour_allowed, hour_info = self._check_limit(
                hour_key,
                self.rate_per_hour,
                3600  # 1 hour window
            )

            if not hour_allowed:
                return False, hour_info

            # Burst limit (using sliding window)
            burst_allowed = self._check_burst(identifier, endpoint)

            if not burst_allowed:
                return False, {
                    "remaining": 0,
                    "reset_at": int(time.time()) + 60,
                    "reason": "burst_limit_exceeded"
                }

            # All limits passed
            return True, {
                "remaining": min(minute_info["remaining"], hour_info["remaining"]),
                "reset_at": minute_info["reset_at"]
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # On error, allow request (fail open)
            return True, {"remaining": 1, "reset_at": int(time.time()) + 60}

    def _check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Dict]:
        """Check token bucket limit."""
        try:
            # Get current count
            current = self.cache.client.get(key)

            if current is None:
                # First request in window
                self.cache.client.setex(key, window_seconds, 1)
                return True, {
                    "remaining": limit - 1,
                    "reset_at": int(time.time()) + window_seconds
                }

            current = int(current)

            if current >= limit:
                # Limit exceeded
                ttl = self.cache.client.ttl(key)
                return False, {
                    "remaining": 0,
                    "reset_at": int(time.time()) + ttl,
                    "reason": "rate_limit_exceeded"
                }

            # Increment counter
            self.cache.client.incr(key)
            ttl = self.cache.client.ttl(key)

            return True, {
                "remaining": limit - current - 1,
                "reset_at": int(time.time()) + ttl
            }

        except Exception as e:
            logger.error(f"Token bucket error: {str(e)}")
            return True, {"remaining": 1, "reset_at": int(time.time()) + window_seconds}

    def _check_burst(self, identifier: str, endpoint: str) -> bool:
        """Check for burst traffic using sliding window."""
        try:
            burst_key = f"rate_limit:{identifier}:{endpoint}:burst"
            current_time = time.time()

            # Use sorted set for sliding window
            # Add current timestamp
            self.cache.client.zadd(burst_key, {str(current_time): current_time})

            # Remove old entries (older than 10 seconds)
            self.cache.client.zremrangebyscore(
                burst_key,
                0,
                current_time - 10
            )

            # Count requests in last 10 seconds
            count = self.cache.client.zcard(burst_key)

            # Set expiry
            self.cache.client.expire(burst_key, 60)

            return count <= self.burst

        except Exception as e:
            logger.error(f"Burst check error: {str(e)}")
            return True

    def reset(self, identifier: str, endpoint: str = "*") -> bool:
        """Reset rate limit for identifier."""
        try:
            pattern = f"rate_limit:{identifier}:{endpoint}:*"
            return self.cache.clear_pattern(pattern) > 0
        except Exception as e:
            logger.error(f"Rate limit reset error: {str(e)}")
            return False

    def get_limit_info(self, identifier: str, endpoint: str = "global") -> Dict:
        """Get current rate limit status for identifier."""
        try:
            minute_key = f"rate_limit:{identifier}:{endpoint}:minute"
            hour_key = f"rate_limit:{identifier}:{endpoint}:hour"

            minute_count = int(self.cache.client.get(minute_key) or 0)
            hour_count = int(self.cache.client.get(hour_key) or 0)

            return {
                "identifier": identifier,
                "endpoint": endpoint,
                "minute_used": minute_count,
                "minute_limit": self.rate_per_minute,
                "minute_remaining": max(0, self.rate_per_minute - minute_count),
                "hour_used": hour_count,
                "hour_limit": self.rate_per_hour,
                "hour_remaining": max(0, self.rate_per_hour - hour_count)
            }
        except Exception as e:
            logger.error(f"Error getting limit info: {str(e)}")
            return {}


# Global instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
