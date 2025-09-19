"""
Input Validation Functions

Provides validation functions for various input types used in the application.
"""

import re
from typing import Optional, Tuple
from config.constants import PATTERNS, LIMITS


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and normalize a phone number.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, normalized_phone)

    Raises:
        ValidationError: If phone number is invalid

    Examples:
        >>> validate_phone_number("+19095551234")
        (True, '+19095551234')
        >>> validate_phone_number("909-555-1234")
        (False, None)
    """
    if not phone:
        return False, None

    # Remove spaces and hyphens for validation
    cleaned = re.sub(r'[\s\-()]', '', phone)

    # Check against pattern
    if not re.match(PATTERNS['PHONE'], cleaned):
        return False, None

    # Ensure it starts with +
    if not cleaned.startswith('+'):
        # Assume US number if no country code
        if len(cleaned) == 10:
            cleaned = '+1' + cleaned
        else:
            return False, None

    return True, cleaned


def validate_uuid(uuid: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a UUID string.

    Args:
        uuid: UUID string to validate

    Returns:
        Tuple of (is_valid, normalized_uuid)

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        (True, '550e8400-e29b-41d4-a716-446655440000')
    """
    if not uuid:
        return False, None

    # Convert to lowercase for consistency
    uuid_lower = uuid.lower()

    if not re.match(PATTERNS['UUID'], uuid_lower):
        return False, None

    return True, uuid_lower


def validate_group_id(group_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Signal group ID.

    Args:
        group_id: Group ID to validate

    Returns:
        Tuple of (is_valid, normalized_group_id)

    Examples:
        >>> validate_group_id("abcd1234...")  # 44 char base64
        (True, 'abcd1234...')
    """
    if not group_id:
        return False, None

    # Check if it matches the expected pattern
    if not re.match(PATTERNS['GROUP_ID'], group_id):
        return False, None

    return True, group_id


def validate_message_content(
    content: str,
    max_length: Optional[int] = None,
    allow_empty: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate message content.

    Args:
        content: Message content to validate
        max_length: Maximum allowed length (defaults to LIMITS['MAX_MESSAGE_LENGTH'])
        allow_empty: Whether to allow empty messages

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_message_content("Hello, world!")
        (True, None)
        >>> validate_message_content("", allow_empty=False)
        (False, 'Message content cannot be empty')
    """
    if not content:
        if allow_empty:
            return True, None
        return False, "Message content cannot be empty"

    max_len = max_length or LIMITS['MAX_MESSAGE_LENGTH']
    if len(content) > max_len:
        return False, f"Message exceeds maximum length of {max_len} characters"

    # Check for control characters (except newlines and tabs)
    control_chars = re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', content)
    if control_chars:
        return False, "Message contains invalid control characters"

    return True, None


def validate_emoji(emoji: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an emoji string for user/group configuration.

    Args:
        emoji: Emoji string to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_emoji("😀")
        (True, None)
        >>> validate_emoji("hello")
        (False, 'Not a valid emoji')
    """
    if not emoji:
        return False, "Emoji cannot be empty"

    if len(emoji) > LIMITS['MAX_EMOJI_LENGTH']:
        return False, f"Emoji exceeds maximum length of {LIMITS['MAX_EMOJI_LENGTH']}"

    # Basic check for emoji-like characters
    # This is a simplified check - could be enhanced with a proper emoji library
    if not any(ord(char) > 127 for char in emoji):
        return False, "Not a valid emoji"

    return True, None


def validate_username(
    username: str,
    min_length: int = 2,
    max_length: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a username.

    Args:
        username: Username to validate
        min_length: Minimum length (default: 2)
        max_length: Maximum length (defaults to LIMITS['MAX_USERNAME'])

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_username("john_doe")
        (True, None)
        >>> validate_username("a")
        (False, 'Username must be at least 2 characters')
    """
    if not username:
        return False, "Username cannot be empty"

    if len(username) < min_length:
        return False, f"Username must be at least {min_length} characters"

    max_len = max_length or LIMITS['MAX_USERNAME']
    if len(username) > max_len:
        return False, f"Username exceeds maximum length of {max_len}"

    # Allow letters, numbers, underscores, hyphens, and dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return False, "Username contains invalid characters"

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an email address.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, normalized_email)

    Examples:
        >>> validate_email("user@example.com")
        (True, 'user@example.com')
    """
    if not email:
        return False, None

    # Convert to lowercase for consistency
    email_lower = email.lower().strip()

    if not re.match(PATTERNS['EMAIL'], email_lower):
        return False, None

    return True, email_lower


def validate_command(command: str, valid_commands: list) -> Tuple[bool, Optional[str]]:
    """
    Validate a command string.

    Args:
        command: Command to validate
        valid_commands: List of valid command names

    Returns:
        Tuple of (is_valid, normalized_command)

    Examples:
        >>> validate_command("/help", ["help", "status"])
        (True, 'help')
    """
    if not command:
        return False, None

    # Remove command prefix if present
    if command.startswith('/'):
        command = command[1:]

    # Convert to lowercase
    command_lower = command.lower().strip()

    if command_lower not in valid_commands:
        return False, None

    return True, command_lower