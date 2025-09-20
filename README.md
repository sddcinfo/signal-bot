# Signal Bot

A powerful, modular Signal messenger bot with web-based management interface, AI integration, and automated message handling capabilities.

**Last Comprehensive Review:** September 20, 2025
**Version:** 1.0.0
**Status:** Production-ready with recent improvements

## Features

### Core Functionality
- **Web Dashboard**: Real-time statistics and system monitoring with live updates
- **Message Management**: View, filter, and search messages across all groups with pagination
- **Group Management**: Monitor and manage Signal groups and memberships with UUID-based tracking
- **User Management**: Track and manage Signal contacts with custom display names and emoji support
- **Setup Wizard**: Easy device linking and initial configuration via QR code or phone number

### AI Integration
- **Multiple Providers**: Full support for Ollama (local), OpenAI, Anthropic Claude, Google Gemini, and Groq
- **Custom Analysis Types**: Create and manage custom AI analysis workflows via web UI or CLI
- **Message Summarization**: Automatic conversation summaries with key points extraction
- **Sentiment Analysis**: Real-time conversation mood and tone tracking with scoring
- **Topic Extraction**: Intelligent identification of discussion topics and action items
- **Daily Highlights**: Automatic extraction of important moments and decisions

### Automation
- **Auto-Replies**: Configurable automatic responses with per-group settings
- **Reaction Handling**: Automatic emoji reactions based on keywords and sentiment
- **Message Filtering**: Advanced filtering by date, sender, group, content, and AI analysis results
- **Daemon Mode**: Real-time message processing with JSON-RPC socket communication
- **Instance Management**: Automatic lock management to prevent duplicate processes

## Architecture

The Signal Bot uses a modular architecture with centralized logging and configuration:

### Core Components

1. **Message Processing Services**
   - `signal_service.py`: Polling-based message processor with configurable intervals
   - `signal_daemon_service.py`: Daemon-based real-time processor using JSON-RPC
   - Both services use centralized logging (`utils.logging`) for consistency
   - Automatic reaction handling and auto-reply support
   - Group synchronization and member management

2. **Web Server** (`web_server.py`)
   - Modular web interface with page-based architecture
   - REST API endpoints for all operations
   - Real-time statistics and monitoring dashboard
   - Threaded request handling for concurrent operations
   - Centralized template system with Jinja2-like syntax

3. **Management System** (`manage.py` / `manage.sh`)
   - Comprehensive service lifecycle management
   - Debug mode with extensive logging capabilities
   - Process monitoring and health checks
   - Automatic restart and recovery mechanisms
   - Environment variable management

### Supporting Modules

4. **Database Layer** (`models/`)
   - SQLite-based storage with proper connection pooling
   - UUID-based user identification
   - Message history with attachment support
   - AI analysis results storage
   - Configuration and settings persistence

5. **Service Layer** (`services/`)
   - AI provider abstraction for multiple LLM backends
   - Message processing pipeline
   - Setup and configuration services
   - Daemon communication handlers
   - Base service class for consistency

6. **Utilities** (`utils/`)
   - Centralized logging system with context support
   - Bot instance management (singleton pattern)
   - Decorators for common patterns
   - Input validators and sanitizers
   - QR code generation for device linking

7. **Configuration** (`config/`)
   - Environment-based settings management
   - Comprehensive constants definition
   - Timeouts, limits, and defaults centralization

### Project Structure

