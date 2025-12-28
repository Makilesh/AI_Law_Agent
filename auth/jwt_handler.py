"""
JWT Token Handler for Authentication.

Handles creation and verification of JWT access and refresh tokens.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import jwt

logger = logging.getLogger(__name__)


class JWTHandler:
    """Handle JWT token creation and verification."""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        access_token_expire_hours: int = 1,
        refresh_token_expire_days: int = 7
    ):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_hours: Access token expiry in hours
            refresh_token_expire_days: Refresh token expiry in days
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")

        self.algorithm = algorithm
        self.access_token_expire_hours = access_token_expire_hours
        self.refresh_token_expire_days = refresh_token_expire_days

        logger.info(f"JWTHandler initialized (access: {access_token_expire_hours}h, refresh: {refresh_token_expire_days}d)")

    def create_access_token(self, user_id: str, username: str, additional_claims: Dict = None) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID
            username: Username
            additional_claims: Optional additional claims to include

        Returns:
            Encoded JWT token string
        """
        try:
            now = datetime.utcnow()
            expire = now + timedelta(hours=self.access_token_expire_hours)

            payload = {
                "sub": user_id,
                "username": username,
                "type": "access",
                "iat": now,
                "exp": expire
            }

            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            return token

        except Exception as e:
            logger.error(f"Access token creation error: {str(e)}")
            raise ValueError(f"Failed to create access token: {str(e)}")

    def create_refresh_token(self, user_id: str, username: str) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: User ID
            username: Username

        Returns:
            Encoded JWT refresh token string
        """
        try:
            now = datetime.utcnow()
            expire = now + timedelta(days=self.refresh_token_expire_days)

            payload = {
                "sub": user_id,
                "username": username,
                "type": "refresh",
                "iat": now,
                "exp": expire
            }

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            return token

        except Exception as e:
            logger.error(f"Refresh token creation error: {str(e)}")
            raise ValueError(f"Failed to create refresh token: {str(e)}")

    def verify_token(self, token: str, token_type: str = "access") -> Tuple[bool, Optional[Dict]]:
        """
        Verify a JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type (access or refresh)

        Returns:
            Tuple of (is_valid, payload_dict)
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return False, None

            return True, payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return False, {"error": "token_expired"}

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return False, {"error": "invalid_token"}

        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return False, {"error": str(e)}

    def decode_token_without_verification(self, token: str) -> Optional[Dict]:
        """
        Decode token without verification (for debugging only).

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None


# Global instance
_jwt_handler = None


def get_jwt_handler() -> JWTHandler:
    """Get or create global JWT handler instance."""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler(
            access_token_expire_hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", 1)),
            refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))
        )
    return _jwt_handler


def create_access_token(user_id: str, username: str, additional_claims: Dict = None) -> str:
    """Convenience function to create access token."""
    return get_jwt_handler().create_access_token(user_id, username, additional_claims)


def create_refresh_token(user_id: str, username: str) -> str:
    """Convenience function to create refresh token."""
    return get_jwt_handler().create_refresh_token(user_id, username)


def verify_token(token: str, token_type: str = "access") -> Tuple[bool, Optional[Dict]]:
    """Convenience function to verify token."""
    return get_jwt_handler().verify_token(token, token_type)
