#!/usr/bin/env python3
"""
Signal Daemon Service - Uses daemon mode instead of polling

This service uses signal-cli in daemon mode for more reliable message handling.
All operations go through a single daemon connection.
"""
import os
import sys
import time
import signal as signal_module
import threading
import logging
import atexit
import argparse
from pathlib import Path
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.database import DatabaseManager
from utils.bot_instance import BotInstanceManager
from services.setup import SetupService
from services.messaging_daemon import MessagingDaemonService
from config.settings import Config


class SignalDaemonPollingService:
    """Signal service using daemon mode instead of polling."""

    def __init__(self, debug=False):
        """Initialize the Signal daemon service."""
        self.shutdown_event = threading.Event()
        self.log_file_path = Path(__file__).parent / "signal_daemon.log"
        self.debug = debug

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.db = DatabaseManager(logger=self.logger)

        # Initialize bot instance manager
        self.instance_manager = BotInstanceManager(self.db, logger=self.logger)
        self.setup = SetupService(self.db, logger=self.logger)

        # Use daemon messaging service instead of regular polling
        self.messaging = None  # Will be initialized after bot is configured

        # Initialize AI provider manager
        from services.ai_provider import initialize_ai_manager
        try:
            self.ai_provider = initialize_ai_manager(db_manager=self.db, logger=self.logger)
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI provider: {e}")
            self.ai_provider = None

        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        self._setup_cleanup_handlers()

        self.logger.info("Signal daemon service initialized (PID: %d)", os.getpid())

    def _setup_logging(self):
        """Setup logging for daemon service."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - [DAEMON-SERVICE] - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.log_file_path, mode='a')
            ],
            force=True
        )

        # Set specific log levels
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)

    def acquire_instance_lock(self, force: bool = False) -> bool:
        """Acquire exclusive bot instance lock."""
        success, message = self.instance_manager.acquire_instance_lock(force=force)
        if not success:
            self.logger.error(message)
            return False

        self.logger.info(message)
        return True

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if self.shutdown_event.is_set():
                return
            signal_name = signal_module.Signals(signum).name
            self.logger.info("Received signal %s. Initiating graceful shutdown...", signal_name)
            self.shutdown()

        signal_module.signal(signal_module.SIGINT, signal_handler)
        signal_module.signal(signal_module.SIGTERM, signal_handler)

    def _setup_cleanup_handlers(self):
        """Setup cleanup handlers for exit."""
        def cleanup_instance():
            """Clean up bot instance on exit."""
            try:
                if self.messaging:
                    self.messaging.stop()
                self.instance_manager.release_instance_lock("Process terminated")
            except Exception:
                pass

        atexit.register(cleanup_instance)

    def get_setup_status(self) -> dict:
        """Get current setup status."""
        return self.setup.get_setup_status()

    def run_setup_if_needed(self):
        """Check setup status."""
        status = self.get_setup_status()

        if not status['bot_configured']:
            self.logger.info("Bot not configured - configure via web interface")
            self.logger.info("Use device linking through the web interface to set up the bot")
            return False
        else:
            self.logger.info(f"Bot already configured: {status['bot_phone_number']}")
            return True

    def start_daemon(self):
        """Start the daemon service."""
        self.logger.info("Starting Signal CLI daemon service")

        # Check setup status
        if not self.run_setup_if_needed():
            self.logger.error("Bot not configured, cannot start daemon")
            return

        # Print status information
        self.print_status()

        try:
            # Initialize daemon messaging service
            self.messaging = MessagingDaemonService(
                self.db,
                signal_cli_path="/usr/local/bin/signal-cli",
                logger=self.logger
            )

            # Start the daemon (this starts both the daemon process and listener thread)
            self.messaging.start()

            self.logger.info("Signal daemon service ready")
            self.logger.info("Press Ctrl+C to stop")

            # Keep main thread alive
            try:
                while not self.shutdown_event.is_set():
                    self.shutdown_event.wait(1.0)
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")

        except Exception as e:
            self.logger.error("Error starting daemon service: %s", e)

    def print_status(self):
        """Print current bot status."""
        try:
            status = self.get_setup_status()
            self.logger.info("Bot Status:")
            self.logger.info("  Signal CLI: %s", "Available" if status['signal_cli_available'] else "Not Available")
            self.logger.info("  Bot Configured: %s", "Yes" if status['bot_configured'] else "No")

            if status['bot_configured']:
                self.logger.info("  Phone: %s", status['bot_phone_number'])

            # Get basic counts from database
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Count total groups
                cursor.execute("SELECT COUNT(*) FROM groups")
                total_groups = cursor.fetchone()[0]

                # Count monitored groups
                cursor.execute("SELECT COUNT(*) FROM groups WHERE is_monitored = 1")
                monitored_groups = cursor.fetchone()[0]

                # Count total users
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                # Count users with reactions configured
                cursor.execute("SELECT COUNT(DISTINCT uuid) FROM user_reactions")
                configured_users = cursor.fetchone()[0]

            self.logger.info("  Groups: %d/%d monitored", monitored_groups, total_groups)
            self.logger.info("  Users: %d/%d configured", configured_users, total_users)
            self.logger.info("  Mode: DAEMON (more reliable message handling)")

        except Exception as e:
            self.logger.error("Error getting status: %s", e)

    def shutdown(self):
        """Shutdown the service gracefully."""
        if self.shutdown_event.is_set():
            return

        self.logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()

        # Stop messaging daemon
        if self.messaging:
            try:
                self.messaging.stop()
                self.logger.info("Stopped messaging daemon")
            except Exception as e:
                self.logger.error("Error stopping messaging daemon: %s", e)

        # Cleanup resources
        self.logger.info("Cleaning up resources...")

        # Clean up old messages (optional)
        try:
            if self.db:
                self.db.cleanup_old_messages()
                self.logger.info("Cleaned up messages older than 30 days")
        except Exception as e:
            self.logger.error("Error during message cleanup: %s", e)

        self.logger.info("Cleanup complete")

        # Release instance lock
        try:
            self.instance_manager.release_instance_lock("Graceful shutdown")
            self.logger.info("Released bot instance lock")
        except Exception as e:
            self.logger.error("Error releasing instance lock: %s", e)


def main():
    """Main entry point for Signal daemon service."""
    parser = argparse.ArgumentParser(description='Signal CLI Daemon Service')
    parser.add_argument('--force', action='store_true',
                       help='Force start even if another instance is running')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Create the daemon service
    service = SignalDaemonPollingService(debug=args.debug)

    # Acquire instance lock
    if not service.acquire_instance_lock(force=args.force):
        sys.exit(1)

    # Start the service
    try:
        service.start_daemon()
    finally:
        service.shutdown()


if __name__ == "__main__":
    main()