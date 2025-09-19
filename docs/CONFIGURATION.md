# Signal Bot Configuration Guide

## Overview

Signal Bot uses a centralized configuration system that supports multiple configuration methods for flexibility. Configuration is managed through the `config/settings.py` module.

## Configuration Methods

### 1. Environment Variables (Recommended for Production)

Set environment variables before starting the bot:

```bash
export SIGNAL_CLI_PATH=/usr/local/bin/signal-cli
export DATABASE_PATH=signal_bot.db
export LOG_LEVEL=INFO
export WEB_HOST=0.0.0.0
export WEB_PORT=8084
```

### 2. .env File (Recommended for Development)

Create a `.env` file in the project root:

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

### 3. Direct Configuration (Development Only)

Edit `config/settings.py` directly for permanent changes.

### 4. Web Dashboard (Runtime Configuration)

Access the web interface at `http://localhost:8084` to configure:
- AI provider settings
- User emoji reactions
- Group monitoring
- Feature toggles

## Configuration Options

### Core Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `SIGNAL_CLI_PATH` | `/usr/local/bin/signal-cli` | Path to signal-cli binary |
| `DATABASE_PATH` | `signal_bot.db` | SQLite database file path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | See settings.py | Log message format string |

### Web Server Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `WEB_HOST` | `0.0.0.0` | Web server host (0.0.0.0 for network access) |
| `WEB_PORT` | `8084` | Production web server port |
| `WEB_PORT_TESTING` | `8085` | Testing web server port |
| `WEB_DEBUG` | `False` | Enable Flask debug mode |

### AI Provider Settings

#### Ollama (Local AI)

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434/` | Ollama server URL |
| `OLLAMA_DEFAULT_MODEL` | `llama3.2:latest` | Default model for local AI |
| `OLLAMA_TIMEOUT` | `300` | Request timeout in seconds |

#### OpenAI

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | `None` | OpenAI API key |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o-mini` | Default OpenAI model |

#### Anthropic Claude

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | `None` | Anthropic API key |
| `CLAUDE_DEFAULT_MODEL` | `claude-3-haiku-20240307` | Default Claude model |

#### Google Gemini

| Setting | Default | Description |
|---------|---------|-------------|
| `GOOGLE_API_KEY` | `None` | Google API key |
| `GEMINI_DEFAULT_MODEL` | `gemini-1.5-flash` | Default Gemini model |
| `GEMINI_CLI_PATH` | `gemini` | Path to Gemini CLI |

### Feature Flags

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_SENTIMENT_ANALYSIS` | `True` | Enable AI sentiment analysis |
| `ENABLE_SUMMARIZATION` | `True` | Enable message summarization |
| `ENABLE_AUTO_RESPONSE` | `True` | Enable automatic responses |
| `ENABLE_GROUP_MONITORING` | `True` | Enable group monitoring |
| `ENABLE_MESSAGE_STORAGE` | `True` | Store message history |
| `ENABLE_ATTACHMENT_STORAGE` | `True` | Store message attachments |

### Performance Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MESSAGE_POLLING_INTERVAL` | `30` | Seconds between message polls |
| `MESSAGE_RETENTION_DAYS` | `30` | Days to keep message history |
| `MAX_ATTACHMENT_SIZE` | `50 * 1024 * 1024` | Max attachment size (50MB) |
| `BATCH_SIZE` | `100` | Database batch operation size |
| `CACHE_TTL` | `900` | Cache time-to-live in seconds |

## Configuration Validation

### Check Current Configuration

```bash
# View active configuration
./manage.sh config

# Or use the check script directly
./check_config.sh
```

### Test Configuration

```bash
# Test module loading with current config
./manage.sh test

# Run with debug logging to verify settings
./run_signal_service.sh --debug
```

## Configuration Best Practices

### 1. Security

- Never commit API keys to version control
- Use environment variables for sensitive data
- Keep `.env` file in `.gitignore`
- Use strong, unique API keys

