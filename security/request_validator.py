"""
Request Validator - Input sanitization and validation.

Validates and sanitizes user inputs to prevent security vulnerabilities
including SQL injection, XSS, and other attacks.
"""

import re
import logging
from typing import Optional, Tuple
import html
import os

logger = logging.getLogger(__name__)


class RequestValidator:
    """Validate and sanitize incoming requests."""

    def __init__(self, max_content_length: int = None):
        """
        Initialize request validator.

        Args:
            max_content_length: Maximum allowed content length in bytes
        """
        self.max_content_length = max_content_length or int(
            os.getenv("MAX_CONTENT_LENGTH", 100000)
        )

        # Dangerous patterns for SQL injection
        self.sql_injection_patterns = [
            r"(\bUNION\b|\bSELECT\b|\bDROP\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b)",
            r"(--|\bOR\b\s+\d+=\d+|;\s*DROP)",
            r"('\s*OR\s*'1'\s*=\s*'1)",
            r"(\bEXEC\b|\bEXECUTE\b)",
            r"(xp_cmdshell|sp_executesql)"
        ]

        # Dangerous patterns for XSS
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",  # Event handlers
            r"<iframe[^>]*>",
            r"<embed[^>]*>",
            r"<object[^>]*>",
            r"<applet[^>]*>"
        ]

        logger.info("RequestValidator initialized")

    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user query for security issues.

        Args:
            query: User input query

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Check length
            if len(query) > self.max_content_length:
                return False, "Query too long"

            # Check for empty
            if not query or not query.strip():
                return False, "Query cannot be empty"

            # Check for SQL injection
            if self._contains_sql_injection(query):
                logger.warning(f"⚠️ Potential SQL injection detected: {query[:100]}")
                return False, "Invalid query format"

            # Check for XSS
            if self._contains_xss(query):
                logger.warning(f"⚠️ Potential XSS detected: {query[:100]}")
                return False, "Invalid characters in query"

            # Check for excessive special characters (possible attack)
            special_char_ratio = sum(not c.isalnum() and not c.isspace() for c in query) / len(query)
            if special_char_ratio > 0.5:
                return False, "Too many special characters"

            return True, None

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False, "Validation error"

    def sanitize_query(self, query: str) -> str:
        """
        Sanitize user query by removing dangerous content.

        Args:
            query: User input query

        Returns:
            Sanitized query
        """
        try:
            # HTML escape
            sanitized = html.escape(query)

            # Remove control characters
            sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

            # Normalize whitespace
            sanitized = ' '.join(sanitized.split())

            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')

            return sanitized

        except Exception as e:
            logger.error(f"Sanitization error: {str(e)}")
            return ""

    def _contains_sql_injection(self, text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        text_upper = text.upper()

        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True

        return False

    def _contains_xss(self, text: str) -> bool:
        """Check if text contains XSS patterns."""
        text_lower = text.lower()

        for pattern in self.xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    def validate_file_upload(
        self,
        filename: str,
        file_size: int,
        allowed_extensions: list = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate file upload.

        Args:
            filename: Uploaded filename
            file_size: File size in bytes
            allowed_extensions: List of allowed extensions (default: ['.pdf'])

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        try:
            allowed_extensions = allowed_extensions or ['.pdf', '.docx', '.txt']

            # Check file size (default 10 MB)
            max_size = 10 * 1024 * 1024
            if file_size > max_size:
                return False, "File too large (max 10MB)"

            # Check if file has extension
            if '.' not in filename:
                return False, "File must have an extension"

            # Check extension
            ext = '.' + filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed_extensions:
                return False, f"Invalid file type (allowed: {', '.join(allowed_extensions)})"

            # Check for path traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                return False, "Invalid filename (path traversal attempt detected)"

            # Check filename length
            if len(filename) > 255:
                return False, "Filename too long"

            # Check for null bytes
            if '\x00' in filename:
                return False, "Invalid filename (null byte)"

            return True, None

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, "Validation error"

    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address format.

        Args:
            email: Email address

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            return False, "Invalid email format"

        if len(email) > 320:  # RFC 5321
            return False, "Email too long"

        return True, None

    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength.

        Args:
            password: Password string

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if len(password) > 128:
            return False, "Password too long"

        # Check for at least one uppercase
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        # Check for at least one lowercase
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

        return True, None


# Global instance
_request_validator = None


def get_request_validator() -> RequestValidator:
    """Get or create global request validator instance."""
    global _request_validator
    if _request_validator is None:
        _request_validator = RequestValidator()
    return _request_validator
