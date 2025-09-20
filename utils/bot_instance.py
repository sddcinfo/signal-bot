"""
Bot Instance Manager
Ensures only one bot instance can run at a time using PID files and database tracking.
"""
import os
import signal
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from models.database import DatabaseManager


class BotInstanceManager:
    """Manages bot instance to ensure only one bot runs at a time."""

    def __init__(self, db: DatabaseManager, pid_file_path: str = "./signal_bot.pid",
                 logger: Optional[logging.Logger] = None):
        """Initialize bot instance manager."""
        self.db = db
        self.pid_file_path = Path(pid_file_path)
        self.logger = logger or logging.getLogger(__name__)
        self.status_id: Optional[int] = None

    def is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is actually running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def get_running_bot_pid(self) -> Optional[int]:
        """Get PID of currently running bot, if any."""
        # Check PID file first
        if self.pid_file_path.exists():
            try:
                with open(self.pid_file_path, 'r') as f:
                    pid = int(f.read().strip())

                if self.is_process_running(pid):
                    return pid
                else:
                    # PID file exists but process is dead, clean it up
                    self.logger.warning(f"Found stale PID file for dead process {pid}")
                    self.pid_file_path.unlink()
            except (ValueError, IOError) as e:
                self.logger.warning(f"Invalid PID file: {e}")
                self.pid_file_path.unlink()

        # Check database for recent bot status
        status = self.db.get_current_bot_status()
        if status and status['status'] != 'stopped':
            pid = status['pid']
            if self.is_process_running(pid):
                return pid

        return None

    def stop_existing_bot(self, force: bool = False) -> bool:
        """Stop any existing bot instance."""
        pid = self.get_running_bot_pid()
        if not pid:
            return True

        self.logger.info(f"Stopping existing bot process {pid}")

        try:
            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)

            # Wait up to 10 seconds for graceful shutdown
            for _ in range(10):
                if not self.is_process_running(pid):
                    break
                time.sleep(1)

            # If still running and force is True, kill it
            if self.is_process_running(pid):
                if force:
                    self.logger.warning(f"Force killing bot process {pid}")
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
                else:
                    self.logger.error(f"Bot process {pid} did not stop gracefully")
                    return False

            # Clean up PID file
            if self.pid_file_path.exists():
                self.pid_file_path.unlink()

            # Update database status
            status = self.db.get_current_bot_status()
            if status and status['pid'] == pid:
                self.db.record_bot_stop(status['id'], 'Stopped by new instance')

            return True

        except OSError as e:
            self.logger.error(f"Failed to stop bot process {pid}: {e}")
            return False

    def acquire_instance_lock(self, force: bool = False) -> Tuple[bool, str]:
        """
        Acquire exclusive lock to run bot instance.

        Returns:
            Tuple of (success, message)
        """
        # Check if another bot is running
        existing_pid = self.get_running_bot_pid()
        if existing_pid:
            if not force:
                return False, f"Another bot instance is already running (PID: {existing_pid})"

            if not self.stop_existing_bot(force=True):
                return False, f"Failed to stop existing bot instance (PID: {existing_pid})"

        # Create PID file
        current_pid = os.getpid()
        try:
            with open(self.pid_file_path, 'w') as f:
                f.write(str(current_pid))

            # Record bot start in database
            self.status_id = self.db.record_bot_start(current_pid, f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")

            self.logger.info(f"Acquired bot instance lock (PID: {current_pid}, Status ID: {self.status_id})")
            return True, f"Bot instance lock acquired (PID: {current_pid})"

        except IOError as e:
            return False, f"Failed to create PID file: {e}"

    def update_status(self, status: str, details: str = None):
        """Update bot status in database."""
        if self.status_id:
            self.db.update_bot_status(self.status_id, status, details)

    def heartbeat(self):
        """Send heartbeat to show bot is still alive."""
        if self.status_id:
            self.db.record_bot_heartbeat(self.status_id)

    def release_instance_lock(self, details: str = "Normal shutdown"):
        """Release the instance lock."""
        # Remove PID file
        if self.pid_file_path.exists():
            try:
                self.pid_file_path.unlink()
            except IOError as e:
                self.logger.warning(f"Failed to remove PID file: {e}")

        # Update database status
        if self.status_id:
            self.db.record_bot_stop(self.status_id, details)
            self.status_id = None

        self.logger.info("Released bot instance lock")

    def cleanup_old_status(self, hours: int = 24):
        """Clean up old bot status records."""
        deleted = self.db.cleanup_old_bot_status(hours)
        if deleted > 0:
            self.logger.debug(f"Cleaned up {deleted} old bot status records")