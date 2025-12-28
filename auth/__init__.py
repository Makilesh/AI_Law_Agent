"""
Authentication package for AI Legal Engine.

Provides JWT-based authentication, password hashing, and user management.
"""

from auth.jwt_handler import create_access_token, create_refresh_token, verify_token, get_jwt_handler
from auth.password import hash_password, verify_password, get_password_handler
from auth.user_manager import get_user_manager

__all__ = [
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'get_jwt_handler',
    'hash_password',
    'verify_password',
    'get_password_handler',
    'get_user_manager'
]
