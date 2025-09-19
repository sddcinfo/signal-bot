"""
Application Constants

This module contains immutable constants used throughout the application.
These are not configuration values but rather fixed constants.
"""

from enum import Enum


# ============= Message Types =============
class MessageType(Enum):
    """Signal message types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    REACTION = "reaction"
    TYPING = "typing"
    READ_RECEIPT = "read_receipt"


# ============= User Roles =============
class UserRole(Enum):
    """User role types."""
    ADMIN = "admin"
    USER = "user"
    BOT = "bot"
    GUEST = "guest"


# ============= Response Status =============
class ResponseStatus(Enum):
    """API response status codes."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    PROCESSING = "processing"


# ============= Sentiment Values =============
class Sentiment(Enum):
    """Sentiment analysis values."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


# ============= Database Tables =============
DB_TABLES = {
    'USERS': 'users',
    'GROUPS': 'groups',
    'MESSAGES': 'messages',
    'GROUP_MEMBERS': 'group_members',
    'CONFIG': 'config',
    'INSTANCE_STATUS': 'instance_status',
    'COMMANDS': 'commands',
    'COMMAND_USAGE': 'command_usage',
}


# ============= Command Names =============
COMMANDS = {
    'HELP': 'help',
    'STATUS': 'status',
    'STATS': 'stats',
    'SUMMARY': 'summary',
    'SENTIMENT': 'sentiment',
    'CONFIG': 'config',
    'MONITOR': 'monitor',
    'UNMONITOR': 'unmonitor',
    'EMOJI': 'emoji',
}


# ============= HTTP Status Codes =============
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'SERVER_ERROR': 500,
}


# ============= Regex Patterns =============
PATTERNS = {
    'UUID': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    'PHONE': r'^\+?[1-9]\d{1,14}$',
    'EMAIL': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'GROUP_ID': r'^[a-zA-Z0-9+/=]{44}$',
}


# ============= Time Constants =============
# All in seconds
TIMEOUTS = {
    'SIGNAL_CLI': 30,
    'DATABASE': 30,
    'WEB_REQUEST': 10,
    'AI_REQUEST': 120,
}


# ============= Size Limits =============
LIMITS = {
    'MAX_MESSAGE_LENGTH': 4000,
    'MAX_GROUP_NAME': 100,
    'MAX_USERNAME': 50,
    'MAX_EMOJI_LENGTH': 10,
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
}


# ============= Default Values =============
DEFAULTS = {
    'USER_EMOJI': '👤',
    'GROUP_EMOJI': '👥',
    'BOT_NAME': 'Signal Bot',
    'UNKNOWN_USER': 'Unknown User',
    'UNKNOWN_GROUP': 'Unknown Group',
}