```
signal-bot/
├── config/              # Configuration and constants
│   ├── __init__.py     # Package initialization
│   ├── constants.py    # Application-wide constants
│   └── settings.py     # Environment-based configuration
├── models/             # Database models and operations
│   ├── database.py     # Main database manager
│   └── user_display_utils.py  # User display helpers
├── services/           # Core business logic
│   ├── ai_analysis.py  # Unified AI analysis service
│   ├── ai_provider.py  # Multi-provider AI abstraction
│   ├── base.py         # Base service class
│   ├── daemon_processor.py    # Daemon message processor
│   ├── messaging.py    # Polling message handler
│   ├── messaging_daemon.py    # Daemon message handler
│   ├── reaction_sender.py     # Reaction handling
│   ├── setup.py        # Bot setup and configuration
│   └── signal_daemon.py # Signal CLI daemon wrapper
├── utils/              # Utility modules
│   ├── bot_instance.py # Instance lock management
│   ├── common.py       # Common utilities
│   ├── decorators.py   # Function decorators
│   ├── logging.py      # Centralized logging setup
│   ├── qrcode_generator.py    # QR code generation
│   └── validators.py   # Input validation
├── web/                # Web interface
│   ├── pages/          # Individual page modules
│   │   ├── ai_analysis.py     # AI analysis interface
│   │   ├── ai_config.py       # AI provider configuration
│   │   ├── dashboard.py       # Main dashboard
│   │   ├── groups.py   # Group management
│   │   ├── messages.py # Message viewer
│   │   ├── settings.py # System settings
│   │   ├── setup.py    # Setup wizard
│   │   └── users.py    # User management
│   ├── shared/         # Shared web components
│   │   ├── base_page.py        # Base page class
│   │   ├── filters.py  # Template filters
│   │   └── templates.py # HTML templates
│   └── server.py       # Main web server
├── docs/               # Documentation
├── signal_service.py   # Polling service entry point
├── signal_daemon_service.py   # Daemon service entry point
├── web_server.py       # Web server entry point
├── manage.py           # Management script
├── manage.sh           # Shell wrapper with DEBUG support
├── manage_ai_types.py  # AI types management CLI
└── requirements.txt    # Python dependencies
```

## Installation

### Prerequisites

- Python 3.8+ (3.10+ recommended)
- Signal CLI v0.13.4+
- SQLite3
- Linux/macOS/WSL

### Quick Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/signal-bot.git
cd signal-bot
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install Signal CLI**:
```bash
./manage.sh install-signal-cli
# Or use the standalone installer:
# ./install_signal_cli.sh
```

5. **Start the bot**:
```bash
./manage.sh start
```

6. **Open web interface**:
```
http://localhost:8084
```

## Usage

### Service Management

```bash
# Start all services
./manage.sh start

# Start specific service
./manage.sh start web      # Just web interface
./manage.sh start signal    # Just message processor

# Use daemon mode (recommended for production)
./manage.sh start signal --daemon

# Stop all services
./manage.sh stop

# Restart services
./manage.sh restart

# Check status
./manage.sh status

# View configuration
./manage.sh config
```

### Debug Mode

Enable comprehensive debug logging:

```bash
# Start with debug logging
./manage.sh DEBUG start

# View debug logs in real-time
./manage.sh debug-tail

# Check debug status
./manage.sh debug-status

# Clean debug logs
./manage.sh debug-clean
```

### Web Interface

Access the web dashboard at `http://localhost:8084`:

- **Dashboard**: System overview and statistics
- **Messages**: Browse and filter messages
- **Groups**: Manage group settings
- **Users**: View and edit contacts
- **AI Config**: Configure AI providers
- **AI Analysis**: Run analysis on conversations
- **Settings**: System configuration
- **Setup**: Initial bot setup wizard

## Configuration

### Environment Variables

Create a `.env` file for sensitive configuration:

```bash
# Signal account
SIGNAL_PHONE=+1234567890

# Web server
WEB_HOST=0.0.0.0
WEB_PORT=8084

# AI Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...

# Ollama (local AI)
OLLAMA_HOST=http://localhost:11434
```

### Configuration Files

- `config/settings.py`: Main configuration
- `config/constants.py`: System constants

### Database

SQLite database is automatically created at `signal_bot.db` with schema:
- Users (UUID-based)
- Groups
- Messages
- Attachments
- Reactions
- AI Analysis Types
- System Settings

## AI Integration

### Supported Providers

1. **Ollama** (Local, recommended)
   - Install: `curl -fsSL https://ollama.ai/install.sh | sh`
   - Models: llama3, mistral, gemma, etc.

2. **OpenAI**
   - GPT-4, GPT-3.5-turbo
   - Requires API key

3. **Anthropic Claude**
   - Claude 3 Opus, Sonnet, Haiku
   - Requires API key

4. **Google Gemini**
   - Gemini Pro, Gemini Pro Vision
   - Requires API key

5. **Groq**
   - Fast inference for open models
   - Requires API key

### AI Analysis Management

The bot includes a comprehensive AI Analysis Types management system accessible through multiple interfaces:

#### Web Interface Management
1. Navigate to AI Config page
2. View, add, edit, or delete analysis types
3. Configure prompts and parameters
4. Test analysis types directly from the interface

#### Command-Line Management
Use the `manage_ai_types.py` script for managing AI analysis types:

```bash
# List all analysis types
python manage_ai_types.py list

# Add a new analysis type
python manage_ai_types.py add --name "custom_type" --display-name "Custom Analysis"

# Edit an existing type
python manage_ai_types.py edit --id 1 --description "Updated description"

# Delete an analysis type
python manage_ai_types.py delete --id 5

# View detailed information
python manage_ai_types.py show --id 1
```

#### Built-in Analysis Types

The system includes four pre-configured analysis types:

1. **Message Summary** (`summary`)
   - Comprehensive summary of conversation topics and key points
   - Extracts key topics, action items, and notable moments
   - Ideal for daily/weekly digests

2. **Sentiment Analysis** (`sentiment`)
   - Analyzes emotional tone and mood of conversations
   - Provides sentiment scores and emotional themes
   - Tracks participant dynamics and trends

3. **Topic Extraction** (`topics`)
   - Extracts and categorizes main discussion topics
   - Shows topic flow and transitions
   - Identifies actionable items and unresolved discussions

4. **Daily Highlights** (`highlights`)
   - Extracts the most important or interesting moments
   - Captures key announcements, decisions, and achievements
   - Perfect for creating bulletin-style daily digests

#### Creating Custom Analysis Types

Custom analysis types can include:
- Custom prompt templates with placeholders
- Group and sender filtering requirements
- Time range configurations
- Privacy settings for anonymization
- Display customization (icons, colors, sort order)

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest tests/test_database.py

# With coverage
python -m pytest --cov=.
```

### Code Style

Follow PEP 8 guidelines. Use the provided style checking:

```bash
# Check code style
flake8 .