### 2. Performance

- Adjust `MESSAGE_POLLING_INTERVAL` based on usage
- Set appropriate `MESSAGE_RETENTION_DAYS`
- Configure `MAX_ATTACHMENT_SIZE` based on needs
- Use local AI (Ollama) for privacy-sensitive data

### 3. Network

- Use `0.0.0.0` for `WEB_HOST` to allow network access
- Configure firewall rules for production
- Use reverse proxy (nginx) for SSL in production

### 4. Logging

- Use `INFO` level for production
- Use `DEBUG` only for troubleshooting
- Rotate logs regularly with `cleanup_backups.sh`
- Monitor log file sizes

## Environment-Specific Configurations

### Development

```env
LOG_LEVEL=DEBUG
WEB_DEBUG=True
WEB_PORT=8085
OLLAMA_HOST=http://localhost:11434/
```

### Production

```env
LOG_LEVEL=INFO
WEB_DEBUG=False
WEB_PORT=8084
WEB_HOST=0.0.0.0
MESSAGE_RETENTION_DAYS=90
```

### Testing

```env
LOG_LEVEL=DEBUG
WEB_PORT=8085
DATABASE_PATH=test_signal_bot.db
MESSAGE_POLLING_INTERVAL=10
```

## AI Provider Configuration

### Setting Up Ollama (Recommended)

1. Install Ollama on your server:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

2. Pull a model:
```bash
ollama pull llama3.2:latest
```

3. Configure in Signal Bot:
```env
OLLAMA_HOST=http://localhost:11434/
OLLAMA_DEFAULT_MODEL=llama3.2:latest
```

4. Use the web dashboard to test and preload models

### Setting Up External Providers

#### OpenAI
1. Get API key from https://platform.openai.com/
2. Set `OPENAI_API_KEY` in environment
3. Choose model in web dashboard

#### Anthropic Claude
1. Get API key from https://console.anthropic.com/
2. Set `ANTHROPIC_API_KEY` in environment
3. Choose model in web dashboard

#### Google Gemini
1. Get API key from https://makersuite.google.com/
2. Set `GOOGLE_API_KEY` in environment
3. Install Gemini CLI if needed
4. Configure in web dashboard

## Troubleshooting Configuration

### Configuration Not Loading

1. Check environment variables:
```bash
env | grep SIGNAL_
```

2. Verify `.env` file location and format

3. Check config module:
```bash
python3 -c "from config.settings import Config; c=Config(); print(c.__dict__)"
```

### Wrong Port or Host

1. Kill existing processes:
```bash
./manage.sh stop
```

2. Set correct environment:
```bash
export WEB_PORT=8084
export WEB_HOST=0.0.0.0
```

3. Restart:
```bash
./manage.sh start
```

### AI Provider Issues

1. Check provider status in web dashboard
2. Verify API keys are set correctly
3. Test connectivity to Ollama:
```bash
curl http://localhost:11434/api/tags
```

4. Check logs for detailed errors:
```bash
tail -f signal_service.log
```

## Advanced Configuration

### Custom Signal CLI Location

If signal-cli is installed in a non-standard location:

```env
SIGNAL_CLI_PATH=/opt/signal-cli/bin/signal-cli
```

### Multiple Bot Instances

Run multiple instances with different configurations:

```bash
# Instance 1
DATABASE_PATH=bot1.db WEB_PORT=8084 ./run_web_server.sh

# Instance 2
DATABASE_PATH=bot2.db WEB_PORT=8086 ./run_web_server.sh
```

### Custom Log Formatting

Edit `LOG_FORMAT` in `config/settings.py`:

```python
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

## Configuration Files Reference

- `config/settings.py` - Main configuration class
- `config/constants.py` - Application constants and enums
- `.env` - Environment overrides (git-ignored)
- `signal_bot.db` - SQLite database with config table

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [API.md](API.md) - Web API configuration endpoints