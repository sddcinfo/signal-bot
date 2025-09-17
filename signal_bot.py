#!/usr/bin/env python3
"""
UUID-based Signal Bot - Clean Architecture

A complete rewrite of the Signal bot using proper UUID-based design:
- UUID as primary key for all users
- Phone numbers as optional metadata
- Clean setup flow: device linking -> group sync -> user discovery
- Simple, reusable database operations
- REST-like web interface
- Non-blocking, thread-safe architecture
- Proper resource management and graceful shutdown

This follows proper Signal architecture where UUIDs are the stable identifier.
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.database import DatabaseManager
from services.setup import SetupService
from services.messaging import MessagingService
from web.server import WebServer


class SignalBot:
    """UUID-based Signal bot with clean, thread-safe architecture."""

    def __init__(self, sync_groups_on_start=False, debug=False):
        """Initialize the Signal bot.

        Args:
            sync_groups_on_start: Whether to sync group memberships on startup
            debug: Enable debug-level logging
        """
        self.shutdown_event = threading.Event()
        self.lock_file_path = Path(__file__).parent / "signal_bot.lock"
        self.log_file_path = Path(__file__).parent / "signal_bot.log"
        self.sync_groups_on_start = sync_groups_on_start
        self.debug = debug

        # Setup logging with detailed formatting
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Create lock file for bot
        self._create_lock_file()

        # Initialize components
        self.db = DatabaseManager(logger=self.logger)
        self.setup = SetupService(self.db, logger=self.logger)
        self.messaging = None  # Will be initialized after bot is configured
        self.web_server = None  # Will be initialized in start_web_interface

        # Initialize AI provider manager with database
        from services.ai_provider import initialize_ai_manager
        initialize_ai_manager(db_manager=self.db, logger=self.logger)

        # Threading components
        self.web_thread = None
        self.polling_thread = None

        # Setup signal handlers and cleanup
        self._setup_signal_handlers()
        self._setup_cleanup_handlers()

        self.logger.info("UUID-based Signal Bot initialized (PID: %d)", os.getpid())

    def _setup_logging(self):
        """Setup logging for bot."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.log_file_path, mode='a')
            ],
            force=True  # Override any existing logging config
        )

        # Set specific log levels for components
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)

    def _create_lock_file(self):
        """Create singleton lock file for bot."""
        try:
            if self.lock_file_path.exists():
                # Check if process is still running
                with open(self.lock_file_path, 'r') as f:
                    old_pid = int(f.read().strip())

                try:
                    os.kill(old_pid, 0)
                    raise RuntimeError(f"Another instance of Signal Bot is running (PID: {old_pid})")
                except (OSError, ProcessLookupError):
                    # Stale lock file, remove it
                    self.lock_file_path.unlink()

            # Create new lock file
            with open(self.lock_file_path, 'w') as f:
                f.write(str(os.getpid()))

        except Exception as e:
            raise RuntimeError(f"Failed to create lock file: {e}")


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
        def cleanup_files():
            """Clean up lock file on exit."""
            try:
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
            except Exception:
                pass

        atexit.register(cleanup_files)

    def start_web_interface(self) -> Optional[str]:
        """Start the web management interface in a separate thread."""
        try:
            self.web_server = WebServer(self.db, self.setup, port=8084, logger=self.logger)

            def web_server_thread():
                """Run web server in separate thread."""
                try:
                    self.web_server.start()
                except Exception as e:
                    self.logger.error("Web server thread error: %s", e)

            self.web_thread = threading.Thread(
                target=web_server_thread,
                name="WebServer",
                daemon=True
            )
            self.web_thread.start()

            # Give the server a moment to start
            time.sleep(0.5)

            url = f"http://localhost:8084"
            self.logger.info("Web interface started successfully on %s", url)
            return url

        except Exception as e:
            self.logger.error("Failed to start web interface: %s", e)
            return None

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
                    self.messaging = MessagingService(
                        self.db,
                        signal_cli_path="/usr/local/bin/signal-cli",
                        logger=self.logger
                    )
                    self.logger.info("Messaging service initialized")
                except Exception as e:
                    self.logger.error("Failed to initialize messaging service: %s", e)
                    return False

            # Poll for new messages and process them
            messages_processed = self.messaging.poll_and_process_messages(timeout_seconds=5)

            # Wait 30 seconds between polls to prevent excessive API calls
            if self.shutdown_event.wait(30.0):
                return False

            return True

        except Exception as e:
            self.logger.error("Polling cycle failed: %s", e)
            return False

    def _polling_worker(self):
        """Worker thread for message polling."""
        self.logger.info("Starting polling worker thread")
        cycle_count = 0

        try:
            while not self.shutdown_event.is_set():
                # Get current status to check if bot is configured
                status = self.get_setup_status()

                if status['bot_configured'] and status['monitored_groups'] > 0:
                    success = self.poll_cycle()
                    if not success:
                        if not self.shutdown_event.is_set():
                            self.logger.warning("Polling cycle failed")

                    cycle_count += 1
                    if cycle_count % 60 == 0:  # Log every 60 cycles
                        self.logger.debug("Polling worker - %d cycles completed", cycle_count)
                else:
                    # Not configured yet, wait longer
                    if self.shutdown_event.wait(5.0):
                        break

        except Exception as e:
            self.logger.error("Polling worker thread error: %s", e, exc_info=True)
        finally:
            self.logger.info("Polling worker thread stopped")

    def run(self):
        """Run the bot with non-blocking, threaded architecture."""
        self.logger.info("Starting UUID-based Signal Bot")

        try:
            # Start web interface
            url = self.start_web_interface()
            if url:
                self.logger.info("Web management interface: %s", url)
            else:
                self.logger.error("Failed to start web interface")
                return

            # Run setup if needed
            self.run_setup_if_needed()

            # Show current status
            status = self.get_setup_status()
            self._log_status(status)

            # Sync group memberships if requested
            if self.sync_groups_on_start and status['bot_configured']:
                self.logger.info("Syncing group memberships from Signal...")
                try:
                    messaging = MessagingService(
                        self.db,
                        self.signal_cli_path,
                        self.logger
                    )
                    if messaging.sync_group_memberships():
                        self.logger.info("Group membership sync completed successfully")
                    else:
                        self.logger.warning("Group membership sync failed")
                except Exception as e:
                    self.logger.error("Error during group sync: %s", e)

            # Start polling worker thread
            self.polling_thread = threading.Thread(
                target=self._polling_worker,
                name="PollingWorker",
                daemon=True
            )
            self.polling_thread.start()

            self.logger.info("Bot ready - use the web interface for configuration")
            self.logger.info("Press Ctrl+C to stop")

            # Main thread just waits for shutdown
            try:
                while not self.shutdown_event.is_set():
                    if self.shutdown_event.wait(10.0):  # Check every 10 seconds
                        break

                    # Periodically log status (every 5 minutes)
                    # This also keeps the main thread responsive

            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")

        except Exception as e:
            self.logger.error("Unexpected error in main thread: %s", e, exc_info=True)
        finally:
            self.cleanup()

    def _log_status(self, status: dict):
        """Log current bot status."""
        self.logger.info("Bot Status:")
        self.logger.info("  Signal CLI: %s", 'Available' if status['signal_cli_available'] else 'Not Available')
        self.logger.info("  Bot Configured: %s", 'Yes' if status['bot_configured'] else 'No')
        if status['bot_configured']:
            self.logger.info("  Phone: %s", status['bot_phone_number'])
            self.logger.info("  Groups: %d/%d monitored", status['monitored_groups'], status['total_groups'])
            self.logger.info("  Users: %d/%d configured", status['configured_users'], status['total_users'])

    def cleanup(self):
        """Clean up resources and stop all threads."""
        self.logger.info("Cleaning up resources...")

        # Stop web interface
        if hasattr(self, 'web_server') and self.web_server:
            try:
                self.web_server.stop()
                self.logger.debug("Web server stopped")
            except Exception as e:
                self.logger.warning("Error stopping web server: %s", e)

        # Wait for threads to complete (with timeout)
        if self.web_thread and self.web_thread.is_alive():
            self.logger.debug("Waiting for web thread to complete...")
            self.web_thread.join(timeout=3.0)
            if self.web_thread.is_alive():
                self.logger.warning("Web thread did not stop gracefully")

        if self.polling_thread and self.polling_thread.is_alive():
            self.logger.debug("Waiting for polling thread to complete...")
            self.polling_thread.join(timeout=3.0)
            if self.polling_thread.is_alive():
                self.logger.warning("Polling thread did not stop gracefully")

        # Clean up old messages
        try:
            self.db.cleanup_old_messages(days=30)
            self.logger.debug("Database cleanup completed")
        except Exception as e:
            self.logger.warning("Failed to cleanup old messages: %s", e)

        self.logger.info("Cleanup complete")

    def shutdown(self):
        """Initiate graceful shutdown."""
        if not self.shutdown_event.is_set():
            self.logger.info("Initiating graceful shutdown...")
            self.shutdown_event.set()

            # Don't call cleanup() here - let the main thread handle it
            # This prevents recursive cleanup calls from signal handlers


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='UUID-based Signal Bot with web interface'
    )
    parser.add_argument(
        '--sync-groups',
        action='store_true',
        help='Sync group memberships from Signal on startup'
    )
    parser.add_argument(
        '--sync-only',
        action='store_true',
        help='Only sync group memberships and exit (do not start bot)'
    )
    parser.add_argument(
        '--web-only',
        action='store_true',
        help='Start only the web interface without message polling'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging for troubleshooting'
    )

    args = parser.parse_args()

    # Handle sync-only mode
    if args.sync_only:
        try:
            from models.database import DatabaseManager
            from services.messaging import MessagingService

            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            logger = logging.getLogger(__name__)

            db = DatabaseManager(Path(__file__).parent / 'signal_bot.db')
            messaging = MessagingService(db, '/usr/local/bin/signal-cli', logger)

            logger.info("Starting group membership sync...")
            if messaging.sync_group_memberships():
                logger.info("Group membership sync completed successfully")
                sys.exit(0)
            else:
                logger.error("Group membership sync failed")
                sys.exit(1)
        except Exception as e:
            print(f"Sync failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Normal bot operation
    try:
        bot = SignalBot(sync_groups_on_start=args.sync_groups, debug=args.debug)
        bot.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start bot: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()