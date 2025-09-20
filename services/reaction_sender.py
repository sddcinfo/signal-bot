#!/usr/bin/env python3
"""
Reaction Sender Service

Sends reactions by temporarily stopping the daemon, sending the reaction,
and restarting the daemon. This works around the JSON-RPC bug.
"""
import os
import time
import subprocess
import threading
import queue
from typing import Optional, Tuple
from dataclasses import dataclass
from utils.logging import get_logger


@dataclass
class ReactionRequest:
    """A pending reaction to send."""
    group_id: str
    target_timestamp: int
    target_author: str
    emoji: str
    retry_count: int = 0


class ReactionSender:
    """Handles sending reactions through a separate queue."""

    def __init__(self, signal_cli_path: str, bot_phone: str, logger: Optional[logging.Logger] = None):
        """Initialize the reaction sender."""
        self.signal_cli_path = signal_cli_path
        self.bot_phone = bot_phone
        self.logger = logger or get_logger(__name__)
        self.reaction_queue = queue.Queue()
        self.sender_thread = None
        self.shutdown_event = threading.Event()
        self.pause_daemon_callback = None
        self.resume_daemon_callback = None

    def set_daemon_callbacks(self, pause_func, resume_func):
        """Set callbacks for pausing/resuming the daemon."""
        self.pause_daemon_callback = pause_func
        self.resume_daemon_callback = resume_func

    def queue_reaction(self, group_id: str, target_timestamp: int, target_author: str, emoji: str) -> bool:
        """Queue a reaction to be sent."""
        request = ReactionRequest(
            group_id=group_id,
            target_timestamp=target_timestamp,
            target_author=target_author,
            emoji=emoji
        )
        self.reaction_queue.put(request)
        self.logger.info(f"Queued reaction {emoji} for sending")
        return True

    def _send_reaction_cli(self, request: ReactionRequest) -> bool:
        """Send a reaction using the CLI."""
        try:
            cmd = [
                self.signal_cli_path,
                '-a', self.bot_phone,
                'sendReaction',
                '-g', request.group_id,
                '-e', request.emoji,
                '--target-author', request.target_author,
                '--target-timestamp', str(request.target_timestamp)
            ]

            self.logger.debug(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"✅ Reaction {request.emoji} sent successfully")
                return True
            else:
                self.logger.error(f"Failed to send reaction: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Reaction send timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error sending reaction: {e}")
            return False

    def _process_reactions(self):
        """Process queued reactions in batches."""
        self.logger.info("Starting reaction sender thread")
        batch_size = 5
        batch_wait_time = 2.0  # seconds

        while not self.shutdown_event.is_set():
            try:
                # Collect reactions for batch processing
                reactions_to_send = []
                deadline = time.time() + batch_wait_time

                while time.time() < deadline and len(reactions_to_send) < batch_size:
                    try:
                        timeout = max(0.1, deadline - time.time())
                        request = self.reaction_queue.get(timeout=timeout)
                        reactions_to_send.append(request)
                    except queue.Empty:
                        break

                if not reactions_to_send:
                    continue

                self.logger.info(f"Processing batch of {len(reactions_to_send)} reactions")

                # Pause daemon if callbacks are set
                daemon_was_paused = False
                if self.pause_daemon_callback:
                    try:
                        self.logger.info("Pausing daemon for reaction sending")
                        self.pause_daemon_callback()
                        daemon_was_paused = True
                        time.sleep(0.5)  # Give daemon time to release lock
                    except Exception as e:
                        self.logger.error(f"Failed to pause daemon: {e}")

                # Send reactions
                for request in reactions_to_send:
                    success = self._send_reaction_cli(request)
                    if not success and request.retry_count < 2:
                        request.retry_count += 1
                        self.reaction_queue.put(request)
                        self.logger.info(f"Requeueing failed reaction (attempt {request.retry_count + 1})")

                # Resume daemon if it was paused
                if daemon_was_paused and self.resume_daemon_callback:
                    try:
                        time.sleep(0.5)  # Brief pause before resuming
                        self.logger.info("Resuming daemon after reactions")
                        self.resume_daemon_callback()
                    except Exception as e:
                        self.logger.error(f"Failed to resume daemon: {e}")

            except Exception as e:
                self.logger.error(f"Error in reaction processor: {e}")
                time.sleep(1)

        self.logger.info("Reaction sender thread stopped")

    def start(self):
        """Start the reaction sender thread."""
        if self.sender_thread and self.sender_thread.is_alive():
            self.logger.warning("Reaction sender already running")
            return

        self.shutdown_event.clear()
        self.sender_thread = threading.Thread(
            target=self._process_reactions,
            name="ReactionSender",
            daemon=True
        )
        self.sender_thread.start()
        self.logger.info("Reaction sender started")

    def stop(self):
        """Stop the reaction sender thread."""
        self.logger.info("Stopping reaction sender")
        self.shutdown_event.set()

        if self.sender_thread:
            self.sender_thread.join(timeout=5)
            if self.sender_thread.is_alive():
                self.logger.warning("Reaction sender thread didn't stop cleanly")

        # Process any remaining reactions
        remaining = []
        while not self.reaction_queue.empty():
            try:
                remaining.append(self.reaction_queue.get_nowait())
            except queue.Empty:
                break

        if remaining:
            self.logger.info(f"Dropped {len(remaining)} unsent reactions")

        self.logger.info("Reaction sender stopped")