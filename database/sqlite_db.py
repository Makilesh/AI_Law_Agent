"""
SQLite Database Handler for AI Legal Engine.

Manages persistent storage for users, conversations, messages, and documents.
"""

import os
import sqlite3
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """SQLite database handler."""

    def __init__(self, db_path: str = "legal_engine.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
        logger.info(f"Database initialized: {db_path}")

    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

    def _create_tables(self):
        """Create all required tables."""
        try:
            cursor = self.conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    phone TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    user_type TEXT DEFAULT 'regular'
                )
            """)

            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    last_message_at TEXT,
                    message_count INTEGER DEFAULT 0,
                    tags TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    language TEXT DEFAULT 'English',
                    routed_to TEXT,
                    routing_confidence REAL,
                    confidence REAL,
                    source TEXT,
                    intent TEXT,
                    entities TEXT,
                    requires_clarification INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)

            # Dialogue sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dialogue_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    current_topic TEXT,
                    current_intent TEXT,
                    dialogue_state TEXT,
                    entities_tracked TEXT,
                    unresolved_entities TEXT,
                    context_summary TEXT,
                    started_at TEXT NOT NULL,
                    updated_at TEXT,
                    turn_count INTEGER DEFAULT 0,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Generated documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    conversation_id INTEGER,
                    template_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    file_path TEXT,
                    status TEXT DEFAULT 'draft',
                    version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    finalized_at TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)

            # Bookmarks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    conversation_id INTEGER,
                    message_id INTEGER,
                    title TEXT,
                    notes TEXT,
                    category TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """)

            self.conn.commit()
            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Table creation error: {str(e)}")
            raise

    def create_user(self, user_data: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new user.

        Args:
            user_data: Dictionary with user fields

        Returns:
            Tuple of (success, message, user_id)
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, phone, created_at, user_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data['username'],
                user_data['email'],
                user_data['password_hash'],
                user_data.get('full_name'),
                user_data.get('phone'),
                user_data['created_at'],
                user_data.get('user_type', 'regular')
            ))

            self.conn.commit()
            user_id = cursor.lastrowid

            logger.info(f"User created: {user_data['username']} (ID: {user_id})")
            return True, "User created successfully", user_id

        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already exists", None
            elif "email" in str(e):
                return False, "Email already exists", None
            else:
                return False, f"Database error: {str(e)}", None

        except Exception as e:
            logger.error(f"Create user error: {str(e)}")
            return False, f"Failed to create user: {str(e)}", None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User dictionary or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User dictionary or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Get user by ID error: {str(e)}")
            return None

    def update_last_login(self, user_id: int):
        """Update user's last login time."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE id = ?
            """, (datetime.utcnow().isoformat(), user_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Update last login error: {str(e)}")

    def create_conversation(self, user_id: int, title: str = None) -> Optional[int]:
        """
        Create a new conversation.

        Args:
            user_id: User ID
            title: Conversation title (optional)

        Returns:
            Conversation ID or None
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO conversations (user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, title or "New Conversation", now, now))

            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Create conversation error: {str(e)}")
            return None

    def add_message(self, conversation_id: int, message_data: Dict) -> Optional[int]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            message_data: Message data dictionary

        Returns:
            Message ID or None
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO messages (
                    conversation_id, role, content, language,
                    routed_to, routing_confidence, confidence, source,
                    intent, entities, requires_clarification, created_at, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                message_data['role'],
                message_data['content'],
                message_data.get('language', 'English'),
                message_data.get('routed_to'),
                message_data.get('routing_confidence'),
                message_data.get('confidence'),
                message_data.get('source'),
                message_data.get('intent'),
                json.dumps(message_data.get('entities', [])),
                message_data.get('requires_clarification', 0),
                now,
                json.dumps(message_data.get('metadata', {}))
            ))

            # Update conversation
            cursor.execute("""
                UPDATE conversations
                SET message_count = message_count + 1,
                    last_message_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, now, conversation_id))

            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Add message error: {str(e)}")
            return None

    def get_conversation_messages(self, conversation_id: int, limit: int = 50) -> List[Dict]:
        """
        Get messages from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages

        Returns:
            List of message dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (conversation_id, limit))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Get messages error: {str(e)}")
            return []

    def get_user_conversations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """
        Get user's conversations.

        Args:
            user_id: User ID
            limit: Maximum number of conversations

        Returns:
            List of conversation dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations
                WHERE user_id = ? AND status = 'active'
                ORDER BY last_message_at DESC
                LIMIT ?
            """, (user_id, limit))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Get conversations error: {str(e)}")
            return []

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Global instance
_database = None


def get_database() -> Database:
    """Get or create global database instance."""
    global _database
    if _database is None:
        db_path = os.getenv("DATABASE_PATH", "legal_engine.db")
        _database = Database(db_path)
    return _database
