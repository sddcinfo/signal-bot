"""
UUID-Based Database Manager for Signal Bot

Clean, UUID-centric database design that follows Signal's architecture:
- UUID as primary key for all users
- Phone number as optional metadata
- Simplified, reusable operations
- Database-centric configuration
"""
import sqlite3
import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class User:
    """Signal user with UUID as primary identifier."""
    uuid: str
    phone_number: Optional[str] = None
    friendly_name: Optional[str] = None
    display_name: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    message_count: int = 0
    is_configured: bool = False


@dataclass
class UserReactions:
    """User reaction preferences."""
    uuid: str
    emojis: List[str]
    reaction_mode: str = 'random'  # 'random', 'sequential', 'ai'
    is_active: bool = True


@dataclass
class Group:
    """Signal group information."""
    group_id: str
    group_name: Optional[str] = None
    is_monitored: bool = False
    member_count: int = 0
    last_synced: Optional[datetime] = None


class DatabaseManager:
    """UUID-based database manager for Signal bot."""

    def __init__(self, db_path: str = "signal_bot.db", logger: Optional[logging.Logger] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
            logger: Optional logger instance
        """
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger(__name__)
        self._lock = threading.RLock()  # Use reentrant lock to allow nested calls
        self._init_database()

    def _init_database(self):
        """Initialize clean UUID-based database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Core users table - UUID as primary key
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uuid TEXT PRIMARY KEY,
                    phone_number TEXT,
                    friendly_name TEXT,
                    display_name TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    is_configured BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User reaction preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_reactions (
                    uuid TEXT PRIMARY KEY REFERENCES users(uuid) ON DELETE CASCADE,
                    emojis TEXT NOT NULL,
                    reaction_mode TEXT DEFAULT 'random',
                    is_active BOOLEAN DEFAULT TRUE,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Groups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT,
                    is_monitored BOOLEAN DEFAULT FALSE,
                    member_count INTEGER DEFAULT 0,
                    last_synced DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Group membership
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT REFERENCES groups(group_id) ON DELETE CASCADE,
                    user_uuid TEXT REFERENCES users(uuid) ON DELETE CASCADE,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (group_id, user_uuid)
                )
            """)

            # Message tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    group_id TEXT REFERENCES groups(group_id),
                    sender_uuid TEXT REFERENCES users(uuid),
                    message_text TEXT,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Attachments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                    attachment_id TEXT,
                    filename TEXT,
                    content_type TEXT,
                    file_size INTEGER,
                    file_path TEXT,
                    file_data BLOB,
                    downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_message_id ON attachments(message_id)")

            # Bot configuration (key-value store)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processed messages (for deduplication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    timestamp INTEGER PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    sender_uuid TEXT NOT NULL,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sentiment analysis results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT REFERENCES groups(group_id),
                    analysis_date DATE NOT NULL,
                    message_count INTEGER NOT NULL,
                    analysis_result TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, analysis_date)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_configured ON users(is_configured)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_monitored ON groups(is_monitored)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_timestamp ON processed_messages(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_group_date ON sentiment_analysis(group_id, analysis_date)")

            self.logger.info("Database initialized with UUID-based schema")

    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection with retry logic."""
        import time
        max_retries = 3
        retry_delay = 0.1

        with self._lock:
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(self.db_path, timeout=10.0)
                    conn.row_factory = sqlite3.Row
                    # Enable WAL mode for better concurrent access
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA busy_timeout=10000')

                    try:
                        yield conn
                        conn.commit()
                        return
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        conn.close()

                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        self.logger.warning(f"Database locked, retry {attempt + 1}/{max_retries} in {retry_delay}s")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise

    # Bot Configuration Methods
    def set_config(self, key: str, value: str) -> None:
        """Set bot configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get bot configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def get_all_config(self) -> Dict[str, str]:
        """Get all bot configuration."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM bot_config")
            return {row['key']: row['value'] for row in cursor.fetchall()}

    # User Management Methods
    def upsert_user(self, uuid: str, phone_number: Optional[str] = None,
                   display_name: Optional[str] = None, friendly_name: Optional[str] = None) -> User:
        """Create or update user by UUID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
            existing_user = cursor.fetchone()

            if existing_user:
                # Update existing user
                updates = []
                params = []

                if phone_number is not None:
                    updates.append("phone_number = ?")
                    params.append(phone_number)

                if display_name is not None:
                    updates.append("display_name = ?")
                    params.append(display_name)

                if friendly_name is not None:
                    updates.append("friendly_name = ?")
                    params.append(friendly_name)

                updates.append("last_seen = CURRENT_TIMESTAMP")
                params.append(uuid)

                if updates:
                    cursor.execute(f"""
                        UPDATE users SET {', '.join(updates)}
                        WHERE uuid = ?
                    """, params)
            else:
                # Create new user
                cursor.execute("""
                    INSERT INTO users (uuid, phone_number, display_name, friendly_name)
                    VALUES (?, ?, ?, ?)
                """, (uuid, phone_number, display_name, friendly_name))

            # Return the user
            return self.get_user(uuid)

    def get_user(self, uuid: str) -> Optional[User]:
        """Get user by UUID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
            row = cursor.fetchone()

            if not row:
                return None

            return User(
                uuid=row['uuid'],
                phone_number=row['phone_number'],
                friendly_name=row['friendly_name'],
                display_name=row['display_name'],
                first_seen=datetime.fromisoformat(row['first_seen']) if row['first_seen'] else None,
                last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                message_count=row['message_count'],
                is_configured=bool(row['is_configured'])
            )

    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number (for backward compatibility)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()

            if not row:
                return None

            return self.get_user(row['uuid'])

    def get_user_uuid_by_phone(self, phone_number: str) -> Optional[str]:
        """Get user UUID by phone number."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid FROM users WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()
            return row['uuid'] if row else None

    def get_user_by_uuid(self, uuid: str) -> Optional[User]:
        """Get user by UUID (alias for get_user for consistency)."""
        return self.get_user(uuid)

    def get_all_users(self) -> List[User]:
        """Get all users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid FROM users ORDER BY last_seen DESC")
            return [self.get_user(row['uuid']) for row in cursor.fetchall()]

    def get_configured_users(self) -> List[User]:
        """Get users with emoji configurations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid FROM users WHERE is_configured = TRUE ORDER BY last_seen DESC")
            return [self.get_user(row['uuid']) for row in cursor.fetchall()]

    def get_discovered_users(self) -> List[User]:
        """Get users without emoji configurations (discovered but not configured)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uuid FROM users WHERE is_configured = FALSE ORDER BY last_seen DESC")
            return [self.get_user(row['uuid']) for row in cursor.fetchall()]

    def increment_user_message_count(self, uuid: str) -> None:
        """Increment message count for user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET message_count = message_count + 1, last_seen = CURRENT_TIMESTAMP
                WHERE uuid = ?
            """, (uuid,))

    # User Reactions Methods
    def set_user_reactions(self, uuid: str, emojis: List[str], reaction_mode: str = 'random') -> None:
        """Set reaction preferences for user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Set reactions
            cursor.execute("""
                INSERT OR REPLACE INTO user_reactions (uuid, emojis, reaction_mode, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (uuid, json.dumps(emojis), reaction_mode))

            # Mark user as configured
            cursor.execute("""
                UPDATE users SET is_configured = TRUE WHERE uuid = ?
            """, (uuid,))

    def get_user_reactions(self, uuid: str) -> Optional[UserReactions]:
        """Get reaction preferences for user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_reactions WHERE uuid = ?", (uuid,))
            row = cursor.fetchone()

            if not row:
                return None

            return UserReactions(
                uuid=row['uuid'],
                emojis=json.loads(row['emojis']),
                reaction_mode=row['reaction_mode'],
                is_active=bool(row['is_active'])
            )

    def get_all_user_reactions(self) -> List[UserReactions]:
        """Get all active user reactions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_reactions WHERE is_active = TRUE")

            reactions = []
            for row in cursor.fetchall():
                reactions.append(UserReactions(
                    uuid=row['uuid'],
                    emojis=json.loads(row['emojis']),
                    reaction_mode=row['reaction_mode'],
                    is_active=bool(row['is_active'])
                ))
            return reactions

    def remove_user_reactions(self, uuid: str) -> None:
        """Remove reaction preferences for user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_reactions WHERE uuid = ?", (uuid,))
            cursor.execute("UPDATE users SET is_configured = FALSE WHERE uuid = ?", (uuid,))

    # Group Management Methods
    def upsert_group(self, group_id: str, group_name: Optional[str] = None,
                     is_monitored: bool = False, member_count: int = 0) -> Group:
        """Create or update group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO groups (group_id, group_name, is_monitored, member_count, last_synced)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (group_id, group_name, is_monitored, member_count))

            return self.get_group(group_id)

    def get_group(self, group_id: str) -> Optional[Group]:
        """Get group by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Convert row to dict to handle column names properly
            row_dict = dict(row)
            return Group(
                group_id=row_dict['group_id'],
                group_name=row_dict.get('group_name'),
                is_monitored=bool(row_dict.get('is_monitored', 0)),
                member_count=row_dict.get('member_count', 0),
                last_synced=datetime.fromisoformat(row_dict['last_synced']) if row_dict.get('last_synced') else None
            )

    def get_all_groups(self) -> List[Group]:
        """Get all groups."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM groups ORDER BY is_monitored DESC, group_name")
            return [self.get_group(row['group_id']) for row in cursor.fetchall()]

    def get_monitored_groups(self) -> List[Group]:
        """Get groups that are being monitored."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM groups WHERE is_monitored = TRUE")
            return [self.get_group(row['group_id']) for row in cursor.fetchall()]

    def set_group_monitoring(self, group_id: str, is_monitored: bool) -> None:
        """Set group monitoring status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE groups SET is_monitored = ? WHERE group_id = ?
            """, (is_monitored, group_id))

    def is_group_monitored(self, group_id: str) -> bool:
        """Check if a group is being monitored."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_monitored FROM groups WHERE group_id = ?", (group_id,))
            row = cursor.fetchone()
            return bool(row['is_monitored']) if row else False

    # Group Membership Methods
    def add_group_member(self, group_id: str, user_uuid: str) -> None:
        """Add user to group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO group_members (group_id, user_uuid)
                VALUES (?, ?)
            """, (group_id, user_uuid))

    def remove_group_member(self, group_id: str, user_uuid: str) -> None:
        """Remove user from group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM group_members WHERE group_id = ? AND user_uuid = ?
            """, (group_id, user_uuid))

    def get_group_members(self, group_id: str) -> List[User]:
        """Get all members of a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_uuid FROM group_members WHERE group_id = ?
            """, (group_id,))
            return [self.get_user(row['user_uuid']) for row in cursor.fetchall()]

    def get_user_groups(self, user_uuid: str) -> List[Group]:
        """Get all groups a user is a member of."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.* FROM groups g
                JOIN group_members gm ON g.group_id = gm.group_id
                WHERE gm.user_uuid = ?
            """, (user_uuid,))

            groups = []
            for row in cursor.fetchall():
                group = Group(
                    group_id=row['group_id'],
                    group_name=row['group_name'],
                    is_monitored=bool(row['is_monitored']),
                    member_count=row['member_count']
                )
                groups.append(group)
            return groups

    def sync_group_members(self, group_id: str, member_uuids: List[str]) -> None:
        """Sync group membership (replace all members)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Remove all existing members
            cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))

            # Add new members
            for uuid in member_uuids:
                cursor.execute("""
                    INSERT INTO group_members (group_id, user_uuid) VALUES (?, ?)
                """, (group_id, uuid))

            # Update member count and last sync
            cursor.execute("""
                UPDATE groups
                SET member_count = ?, last_synced = CURRENT_TIMESTAMP
                WHERE group_id = ?
            """, (len(member_uuids), group_id))

    # Message Tracking Methods
    def is_message_processed(self, timestamp: int, group_id: str, sender_uuid: str) -> bool:
        """Check if message has been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM processed_messages
                WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
            """, (timestamp, group_id, sender_uuid))
            return cursor.fetchone() is not None

    def mark_message_processed(self, timestamp: int, group_id: str, sender_uuid: str,
                             message_text: Optional[str] = None) -> Optional[int]:
        """Mark message as processed and return message ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if message_text column exists, add if not
            cursor.execute("PRAGMA table_info(processed_messages)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'message_text' in columns:
                # Insert with message_text if column exists
                cursor.execute("""
                    INSERT OR IGNORE INTO processed_messages
                    (timestamp, group_id, sender_uuid, message_text, processed_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (timestamp, group_id, sender_uuid, message_text))
            else:
                # Insert without message_text if column doesn't exist
                cursor.execute("""
                    INSERT OR IGNORE INTO processed_messages
                    (timestamp, group_id, sender_uuid, processed_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (timestamp, group_id, sender_uuid))

            message_id = None
            # Also insert into messages table for viewing
            if message_text:
                cursor.execute("""
                    INSERT OR IGNORE INTO messages
                    (timestamp, group_id, sender_uuid, message_text, processed_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (timestamp, group_id, sender_uuid, message_text))

                # Get the message ID
                cursor.execute("""
                    SELECT id FROM messages
                    WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
                """, (timestamp, group_id, sender_uuid))
                row = cursor.fetchone()
                if row:
                    message_id = row['id']

            # Increment user message count in the same transaction
            cursor.execute("""
                UPDATE users
                SET message_count = message_count + 1,
                    last_message_at = datetime('now')
                WHERE uuid = ?
            """, (sender_uuid,))

            return message_id

    def cleanup_old_messages(self, days: int = 30) -> None:
        """Clean up old processed messages."""
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM processed_messages
                WHERE processed_at < ?
            """, (cutoff_date,))

            cursor.execute("""
                DELETE FROM messages
                WHERE processed_at < ?
            """, (cutoff_date,))

            self.logger.info(f"Cleaned up messages older than {days} days")

    def get_group_messages(self, group_id: str, limit: int = 100, offset: int = 0, attachments_only: bool = False) -> List[Dict[str, Any]]:
        """Get messages from a specific group with sender info."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query based on whether we want only messages with attachments
            if attachments_only:
                query = """
                    SELECT DISTINCT
                        m.id,
                        m.timestamp,
                        m.message_text,
                        m.processed_at,
                        u.uuid as sender_uuid,
                        u.friendly_name,
                        u.display_name,
                        u.phone_number
                    FROM messages m
                    LEFT JOIN users u ON m.sender_uuid = u.uuid
                    INNER JOIN attachments a ON m.id = a.message_id
                    WHERE m.group_id = ?
                    ORDER BY m.timestamp DESC
                    LIMIT ? OFFSET ?
                """
            else:
                query = """
                    SELECT
                        m.id,
                        m.timestamp,
                        m.message_text,
                        m.processed_at,
                        u.uuid as sender_uuid,
                        u.friendly_name,
                        u.display_name,
                        u.phone_number
                    FROM messages m
                    LEFT JOIN users u ON m.sender_uuid = u.uuid
                    WHERE m.group_id = ?
                    ORDER BY m.timestamp DESC
                    LIMIT ? OFFSET ?
                """

            cursor.execute(query, (group_id, limit, offset))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'message_text': row['message_text'],
                    'processed_at': row['processed_at'],
                    'sender_uuid': row['sender_uuid'],
                    'sender_name': row['friendly_name'] or row['display_name'] or row['phone_number'] or row['sender_uuid'],
                    'sender_phone': row['phone_number']
                })
            return messages

    def get_group_message_count(self, group_id: str, attachments_only: bool = False) -> int:
        """Get total number of messages for a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if attachments_only:
                cursor.execute("""
                    SELECT COUNT(DISTINCT m.id) as count
                    FROM messages m
                    INNER JOIN attachments a ON m.id = a.message_id
                    WHERE m.group_id = ?
                """, (group_id,))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM messages WHERE group_id = ?", (group_id,))
            return cursor.fetchone()['count']

    def get_recent_group_messages(self, group_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent messages from a group within specified hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    m.id,
                    m.timestamp,
                    m.message_text,
                    m.processed_at,
                    u.uuid as sender_uuid,
                    u.friendly_name,
                    u.display_name,
                    u.phone_number
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ?
                AND m.processed_at > datetime('now', '-{} hours')
                ORDER BY m.timestamp DESC
            """.format(hours), (group_id,))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'message_text': row['message_text'],
                    'processed_at': row['processed_at'],
                    'sender_uuid': row['sender_uuid'],
                    'sender_name': row['friendly_name'] or row['display_name'] or row['phone_number'] or row['sender_uuid'],
                    'sender_phone': row['phone_number']
                })
            return messages

    def get_group_messages_by_sender(self, group_id: str) -> Dict[str, Dict[str, Any]]:
        """Get messages grouped by sender for a specific group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.uuid as sender_uuid,
                    u.friendly_name,
                    u.display_name,
                    u.phone_number,
                    COUNT(m.id) as message_count,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ?
                GROUP BY u.uuid
                ORDER BY COUNT(m.id) DESC, MAX(m.timestamp) DESC
            """, (group_id,))

            senders = {}
            for row in cursor.fetchall():
                sender_uuid = row['sender_uuid']
                sender_name = row['friendly_name'] or row['display_name'] or row['phone_number'] or sender_uuid[:8]

                senders[sender_uuid] = {
                    'name': sender_name,
                    'phone': row['phone_number'],
                    'message_count': row['message_count'],
                    'first_message': row['first_message'],
                    'last_message': row['last_message'],
                    'messages': []
                }

            # Now get recent messages for each sender
            for sender_uuid in senders.keys():
                cursor.execute("""
                    SELECT
                        m.id,
                        m.timestamp,
                        m.message_text,
                        m.processed_at
                    FROM messages m
                    WHERE m.group_id = ? AND m.sender_uuid = ?
                    ORDER BY m.timestamp DESC
                    LIMIT 10
                """, (group_id, sender_uuid))

                messages = []
                for msg_row in cursor.fetchall():
                    messages.append({
                        'id': msg_row['id'],
                        'timestamp': msg_row['timestamp'],
                        'message_text': msg_row['message_text'],
                        'processed_at': msg_row['processed_at']
                    })

                senders[sender_uuid]['messages'] = messages

            return senders

    def get_sender_messages(self, group_id: str, sender_uuid: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all messages from a specific sender in a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    m.id,
                    m.timestamp,
                    m.message_text,
                    m.processed_at,
                    u.uuid as sender_uuid,
                    u.friendly_name,
                    u.display_name,
                    u.phone_number
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ? AND m.sender_uuid = ?
                ORDER BY m.timestamp DESC
                LIMIT ? OFFSET ?
            """, (group_id, sender_uuid, limit, offset))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'message_text': row['message_text'],
                    'processed_at': row['processed_at'],
                    'sender_uuid': row['sender_uuid'],
                    'sender_name': row['friendly_name'] or row['display_name'] or row['phone_number'] or row['sender_uuid'],
                    'sender_phone': row['phone_number']
                })
            return messages

    def get_group_sender_stats(self, group_id: str) -> List[Dict[str, Any]]:
        """Get statistics for each sender in a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.uuid as sender_uuid,
                    u.friendly_name,
                    u.display_name,
                    u.phone_number,
                    COUNT(m.id) as total_messages,
                    MIN(m.timestamp) as first_message_timestamp,
                    MAX(m.timestamp) as last_message_timestamp,
                    AVG(LENGTH(m.message_text)) as avg_message_length
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ?
                GROUP BY u.uuid
                ORDER BY COUNT(m.id) DESC
            """, (group_id,))

            stats = []
            for row in cursor.fetchall():
                sender_name = row['friendly_name'] or row['display_name'] or row['phone_number'] or row['sender_uuid'][:8]

                stats.append({
                    'sender_uuid': row['sender_uuid'],
                    'sender_name': sender_name,
                    'sender_phone': row['phone_number'],
                    'total_messages': row['total_messages'],
                    'first_message_timestamp': row['first_message_timestamp'],
                    'last_message_timestamp': row['last_message_timestamp'],
                    'avg_message_length': round(row['avg_message_length'] or 0, 1)
                })

            return stats

    # Statistics Methods
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count totals
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as configured FROM users WHERE is_configured = TRUE")
            configured_users = cursor.fetchone()['configured']

            cursor.execute("SELECT COUNT(*) as total FROM groups")
            total_groups = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as monitored FROM groups WHERE is_monitored = TRUE")
            monitored_groups = cursor.fetchone()['monitored']

            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total_messages = cursor.fetchone()['total']

            # Recent activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as recent
                FROM messages
                WHERE processed_at > datetime('now', '-1 day')
            """)
            recent_messages = cursor.fetchone()['recent']

            return {
                'total_users': total_users,
                'configured_users': configured_users,
                'discovered_users': total_users - configured_users,
                'total_groups': total_groups,
                'monitored_groups': monitored_groups,
                'total_messages': total_messages,
                'recent_messages_24h': recent_messages
            }

    def consolidate_duplicate_users(self) -> int:
        """
        Consolidate duplicate user entries using UUID-first approach with timestamp resolution.

        This fixes issues where the same person has multiple UUID entries due to:
        - Malformed phone-based UUIDs (e.g., "phone_+61403999944")
        - Multiple valid UUIDs for the same phone number

        Strategy:
        1. Group users by phone number
        2. For each phone number with multiple UUIDs:
           - Identify the canonical UUID (most recent valid UUID)
           - Merge data from duplicate entries
           - Transfer group memberships to canonical UUID
           - Remove duplicate entries

        Returns:
            Number of duplicate entries removed
        """
        duplicates_removed = 0

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Find phone numbers with multiple UUID entries
                cursor.execute("""
                    SELECT phone_number, COUNT(*) as count
                    FROM users
                    WHERE phone_number IS NOT NULL AND phone_number != ''
                    GROUP BY phone_number
                    HAVING COUNT(*) > 1
                """)

                duplicate_phones = cursor.fetchall()
                self.logger.info(f"Found {len(duplicate_phones)} phone numbers with duplicate UUIDs")

                for phone_row in duplicate_phones:
                    phone_number = phone_row['phone_number']

                    # Get all UUIDs for this phone number, ordered by timestamp (newest first)
                    cursor.execute("""
                        SELECT uuid, friendly_name, display_name, created_at, last_seen,
                               message_count, is_configured,
                               CASE
                                   WHEN uuid LIKE 'phone_%' THEN 0
                                   WHEN LENGTH(uuid) = 36 AND uuid LIKE '%-%-%-%-%' THEN 2
                                   ELSE 1
                               END as uuid_quality
                        FROM users
                        WHERE phone_number = ?
                        ORDER BY uuid_quality DESC, last_seen DESC, created_at DESC
                    """, (phone_number,))

                    all_entries = cursor.fetchall()
                    if len(all_entries) <= 1:
                        continue

                    # The first entry is our canonical UUID (highest quality, most recent)
                    canonical = all_entries[0]
                    canonical_uuid = canonical['uuid']
                    duplicates = all_entries[1:]

                    self.logger.info(f"Consolidating {len(duplicates)} duplicate(s) for {phone_number} into canonical UUID {canonical_uuid}")

                    # Merge data into canonical entry
                    merged_friendly_name = canonical['friendly_name']
                    merged_display_name = canonical['display_name']
                    merged_message_count = canonical['message_count']
                    merged_is_configured = canonical['is_configured']

                    # Merge data from duplicates (prioritize non-empty values)
                    for dup in duplicates:
                        if not merged_friendly_name and dup['friendly_name']:
                            merged_friendly_name = dup['friendly_name']
                        if not merged_display_name and dup['display_name']:
                            merged_display_name = dup['display_name']
                        merged_message_count += (dup['message_count'] or 0)
                        if dup['is_configured']:
                            merged_is_configured = True

                    # Update canonical entry with merged data
                    cursor.execute("""
                        UPDATE users
                        SET friendly_name = ?, display_name = ?, message_count = ?, is_configured = ?
                        WHERE uuid = ?
                    """, (merged_friendly_name, merged_display_name, merged_message_count, merged_is_configured, canonical_uuid))

                    # Transfer group memberships from duplicates to canonical
                    for dup in duplicates:
                        dup_uuid = dup['uuid']

                        # Get groups the duplicate was a member of
                        cursor.execute("SELECT group_id FROM group_members WHERE user_uuid = ?", (dup_uuid,))
                        dup_groups = cursor.fetchall()

                        # Transfer memberships to canonical UUID
                        for group_row in dup_groups:
                            group_id = group_row['group_id']
                            # Use INSERT OR IGNORE to avoid duplicate key errors
                            cursor.execute("""
                                INSERT OR IGNORE INTO group_members (group_id, user_uuid)
                                VALUES (?, ?)
                            """, (group_id, canonical_uuid))

                        # Transfer user reactions if canonical doesn't have any
                        cursor.execute("SELECT * FROM user_reactions WHERE uuid = ?", (canonical_uuid,))
                        canonical_reactions = cursor.fetchone()

                        if not canonical_reactions:
                            cursor.execute("SELECT * FROM user_reactions WHERE uuid = ?", (dup_uuid,))
                            dup_reactions = cursor.fetchone()
                            if dup_reactions:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO user_reactions
                                    (uuid, emojis, reaction_mode, is_active, updated_at)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (canonical_uuid, dup_reactions['emojis'], dup_reactions['reaction_mode'],
                                     dup_reactions['is_active'], dup_reactions['updated_at']))

                        # Update any message references
                        cursor.execute("UPDATE messages SET sender_uuid = ? WHERE sender_uuid = ?", (canonical_uuid, dup_uuid))
                        cursor.execute("UPDATE processed_messages SET sender_uuid = ? WHERE sender_uuid = ?", (canonical_uuid, dup_uuid))

                        self.logger.debug(f"Transferred data from duplicate UUID {dup_uuid} to canonical {canonical_uuid}")

                    # Remove duplicate entries (in order: user_reactions, group_members, then users)
                    for dup in duplicates:
                        dup_uuid = dup['uuid']
                        cursor.execute("DELETE FROM user_reactions WHERE uuid = ?", (dup_uuid,))
                        cursor.execute("DELETE FROM group_members WHERE user_uuid = ?", (dup_uuid,))
                        cursor.execute("DELETE FROM users WHERE uuid = ?", (dup_uuid,))
                        duplicates_removed += 1
                        self.logger.debug(f"Removed duplicate UUID {dup_uuid}")

                self.logger.info(f"UUID consolidation complete. Removed {duplicates_removed} duplicate entries")
                return duplicates_removed

        except Exception as e:
            self.logger.error(f"Failed to consolidate duplicate users: {e}")
            return 0

    # Sentiment Analysis Methods
    def get_sentiment_analysis(self, group_id: str, analysis_date: date) -> Optional[str]:
        """Get stored sentiment analysis for a group and date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_result FROM sentiment_analysis
                WHERE group_id = ? AND analysis_date = ?
            """, (group_id, analysis_date.strftime('%Y-%m-%d')))
            row = cursor.fetchone()
            return row['analysis_result'] if row else None

    def store_sentiment_analysis(self, group_id: str, analysis_date: date,
                                message_count: int, analysis_result: str) -> None:
        """Store sentiment analysis result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sentiment_analysis
                (group_id, analysis_date, message_count, analysis_result)
                VALUES (?, ?, ?, ?)
            """, (group_id, analysis_date.strftime('%Y-%m-%d'), message_count, analysis_result))

    def get_sentiment_history(self, group_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get sentiment analysis history for a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_date, message_count, analysis_result, created_at
                FROM sentiment_analysis
                WHERE group_id = ?
                ORDER BY analysis_date DESC
                LIMIT ?
            """, (group_id, days))

            return [dict(row) for row in cursor.fetchall()]

    def get_hourly_message_counts(self, target_date: date, user_timezone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get hourly message counts by group for a specific date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if user_timezone:
                # Convert user's day to UTC range for database query
                try:
                    import zoneinfo
                    from datetime import datetime, timezone
                    tz = zoneinfo.ZoneInfo(user_timezone)

                    # Create start and end of day in user's timezone
                    start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
                    end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=tz)

                    # Convert to UTC timestamps (milliseconds)
                    start_timestamp = int(start_of_day.timestamp() * 1000)
                    end_timestamp = int(end_of_day.timestamp() * 1000)

                    # Query with timezone conversion for grouping by hour
                    cursor.execute("""
                        SELECT
                            g.group_name,
                            m.group_id,
                            CAST((m.timestamp / 1000 + ?) / 3600 % 24 AS INTEGER) as hour,
                            COUNT(*) as message_count
                        FROM messages m
                        LEFT JOIN groups g ON m.group_id = g.group_id
                        WHERE m.timestamp >= ? AND m.timestamp <= ?
                        AND m.message_text IS NOT NULL AND m.message_text != ''
                        GROUP BY m.group_id, hour
                        ORDER BY g.group_name, hour
                    """, (tz.utcoffset(start_of_day).total_seconds(), start_timestamp, end_timestamp))

                except ImportError:
                    # Fallback to UTC if zoneinfo not available
                    cursor.execute("""
                        SELECT
                            g.group_name,
                            m.group_id,
                            CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                            COUNT(*) as message_count
                        FROM messages m
                        LEFT JOIN groups g ON m.group_id = g.group_id
                        WHERE date(m.timestamp/1000, 'unixepoch') = ?
                        AND m.message_text IS NOT NULL AND m.message_text != ''
                        GROUP BY m.group_id, hour
                        ORDER BY g.group_name, hour
                    """, (target_date.strftime('%Y-%m-%d'),))
            else:
                # No timezone provided, use UTC
                cursor.execute("""
                    SELECT
                        g.group_name,
                        m.group_id,
                        CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                        COUNT(*) as message_count
                    FROM messages m
                    LEFT JOIN groups g ON m.group_id = g.group_id
                    WHERE date(m.timestamp/1000, 'unixepoch') = ?
                    AND m.message_text IS NOT NULL AND m.message_text != ''
                    GROUP BY m.group_id, hour
                    ORDER BY g.group_name, hour
                """, (target_date.strftime('%Y-%m-%d'),))

            return [dict(row) for row in cursor.fetchall()]

    def get_group_activity_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get activity summary for groups over the last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    g.group_name,
                    m.group_id,
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT date(m.timestamp/1000, 'unixepoch')) as active_days,
                    MIN(datetime(m.timestamp/1000, 'unixepoch')) as first_message,
                    MAX(datetime(m.timestamp/1000, 'unixepoch')) as last_message
                FROM messages m
                LEFT JOIN groups g ON m.group_id = g.group_id
                WHERE m.timestamp >= (strftime('%s', 'now', '-{} days') * 1000)
                AND m.message_text IS NOT NULL AND m.message_text != ''
                GROUP BY m.group_id
                ORDER BY total_messages DESC
            """.format(days))

            return [dict(row) for row in cursor.fetchall()]

    def clear_database(self) -> bool:
        """Clear all data from the database for a fresh start."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                self.logger.info("Clearing all database tables...")

                # Drop all tables in reverse order due to foreign key constraints
                tables_to_clear = [
                    'group_members',
                    'user_reactions',
                    'messages',
                    'processed_messages',
                    'sentiment_analysis',
                    'groups',
                    'users',
                    'bot_config'
                ]

                for table in tables_to_clear:
                    cursor.execute(f"DELETE FROM {table}")
                    self.logger.debug(f"Cleared table: {table}")

                # Reset auto-increment counters
                cursor.execute("DELETE FROM sqlite_sequence")

                self.logger.info("Database cleared successfully - all tables are empty")
                return True

        except Exception as e:
            self.logger.error(f"Failed to clear database: {e}")
            return False

    def get_all_messages(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all processed messages with pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    timestamp,
                    group_id,
                    sender_uuid,
                    message_text,
                    processed_at
                FROM processed_messages
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_total_message_count(self) -> int:
        """Get total count of processed messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM processed_messages")
            return cursor.fetchone()['total']

    def get_message_count_by_group(self, group_id: str) -> int:
        """Get total number of messages for a specific group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM processed_messages WHERE group_id = ?", (group_id,))
            return cursor.fetchone()['total']

    def get_messages_by_group_and_sender(self, group_id: str, sender_uuid: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages filtered by both group and sender."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # First check what columns exist
            cursor.execute("PRAGMA table_info(processed_messages)")
            columns = [col[1] for col in cursor.fetchall()]

            # Build query with proper joins to get real names
            base_columns = [
                "pm.timestamp",
                "pm.group_id",
                "pm.sender_uuid as sender",
                "pm.processed_at",
                "COALESCE(g.group_name, 'Unknown Group') as group_display",
                "COALESCE(u.friendly_name, u.display_name, u.phone_number, pm.sender_uuid) as sender_display"
            ]

            # Add message_text if it exists
            if 'message_text' in columns:
                base_columns.insert(3, "pm.message_text")
            else:
                base_columns.insert(3, "'' as message_text")

            query = f"""
                SELECT {', '.join(base_columns)}
                FROM processed_messages pm
                LEFT JOIN groups g ON pm.group_id = g.group_id
                LEFT JOIN users u ON pm.sender_uuid = u.uuid
                WHERE pm.group_id = ? AND pm.sender_uuid = ?
                ORDER BY pm.timestamp DESC
                LIMIT ? OFFSET ?
            """

            cursor.execute(query, (group_id, sender_uuid, limit, offset))
            rows = cursor.fetchall()

            # Convert to list of dicts
            result = []
            for row in rows:
                result.append({
                    'timestamp': row[0],
                    'group_id': row[1],
                    'sender': row[2],
                    'message_text': row[3],
                    'processed_at': row[4],
                    'group_display': row[5],
                    'sender_display': row[6]
                })

            return result

    def get_message_count_by_group_and_sender(self, group_id: str, sender_uuid: str) -> int:
        """Get count of messages for a specific group and sender."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM processed_messages
                WHERE group_id = ? AND sender_uuid = ?
            """, (group_id, sender_uuid))
            return cursor.fetchone()[0]

    def get_messages_by_group_with_names(self, group_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all messages with group names and sender info, optionally filtered by group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # First check what columns exist
            cursor.execute("PRAGMA table_info(processed_messages)")
            columns = [col[1] for col in cursor.fetchall()]

            # Build query with proper joins to get real names
            base_columns = [
                "pm.timestamp",
                "pm.group_id",
                "pm.sender_uuid as sender",
                "pm.processed_at",
                "COALESCE(g.group_name, 'Unknown Group') as group_display",
                "COALESCE(u.friendly_name, u.display_name, u.phone_number, pm.sender_uuid) as sender_display"
            ]

            # Add message_text if it exists, otherwise use placeholder
            if 'message_text' in columns:
                base_columns.insert(3, "pm.message_text")
            else:
                base_columns.insert(3, "'' as message_text")

            # Build query with optional group filter
            where_clause = ""
            params = []
            if group_id:
                where_clause = "WHERE pm.group_id = ?"
                params.append(group_id)

            query = f"""
                SELECT {', '.join(base_columns)}
                FROM processed_messages pm
                LEFT JOIN groups g ON pm.group_id = g.group_id
                LEFT JOIN users u ON pm.sender_uuid = u.uuid
                {where_clause}
                ORDER BY pm.timestamp DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def store_message_with_attachments(self, timestamp: int, group_id: str, sender_uuid: str,
                                     message_text: str, attachments: List[Dict[str, Any]] = None) -> int:
        """Store message in messages table and return message_id for attachment linking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (timestamp, group_id, sender_uuid, message_text)
                VALUES (?, ?, ?, ?)
            """, (timestamp, group_id, sender_uuid, message_text))
            message_id = cursor.lastrowid

            # Store attachments in the same connection to avoid locking issues
            if attachments:
                import os
                for att in attachments:
                    # Read file content if file exists
                    file_data = None
                    file_path = att.get('file_path')
                    if file_path and os.path.exists(file_path):
                        try:
                            with open(file_path, 'rb') as f:
                                file_data = f.read()
                            # Keep the file in filesystem for reference
                            self.logger.debug(f"Stored attachment in database, file remains at: {file_path}")
                        except Exception as e:
                            self.logger.warning(f"Failed to read attachment file {file_path}: {e}")

                    cursor.execute("""
                        INSERT INTO attachments (
                            message_id, attachment_id, filename, content_type,
                            file_size, file_path, file_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        message_id,
                        att.get('id'),
                        att.get('filename'),
                        att.get('contentType'),
                        att.get('size', 0),
                        file_path,  # Keep for reference, but data is in file_data
                        file_data
                    ))

            return message_id

    def store_attachment(self, message_id: int, attachment: Dict[str, Any]) -> None:
        """Store attachment information linked to a message."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attachments (
                    message_id, attachment_id, filename, content_type,
                    file_size, file_path
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                attachment.get('id'),
                attachment.get('filename'),
                attachment.get('contentType'),
                attachment.get('size', 0),
                attachment.get('file_path')  # We'll construct this path
            ))

    def get_message_attachments(self, message_id: int) -> List[Dict[str, Any]]:
        """Get all attachments for a message."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, attachment_id, filename, content_type, file_size,
                       file_path, file_data, downloaded_at
                FROM attachments
                WHERE message_id = ?
                ORDER BY downloaded_at
            """, (message_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_messages_with_attachments(self, group_id: Optional[str] = None,
                                    limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages with their attachments included."""
        messages = self.get_messages_by_group_with_names(group_id, limit, offset)

        # For messages table, we need to get the message IDs and fetch attachments
        # First, let's see if we can get message IDs from processed_messages
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if we have corresponding entries in messages table
            for message in messages:
                cursor.execute("""
                    SELECT id FROM messages
                    WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
                    LIMIT 1
                """, (message['timestamp'], message['group_id'], message['sender']))

                row = cursor.fetchone()
                if row:
                    message['attachments'] = self.get_message_attachments(row['id'])
                else:
                    message['attachments'] = []

        return messages

    def reconcile_message_tables(self) -> int:
        """
        Reconcile processed_messages table with messages table to catch any missing entries.
        Returns the number of messages synchronized.
        """
        synchronized_count = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Find messages in messages table that aren't in processed_messages
            cursor.execute("""
                SELECT m.timestamp, m.group_id, m.sender_uuid, m.message_text
                FROM messages m
                LEFT JOIN processed_messages pm ON m.timestamp = pm.timestamp
                    AND m.group_id = pm.group_id
                    AND m.sender_uuid = pm.sender_uuid
                WHERE pm.timestamp IS NULL
            """)

            missing_messages = cursor.fetchall()

            if missing_messages:
                self.logger.info(f"Found {len(missing_messages)} messages missing from processed_messages table")

                # Insert missing messages into processed_messages
                for msg in missing_messages:
                    cursor.execute("""
                        INSERT OR IGNORE INTO processed_messages
                        (timestamp, group_id, sender_uuid, message_text)
                        VALUES (?, ?, ?, ?)
                    """, (msg['timestamp'], msg['group_id'], msg['sender_uuid'], msg['message_text']))

                    if cursor.rowcount > 0:
                        synchronized_count += 1
                        self.logger.debug(f"Synchronized message: {msg['message_text'][:50]}...")

            # Also sync the other direction - remove processed_messages that don't have corresponding messages
            cursor.execute("""
                DELETE FROM processed_messages
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages m
                    WHERE m.timestamp = processed_messages.timestamp
                    AND m.group_id = processed_messages.group_id
                    AND m.sender_uuid = processed_messages.sender_uuid
                )
            """)

            if cursor.rowcount > 0:
                self.logger.info(f"Removed {cursor.rowcount} orphaned entries from processed_messages")

        if synchronized_count > 0:
            self.logger.info(f"Reconciliation complete: synchronized {synchronized_count} messages")

        return synchronized_count

    def sync_from_signal_cli_database(self) -> dict:
        """
        Sync user and group data from signal-cli's database to catch any updates.
        Returns dict with sync counts.
        """
        import sqlite3
        import os
        from pathlib import Path

        # Path to signal-cli database
        signal_cli_db_path = Path.home() / ".local/share/signal-cli/data/205515.d/account.db"

        if not signal_cli_db_path.exists():
            self.logger.warning(f"Signal-cli database not found at {signal_cli_db_path}")
            return {"users": 0, "groups": 0, "sent_messages": 0}

        sync_counts = {"users": 0, "groups": 0, "sent_messages": 0}

        try:
            # Connect to signal-cli database (read-only)
            signal_cli_conn = sqlite3.connect(f"file:{signal_cli_db_path}?mode=ro", uri=True)
            signal_cli_conn.row_factory = sqlite3.Row
            signal_cli_cursor = signal_cli_conn.cursor()

            # Sync users from recipient table
            signal_cli_cursor.execute("""
                SELECT aci, number, given_name, family_name, profile_given_name, profile_family_name
                FROM recipient
                WHERE aci IS NOT NULL
            """)

            recipients = signal_cli_cursor.fetchall()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for recipient in recipients:
                    uuid = recipient['aci']
                    phone = recipient['number']

                    # Determine best display name
                    display_name = None
                    if recipient['given_name']:
                        display_name = f"{recipient['given_name']} {recipient['family_name'] or ''}".strip()
                    elif recipient['profile_given_name']:
                        display_name = f"{recipient['profile_given_name']} {recipient['profile_family_name'] or ''}".strip()

                    # Update our users table
                    cursor.execute("""
                        INSERT OR REPLACE INTO users (uuid, phone_number, display_name, first_seen)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (uuid, phone, display_name))

                    if cursor.rowcount > 0:
                        sync_counts["users"] += 1

            # Sync groups from group_v2 table
            signal_cli_cursor.execute("""
                SELECT group_id, group_data
                FROM group_v2
            """)

            groups = signal_cli_cursor.fetchall()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for group in groups:
                    group_id = group['group_id']
                    if group_id:
                        # Convert binary group_id to base64 string for our database
                        import base64
                        group_id_str = base64.b64encode(group_id).decode('ascii')

                        # For now, just ensure group exists in our table
                        # TODO: Parse group_data blob to get group name and members
                        cursor.execute("""
                            INSERT OR IGNORE INTO groups (group_id, group_name, created_at)
                            VALUES (?, ?, datetime('now'))
                        """, (group_id_str, f"Group {group_id_str[:8]}"))

                        if cursor.rowcount > 0:
                            sync_counts["groups"] += 1

            signal_cli_conn.close()

            if any(count > 0 for count in sync_counts.values()):
                self.logger.info(f"Signal-cli sync complete: {sync_counts}")
            else:
                self.logger.debug("Signal-cli sync complete - no updates needed")

        except Exception as e:
            self.logger.error(f"Error syncing from signal-cli database: {e}")

        return sync_counts