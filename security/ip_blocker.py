"""
IP Blocker - Manage blocked and whitelisted IP addresses.

Provides functionality to block malicious IPs and whitelist trusted IPs,
with automatic expiry and audit logging.
"""

import logging
from typing import List, Optional, Dict
from cache.redis_cache import get_redis_cache
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class IPBlocker:
    """Manage IP blocking and whitelisting."""

    def __init__(self):
        """Initialize IP blocker."""
        self.cache = get_redis_cache()
        logger.info("IPBlocker initialized")

    def is_blocked(self, ip_address: str) -> bool:
        """
        Check if IP address is blocked.

        Args:
            ip_address: IP address to check

        Returns:
            True if blocked, False otherwise
        """
        if not self.cache.client:
            return False

        try:
            blocked_key = f"blocked_ips:{ip_address}"
            return self.cache.client.exists(blocked_key) > 0
        except Exception as e:
            logger.error(f"Error checking blocked IP: {str(e)}")
            return False

    def is_whitelisted(self, ip_address: str) -> bool:
        """
        Check if IP address is whitelisted.

        Args:
            ip_address: IP address to check

        Returns:
            True if whitelisted, False otherwise
        """
        if not self.cache.client:
            return False

        try:
            whitelist_key = "whitelisted_ips"
            return self.cache.client.sismember(whitelist_key, ip_address)
        except Exception as e:
            logger.error(f"Error checking whitelist: {str(e)}")
            return False

    def block_ip(
        self,
        ip_address: str,
        reason: str = "abuse",
        duration_hours: int = 24
    ) -> bool:
        """
        Block an IP address.

        Args:
            ip_address: IP to block
            reason: Reason for blocking
            duration_hours: Block duration in hours (0 = permanent)

        Returns:
            Success status
        """
        if not self.cache.client:
            return False

        try:
            blocked_key = f"blocked_ips:{ip_address}"

            # Store block info
            block_info = json.dumps({
                "ip": ip_address,
                "reason": reason,
                "blocked_at": datetime.now().isoformat(),
                "expires_at": (
                    datetime.now() + timedelta(hours=duration_hours)
                ).isoformat() if duration_hours > 0 else "never"
            })

            if duration_hours > 0:
                # Temporary block
                ttl = duration_hours * 3600
                success = self.cache.client.setex(blocked_key, ttl, block_info)
            else:
                # Permanent block
                success = self.cache.client.set(blocked_key, block_info)

            if success:
                logger.warning(f"🚫 Blocked IP {ip_address}: {reason}")

            return bool(success)

        except Exception as e:
            logger.error(f"Error blocking IP: {str(e)}")
            return False

    def unblock_ip(self, ip_address: str) -> bool:
        """
        Unblock an IP address.

        Args:
            ip_address: IP to unblock

        Returns:
            Success status
        """
        if not self.cache.client:
            return False

        try:
            blocked_key = f"blocked_ips:{ip_address}"
            success = self.cache.delete(blocked_key)

            if success:
                logger.info(f"✅ Unblocked IP: {ip_address}")

            return success

        except Exception as e:
            logger.error(f"Error unblocking IP: {str(e)}")
            return False

    def add_to_whitelist(self, ip_address: str) -> bool:
        """Add IP to whitelist (bypasses rate limiting and blocking)."""
        if not self.cache.client:
            return False

        try:
            whitelist_key = "whitelisted_ips"
            success = self.cache.client.sadd(whitelist_key, ip_address)

            if success:
                logger.info(f"✅ Added to whitelist: {ip_address}")

            return bool(success)

        except Exception as e:
            logger.error(f"Error adding to whitelist: {str(e)}")
            return False

    def remove_from_whitelist(self, ip_address: str) -> bool:
        """Remove IP from whitelist."""
        if not self.cache.client:
            return False

        try:
            whitelist_key = "whitelisted_ips"
            success = self.cache.client.srem(whitelist_key, ip_address)

            if success:
                logger.info(f"🗑️ Removed from whitelist: {ip_address}")

            return bool(success)

        except Exception as e:
            logger.error(f"Error removing from whitelist: {str(e)}")
            return False

    def get_blocked_ips(self) -> List[Dict]:
        """Get list of all blocked IPs."""
        if not self.cache.client:
            return []

        try:
            pattern = "blocked_ips:*"
            blocked_keys = self.cache.client.keys(pattern)

            blocked_ips = []
            for key in blocked_keys:
                ip_info_str = self.cache.client.get(key)
                if ip_info_str:
                    try:
                        ip_info = json.loads(ip_info_str)
                        # Add TTL info
                        ttl = self.cache.client.ttl(key)
                        ip_info["ttl_seconds"] = ttl if ttl > 0 else "permanent"
                        blocked_ips.append(ip_info)
                    except json.JSONDecodeError:
                        # Legacy format or corrupted data
                        ip = key.split(":")[-1]
                        blocked_ips.append({"ip": ip, "reason": "unknown"})

            return blocked_ips

        except Exception as e:
            logger.error(f"Error getting blocked IPs: {str(e)}")
            return []

    def get_whitelist(self) -> List[str]:
        """Get list of whitelisted IPs."""
        if not self.cache.client:
            return []

        try:
            whitelist_key = "whitelisted_ips"
            return list(self.cache.client.smembers(whitelist_key))
        except Exception as e:
            logger.error(f"Error getting whitelist: {str(e)}")
            return []

    def get_block_info(self, ip_address: str) -> Optional[Dict]:
        """Get detailed information about a blocked IP."""
        if not self.cache.client:
            return None

        try:
            blocked_key = f"blocked_ips:{ip_address}"
            info_str = self.cache.client.get(blocked_key)

            if info_str:
                info = json.loads(info_str)
                ttl = self.cache.client.ttl(blocked_key)
                info["ttl_seconds"] = ttl if ttl > 0 else "permanent"
                return info

            return None

        except Exception as e:
            logger.error(f"Error getting block info: {str(e)}")
            return None


# Global instance
_ip_blocker = None


def get_ip_blocker() -> IPBlocker:
    """Get or create global IP blocker instance."""
    global _ip_blocker
    if _ip_blocker is None:
        _ip_blocker = IPBlocker()
    return _ip_blocker
