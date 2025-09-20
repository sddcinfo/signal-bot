# Signal Bot Style Guide

## Overview

This document outlines the coding standards and best practices for the Signal Bot codebase. Following these guidelines ensures consistency, maintainability, and high code quality across the project.

## Python Version

- **Required:** Python 3.8+
- **Recommended:** Python 3.10+

## Code Structure

### Module Organization

```
signal-bot/
├── config/          # Configuration and constants
├── utils/           # Shared utilities
├── services/        # Business logic services
├── models/          # Data models and database
├── web/            # Web interface
└── docs/           # Documentation
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
import sys
from typing import Optional, List

# Third-party
import requests
from sqlalchemy import create_engine

# Local
from config.settings import Config
from utils.common import safe_strip
from models.database import DatabaseManager
```

## Naming Conventions

### Variables and Functions

- Use `snake_case` for variables and functions
- Be descriptive but concise
- Avoid abbreviations unless widely understood

```python
# Good
user_phone_number = "+19095551234"
def calculate_message_count():
    pass

# Bad
usrPhn = "+19095551234"
def calc_msg_cnt():
    pass
```

### Classes

- Use `PascalCase` for class names
- Be descriptive and indicate purpose

```python
# Good
class MessageProcessor:
    pass

class DatabaseManager:
    pass

# Bad
class message_processor:
    pass

class DBMgr:
    pass
```

### Constants

- Use `UPPER_CASE` with underscores
- Define in `config/constants.py` or at module level

```python
# Good
MAX_MESSAGE_LENGTH = 4000
DEFAULT_TIMEOUT = 30

# Bad
maxMessageLength = 4000
default_timeout = 30
```

### Private Methods and Variables

- Prefix with single underscore for internal use
- Double underscore only for name mangling (rare)

```python
class Service:
    def __init__(self):
        self._internal_state = {}

    def _helper_method(self):
        """Internal helper method."""
        pass
```

## Documentation

### Docstrings

Use Google-style docstrings for all public functions, classes, and modules.

```python
def process_message(content: str, max_length: int = 100) -> str:
    """
    Process and validate message content.

    Args:
        content: The message content to process
        max_length: Maximum allowed length (default: 100)

    Returns:
        Processed message string

    Raises:
        ValueError: If content is invalid

    Examples:
        >>> process_message("Hello, world!")
        'Hello, world!'
    """
    pass
```

### Type Hints

Always use type hints for function arguments and return values.

```python
from typing import Optional, List, Dict, Any

def get_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user data by ID."""
    pass

def process_messages(messages: List[str]) -> List[str]:
    """Process multiple messages."""
    pass
```

### Comments

- Use comments sparingly - code should be self-documenting
- Explain WHY, not WHAT
- Update comments when code changes

```python
# Good: Explains why
# Use exponential backoff to avoid overwhelming the API
delay = base_delay * (2 ** attempt)

# Bad: Explains what (obvious from code)
# Multiply base_delay by 2 to the power of attempt
delay = base_delay * (2 ** attempt)
```

## Error Handling

### Use Specific Exceptions

```python
# Good
try:
    result = process_data(data)
except ValueError as e:
    logger.error(f"Invalid data format: {e}")
except ConnectionError as e:
    logger.error(f"Network error: {e}")

# Bad
try:
    result = process_data(data)
except Exception as e:
    logger.error(f"Error: {e}")
```

### Custom Exceptions

Define custom exceptions when appropriate:

```python
class SignalBotError(Exception):
    """Base exception for Signal Bot."""
    pass

class ConfigurationError(SignalBotError):
    """Configuration-related errors."""
    pass
```

## Logging

### Use Module-Specific Loggers

```python
from utils.logging import get_logger

logger = get_logger(__name__)

def process():
    logger.info("Processing started")
    try:
        # ... processing ...
        logger.debug("Intermediate step completed")
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
```

### Log Levels

- **DEBUG:** Detailed diagnostic information
- **INFO:** General informational messages
- **WARNING:** Warning messages for potentially harmful situations
- **ERROR:** Error events that might still allow continuation
- **CRITICAL:** Very severe errors that might cause abort

## Database Operations

### Use Context Managers

```python
# Good
with self.db._get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (user_id,))
    return cursor.fetchone()

# Bad
conn = self.db._get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE uuid = ?", (user_id,))
result = cursor.fetchone()
conn.close()
return result
```

### Use Parameterized Queries

```python
# Good - Safe from SQL injection
cursor.execute("SELECT * FROM users WHERE uuid = ?", (user_id,))

# Bad - Vulnerable to SQL injection
cursor.execute(f"SELECT * FROM users WHERE uuid = '{user_id}'")
```

## Configuration Management

### Use Centralized Configuration

```python
from config.settings import Config

config = Config()
signal_path = config.SIGNAL_CLI_PATH
timeout = config.get('TIMEOUT', 30)  # With default
```

### Environment Variables

- Prefix with `SIGNAL_BOT_` for clarity
- Document in `.env.example`
- Never commit secrets

## Testing

### Unit Tests

```python
import unittest
from utils.common import safe_strip

class TestCommonUtils(unittest.TestCase):
    def test_safe_strip(self):
        """Test safe_strip handles various inputs."""
        self.assertEqual(safe_strip("  test  "), "test")
        self.assertIsNone(safe_strip(None))
        self.assertIsNone(safe_strip(""))
```

### Test Organization

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test data
└── conftest.py     # Pytest configuration
```

## Performance

### Use Generators for Large Data Sets

```python
# Good - Memory efficient
def get_messages():
    with self.db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages")
        for row in cursor:
            yield Message(row)

# Bad - Loads all into memory
def get_messages():
    with self.db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages")
        return [Message(row) for row in cursor.fetchall()]
```

### Cache Expensive Operations

```python
from utils.decorators import cache_result

@cache_result(ttl=300)  # Cache for 5 minutes
def expensive_calculation(param):
    # ... complex calculation ...
    return result
```

## Security

### Never Log Sensitive Data

```python
# Good
logger.info(f"User {user_id} authenticated")

# Bad
logger.info(f"User {user_id} authenticated with password {password}")
```

### Validate All Inputs

```python
from utils.validators import validate_phone_number

def send_message(phone: str, content: str):
    is_valid, normalized = validate_phone_number(phone)
    if not is_valid:
        raise ValueError(f"Invalid phone number: {phone}")

    # Use normalized phone number
    _send_to_signal(normalized, content)
```

## Code Quality Tools

### Required Tools

- **black:** Code formatting
- **pylint:** Code analysis
- **mypy:** Type checking
- **pytest:** Testing

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/pylint-dev/pylint
    rev: v2.16.0
    hooks:
      - id: pylint
```

## Git Commit Messages

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes
- **refactor:** Code refactoring
- **test:** Test changes
- **chore:** Build/tooling changes

### Examples

```
feat: add user profile management

Implement user profile CRUD operations with validation
and proper error handling.

Closes #123
```

## Pull Request Guidelines

1. Keep PRs focused and small
2. Include tests for new features
3. Update documentation
4. Follow the PR template
5. Ensure all checks pass

## Deprecation

When deprecating functionality:

```python
import warnings

def old_function():
    """
    Deprecated: Use new_function() instead.

    .. deprecated:: 1.2.0
       Use :func:`new_function` instead.
    """
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

## Resources

- [PEP 8](https://pep8.org/) - Python Style Guide
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints](https://docs.python.org/3/library/typing.html)
- [Logging Best Practices](https://docs.python.org/3/howto/logging.html)