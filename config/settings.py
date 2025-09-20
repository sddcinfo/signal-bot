"""
Centralized Configuration for Signal Bot

This module contains all configuration settings for the Signal Bot application.
Settings can be overridden via environment variables.

Usage:
    from config import Config
    config = Config()
    signal_path = config.SIGNAL_CLI_PATH
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent


def find_signal_cli_path() -> str:
    """
    Auto-detect signal-cli path from common locations.
    Returns the first working signal-cli path found.
    """
    # Check environment variable first
    env_path = os.getenv('SIGNAL_CLI_PATH')
    if env_path and Path(env_path).exists():
        return env_path

    # Common paths to check
    paths_to_check = [
        '/opt/homebrew/bin/signal-cli',  # Homebrew on Apple Silicon Macs
        '/usr/local/bin/signal-cli',      # Homebrew on Intel Macs or Linux
        '/usr/bin/signal-cli',             # System package manager
        '/snap/bin/signal-cli',            # Snap package
    ]

    # Check if signal-cli is in PATH
    try:
        result = subprocess.run(['which', 'signal-cli'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            path_from_which = result.stdout.strip()
            if path_from_which not in paths_to_check:
                paths_to_check.insert(0, path_from_which)
    except Exception:
        pass

    # Test each path
    for path in paths_to_check:
        if Path(path).exists():
            try:
                # Verify it actually works
                result = subprocess.run([path, '--version'],
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return path
            except Exception:
                continue

    # Default fallback
    return '/usr/local/bin/signal-cli'


class Config:
    """
    Central configuration class for Signal Bot.

    All configuration values have sensible defaults and can be overridden
    via environment variables using the same name.

    Naming Convention:
        - Use UPPER_CASE for configuration constants
        - Prefix with module name for clarity (e.g., DB_PATH, LOG_LEVEL)
    """

    # ============= Core Paths =============
    SIGNAL_CLI_PATH: str = find_signal_cli_path()
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'signal_bot.db')

    # ============= Logging Configuration =============
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT',
        '%(asctime)s - [%(name)s] - %(module)s - %(levelname)s - [%(threadName)s] - %(message)s'
    )
    LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'

    # Service-specific log configurations
    SIGNAL_SERVICE_LOG_FILE: str = os.getenv('SIGNAL_SERVICE_LOG_FILE', 'signal_service.log')
    WEB_SERVER_LOG_FILE: str = os.getenv('WEB_SERVER_LOG_FILE', 'web_server.log')
    SIGNAL_BOT_LOG_FILE: str = os.getenv('SIGNAL_BOT_LOG_FILE', 'signal_bot.log')

    # ============= Web Server Configuration =============
    WEB_HOST: str = os.getenv('WEB_HOST', '0.0.0.0')
    WEB_PORT: int = int(os.getenv('WEB_PORT', '8084'))
    WEB_DEBUG: bool = os.getenv('WEB_DEBUG', 'False').lower() == 'true'

    # ============= AI Provider Configuration =============
    # Ollama settings
    OLLAMA_HOST: str = os.getenv('OLLAMA_HOST', 'http://192.168.10.160:11434/')
    OLLAMA_DEFAULT_MODEL: str = os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3.2:latest')
    OLLAMA_TIMEOUT: int = int(os.getenv('OLLAMA_TIMEOUT', '120'))

    # Google Gemini settings
    GOOGLE_API_KEY: Optional[str] = os.getenv('GOOGLE_API_KEY')
    GEMINI_DEFAULT_MODEL: str = os.getenv('GEMINI_DEFAULT_MODEL', 'gemini-1.5-flash')

    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_DEFAULT_MODEL: str = os.getenv('OPENAI_DEFAULT_MODEL', 'gpt-4o-mini')

    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_DEFAULT_MODEL: str = os.getenv('CLAUDE_DEFAULT_MODEL', 'claude-3-5-sonnet-20241022')

    # ============= Signal Service Configuration =============
    SIGNAL_RECEIVE_TIMEOUT: int = int(os.getenv('SIGNAL_RECEIVE_TIMEOUT', '5'))
    SIGNAL_POLL_INTERVAL: float = float(os.getenv('SIGNAL_POLL_INTERVAL', '0.1'))
    SIGNAL_COMMAND_PREFIX: str = os.getenv('SIGNAL_COMMAND_PREFIX', '/')
    SIGNAL_SUBPROCESS_TIMEOUT: int = int(os.getenv('SIGNAL_SUBPROCESS_TIMEOUT', '30'))

    # ============= Message Processing =============
    MESSAGE_BATCH_SIZE: int = int(os.getenv('MESSAGE_BATCH_SIZE', '10'))
    MESSAGE_RATE_LIMIT: int = int(os.getenv('MESSAGE_RATE_LIMIT', '50'))
    MESSAGE_RATE_WINDOW: int = int(os.getenv('MESSAGE_RATE_WINDOW', '60'))

    # ============= Database Configuration =============
    DB_TIMEOUT: int = int(os.getenv('DB_TIMEOUT', '30'))
    DB_MAX_RETRIES: int = int(os.getenv('DB_MAX_RETRIES', '3'))
    DB_RETRY_DELAY: float = float(os.getenv('DB_RETRY_DELAY', '0.5'))

    # ============= Feature Flags =============
    ENABLE_SENTIMENT_ANALYSIS: bool = os.getenv('ENABLE_SENTIMENT_ANALYSIS', 'True').lower() == 'true'
    ENABLE_SUMMARIZATION: bool = os.getenv('ENABLE_SUMMARIZATION', 'True').lower() == 'true'
    ENABLE_AUTO_RESPONSE: bool = os.getenv('ENABLE_AUTO_RESPONSE', 'True').lower() == 'true'
    ENABLE_GROUP_MONITORING: bool = os.getenv('ENABLE_GROUP_MONITORING', 'True').lower() == 'true'

    # ============= Limits and Thresholds =============
    MAX_MESSAGE_LENGTH: int = int(os.getenv('MAX_MESSAGE_LENGTH', '4000'))
    MAX_GROUP_MEMBERS: int = int(os.getenv('MAX_GROUP_MEMBERS', '1000'))
    MAX_SUMMARY_LENGTH: int = int(os.getenv('MAX_SUMMARY_LENGTH', '500'))
    MIN_MESSAGES_FOR_SUMMARY: int = int(os.getenv('MIN_MESSAGES_FOR_SUMMARY', '5'))

    # ============= UI Configuration =============
    UI_THEME: str = os.getenv('UI_THEME', 'dark')
    UI_PAGE_SIZE: int = int(os.getenv('UI_PAGE_SIZE', '50'))
    UI_REFRESH_INTERVAL: int = int(os.getenv('UI_REFRESH_INTERVAL', '30'))

    # ============= Security =============
    ENABLE_INSTANCE_LOCK: bool = os.getenv('ENABLE_INSTANCE_LOCK', 'True').lower() == 'true'
    INSTANCE_LOCK_TIMEOUT: int = int(os.getenv('INSTANCE_LOCK_TIMEOUT', '300'))

    @classmethod
    def get(cls, key: str, default=None):
        """
        Get configuration value by key.

        Args:
            key: Configuration key (should be in UPPER_CASE)
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return getattr(cls, key, default)

    @classmethod
    def update(cls, key: str, value):
        """
        Update configuration value at runtime.

        Args:
            key: Configuration key to update
            value: New value
        """
        setattr(cls, key, value)

    @classmethod
    def to_dict(cls):
        """
        Export all configuration as dictionary.

        Returns:
            Dict of all configuration values
        """
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }


# Singleton instance
_config = None


def get_config() -> Config:
    """
    Get singleton configuration instance.

    Returns:
        Config: Global configuration instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config