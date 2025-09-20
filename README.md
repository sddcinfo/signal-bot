# Signal Bot

A powerful, modular Signal messenger bot with web-based management interface, AI integration, and automated message handling capabilities.

## Features

### Core Functionality
- **Web Dashboard**: Real-time statistics and system monitoring
- **Message Management**: View, filter, and search messages across all groups
- **Group Management**: Monitor and manage Signal groups and memberships
- **User Management**: Track and manage Signal contacts with custom names
- **Setup Wizard**: Easy device linking and initial configuration

### AI Integration
- **Multiple Providers**: Support for Ollama, OpenAI, Anthropic Claude, Google Gemini, and Groq
- **Custom Analysis Types**: Create custom AI analysis workflows
- **Message Summarization**: Automatic conversation summaries
- **Sentiment Analysis**: Track conversation mood and tone
- **Topic Extraction**: Identify key discussion topics

### Automation
- **Auto-Replies**: Configurable automatic responses
- **Reaction Handling**: Automatic emoji reactions based on keywords
- **Message Filtering**: Advanced filtering by date, sender, group, and content
- **Daemon Mode**: Real-time message processing with JSON-RPC

## Architecture

The Signal Bot uses a modular architecture with three main components:

1. **Message Processing Service**
   - `signal_service.py`: Polling-based message processor
   - `signal_daemon_service.py`: Daemon-based real-time processor
   - Handles reactions and auto-replies

2. **Web Server** (`web_server.py`)
   - Web-based management interface
   - REST API for frontend operations
   - Real-time statistics and monitoring

3. **Management System** (`manage.py` / `manage.sh`)
   - Service lifecycle management
   - System configuration
   - Debug and monitoring tools

### Project Structure

```
signal-bot/
├── config/           # Configuration modules
├── models/          # Database models
├── services/        # Business logic
├── utils/           # Utility functions
├── web/             # Web interface
│   ├── pages/       # Page components
│   └── shared/      # Shared templates
├── docs/            # Documentation
├── manage.py        # Management script
├── manage.sh        # Shell wrapper with DEBUG
└── requirements.txt # Dependencies
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

3. **Port 8084 in use**
   ```bash
   # Change port in config/settings.py
   # Or use environment variable:
   WEB_PORT=8085 ./manage.sh start
   ```

4. **Permission errors**
   ```bash
   chmod +x manage.sh
   chmod +x *.sh
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

## Security

- Never commit `.env` files or credentials
- Use environment variables for sensitive data
- Regularly update Signal CLI and dependencies
- Review group permissions and monitoring settings
- Use HTTPS for production deployments

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