# Format code
black .
```

### API Documentation

REST API endpoints are documented at:
- [docs/API.md](docs/API.md)

### Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## Technical Details

### Logging System

The application uses a centralized logging system (`utils.logging`) that provides:
- Consistent log formatting across all modules
- Contextual logging with user/group/message IDs
- Automatic third-party library log suppression
- Debug mode override capability
- File and console output handlers
- Log rotation support (when configured)

**Log Levels:**
- **DEBUG**: Detailed diagnostic information (enabled with `--debug` flag)
- **INFO**: General operational messages (default level)
- **WARNING**: Warning conditions that should be reviewed
- **ERROR**: Error conditions that need attention
- **CRITICAL**: Critical failures requiring immediate action

### Database Schema

Key tables and their purposes:
- `users`: UUID-based user records with display names
- `groups`: Group information and settings
- `messages`: Complete message history with metadata
- `attachments`: File attachments linked to messages
- `reactions`: Emoji reactions to messages
- `ai_analysis_types`: Configurable AI analysis definitions
- `ai_analysis_results`: Stored analysis results
- `config`: Key-value configuration storage
- `instance_status`: Bot instance lock management

### Constants and Configuration

All hard-coded values are centralized in `config/constants.py`:
- **TIMEOUTS**: Signal CLI, database, web, and AI request timeouts
- **NETWORK**: Default ports, hosts, and socket paths
- **LOGGING**: Log levels, formats, and rotation settings
- **PROCESS**: PID files, lock files, restart settings
- **PATHS**: Log files, database, and directory paths
- **LIMITS**: Message length, file sizes, and rate limits
- **DEFAULTS**: Default emojis, names, and values

## Recent Improvements (September 2025)

### Code Quality Enhancements
1. **Logging Standardization**: Migrated all services to use centralized `utils.logging` module
2. **Constants Extraction**: Moved all hard-coded values to `config/constants.py`
3. **Documentation**: Added comprehensive docstrings to key modules
4. **Error Handling**: Improved exception handling and error reporting

### Architecture Improvements
1. **Centralized Configuration**: All configuration now flows through `config/` modules
2. **Instance Management**: Robust singleton pattern for preventing duplicate processes
3. **Resource Management**: Proper cleanup of database connections and file handles
4. **Debug Mode**: Enhanced debug logging with structured context information

### Known Areas for Future Enhancement
1. **Complex Function Refactoring**: Some functions like `process_message()` could be broken down
2. **Test Coverage**: Need to add comprehensive unit and integration tests
3. **API Documentation**: REST API endpoints need OpenAPI/Swagger documentation
4. **Performance Monitoring**: Add metrics collection and monitoring capabilities

## Troubleshooting

### Common Issues

1. **Signal CLI not found**
   ```bash
   ./manage.sh install-signal-cli
   export PATH=$PATH:/usr/local/bin
   ```

2. **Database locked errors**
   ```bash
   ./manage.sh stop
   rm signal_bot.lock
   ./manage.sh start
   ```

3. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :8084
   # Change port in environment
   WEB_PORT=8085 ./manage.sh start
   ```

4. **Permission errors**
   ```bash
   chmod +x manage.sh
   chmod +x *.py
   chmod +x *.sh
   ```

5. **Logging issues**
   ```bash
   # Enable debug mode for detailed logs
   ./manage.sh DEBUG start
   # Check debug log
   tail -f signal_bot_debug.log
   ```

6. **AI Provider failures**
   ```bash
   # Verify API keys are set
   env | grep API_KEY
   # Test Ollama connection
   curl http://localhost:11434/api/tags
   ```

### Logs

Check logs for detailed error information:

```bash
# View recent logs
tail -f signal_service.log
tail -f web_server.log

# Debug mode for verbose logging
./manage.sh DEBUG start
```

## Security Considerations

### Best Practices
- Never commit `.env` files or credentials to version control
- Use environment variables for all sensitive configuration
- Regularly update Signal CLI and Python dependencies
- Review group permissions and monitoring settings periodically
- Use HTTPS with proper certificates for production deployments
- Enable debug logging only when necessary (sensitive data may be logged)

### Data Protection
- User UUIDs are used instead of phone numbers where possible
- Database file permissions should be restricted (chmod 600)
- Log files may contain sensitive information - secure appropriately
- AI API keys are never logged or displayed in the UI
- Message content can be anonymized for AI analysis when configured

### Process Security
- Instance lock prevents multiple bot processes
- Signal CLI runs with minimal required permissions
- Web server binds to configurable interfaces (default: all interfaces)
- Database connections use proper transaction isolation
- File uploads are restricted by size and type

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [API Reference](docs/API.md) - REST API documentation
- [Configuration](docs/CONFIGURATION.md) - Detailed configuration options
- [Installation](docs/INSTALLATION.md) - Step-by-step setup
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Contributing](docs/CONTRIBUTING.md) - Development guidelines

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Search [existing issues](https://github.com/yourusername/signal-bot/issues)
- Open a [new issue](https://github.com/yourusername/signal-bot/issues/new)

## Acknowledgments

Built with:
- [Signal CLI](https://github.com/AsamK/signal-cli) - Signal messenger CLI
- [Python](https://python.org) - Programming language
- [SQLite](https://sqlite.org) - Database engine
- [Ollama](https://ollama.ai) - Local AI models

## Authors

- Your Name - Initial work

See also the list of [contributors](https://github.com/yourusername/signal-bot/contributors).