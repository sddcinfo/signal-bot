"""
UUID-Based Database Manager for Signal Bot

Clean, UUID-centric database design that follows Signal's architecture:
- UUID as primary key for all users
- Phone number as optional metadata
- Simplified, reusable operations
- Database-centric configuration
"""
import sqlite3
from config.settings import Config
import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .user_display_utils import get_user_display_sql


@dataclass
class User:
    """Signal user with UUID as primary identifier."""
    uuid: str
    phone_number: Optional[str] = None
    friendly_name: Optional[str] = None
    contact_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    profile_given_name: Optional[str] = None
    profile_family_name: Optional[str] = None
    username: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    message_count: int = 0
    is_configured: bool = False

    def get_display_name(self) -> str:
        """Get the best display name for this user, prioritizing non-empty values."""
        # Priority: contact_name > given+family name > profile given+family > username > friendly_name > phone_number > UUID

        # 1. Contact name (address book name)
        if self.contact_name and self.contact_name.strip():
            return self.contact_name.strip()

        # 2. Combined given + family name from contact
        given = self.given_name.strip() if self.given_name else ""
        family = self.family_name.strip() if self.family_name else ""
        if given and family:
            return f"{given} {family}"
        elif given:
            return given
        elif family:
            return family

        # 3. Combined profile given + family name
        profile_given = self.profile_given_name.strip() if self.profile_given_name else ""
        profile_family = self.profile_family_name.strip() if self.profile_family_name else ""
        if profile_given and profile_family:
            return f"{profile_given} {profile_family}"
        elif profile_given:
            return profile_given
        elif profile_family:
            return profile_family

        # 4. Username
        if self.username and self.username.strip():
            return self.username.strip()

        # 5. Legacy friendly_name
        if self.friendly_name and self.friendly_name.strip():
            return self.friendly_name.strip()

        # 6. Phone number
        if self.phone_number:
            return self.phone_number

        # 7. UUID fallback
        return f"User {self.uuid}"

    def get_identifier(self) -> str:
        """Get a unique identifier string with both name and UUID for debugging."""
        display_name = self.get_display_name()
        if display_name.startswith("User "):
            return display_name  # Already includes UUID
        else:
            return f"{display_name} ({self.uuid})"


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
                    contact_name TEXT,
                    given_name TEXT,
                    family_name TEXT,
                    profile_given_name TEXT,
                    profile_family_name TEXT,
                    username TEXT,
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

            # Bot status tracking (24-hour rolling history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pid INTEGER,
                    status TEXT NOT NULL,
                    started_at DATETIME,
                    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_status_heartbeat ON bot_status(last_heartbeat)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_status_created ON bot_status(created_at)")

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

            # Summary analysis cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summary_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT REFERENCES groups(group_id),
                    analysis_date DATE NOT NULL,
                    hours INTEGER NOT NULL DEFAULT 24,
                    message_count INTEGER NOT NULL,
                    summary_result TEXT NOT NULL,
                    is_local_ai BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, analysis_date, hours)
                )
            """)

            # Message mentions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER REFERENCES messages(id),
                    mentioned_uuid TEXT REFERENCES users(uuid),
                    mention_start INTEGER NOT NULL,
                    mention_length INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_group_date ON summary_analysis(group_id, analysis_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentions_message ON mentions(message_id)")

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
                    # Allow connections from multiple threads
                    conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    # Enable WAL mode for better concurrent access
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA busy_timeout=15000')  # Increased to 15 seconds
                    conn.execute('PRAGMA cache_size=-32000')  # 32MB cache
                    conn.execute('PRAGMA temp_store=MEMORY')  # Use memory for temp tables

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
                   friendly_name: Optional[str] = None, contact_name: Optional[str] = None,
                   given_name: Optional[str] = None, family_name: Optional[str] = None,
                   profile_given_name: Optional[str] = None, profile_family_name: Optional[str] = None,
                   username: Optional[str] = None) -> User:
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

                # Helper function to safely update field if not empty
                def update_field_if_not_empty(field_name: str, new_value: Optional[str]):
                    if new_value is not None and new_value.strip():
                        # Handle both dict and sqlite3.Row access
                        try:
                            existing_value = existing_user[field_name] if field_name in existing_user.keys() else None
                        except (KeyError, TypeError):
                            existing_value = None

                        if not existing_value or (isinstance(existing_value, str) and existing_value.strip() == ''):
                            updates.append(f"{field_name} = ?")
                            params.append(new_value.strip())

                # Update phone_number if we don't have one
                if phone_number is not None and phone_number.strip():
                    existing_phone = existing_user['phone_number']
                    if not existing_phone or existing_phone.strip() == '':
                        updates.append("phone_number = ?")
                        params.append(phone_number)

                # Update all contact fields if not empty and we don't have them
                update_field_if_not_empty('contact_name', contact_name)
                update_field_if_not_empty('given_name', given_name)
                update_field_if_not_empty('family_name', family_name)
                update_field_if_not_empty('profile_given_name', profile_given_name)
                update_field_if_not_empty('profile_family_name', profile_family_name)
                update_field_if_not_empty('username', username)

                # Only update friendly_name if it's not empty and not a generic fallback
                if friendly_name is not None and friendly_name.strip():
                    # Don't overwrite real names with generic fallbacks
                    try:
                        existing_friendly = existing_user['friendly_name'] if 'friendly_name' in existing_user.keys() else None
                    except (KeyError, TypeError):
                        existing_friendly = None
                    is_generic_name = (
                        friendly_name.startswith(f"User {uuid}") or
                        friendly_name.startswith("User +") or
                        friendly_name == uuid
                    )
                    is_existing_real_name = (
                        existing_friendly and
                        not existing_friendly.startswith(f"User {uuid}") and
                        not existing_friendly.startswith("User +") and
                        existing_friendly != uuid
                    )

                    # Update if we don't have a name, or if new name is real and existing is generic
                    if not existing_friendly or (not is_generic_name and not is_existing_real_name):
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
                    INSERT INTO users (uuid, phone_number, friendly_name, contact_name, given_name,
                                     family_name, profile_given_name, profile_family_name, username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uuid, phone_number, friendly_name, contact_name, given_name,
                      family_name, profile_given_name, profile_family_name, username))

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

            # Helper function to safely get field from row
            def safe_get(field_name: str):
                try:
                    return row[field_name] if field_name in row.keys() else None
                except (KeyError, TypeError):
                    return None

            return User(
                uuid=row['uuid'],
                phone_number=row['phone_number'],
                friendly_name=row['friendly_name'],
                contact_name=safe_get('contact_name'),
                given_name=safe_get('given_name'),
                family_name=safe_get('family_name'),
                profile_given_name=safe_get('profile_given_name'),
                profile_family_name=safe_get('profile_family_name'),
                username=safe_get('username'),
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

    def _build_message_query_filters(self,
                                    group_id: Optional[str] = None,
                                    sender_uuid: Optional[str] = None,
                                    start_date: Optional[str] = None,
                                    end_date: Optional[str] = None,
                                    user_timezone: Optional[str] = None,
                                    attachments_only: bool = False,
                                    monitored_only: bool = True) -> tuple[List[str], List[Any]]:
        """Build standardized WHERE conditions and parameters for message queries.

        This is the SINGLE SOURCE OF TRUTH for message filtering logic.
        All message queries MUST use this method to ensure consistency.

        Args:
            group_id: Filter by specific group
            sender_uuid: Filter by specific sender
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            user_timezone: User's timezone for date conversion
            attachments_only: Only include messages with attachments
            monitored_only: Only include messages from monitored groups

        Returns:
            Tuple of (where_conditions list, params list)
        """
        where_conditions = []
        params = []

        # Group filtering
        if group_id:
            where_conditions.append("m.group_id = ?")
            params.append(group_id)
        elif monitored_only:
            # Only include monitored groups by default
            where_conditions.append("""
                m.group_id IN (
                    SELECT group_id FROM groups WHERE is_monitored = 1
                )
            """)

        # Sender filtering
        if sender_uuid:
            where_conditions.append("m.sender_uuid = ?")
            params.append(sender_uuid)

        # Date filtering using shared conversion
        if start_date:
            start_timestamp, _ = self._convert_date_to_utc_range(start_date, user_timezone)
            where_conditions.append("m.timestamp >= ?")
            params.append(start_timestamp)

        if end_date:
            _, end_timestamp = self._convert_date_to_utc_range(end_date, user_timezone)
            where_conditions.append("m.timestamp <= ?")
            params.append(end_timestamp)

        # Attachment filtering
        if attachments_only:
            where_conditions.append("""
                EXISTS (
                    SELECT 1 FROM attachments a
                    WHERE a.message_id = m.id
                )
            """)

        return where_conditions, params

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
        """Get users without emoji configurations (discovered but not configured), sorted by monitored group membership."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Sort by whether user is in monitored groups (users in monitored groups first), then by last_seen
            cursor.execute("""
                SELECT DISTINCT u.uuid,
                       CASE WHEN EXISTS (
                           SELECT 1 FROM group_members gm
                           JOIN groups g ON gm.group_id = g.group_id
                           WHERE gm.user_uuid = u.uuid AND g.is_monitored = 1
                       ) THEN 1 ELSE 0 END as in_monitored_group
                FROM users u
                WHERE u.is_configured = FALSE
                ORDER BY in_monitored_group DESC, u.last_seen DESC
            """)
            return [self.get_user(row['uuid']) for row in cursor.fetchall()]

    def get_user_statistics(self) -> dict:
        """Get user statistics including total, configured, and discovered counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get total users
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total = cursor.fetchone()['total']

            # Get configured users
            cursor.execute("SELECT COUNT(*) as configured FROM users WHERE is_configured = TRUE")
            configured = cursor.fetchone()['configured']

            # Get discovered users
            cursor.execute("SELECT COUNT(*) as discovered FROM users WHERE is_configured = FALSE")
            discovered = cursor.fetchone()['discovered']

            return {
                'total': total,
                'configured': configured,
                'discovered': discovered
            }

    def get_user_monitored_groups(self, uuid: str) -> List[str]:
        """Get list of monitored group IDs that the user belongs to."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT gm.group_id
                FROM group_members gm
                JOIN groups g ON gm.group_id = g.group_id
                WHERE gm.user_uuid = ? AND g.is_monitored = 1
            """, (uuid,))
            return [row['group_id'] for row in cursor.fetchall()]

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
        """Check if message has been processed (reacted to)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM messages
                WHERE timestamp = ? AND group_id = ? AND sender_uuid = ? AND reacted = TRUE
            """, (timestamp, group_id, sender_uuid))
            return cursor.fetchone() is not None

    def mark_message_processed(self, timestamp: int, group_id: str, sender_uuid: str,
                             message_text: Optional[str] = None) -> Optional[int]:
        """Mark message as processed (reacted to) and return message ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert or update message with reacted=TRUE
            if message_text:
                cursor.execute("""
                    INSERT OR IGNORE INTO messages
                    (timestamp, group_id, sender_uuid, message_text, processed_at, reacted)
                    VALUES (?, ?, ?, ?, datetime('now'), TRUE)
                """, (timestamp, group_id, sender_uuid, message_text))

            # Always mark as reacted (in case message already existed)
            cursor.execute("""
                UPDATE messages
                SET reacted = TRUE
                WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
            """, (timestamp, group_id, sender_uuid))

            # Get the message ID
            cursor.execute("""
                SELECT id FROM messages
                WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
            """, (timestamp, group_id, sender_uuid))
            row = cursor.fetchone()
            message_id = row['id'] if row else None

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
                    'sender_name': row['friendly_name'] or row['phone_number'] or row['sender_uuid'],
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
                    'sender_name': row['friendly_name'] or row['phone_number'] or row['sender_uuid'],
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
                sender_name = row['friendly_name'] or row['phone_number'] or sender_uuid

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
                    'sender_name': row['friendly_name'] or row['phone_number'] or row['sender_uuid'],
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
                sender_name = row['friendly_name'] or row['phone_number'] or row['sender_uuid'][:8]

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

    # Summary Analysis Methods
    def get_summary_analysis(self, group_id: str, analysis_date: date, hours: int = 24) -> Optional[str]:
        """Get stored summary analysis for a group and date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT summary_result FROM summary_analysis
                WHERE group_id = ? AND analysis_date = ? AND hours = ?
            """, (group_id, analysis_date.strftime('%Y-%m-%d'), hours))
            row = cursor.fetchone()
            return row['summary_result'] if row else None

    def store_summary_analysis(self, group_id: str, analysis_date: date, hours: int,
                              message_count: int, summary_result: str, is_local_ai: bool = False) -> None:
        """Store summary analysis result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO summary_analysis
                (group_id, analysis_date, hours, message_count, summary_result, is_local_ai)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (group_id, analysis_date.strftime('%Y-%m-%d'), hours, message_count, summary_result, is_local_ai))

    def get_summary_history(self, group_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get summary analysis history for a group."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_date, hours, message_count, summary_result, is_local_ai, created_at
                FROM summary_analysis
                WHERE group_id = ?
                ORDER BY analysis_date DESC, created_at DESC
                LIMIT ?
            """, (group_id, days))

            return [dict(row) for row in cursor.fetchall()]

    def get_hourly_message_counts(self, target_date: date, user_timezone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get hourly message counts by group for a specific date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            date_str = target_date.strftime('%Y-%m-%d')

            # Use centralized filter builder for consistency
            # monitored_only=False to include ALL groups for activity view
            where_conditions, params = self._build_message_query_filters(
                start_date=date_str,
                end_date=date_str,
                user_timezone=user_timezone,
                monitored_only=False  # Activity page shows ALL groups
            )

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            if user_timezone:
                try:
                    import zoneinfo
                    from datetime import datetime
                    tz = zoneinfo.ZoneInfo(user_timezone)
                    start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
                    offset_seconds = tz.utcoffset(start_of_day).total_seconds()

                    # Query with timezone conversion for grouping by hour
                    query = f"""
                        SELECT
                            g.group_name,
                            m.group_id,
                            CAST((m.timestamp / 1000 + ?) / 3600 % 24 AS INTEGER) as hour,
                            COUNT(*) as message_count
                        FROM messages m
                        LEFT JOIN groups g ON m.group_id = g.group_id
                        {where_clause}
                        GROUP BY m.group_id, hour
                        ORDER BY g.group_name, hour
                    """
                    cursor.execute(query, [offset_seconds] + params)

                except ImportError:
                    # Fallback to UTC if zoneinfo not available
                    query = f"""
                        SELECT
                            g.group_name,
                            m.group_id,
                            CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                            COUNT(*) as message_count
                        FROM messages m
                        LEFT JOIN groups g ON m.group_id = g.group_id
                        {where_clause}
                        GROUP BY m.group_id, hour
                        ORDER BY g.group_name, hour
                    """
                    cursor.execute(query, params)
            else:
                # No timezone provided, use UTC
                query = f"""
                    SELECT
                        g.group_name,
                        m.group_id,
                        CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                        COUNT(*) as message_count
                    FROM messages m
                    LEFT JOIN groups g ON m.group_id = g.group_id
                    {where_clause}
                    GROUP BY m.group_id, hour
                    ORDER BY g.group_name, hour
                """
                cursor.execute(query, params)

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
                f"{get_user_display_sql('u')} as sender_display"
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
                "m.timestamp",
                "m.group_id",
                "m.sender_uuid as sender",
                "NULL as processed_at",
                "COALESCE(g.group_name, 'Unknown Group') as group_display",
                f"{get_user_display_sql('u')} as sender_display"
            ]

            # Add message_text if it exists, otherwise use placeholder
            if 'message_text' in columns:
                base_columns.insert(3, "m.message_text")
            else:
                base_columns.insert(3, "m.message_text")

            # Build query with optional group filter
            where_clause = ""
            params = []
            if group_id:
                where_clause = "WHERE m.group_id = ?"
                params.append(group_id)

            query = f"""
                SELECT {', '.join(base_columns)}
                FROM messages m
                LEFT JOIN groups g ON m.group_id = g.group_id
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                {where_clause}
                ORDER BY m.timestamp DESC
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
                       file_path, file_data, downloaded_at, pack_id, sticker_id
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

    def get_messages_by_group_with_names_filtered(self, group_id: Optional[str] = None,
                                                 sender_uuid: Optional[str] = None,
                                                 attachments_only: bool = False,
                                                 start_date: Optional[str] = None,
                                                 end_date: Optional[str] = None,
                                                 user_timezone: Optional[str] = None,
                                                 limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages with proper server-side filtering including attachments and date ranges.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query with proper joins to get real names (using messages table like activity page)
            base_columns = [
                "m.id",
                "m.timestamp",
                "m.group_id",
                "m.sender_uuid as sender",
                "m.message_text",
                "m.processed_at",
                "COALESCE(g.group_name, 'Unknown Group') as group_display",
                f"{get_user_display_sql('u')} as sender_display"
            ]

            # Use centralized filter builder for consistency
            # Messages page shows only monitored groups by default (unlike Activity page)
            where_conditions, params = self._build_message_query_filters(
                group_id=group_id,
                sender_uuid=sender_uuid,
                start_date=start_date,
                end_date=end_date,
                user_timezone=user_timezone,
                attachments_only=attachments_only,
                monitored_only=not group_id  # If no specific group, show only monitored
            )

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT {', '.join(base_columns)}
                FROM messages m
                LEFT JOIN groups g ON m.group_id = g.group_id
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                {where_clause}
                ORDER BY m.timestamp DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Get attachments for each message
            messages = []
            for row in rows:
                message = dict(row)
                # Get attachments for this specific message
                cursor.execute("""
                    SELECT id FROM messages
                    WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
                    LIMIT 1
                """, (message['timestamp'], message['group_id'], message['sender']))
                msg_row = cursor.fetchone()
                if msg_row:
                    message['attachments'] = self.get_message_attachments(msg_row['id'])
                else:
                    message['attachments'] = []
                messages.append(message)

            return messages

    def get_message_count_filtered(self, group_id: Optional[str] = None,
                                  sender_uuid: Optional[str] = None,
                                  attachments_only: bool = False,
                                  start_date: Optional[str] = None,
                                  end_date: Optional[str] = None,
                                  user_timezone: Optional[str] = None) -> int:
        """Get count of messages with proper server-side filtering including attachments and date ranges.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Use centralized filter builder for consistency
            # Messages page shows only monitored groups by default
            where_conditions, params = self._build_message_query_filters(
                group_id=group_id,
                sender_uuid=sender_uuid,
                start_date=start_date,
                end_date=end_date,
                user_timezone=user_timezone,
                attachments_only=attachments_only,
                monitored_only=not group_id  # If no specific group, show only monitored
            )

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT COUNT(*) as total
                FROM messages m
                {where_clause}
            """

            cursor.execute(query, params)
            return cursor.fetchone()['total']

    # Bot Status Tracking Methods
    def record_bot_start(self, pid: int, details: str = None) -> int:
        """Record bot start and return status record ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bot_status (pid, status, started_at, details)
                VALUES (?, 'starting', datetime('now'), ?)
            """, (pid, details))
            return cursor.lastrowid

    def update_bot_status(self, status_id: int, status: str, details: str = None):
        """Update bot status record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bot_status
                SET status = ?, last_heartbeat = datetime('now'), details = ?
                WHERE id = ?
            """, (status, details, status_id))

    def record_bot_heartbeat(self, status_id: int):
        """Record bot heartbeat to show it's still alive."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bot_status
                SET last_heartbeat = datetime('now')
                WHERE id = ?
            """, (status_id,))

    def record_bot_stop(self, status_id: int, details: str = None):
        """Record bot stop."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bot_status
                SET status = 'stopped', last_heartbeat = datetime('now'), details = ?
                WHERE id = ?
            """, (details, status_id))

    def cleanup_old_bot_status(self, hours: int = 24):
        """Clean up bot status records older than specified hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM bot_status
                WHERE created_at < datetime('now', '-{} hours')
            """.format(hours))
            return cursor.rowcount

    def get_bot_status_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get bot status history for the last specified hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, pid, status, started_at, last_heartbeat, details, created_at
                FROM bot_status
                WHERE created_at >= datetime('now', '-{} hours')
                ORDER BY created_at DESC
            """.format(hours))

            return [dict(row) for row in cursor.fetchall()]

    def get_current_bot_status(self) -> Optional[Dict[str, Any]]:
        """Get the most recent bot status record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, pid, status, started_at, last_heartbeat, details, created_at
                FROM bot_status
                ORDER BY created_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            return dict(row) if row else None

    def _convert_date_to_utc_range(self, date_str: str, user_timezone: str = None) -> tuple[int, int]:
        """Convert YYYY-MM-DD date string to UTC timestamp range (start and end of day in milliseconds).

        Args:
            date_str: Date in YYYY-MM-DD format
            user_timezone: User's timezone (e.g., 'America/New_York'). If None, uses UTC.

        This ensures consistent date filtering across all methods.
        """
        import datetime

        if user_timezone:
            try:
                import zoneinfo
                # Parse date and create start/end of day in user's timezone
                target_date = datetime.date.fromisoformat(date_str)
                tz = zoneinfo.ZoneInfo(user_timezone)

                # Create start and end of day in user's timezone
                start_of_day = datetime.datetime.combine(target_date, datetime.datetime.min.time()).replace(tzinfo=tz)
                end_of_day = datetime.datetime.combine(target_date, datetime.datetime.max.time()).replace(tzinfo=tz)

                # Convert to UTC timestamps (milliseconds)
                start_timestamp = int(start_of_day.timestamp() * 1000)
                end_timestamp = int(end_of_day.timestamp() * 1000)

                return start_timestamp, end_timestamp
            except Exception:
                # Fall back to UTC if timezone conversion fails
                pass

        # Original UTC-based logic as fallback
        start_dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
        start_timestamp = int(start_dt.timestamp() * 1000)

        # Create end of day in UTC
        end_dt = start_dt.replace(hour=23, minute=59, second=59, microsecond=999000)
        end_timestamp = int(end_dt.timestamp() * 1000)

        return start_timestamp, end_timestamp

    def is_bot_running(self, max_heartbeat_age_minutes: int = 5) -> bool:
        """Check if bot is currently running based on recent heartbeat."""
        status = self.get_current_bot_status()
        if not status or status['status'] == 'stopped':
            return False

        # Check if heartbeat is recent
        from datetime import datetime, timedelta
        try:
            last_heartbeat = datetime.fromisoformat(status['last_heartbeat'])
            cutoff = datetime.now() - timedelta(minutes=max_heartbeat_age_minutes)
            return last_heartbeat > cutoff
        except:
            return False

    def add_mention(self, message_id: int, mentioned_uuid: str, mention_start: int, mention_length: int):
        """Add a mention record for a message."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mentions (message_id, mentioned_uuid, mention_start, mention_length)
                VALUES (?, ?, ?, ?)
            """, (message_id, mentioned_uuid, mention_start, mention_length))
            conn.commit()

    def get_message_mentions(self, message_id: int):
        """Get all mentions for a specific message with user details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.mention_start, m.mention_length, u.uuid, u.friendly_name, u.phone_number
                FROM mentions m
                LEFT JOIN users u ON m.mentioned_uuid = u.uuid
                WHERE m.message_id = ?
                ORDER BY m.mention_start
            """, (message_id,))

            mentions = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                mentions.append(row_dict)
            return mentions

    def get_mentions_for_messages(self, message_ids: list):
        """Get mentions for multiple messages efficiently."""
        if not message_ids:
            return {}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(message_ids))
            cursor.execute(f"""
                SELECT m.message_id, m.mention_start, m.mention_length,
                       u.uuid, u.friendly_name, u.phone_number
                FROM mentions m
                LEFT JOIN users u ON m.mentioned_uuid = u.uuid
                WHERE m.message_id IN ({placeholders})
                ORDER BY m.message_id, m.mention_start
            """, message_ids)

            mentions_by_message = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                message_id = row_dict['message_id']
                if message_id not in mentions_by_message:
                    mentions_by_message[message_id] = []
                mentions_by_message[message_id].append(row_dict)

            return mentions_by_message