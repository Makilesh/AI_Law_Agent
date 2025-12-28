"""
Database package for AI Legal Engine.

Provides SQLite database operations for users, conversations, and sessions.
"""

from database.sqlite_db import get_database, Database

__all__ = ['get_database', 'Database']
