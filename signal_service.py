#!/usr/bin/env python3
"""
Signal Bot Polling Service

Polls Signal CLI for incoming messages and processes them through the message handler.
Runs independently from the web interface to ensure continuous message processing.

Key features:
- Periodic polling of Signal CLI receive command
- Message persistence to database
- Reaction and auto-reply support
- Group and user synchronization
- Graceful shutdown handling
"""
import os
from config.settings import Config
from config.constants import PATHS, TIMEOUTS, PROCESS
import sys
import time
import signal as signal_module
import threading
import atexit
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.database import DatabaseManager
from utils.bot_instance import BotInstanceManager
from utils.logging import setup_logger, get_logger
from services.setup import SetupService
from services.messaging import MessagingService


class SignalPollingService:
    """Standalone Signal CLI polling service."""

    def __init__(self, sync_groups_on_start=False, debug=False):
        """Initialize the Signal polling service.

        Args:
            sync_groups_on_start: Whether to sync group memberships on startup
            debug: Enable debug-level logging
        """
        self.shutdown_event = threading.Event()
        self.log_file_path = Path(__file__).parent / PATHS['SIGNAL_SERVICE_LOG']
        self.sync_groups_on_start = sync_groups_on_start
        self.debug = debug

        # Setup centralized logging
        self.logger = setup_logger(
            __name__,
            log_file=str(self.log_file_path),
            debug_override=debug
        )

        # Initialize components
        self.db = DatabaseManager(logger=self.logger)

        # Initialize bot instance manager (ensures only one polling service runs)
        self.instance_manager = BotInstanceManager(self.db, logger=self.logger)
        self.setup = SetupService(self.db, logger=self.logger)
        self.messaging = None  # Will be initialized after bot is configured

        # Initialize AI provider manager with database
        from services.ai_provider import initialize_ai_manager
        try:
            self.ai_provider = initialize_ai_manager(db_manager=self.db, logger=self.logger)
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI provider: {e}")
            self.ai_provider = None

        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        self._setup_cleanup_handlers()

        self.logger.info("Signal polling service initialized (PID: %d)", os.getpid())


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
                self.instance_manager.release_instance_lock("Process terminated")
            except Exception:
                pass

        atexit.register(cleanup_instance)

    def get_setup_status(self) -> dict:
        """Get current setup status."""
        return self.setup.get_setup_status()

    def run_setup_if_needed(self):
        """Check setup status but don't auto-run setup - setup only via web interface."""
        status = self.get_setup_status()

        if not status['bot_configured']:
            self.logger.info("Bot not configured - configure via web interface")
            self.logger.info("Use device linking through the web interface to set up the bot")
        else:
            self.logger.info(f"Bot already configured: {status['bot_phone_number']}")

    def poll_cycle(self) -> bool:
        """
        Execute one polling cycle to receive and process messages.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize messaging service if not already done
            if not self.messaging:
                try:
                    # Use signal-cli path from database or auto-detected path
                    signal_cli_path = self.db.get_config("signal_cli_path") or self.signal_cli_path
                    self.messaging = MessagingService(
                        self.db,
                        signal_cli_path=signal_cli_path,
                        logger=self.logger
                    )
                    self.logger.info(f"Messaging service initialized with signal-cli at: {signal_cli_path}")
                except Exception as e:
                    self.logger.error("Failed to initialize messaging service: %s", e)
                    return False

            # Poll for new messages and process them
            messages_processed = self.messaging.poll_and_process_messages(timeout_seconds=5)

            # Wait 10 seconds between polls (reduced from 30 for better responsiveness)
            if self.shutdown_event.wait(10.0):
                return False  # Shutdown was requested

            return True

        except Exception as e:
            self.logger.error("Error in polling cycle: %s", e)
            return True  # Continue polling despite errors

    def start_polling(self):
        """Start the main polling loop."""
        self.logger.info("Starting Signal CLI polling service")

        # Check setup status
        self.run_setup_if_needed()

        # Print status information
        self.print_status()

        # Perform initial sync to catch any missed messages
        self.logger.info("Performing initial message sync...")
        try:
            if not self.messaging:
                # Use signal-cli path from database or auto-detected path
                signal_cli_path = self.db.get_config("signal_cli_path") or self.signal_cli_path
                self.messaging = MessagingService(
                    self.db,
                    signal_cli_path=signal_cli_path,
                    logger=self.logger
                )
                self.logger.info(f"Messaging service initialized for startup sync with signal-cli at: {signal_cli_path}")

            # Poll immediately on startup to get any queued messages
            messages_processed = self.messaging.poll_and_process_messages(timeout_seconds=10)
            if messages_processed > 0:
                self.logger.info(f"Startup sync: processed {messages_processed} queued messages")
            else:
                self.logger.info("Startup sync: no queued messages found")
        except Exception as e:
            self.logger.warning(f"Startup sync failed: {e}")

        # Run polling loop in a separate thread
        def polling_worker():
            """Main polling worker thread."""
            self.logger.info("Starting polling worker thread")
            while not self.shutdown_event.is_set():
                if not self.poll_cycle():
                    break
            self.logger.info("Polling worker thread stopped")

        polling_thread = threading.Thread(
            target=polling_worker,
            name="PollingWorker",
            daemon=False
        )
        polling_thread.start()

        self.logger.info("Signal polling service ready")
        self.logger.info("Press Ctrl+C to stop")

        # Keep main thread alive
        try:
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(1.0)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")

        # Wait for polling thread to finish
        polling_thread.join(timeout=10.0)

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

                # Count users with reactions configured (as a proxy for "configured")
                cursor.execute("SELECT COUNT(DISTINCT uuid) FROM user_reactions")
                configured_users = cursor.fetchone()[0]

            self.logger.info("  Groups: %d/%d monitored", monitored_groups, total_groups)
            self.logger.info("  Users: %d/%d configured", configured_users, total_users)

        except Exception as e:
            self.logger.error("Error getting status: %s", e)

    def shutdown(self):
        """Shutdown the service gracefully."""
        if self.shutdown_event.is_set():
            return

        self.logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()

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
    """Main entry point for Signal polling service."""
    parser = argparse.ArgumentParser(description='Signal CLI Polling Service')
    parser.add_argument('--sync-groups', action='store_true',
                       help='Sync group memberships on startup')
    parser.add_argument('--force', action='store_true',
                       help='Force start even if another instance is running')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Create the polling service
    service = SignalPollingService(
        sync_groups_on_start=args.sync_groups,
        debug=args.debug
    )

    # Acquire instance lock
    if not service.acquire_instance_lock(force=args.force):
        sys.exit(1)

    # Start the service
    try:
        service.start_polling()
    finally:
        service.shutdown()


if __name__ == "__main__":
    main()