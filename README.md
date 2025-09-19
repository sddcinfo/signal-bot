# Signal Bot

A powerful, modular Python bot for Signal messenger with AI integration, automated responses, and comprehensive group management capabilities.

## Features

- 🤖 **AI-Powered Responses** - Integration with multiple AI providers (Ollama, OpenAI, Anthropic, Google Gemini)
- 📊 **Message Analytics** - Sentiment analysis and message summarization
- 👥 **Group Management** - Monitor and manage Signal groups with granular controls
- 🌐 **Web Dashboard** - Beautiful web interface for configuration and monitoring
- 📝 **Command System** - Extensible command framework for bot interactions
- 🔄 **Auto-Sync** - Automatic synchronization of users and groups
- 📈 **Real-time Statistics** - Track message flow, user activity, and system health
- 🎨 **Customizable** - User-specific emoji configurations and preferences
- 🔐 **UUID-based Architecture** - Reliable user identification using Signal UUIDs
- 🧩 **Modular Design** - Clean separation of concerns with reusable components
- 📎 **Attachment Support** - Handle images, files, and media attachments
- ⏰ **Timezone Support** - Proper timestamp handling across timezones
- 🔒 **Thread-Safe** - SQLite with proper locking for concurrent access
- 📊 **Activity Visualization** - Charts and graphs for message patterns
- 🚀 **Performance Optimized** - Caching, indexing, and batch operations

## Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Management Scripts](#management-scripts)
- [Development](#development)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Architecture

Signal Bot uses a modular architecture designed for scalability and maintainability:

```
signal-bot/
├── config/          # Centralized configuration
│   ├── settings.py  # Application settings
│   └── constants.py # Application constants
├── utils/           # Shared utilities
│   ├── common.py    # Helper functions
│   ├── logging.py   # Logging setup
│   ├── validators.py # Input validation
│   └── decorators.py # Reusable decorators
├── services/        # Business logic
│   ├── base.py      # Base service class
│   ├── messaging.py # Message handling
│   ├── setup.py     # Bot setup
│   └── ai_provider.py # AI integrations
├── models/          # Data layer
│   └── database.py  # Database management
├── web/            # Web interface
│   ├── server.py   # Web server
│   ├── pages/      # Page modules
│   └── shared/     # Shared components
└── docs/           # Documentation
```

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Installation

### Prerequisites

- Python 3.8+ (3.10+ recommended)
- signal-cli installed and configured
- SQLite3
- Virtual environment (recommended)

### Step 1: Install signal-cli

```bash
# Run the automated installer
./install_signal_cli.sh

# Or install manually
wget https://github.com/AsamK/signal-cli/releases/download/v0.13.4/signal-cli-0.13.4.tar.gz
tar xf signal-cli-0.13.4.tar.gz -C /opt/
ln -sf /opt/signal-cli-0.13.4/bin/signal-cli /usr/local/bin/
```

### Step 2: Set Up Python Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/signal-bot.git
cd signal-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Signal Account

```bash
# Register a new Signal account (if needed)
signal-cli -u +YOUR_PHONE_NUMBER register

# Verify with SMS code
signal-cli -u +YOUR_PHONE_NUMBER verify SMS_CODE

# Or link to existing account via web dashboard
# Navigate to http://localhost:8084/setup after starting the bot
```

## Quick Start

### Using the Management Script

```bash
# Start all services
./manage.sh start

# Check status
./manage.sh status

# View configuration
./manage.sh config

# Access web dashboard
open http://localhost:8084
```

### Manual Start

```bash
# Start Signal service
./run_signal_service.sh

# In another terminal, start web server
./run_web_server.sh

# Or restart everything
./restart.sh
```

## Configuration

### Environment Variables

Create a `.env` file to override default settings:

```env
# Core Settings
SIGNAL_CLI_PATH=/usr/local/bin/signal-cli
DATABASE_PATH=signal_bot.db
LOG_LEVEL=INFO

# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8084
WEB_DEBUG=False

# AI Providers
OLLAMA_HOST=http://localhost:11434/
OLLAMA_DEFAULT_MODEL=llama3.2:latest

# Optional AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GOOGLE_API_KEY=...

# Feature Flags
ENABLE_SENTIMENT_ANALYSIS=True
ENABLE_SUMMARIZATION=True
ENABLE_AUTO_RESPONSE=True
ENABLE_GROUP_MONITORING=True
```

### Configuration Files

All configuration is centralized in `config/settings.py`. You can:

1. Set environment variables (recommended for deployment)
2. Edit `config/settings.py` directly (for development)
3. Use the web dashboard for runtime configuration

For detailed configuration options, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Usage

### Web Dashboard

Access the dashboard at `http://localhost:8084`:

- **Dashboard**: Overview of bot status and activity
- **Users**: Manage users and emoji configurations
- **Groups**: Monitor and manage Signal groups
- **Messages**: View message history and analytics
- **Settings**: Configure bot behavior
- **Setup**: Initial bot setup and Signal account linking
- **AI Config**: Configure AI providers and models

### Signal Commands

Send commands to the bot via Signal:

- `/help` - Show available commands
- `/status` - Bot status
- `/stats [group]` - Group statistics
- `/summary [hours]` - Message summary
- `/sentiment [hours]` - Sentiment analysis
- `/monitor <group>` - Start monitoring a group
- `/unmonitor <group>` - Stop monitoring a group

### Management Scripts

```bash
# Main management script
./manage.sh {start|stop|restart|status|config|cleanup|logs|test|help}

# Individual scripts
./check_status.sh       # Detailed status check
./check_config.sh       # Configuration validation
./cleanup_backups.sh    # Clean old files (use --dry-run first)
./restart.sh           # Quick restart all services
```
# or
python3 signal_bot.py [options]

Options:
  --sync-groups    Sync group memberships from Signal on startup
  --sync-only      Only sync group memberships and exit (useful for cron)
  --debug          Enable debug logging for troubleshooting
  --force          Force start even if another instance is running
  --help           Show help message
```

## Setup Flow

1. **Device Linking**: Link your Signal device via QR code
2. **Group Discovery**: Automatically discover all Signal groups
3. **Group Monitoring**: Select which groups to monitor for messages
4. **User Configuration**: Set emoji reactions for specific users
5. **Start Polling**: Bot begins watching for messages and sending reactions

## Web Interface Pages

Access the web interface at http://YOUR_SERVER:8084 (or YOUR_SERVER:8085 for testing):

- **Overview** (`/`): Dashboard with bot status and statistics
- **Groups** (`/groups`): View all groups, enable/disable monitoring, see member counts
- **Users** (`/users`): Configure emoji reactions for users, manage discovered users
- **Messages** (`/messages`): Enhanced message history with smart filtering:
  - **Smart Group Filter**: Shows only monitored groups (not all groups)
  - **Dynamic Member Filter**: When group selected, shows only members of that group
  - **Single Date Filter**: Simplified date selection with compact layout
  - **Tabbed Interface**: All Messages, Attachments, Mentions, Reactions
  - **Enhanced Formatting**: Compact, one-line filter layout with minimal whitespace
- **Sentiment** (`/sentiment`): Privacy-aware AI sentiment analysis of group conversations
- **Summary** (`/summary`): Privacy-aware AI summaries of recent group conversations
- **Activity** (`/activity`): Visualize hourly message patterns with vertical bar charts
- **AI Config** (`/ai-config`): Configure local (Ollama) and external (Gemini) AI providers
- **Bot Status** (`/bot-status`): Real-time monitoring of bot services and system status

## How It Works

1. **Message Polling**: Bot polls Signal for new messages every 30 seconds
2. **Group Check**: Only processes messages from monitored groups
3. **User Check**: Checks if the sender has configured emoji reactions
4. **Reaction Sending**: Automatically sends the configured emoji as a reaction
5. **Message Storage**: Stores message history for viewing in web interface

## Configuration

### Monitoring Groups
1. Go to the Groups page
2. Click "Monitor" on groups you want to watch
3. Only messages from monitored groups will trigger reactions

### Configuring User Reactions
1. Go to the Users page
2. Find the user you want to configure
3. Click "Configure" and select emojis
4. Choose reaction mode (random, sequential, AI)
5. Save the configuration

### Enhanced Message Filtering
The Messages page features a completely redesigned filtering system:

**Smart Group Filtering:**
- Shows only monitored groups in the dropdown (not all groups)
- Reduces clutter by focusing on relevant groups only

**Dynamic Member Filtering:**
- When a group is selected, member dropdown shows only that group's members
- Automatically updates based on group selection for precise targeting

**Simplified Date Selection:**
- Single date field instead of confusing start/end date ranges
- Compact, one-line layout with minimal whitespace
- All filters displayed cleanly on a single row

**Tabbed Message Views:**
- All Messages: Complete message history
- Attachments: Messages with files, images, or stickers
- Mentions: Messages containing @mentions
- Reactions: Messages with emoji reactions

**Enhanced Display:**
- Attachments displayed inline with thumbnails for images
- Full pagination support with maintained filter states
- Clean, compact formatting for better usability

### AI Configuration
1. Go to the AI Config page
2. Configure Ollama (local AI) settings:
   - Host/IP address (e.g., 192.168.10.160:11434)
   - Model selection from available models
   - Enable/disable local AI
   - Model preloading for faster responses
3. Configure Gemini (external AI) settings:
   - CLI path and enable/disable options
4. AI providers automatically fallback from local to external
5. **Enhanced Provider Status**: View real-time information including:
   - Loaded models with memory usage (VRAM)
   - Model specifications (parameters, quantization, context length)
   - Available models and total storage usage
   - Current model status and expiration times

### Sentiment Analysis
1. Go to the Sentiment page
2. Select a monitored group
3. Select a date to analyze (defaults to today)
4. Click "Analyze Sentiment" or "Force Refresh"
5. View AI-powered analysis with privacy protection:
   - 🏠 **Local AI**: Shows real usernames and full conversation details
   - 🌐 **External AI**: Anonymized analysis without user identifiers
6. Results include emotion patterns, mood progression, and conversation themes
7. Cached for efficiency with timezone-aware processing

### Message Summarization
1. Go to the Summary page
2. Select a monitored group
3. Choose how many hours to look back (default: 24)
4. Click "Generate Summary" for privacy-aware AI analysis:
   - 🏠 **Local AI**: Detailed summaries with participant information
   - 🌐 **External AI**: Anonymous summaries without user identifiers
5. View key topics, decisions, action items, and overall conversation tone
6. Markdown formatting with proper table rendering
7. Timestamps displayed in your browser's timezone for consistency

### Activity Visualization
1. Go to the Activity page
2. Select a date to analyze
3. View hourly message distribution as bar charts
4. Each monitored group gets its own color-coded chart
5. Timezone-aware hour calculations based on browser location

## Architecture

### Separated Services Architecture (Recommended)

**Signal CLI Service** (`signal_service.py`):
- Standalone Signal CLI polling and message processing
- Runs independently and continuously
- Handles message storage, reactions, and attachment downloads
- Can remain running while web server is restarted

**Web Server** (`web_server.py`):
- Standalone web interface for configuration and monitoring
- Can be restarted independently for updates and testing
- Automatic port conflict resolution (kills existing processes)
- Network accessible (binds to 0.0.0.0) for remote access

**Shared Components:**
- **Database** (`models/database.py`): UUID-based SQLite operations with sentiment caching
- **Messaging Service** (`services/messaging.py`): Message polling and reaction sending with cleaner debug logging
- **Setup Service** (`services/setup.py`): Device linking and configuration
- **AI Provider** (`services/ai_provider.py`): Unified interface for local (Ollama) and external (Gemini) AI
- **Sentiment Service** (`services/sentiment.py`): Privacy-aware sentiment analysis with AI provider abstraction
- **Summarization Service** (`services/summarization.py`): Privacy-aware message summarization
- **Modular Web Interface** (`web/`): Separated pages with shared templates and enhanced filtering

**Utilities:**
- **Status Checker** (`check_status.sh`): Monitor running services, ports, and system status
- **QR Generator** (`utils/qrcode_generator.py`): ASCII QR code generation
- **Port Management**: Simplified system using only 8084 (production) and 8085 (testing)

### Legacy All-in-One Architecture

**Main Bot** (`signal_bot.py`): Combined orchestrator with threading, message polling, and web server

## Database Schema

The bot uses a UUID-centric design:
- **users**: UUID as primary key, stores phone numbers, display names, and friendly names
- **groups**: Tracks all Signal groups with monitoring status and member counts
- **group_members**: Maps users to their group memberships
- **user_reactions**: Stores emoji configurations for each user
- **processed_messages**: Tracks all messages to avoid duplicates
- **messages**: Stores full message history with text content
- **attachments**: Stores message attachments with file data as BLOBs
- **sentiment_analysis**: Caches AI-powered sentiment analysis results
- **config**: Stores AI provider configuration (Ollama host, models, Gemini path)

## Requirements

- Python 3.8+
- signal-cli (installed via `./install_signal_cli.sh`)
- SQLite3 (included with Python)
- Web browser for management interface

### AI Features (Optional)
- **Local AI**: Ollama server for private, local analysis
- **External AI**: Gemini CLI for cloud-based analysis
- **Python Dependencies**: Automatically installed via `./run_bot.sh`:
  - `requests` for Ollama API communication
  - `markdown` for HTML rendering with table support
  - `google-generativeai` for Gemini integration
  - `qrcode[pil]` for QR code generation

## Troubleshooting

### Service Status and Monitoring

**Check what's running:**
```bash
./check_status.sh
```
This shows running processes, ports in use, Signal CLI status, database info, and log file sizes.

**Service-specific issues:**
- **Signal CLI Service**: Check `signal_service.log` for polling errors
- **Web Server**: Check web server output for binding or startup issues
- **Port conflicts**: Use `./check_status.sh` to see what's using which ports

### Bot not receiving messages
- Ensure signal-cli is properly linked: Check Setup page
- Verify groups are monitored: Check Groups page
- Check Signal CLI service is running: `./check_status.sh`
- Check logs: `tail -f signal_service.log` (for separated services) or `tail -f signal_bot.log` (for all-in-one)
- Enable debug logging: `./run_signal_service.sh --debug`

### Reactions not being sent
- Verify user has reactions configured: Check Users page
- Ensure user is sending messages in monitored groups
- Check that reactions are enabled for the user
- Verify Signal CLI service is processing messages

### Web interface not accessible
- Check web server is running: `./check_status.sh`
- Verify correct port (8084 for production, 8085 for testing)
- Ensure web server binds to 0.0.0.0 for network access
- Try restarting: `./run_web_server.sh` (automatically kills conflicting processes)

### Enhanced Message Filtering issues
- If groups don't appear: Ensure they are monitored (Groups page)
- If members don't update: Select a group first, then member filter will populate
- If filters reset: This is expected behavior for simplified single-date filtering

### Attachments not displaying
- Check that attachment was properly downloaded from signal-cli
- Verify attachment exists in database: check logs for storage confirmation
- Ensure web server can serve the attachment endpoint

### Group memberships not showing
- Use separated services: `./run_signal_service.sh --sync-groups`
- Or legacy all-in-one: `python3 signal_bot.py --sync-only`

### AI model loading issues
- **"llm server loading model" errors**: Bot automatically retries with intelligent loading detection
- **Model not loading**: Use "Preload Model" button in AI Config page for large models
- **Slow responses**: Check AI Config page for model status and VRAM usage
- **Model memory issues**: View loaded models and memory usage in Provider Status section

### Debug logging
- Debug messages now only appear when explicitly enabled with `--debug`
- Cleaner logs by default with `INFO` level logging
- Use debug mode only when troubleshooting specific issues

### Port management issues
- Only two ports are used: 8084 (production) and 8085 (testing)
- Automatic conflict resolution kills existing processes on the target port
- Check current port usage: `./check_status.sh`

## Development

### Project Structure

The Signal Bot uses a modular architecture for maintainability and scalability. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed information.

### Key Components

- **Configuration** (`config/`): Centralized settings and constants
- **Utilities** (`utils/`): Shared helper functions and decorators
- **Services** (`services/`): Business logic with BaseService pattern
- **Models** (`models/`): Database abstraction layer
- **Web** (`web/`): Modular web interface with shared components

### Development Guidelines

- Follow the coding standards in [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md)
- See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines
- Use the management scripts for testing and validation:
  - `./manage.sh test` - Test module loading
  - `./manage.sh config` - Validate configuration
  - `./check_status.sh` - Check service status

### Testing

```bash
# Test module loading and configuration
./manage.sh test

# Run with debug logging
./run_signal_service.sh --debug

# Test web server on alternate port
./run_web_server.sh --testing
```

## Contributing

We welcome contributions! Please see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT