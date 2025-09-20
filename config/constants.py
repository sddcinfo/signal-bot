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
    'SIGNAL_CLI_DAEMON': 60,
    'SIGNAL_CLI_LONG': 120,
    'DATABASE': 30,
    'WEB_REQUEST': 10,
    'AI_REQUEST': 120,
    'AI_RETRY_DELAY': 15,
    'MESSAGE_PROCESS_WAIT': 10,
    'POLL_INTERVAL': 5,
    'DAEMON_RECONNECT': 5,
    'PROCESS_KILL_WAIT': 5,
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
    'LOCALHOST': 'localhost',
    'FILTER_HOURS': 24,
    'MAX_MESSAGES_PER_PAGE': 100,
}


# ============= Network Configuration =============
NETWORK = {
    'DEFAULT_WEB_PORT': 8084,
    'DEFAULT_WEB_HOST': '0.0.0.0',
    'OLLAMA_DEFAULT_HOST': 'http://localhost:11434',
    'JSON_RPC_PORT': 7583,
    'SOCKET_PATH': '/var/run/signal-cli/socket',
}


# ============= Logging Configuration =============
LOGGING = {
    'DEFAULT_LEVEL': 'INFO',
    'DEBUG_LEVEL': 'DEBUG',
    'FORMAT': '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    'DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
    'MAX_LOG_SIZE': 10 * 1024 * 1024,  # 10MB
    'LOG_BACKUP_COUNT': 5,
}


# ============= Process Management =============
PROCESS = {
    'PID_FILE': 'signal_bot.pid',
    'LOCK_FILE': 'signal_bot.lock',
    'INSTANCE_CHECK_INTERVAL': 5,
    'MAX_RESTART_ATTEMPTS': 3,
    'RESTART_DELAY': 5,
}


# ============= File Paths =============
PATHS = {
    'SIGNAL_SERVICE_LOG': 'signal_service.log',
    'SIGNAL_DAEMON_LOG': 'signal_daemon.log',
    'WEB_SERVER_LOG': 'web_server.log',
    'DEBUG_LOG': 'signal_bot_debug.log',
    'DATABASE': 'signal_bot.db',
    'CONFIG_DIR': 'config',
    'WEB_DIR': 'web',
}