"""
Common Utility Functions

Shared helper functions used throughout the Signal Bot application.
"""

import re
import hashlib
from datetime import datetime
from typing import Optional, Any
from config.constants import PATTERNS


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB", "256 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def safe_strip(value: Any) -> Optional[str]:
    """
    Safely strip whitespace from strings, handling None and non-string types.

    Args:
        value: Value to strip (can be None, string, or any type)

    Returns:
        Stripped string or None if input is None or empty

    Examples:
        >>> safe_strip("  hello  ")
        'hello'
        >>> safe_strip(None)
        None
        >>> safe_strip(123)
        None
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def is_valid_uuid(identifier: str) -> bool:
    """
    Check if a string is a valid UUID format.

    Args:
        identifier: String to validate

    Returns:
        True if valid UUID format, False otherwise

    Examples:
        >>> is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_valid_uuid("not-a-uuid")
        False
    """
    if not identifier or not isinstance(identifier, str):
        return False
    return bool(re.match(PATTERNS['UUID'], identifier.lower()))


def is_valid_phone(phone: str) -> bool:
    """
    Check if a string is a valid phone number format.

    Args:
        phone: Phone number string to validate

    Returns:
        True if valid phone format, False otherwise

    Examples:
        >>> is_valid_phone("+19095551234")
        True
        >>> is_valid_phone("123")
        False
    """
    if not phone or not isinstance(phone, str):
        return False
    return bool(re.match(PATTERNS['PHONE'], phone))


def phone_to_uuid(phone_number: str) -> str:
    """
    Convert a phone number to a deterministic UUID format.

    This is used for creating consistent UUIDs for phone-only contacts.

    Args:
        phone_number: Phone number to convert

    Returns:
        UUID string derived from phone number

    Examples:
        >>> phone_to_uuid("+19095551234")
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """
    # Create deterministic UUID from phone number hash
    phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:32]
    return f"{phone_hash[:8]}-{phone_hash[8:12]}-{phone_hash[12:16]}-{phone_hash[16:20]}-{phone_hash[20:32]}"


def format_phone_number(phone: str) -> str:
    """
    Format a phone number for display.

    Args:
        phone: Phone number to format

    Returns:
        Formatted phone number string

    Examples:
        >>> format_phone_number("+19095551234")
        '+1 (909) 555-1234'
    """
    if not phone:
        return ""

    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # US phone number formatting
    if cleaned.startswith('+1') and len(cleaned) == 12:
        return f"+1 ({cleaned[2:5]}) {cleaned[5:8]}-{cleaned[8:12]}"

    # Default: just return cleaned number
    return cleaned


def get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string

    Examples:
        >>> get_timestamp()
        '2024-01-15T10:30:45.123456'
    """
    return datetime.utcnow().isoformat()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length, adding suffix if truncated.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 100)
        suffix: Suffix to add if truncated (default: "...")

    Returns:
        Truncated text with suffix if needed

    Examples:
        >>> truncate_text("This is a very long text", 10)
        'This is...'
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    # Account for suffix length
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix

    return text[:truncate_at] + suffix


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Examples:
        >>> format_duration(65)
        '1m 5s'
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds < 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem

    Examples:
        >>> sanitize_filename("my/file:name?.txt")
        'my_file_name_.txt'
    """
    if not filename:
        return "unnamed"

    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')

    # Ensure it's not empty
    return sanitized if sanitized else "unnamed"


def parse_bool(value: Any) -> bool:
    """
    Parse various representations of boolean values.

    Args:
        value: Value to parse as boolean

    Returns:
        Boolean representation

    Examples:
        >>> parse_bool("true")
        True
        >>> parse_bool("1")
        True
        >>> parse_bool("no")
        False
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on', 'enabled')

    return bool(value)