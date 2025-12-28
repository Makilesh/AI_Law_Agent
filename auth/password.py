"""
Password Hashing and Verification using bcrypt.

Provides secure password hashing and verification for user authentication.
"""

import logging
import bcrypt

logger = logging.getLogger(__name__)


class PasswordHandler:
    """Handle password hashing and verification."""

    def __init__(self):
        """Initialize password handler."""
        self.rounds = 12  # bcrypt rounds for hashing
        logger.info("PasswordHandler initialized")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Raises:
            ValueError: If password is invalid
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(password) > 72:  # bcrypt limitation
            raise ValueError("Password must be at most 72 characters")

        try:
            # Generate salt and hash
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

            return hashed.decode('utf-8')

        except Exception as e:
            logger.error(f"Password hashing error: {str(e)}")
            raise ValueError(f"Failed to hash password: {str(e)}")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False


# Global instance
_password_handler = None


def get_password_handler() -> PasswordHandler:
    """Get or create global password handler instance."""
    global _password_handler
    if _password_handler is None:
        _password_handler = PasswordHandler()
    return _password_handler


def hash_password(password: str) -> str:
    """Convenience function to hash a password."""
    return get_password_handler().hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Convenience function to verify a password."""
    return get_password_handler().verify_password(password, hashed_password)
