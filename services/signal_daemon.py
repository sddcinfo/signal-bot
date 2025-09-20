#!/usr/bin/env python3
"""
Signal CLI Daemon Service

Uses signal-cli in daemon mode with JSON-RPC for reliable message handling.
This approach maintains a persistent connection and shouldn't drop messages.
"""
import os
import sys
import time
import json
import socket
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import signal as signal_module
from utils.logging import get_logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import DatabaseManager
from services.messaging import MessagingService


class SignalDaemonService:
    """Service that manages signal-cli in daemon mode."""

    def __init__(self, db: DatabaseManager, logger: Optional[logging.Logger] = None):
        """Initialize the daemon service."""
        self.db = db
        self.logger = logger or get_logger(__name__)
        self.signal_cli_path = "/usr/local/bin/signal-cli"
        self.socket_path = "/tmp/signal-cli.socket"
        self.daemon_process = None
        self.socket_client = None
        self.shutdown_event = threading.Event()
        self.message_thread = None

        # Get bot phone number from database
        self.bot_phone = self.db.get_config('bot_phone_number')
        if not self.bot_phone:
            raise ValueError("Bot not configured - no phone number found")

        # Initialize messaging service for processing
        self.messaging = MessagingService(
            self.db,
            signal_cli_path=self.signal_cli_path,
            logger=self.logger
        )

    def start_daemon(self) -> bool:
        """Start signal-cli in daemon mode."""
        try:
            # Clean up any existing socket
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
                self.logger.info("Removed existing socket file")

            # Start signal-cli daemon
            cmd = [
                self.signal_cli_path,
                "-a", self.bot_phone,
                "daemon",
                "--socket", self.socket_path
            ]

            self.logger.info("Starting signal-cli daemon...")
            self.daemon_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait for socket to be created
            max_wait = 30  # seconds
            for i in range(max_wait):
                if os.path.exists(self.socket_path):
                    self.logger.info("Daemon socket created after %d seconds", i + 1)
                    break
                time.sleep(1)
            else:
                self.logger.error("Daemon socket not created after %d seconds", max_wait)
                self.stop_daemon()
                return False

            # Connect to socket
            time.sleep(2)  # Give daemon a moment to fully initialize
            if not self._connect_to_socket():
                self.stop_daemon()
                return False

            self.logger.info("Signal-cli daemon started successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to start daemon: %s", e)
            return False

    def _connect_to_socket(self) -> bool:
        """Connect to the daemon socket."""
        try:
            self.socket_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket_client.connect(self.socket_path)
            self.socket_client.settimeout(1.0)  # Non-blocking with timeout
            self.logger.info("Connected to daemon socket")
            return True
        except Exception as e:
            self.logger.error("Failed to connect to socket: %s", e)
            return False

    def _send_json_rpc(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the daemon."""
        try:
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": int(time.time() * 1000)
            }

            request_str = json.dumps(request) + "\n"
            self.socket_client.send(request_str.encode('utf-8'))

            # Read response
            response_data = b""
            while True:
                try:
                    chunk = self.socket_client.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    if b"\n" in response_data:
                        break
                except socket.timeout:
                    break

            if response_data:
                response = json.loads(response_data.decode('utf-8').strip())
                return response

        except Exception as e:
            self.logger.error("Error sending JSON-RPC request: %s", e)

        return None

    def subscribe_receive(self):
        """Subscribe to receive messages from the daemon."""
        try:
            # Subscribe to receive updates
            result = self._send_json_rpc("subscribe", {"receive": True})
            if result:
                self.logger.info("Subscribed to receive messages: %s", result)
                return True
            else:
                self.logger.error("Failed to subscribe to messages")
                return False
        except Exception as e:
            self.logger.error("Error subscribing to messages: %s", e)
            return False

    def listen_for_messages(self):
        """Listen for incoming messages from the daemon."""
        self.logger.info("Starting message listener thread")

        # First subscribe
        if not self.subscribe_receive():
            self.logger.error("Failed to subscribe, stopping listener")
            return

        buffer = b""
        while not self.shutdown_event.is_set():
            try:
                # Read from socket with timeout
                try:
                    data = self.socket_client.recv(4096)
                except socket.timeout:
                    continue

                if not data:
                    self.logger.warning("Socket closed, attempting reconnection...")
                    if self._connect_to_socket() and self.subscribe_receive():
                        continue
                    else:
                        break

                buffer += data

                # Process complete messages (ending with newline)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line:
                        try:
                            message = json.loads(line.decode('utf-8'))

                            # Check if this is a message notification
                            if message.get("method") == "receive":
                                params = message.get("params", {})
                                envelope = params.get("envelope", {})

                                if envelope:
                                    self.logger.info("Received message via daemon")
                                    # Process the message using existing messaging service
                                    # Wrap it in the expected format
                                    wrapped_envelope = {"envelope": envelope}
                                    if self.messaging.process_message(wrapped_envelope):
                                        self.logger.info("Message processed successfully")

                        except json.JSONDecodeError as e:
                            self.logger.warning("Failed to parse message: %s", e)
                        except Exception as e:
                            self.logger.error("Error processing message: %s", e)

            except Exception as e:
                self.logger.error("Error in message listener: %s", e)
                if not self.shutdown_event.is_set():
                    time.sleep(1)

        self.logger.info("Message listener thread stopped")

    def send_reaction(self, group_id: str, target_timestamp: int, target_author: str, emoji: str) -> bool:
        """Send a reaction using the daemon."""
        try:
            params = {
                "account": self.bot_phone,
                "groupId": group_id,
                "targetTimestamp": target_timestamp,
                "targetAuthor": target_author,
                "emoji": emoji
            }

            result = self._send_json_rpc("sendReaction", params)
            if result and not result.get("error"):
                self.logger.info("Sent reaction %s successfully", emoji)
                return True
            else:
                error = result.get("error") if result else "No response"
                self.logger.warning("Failed to send reaction: %s", error)
                return False

        except Exception as e:
            self.logger.error("Error sending reaction: %s", e)
            return False

    def start(self):
        """Start the daemon service and message listener."""
        if not self.start_daemon():
            raise RuntimeError("Failed to start signal-cli daemon")

        # Start message listener thread
        self.message_thread = threading.Thread(
            target=self.listen_for_messages,
            name="MessageListener",
            daemon=False
        )
        self.message_thread.start()

        self.logger.info("Signal daemon service started")

    def stop(self):
        """Stop the daemon service."""
        self.logger.info("Stopping signal daemon service...")

        # Signal shutdown
        self.shutdown_event.set()

        # Close socket connection
        if self.socket_client:
            try:
                self.socket_client.close()
            except Exception as e:
                self.logger.error("Error closing socket: %s", e)

        # Wait for message thread
        if self.message_thread and self.message_thread.is_alive():
            self.message_thread.join(timeout=5)

        # Stop daemon process
        self.stop_daemon()

        self.logger.info("Signal daemon service stopped")

    def stop_daemon(self):
        """Stop the daemon process."""
        if self.daemon_process:
            try:
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=10)
                self.logger.info("Daemon process terminated")
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
                self.daemon_process.wait()
                self.logger.warning("Daemon process killed (did not terminate gracefully)")
            except Exception as e:
                self.logger.error("Error stopping daemon: %s", e)

        # Clean up socket file
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
                self.logger.info("Removed socket file")
            except Exception as e:
                self.logger.error("Error removing socket file: %s", e)


def main():
    """Test the daemon service."""
    logger = get_logger(__name__)

    # Initialize database
    db = DatabaseManager(logger=logger)

    # Create daemon service
    daemon = SignalDaemonService(db, logger=logger)

    def signal_handler(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        daemon.stop()
        sys.exit(0)

    signal_module.signal(signal_module.SIGINT, signal_handler)
    signal_module.signal(signal_module.SIGTERM, signal_handler)

    try:
        daemon.start()

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        daemon.stop()


if __name__ == "__main__":
    main()