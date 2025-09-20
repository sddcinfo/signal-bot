#!/usr/bin/env python3
"""
Enhanced Messaging Service with Daemon Support

This service integrates signal-cli daemon mode for reliable message handling.
It receives messages and sends reactions through the same daemon connection.
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


class MessagingDaemonService:
    """Messaging service that uses signal-cli daemon mode."""

    def __init__(self, db: DatabaseManager, signal_cli_path: str = "/usr/local/bin/signal-cli",
                 logger: Optional[logging.Logger] = None):
        """Initialize the daemon messaging service."""
        self.db = db
        self.logger = logger or get_logger(__name__)
        self.signal_cli_path = signal_cli_path
        self.socket_path = "/tmp/signal-cli.socket"
        self.daemon_process = None
        self.socket_client = None
        self.shutdown_event = threading.Event()
        self.request_counter = 0
        self.pending_responses = {}
        self.response_lock = threading.Lock()

        # Get bot phone number from database
        self.bot_phone = self.db.get_config('bot_phone_number')
        if not self.bot_phone:
            raise ValueError("Bot not configured - no phone number found")

        # Track if daemon is running
        self.daemon_running = False

    def start_daemon(self) -> bool:
        """Start signal-cli in daemon mode."""
        try:
            # Check if daemon already running
            if self.daemon_running and self.daemon_process and self.daemon_process.poll() is None:
                self.logger.info("Daemon already running")
                return True

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

            self.logger.info("Starting signal-cli daemon with command: %s", ' '.join(cmd))
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

            self.daemon_running = True
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
            self.socket_client.settimeout(0.1)  # Very short timeout for non-blocking reads
            self.logger.info("Connected to daemon socket at %s", self.socket_path)
            return True
        except Exception as e:
            self.logger.error("Failed to connect to socket: %s", e)
            return False

    def _get_next_id(self) -> str:
        """Get next request ID."""
        self.request_counter += 1
        return str(self.request_counter)

    def _send_json_rpc(self, method: str, params: Dict[str, Any], wait_response: bool = True) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the daemon."""
        try:
            request_id = self._get_next_id()
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": request_id
            }

            request_str = json.dumps(request) + "\n"
            self.logger.debug("Sending JSON-RPC: %s", request_str.strip())

            self.socket_client.send(request_str.encode('utf-8'))

            if not wait_response:
                return {"success": True}

            # Wait for response with specific ID
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                with self.response_lock:
                    if request_id in self.pending_responses:
                        response = self.pending_responses.pop(request_id)
                        return response
                time.sleep(0.1)

            self.logger.warning("Timeout waiting for response to request %s", request_id)
            return None

        except Exception as e:
            self.logger.error("Error sending JSON-RPC request: %s", e)
            return None

    def subscribe_receive(self) -> bool:
        """Subscribe to receive messages from the daemon."""
        # In default mode (--receive-mode=on-start), messages are automatically
        # received as notifications, no subscription needed
        self.logger.info("Daemon in automatic receive mode - messages will be received automatically")
        return True

    def send_reaction(self, group_id: str, target_timestamp: int, target_author: str, emoji: str) -> bool:
        """Send a reaction using the daemon JSON-RPC.

        Args:
            group_id: Group ID
            target_timestamp: Message timestamp
            target_author: Message author UUID
            emoji: Reaction emoji

        Returns:
            True if reaction sent successfully
        """
        if not self.socket_client:
            self.logger.error("Not connected to daemon")
            return False

        try:
            request_id = str(int(time.time() * 1000))

            # Prepare reaction request with CORRECT parameter names!
            # Use targetTimestamp NOT targetSentTimestamp
            request = {
                "jsonrpc": "2.0",
                "method": "sendReaction",
                "params": {
                    "groupId": group_id,
                    "targetAuthor": target_author,
                    "targetTimestamp": int(target_timestamp),  # This was the issue!
                    "emoji": emoji
                },
                "id": request_id
            }

            self.logger.info(f"Sending reaction {emoji} to message {target_timestamp} in group {group_id[:8]}")

            # Send the request
            request_str = json.dumps(request) + "\n"
            self.socket_client.send(request_str.encode('utf-8'))

            # Wait for response to confirm success
            max_wait = 5  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                with self.response_lock:
                    if request_id in self.pending_responses:
                        response = self.pending_responses.pop(request_id)
                        if "error" in response:
                            self.logger.error(f"Reaction failed: {response['error']}")
                            return False
                        else:
                            self.logger.info(f"✅ Reaction {emoji} sent successfully via daemon!")
                            return True
                time.sleep(0.1)

            # If no response in time, assume success (fire and forget)
            self.logger.info(f"Reaction {emoji} sent (no response, assuming success)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send reaction: {e}")
            return False

    def process_message(self, envelope: Dict[str, Any]) -> bool:
        """Process a message envelope using daemon-native processor."""
        try:
            # Use the daemon-native processor
            from services.daemon_processor import DaemonMessageProcessor

            # Create processor with our daemon's send_reaction
            processor = DaemonMessageProcessor(
                db=self.db,
                send_reaction_func=self.send_reaction,
                logger=self.logger
            )

            # Process the envelope
            return processor.process_envelope(envelope)

        except Exception as e:
            self.logger.error("Error processing message: %s", e)
            return False

    def listen_for_messages(self):
        """Listen for incoming messages from the daemon."""
        self.logger.info("Starting daemon message listener")

        # In automatic mode, no subscription needed
        if not self.subscribe_receive():
            self.logger.error("Failed to initialize listener")
            return

        buffer = b""
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        messages_received = 0

        while not self.shutdown_event.is_set():
            try:
                # Try to read from socket
                try:
                    data = self.socket_client.recv(4096)
                except socket.timeout:
                    continue
                except socket.error as e:
                    if e.errno == 11:  # Resource temporarily unavailable
                        continue
                    raise

                if not data:
                    self.logger.warning("Socket closed, attempting reconnection...")
                    if reconnect_attempts < max_reconnect_attempts:
                        reconnect_attempts += 1
                        time.sleep(2 * reconnect_attempts)  # Exponential backoff

                        if self._connect_to_socket():
                            reconnect_attempts = 0
                            self.logger.info("Reconnected to daemon socket")
                            continue
                        else:
                            self.logger.error("Reconnection attempt %d failed", reconnect_attempts)
                    else:
                        self.logger.error("Max reconnection attempts reached, stopping listener")
                        break

                buffer += data

                # Process complete messages (ending with newline)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line:
                        continue

                    try:
                        message = json.loads(line.decode('utf-8'))

                        # Check if this is a response to our request (has "id")
                        if "id" in message and message.get("id"):
                            with self.response_lock:
                                self.pending_responses[message["id"]] = message
                            self.logger.debug("Received response for request %s", message["id"])
                            continue

                        # Check if this is a receive notification (automatic mode)
                        if message.get("method") == "receive":
                            params = message.get("params", {})
                            envelope = params.get("envelope", {})

                            if envelope:
                                messages_received += 1

                                # Log message details safely
                                timestamp = envelope.get("timestamp")
                                source_uuid = envelope.get("sourceUuid", "")
                                source_number = envelope.get("sourceNumber", "")
                                source = source_number or (source_uuid[:8] if source_uuid else "unknown")

                                data_msg = envelope.get("dataMessage", {})
                                if data_msg:
                                    if isinstance(data_msg, dict):
                                        msg_text = data_msg.get("message", "")
                                        msg_preview = msg_text[:50] if msg_text else "(no text)"
                                    else:
                                        msg_preview = str(data_msg)[:50] if data_msg else "(empty)"
                                    self.logger.info("📨 REAL-TIME message #%d from %s: %s",
                                                   messages_received, source, msg_preview)

                                # Process the message immediately
                                # Don't wrap the envelope - it's already the full envelope
                                try:
                                    result = self.process_message(envelope)
                                    if result:
                                        # Check if this was actually a data message that we care about
                                        if data_msg and isinstance(data_msg, dict) and data_msg.get("message"):
                                            self.logger.info("✅ Message #%d processed successfully via daemon", messages_received)
                                        else:
                                            # Other types of envelopes (reactions, receipts, etc.)
                                            self.logger.debug("Processed envelope #%d (non-message)", messages_received)
                                    else:
                                        # Only warn about actual message failures
                                        if data_msg and isinstance(data_msg, dict) and data_msg.get("message"):
                                            self.logger.warning("❌ Failed to process message #%d via daemon", messages_received)
                                        else:
                                            self.logger.debug("Skipped envelope #%d (not relevant)", messages_received)
                                except Exception as e:
                                    self.logger.error(f"Exception processing envelope #{messages_received}: {e}")
                                    import traceback
                                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                                    # Only warn about failures for actual messages
                                    if data_msg and isinstance(data_msg, dict) and data_msg.get("message"):
                                        self.logger.warning("❌ Failed to process message #%d via daemon", messages_received)
                        else:
                            # Log other notifications for debugging
                            method = message.get("method", "unknown")
                            if method != "unknown":
                                self.logger.debug("Received notification: method=%s", method)

                    except json.JSONDecodeError as e:
                        self.logger.warning("Failed to parse JSON: %s - Data: %s", e, line[:100])
                    except Exception as e:
                        self.logger.error("Error processing daemon message: %s", e)

            except Exception as e:
                self.logger.error("Error in daemon listener: %s", e)
                if not self.shutdown_event.is_set():
                    time.sleep(1)

        self.logger.info("Daemon message listener stopped (received %d messages)", messages_received)

    def start(self):
        """Start the daemon service and message listener."""
        if not self.start_daemon():
            raise RuntimeError("Failed to start signal-cli daemon")

        # Start message listener thread
        self.message_thread = threading.Thread(
            target=self.listen_for_messages,
            name="DaemonListener",
            daemon=False
        )
        self.message_thread.start()

        self.logger.info("Messaging daemon service started")

    def stop(self):
        """Stop the daemon service."""
        self.logger.info("Stopping messaging daemon service...")

        # Signal shutdown
        self.shutdown_event.set()

        # Close socket connection
        if self.socket_client:
            try:
                self.socket_client.close()
                self.logger.info("Closed socket connection")
            except Exception as e:
                self.logger.error("Error closing socket: %s", e)

        # Stop daemon process
        self.stop_daemon()

        self.daemon_running = False
        self.logger.info("Messaging daemon service stopped")

    def stop_daemon(self):
        """Stop the daemon process."""
        if self.daemon_process:
            try:
                self.logger.info("Terminating daemon process...")
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=10)
                self.logger.info("Daemon process terminated")
            except subprocess.TimeoutExpired:
                self.logger.warning("Daemon didn't terminate, killing...")
                self.daemon_process.kill()
                self.daemon_process.wait()
                self.logger.warning("Daemon process killed")
            except Exception as e:
                self.logger.error("Error stopping daemon: %s", e)
            finally:
                self.daemon_process = None

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
    daemon = MessagingDaemonService(db, logger=logger)

    def signal_handler(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        daemon.stop()
        sys.exit(0)

    signal_module.signal(signal_module.SIGINT, signal_handler)
    signal_module.signal(signal_module.SIGTERM, signal_handler)

    try:
        daemon.start()

        logger.info("Daemon service running, press Ctrl+C to stop")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        daemon.stop()


if __name__ == "__main__":
    main()