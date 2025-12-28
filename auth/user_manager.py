"""
User Manager for Authentication and User Operations.

Handles user registration, login, and user management operations.
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime

from auth.password import get_password_handler
from auth.jwt_handler import get_jwt_handler

logger = logging.getLogger(__name__)


class UserManager:
    """Manage user authentication and operations."""

    def __init__(self):
        """Initialize user manager."""
        self.password_handler = get_password_handler()
        self.jwt_handler = get_jwt_handler()
        logger.info("UserManager initialized")

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = None,
        phone: str = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Register a new user.

        Args:
            username: Username (unique)
            email: Email address
            password: Plain text password
            full_name: Full name (optional)
            phone: Phone number (optional)

        Returns:
            Tuple of (success, message, user_data)
        """
        try:
            # Validate inputs
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters", None

            if not email or "@" not in email:
                return False, "Invalid email address", None

            if len(password) < 8:
                return False, "Password must be at least 8 characters", None

            # Hash password
            password_hash = self.password_handler.hash_password(password)

            user_data = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name or username,
                "phone": phone,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "user_type": "regular"
            }

            logger.info(f"User registered: {username}")
            return True, "User registered successfully", user_data

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False, f"Registration failed: {str(e)}", None

    def login_user(
        self,
        username: str,
        password: str,
        password_hash_from_db: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate user login.

        Args:
            username: Username
            password: Plain text password
            password_hash_from_db: Hashed password from database

        Returns:
            Tuple of (success, message, tokens_dict)
        """
        try:
            # Verify password
            if not self.password_handler.verify_password(password, password_hash_from_db):
                logger.warning(f"Failed login attempt for: {username}")
                return False, "Invalid credentials", None

            # Generate tokens (user_id will be set by caller)
            access_token = self.jwt_handler.create_access_token(
                user_id=username,  # Will be replaced with actual ID
                username=username
            )

            refresh_token = self.jwt_handler.create_refresh_token(
                user_id=username,
                username=username
            )

            tokens = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_handler.access_token_expire_hours * 3600
            }

            logger.info(f"User logged in: {username}")
            return True, "Login successful", tokens

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, f"Login failed: {str(e)}", None

    def verify_access_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify an access token.

        Args:
            token: JWT access token

        Returns:
            Tuple of (is_valid, payload)
        """
        return self.jwt_handler.verify_token(token, "access")

    def verify_refresh_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify a refresh token.

        Args:
            token: JWT refresh token

        Returns:
            Tuple of (is_valid, payload)
        """
        return self.jwt_handler.verify_token(token, "refresh")

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Tuple of (success, message, new_access_token)
        """
        try:
            is_valid, payload = self.verify_refresh_token(refresh_token)

            if not is_valid:
                return False, "Invalid or expired refresh token", None

            # Create new access token
            new_access_token = self.jwt_handler.create_access_token(
                user_id=payload.get("sub"),
                username=payload.get("username")
            )

            return True, "Token refreshed successfully", new_access_token

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False, f"Token refresh failed: {str(e)}", None


# Global instance
_user_manager = None


def get_user_manager() -> UserManager:
    """Get or create global user manager instance."""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
