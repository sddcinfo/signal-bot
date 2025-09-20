# Contributing to Signal Bot

## Welcome!

Thank you for considering contributing to Signal Bot! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive criticism
- Help others learn and grow
- Maintain professionalism

## Development Setup

### Prerequisites

- Python 3.8+
- signal-cli installed
- SQLite3
- Virtual environment

### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/signal-bot.git
cd signal-bot
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python3 -c "from models.database import DatabaseManager; db = DatabaseManager(); print('Database initialized')"
```

## Architecture Overview

### Core Modules

- **config/**: Centralized configuration and constants
- **utils/**: Shared utilities and helpers
- **services/**: Business logic and service classes
- **models/**: Data models and database management
- **web/**: Web interface and API

### Service Architecture

All services inherit from `BaseService` which provides:
- Standardized initialization
- Consistent logging
- Database connection management
- Error handling patterns

## How to Contribute

### 1. Find an Issue

- Check existing issues or create a new one
- Comment on the issue to claim it
- Wait for maintainer approval

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Changes

Follow the [Style Guide](STYLE_GUIDE.md) and ensure:
- Code is properly formatted
- All tests pass
- Documentation is updated
- No hardcoded values

### 4. Test Your Changes

```bash
# Run unit tests
python -m pytest tests/unit

# Run integration tests
python -m pytest tests/integration

# Test specific module
python -m pytest tests/unit/test_utils.py
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Adding New Features

### 1. Create a New Service

When adding a new service, inherit from `BaseService`:

```python
# services/my_service.py
from services.base import BaseService
from utils.decorators import handle_errors

class MyService(BaseService):
    """
    My new service description.

    This service handles...
    """

    def initialize(self):
        """Initialize service-specific components."""
        self.my_setting = self.config.get('MY_SETTING', 'default')
        self.logger.info("MyService initialized")

    @handle_errors(default_return=None)
    def process_data(self, data: str) -> Optional[str]:
        """
        Process some data.

        Args:
            data: Input data to process

        Returns:
            Processed data or None on error
        """
        # Implementation here
        return processed_data
```

### 2. Add Configuration

Add new settings to `config/settings.py`:

```python
class Config:
    # ... existing config ...

    # My Service Configuration
    MY_SERVICE_ENABLED: bool = os.getenv('MY_SERVICE_ENABLED', 'True').lower() == 'true'
    MY_SERVICE_TIMEOUT: int = int(os.getenv('MY_SERVICE_TIMEOUT', '30'))
```

### 3. Create Utilities

Add reusable functions to appropriate utils modules:

```python
# utils/my_utils.py
def my_helper_function(param: str) -> str:
    """
    Helper function description.

    Args:
        param: Parameter description

    Returns:
        Return value description
    """
    # Implementation
    return result
```

### 4. Add Web Page (if needed)

Create a new page module:

```python
# web/pages/my_page.py
from web.shared.base_page import BasePage

class MyPage(BasePage):
    """My page description."""

    def get_html(self) -> str:
        """Generate HTML for my page."""
        return self.render_template(
            title="My Page",
            content=self._generate_content()
        )

    def _generate_content(self) -> str:
        """Generate page content."""
        # Implementation
        return content
```

### 5. Update Documentation

- Add docstrings to all new code
- Update README if adding major features
- Add examples to relevant documentation

## Working with Databases

### Adding New Tables

1. Update `models/database.py` schema:

```python
def _create_tables(self):
    # ... existing tables ...

    # Create my_table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS my_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
```

2. Add accessor methods:

```python
def get_my_data(self, data_id: int) -> Optional[Dict]:
    """Get data by ID."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM my_table WHERE id = ?", (data_id,))
        return cursor.fetchone()
```

## Testing Guidelines

### Unit Tests

Test individual functions and methods:

```python
# tests/unit/test_my_service.py
import unittest
from unittest.mock import Mock, patch
from services.my_service import MyService

class TestMyService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = MyService(db=self.mock_db)

    def test_process_data(self):
        """Test data processing."""
        result = self.service.process_data("test")
        self.assertEqual(result, "expected")
```

### Integration Tests

Test component interaction:

```python
# tests/integration/test_my_integration.py
def test_full_workflow():
    """Test complete workflow."""
    # Setup
    service = MyService()

    # Execute
    result = service.full_workflow()

    # Verify
    assert result.success
```

## Common Patterns

### Using Decorators

```python
from utils.decorators import handle_errors, with_retry, log_execution_time

@log_execution_time()
@handle_errors(default_return=None)
@with_retry(max_attempts=3)
def unreliable_operation():
    """Operation that might fail."""
    pass
```

### Async Operations

```python
import asyncio
from utils.decorators import async_to_sync

async def async_operation():
    """Async operation."""
    await asyncio.sleep(1)
    return "result"

# Make it sync if needed
sync_operation = async_to_sync(async_operation)
```

### Context Managers

```python
class MyResource:
    def __enter__(self):
        """Acquire resource."""
        self.resource = acquire_resource()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release resource."""
        release_resource(self.resource)
```

## Performance Considerations

### Database Queries

- Use indexes for frequently queried columns
- Batch operations when possible
- Use prepared statements
- Implement connection pooling for high load

### Caching

```python
from utils.decorators import cache_result

@cache_result(ttl=300)  # Cache for 5 minutes
def expensive_operation(param):
    """Expensive operation that should be cached."""
    return result
```

### Memory Management

- Use generators for large datasets
- Clear caches periodically
- Profile memory usage with `memory_profiler`

## Debugging Tips

### Enable Debug Logging

```python
# Set in .env or environment
LOG_LEVEL=DEBUG
```

### Use the Logger

```python
logger.debug(f"Variable state: {variable}")
logger.info(f"Operation completed: {result}")
logger.error(f"Operation failed: {error}", exc_info=True)
```

### Interactive Debugging

```python
import pdb

def problematic_function():
    # ... some code ...
    pdb.set_trace()  # Debugger will stop here
    # ... more code ...
```

## Release Process

1. Update version in `__version__`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release branch
5. Tag release
6. Deploy

## Getting Help

- Check existing documentation
- Search closed issues
- Ask in discussions
- Create an issue with:
  - Clear description
  - Steps to reproduce
  - Expected vs actual behavior
  - System information

## Code Review Checklist

Before submitting PR, ensure:

- [ ] Code follows style guide
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] No sensitive data in code
- [ ] Proper error handling
- [ ] Logging added where appropriate
- [ ] Type hints included
- [ ] Docstrings complete
- [ ] PR description clear

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.