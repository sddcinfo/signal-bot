#!/usr/bin/env python3
"""
Daemon-native message processor

Processes messages entirely through the daemon interface without mixing subprocess calls.
"""
import logging
import random
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.database import DatabaseManager


class DaemonMessageProcessor:
    """Process messages entirely through daemon interface."""

    def __init__(self, db: DatabaseManager, send_reaction_func, logger: Optional[logging.Logger] = None):
        """Initialize the processor.

        Args:
            db: Database manager
            send_reaction_func: Function to send reactions via daemon
            logger: Logger instance
        """
        self.db = db
        self.send_reaction = send_reaction_func
        self.logger = logger or logging.getLogger(__name__)

    def process_envelope(self, envelope: Dict[str, Any]) -> bool:
        """Process a message envelope from the daemon.

        Args:
            envelope: Message envelope from signal-cli daemon

        Returns:
            True if processed successfully
        """
        try:
            # The envelope might be wrapped or not - handle both
            if 'envelope' in envelope:
                actual_envelope = envelope['envelope']
            else:
                actual_envelope = envelope

            # Extract basic info
            timestamp = actual_envelope.get('timestamp')
            source_uuid = actual_envelope.get('sourceUuid')
            source_number = actual_envelope.get('sourceNumber')

            self.logger.info(f"Processing envelope: timestamp={timestamp}, source_uuid={source_uuid[:8] if source_uuid else None}")

            if not timestamp:
                self.logger.debug("Envelope missing timestamp, skipping")
                return True  # Not a failure, just incomplete

            # Handle data messages
            data_message = actual_envelope.get('dataMessage')
            if not data_message:
                # Check for sync messages (messages we sent)
                sync_message = actual_envelope.get('syncMessage', {})
                sent_message = sync_message.get('sentMessage', {})
                data_message = sent_message.get('message')

                if data_message:
                    # This is a message we sent - skip processing
                    self.logger.debug("Skipping sync message (sent by us)")
                    return True

                self.logger.debug("Not a data message (might be reaction, typing, etc.), skipping gracefully")
                return True  # Not a failure, just a different message type

            # Extract message content
            if isinstance(data_message, str):
                message_text = data_message
                group_info = None
            else:
                message_text = data_message.get('message', '')
                group_info = data_message.get('groupInfo') or data_message.get('groupV2')

            # Only process group messages
            if not group_info:
                self.logger.debug("Not a group message, skipping gracefully")
                return True  # Not a failure, just not relevant

            group_id = group_info.get('groupId')
            if not group_id:
                self.logger.warning("No group ID found in group_info")
                return False

            # Ensure we have the sender info
            if not source_uuid:
                self.logger.debug("No source UUID, skipping message")
                return True  # Not a failure for system messages

            self.logger.info(f"Message from {source_uuid[:8]} in group {group_id[:8]}: {message_text[:50] if message_text else '(no text)'}")

            # Check if group is monitored
            is_monitored = self._is_group_monitored(group_id)
            self.logger.info(f"Group {group_id[:8]} monitored status: {is_monitored}")
            if not is_monitored:
                self.logger.info(f"Group {group_id[:8]} not monitored, skipping reaction but storing message")
                # Still store the message even if not monitored
                pass  # Continue to store

            # Store the message
            message_id = self._store_message(
                source_uuid=source_uuid,
                group_id=group_id,
                message_text=message_text,
                timestamp=timestamp
            )

            if not message_id:
                self.logger.warning("Failed to store message")
                return False

            self.logger.info(f"Stored message {message_id} from {source_uuid[:8]} in group {group_id[:8]}: {message_text[:50] if message_text else '(no text)'}")

            # Check if we should react (only if group is monitored)
            if is_monitored and self._should_react(source_uuid, group_id):
                emoji = self._select_reaction(source_uuid)
                self.logger.info(f"Selected reaction emoji: {emoji}")
                if emoji:
                    self.logger.info(f"Attempting to send reaction {emoji} to timestamp {timestamp} from {source_uuid}")
                    success = self.send_reaction(
                        group_id=group_id,
                        target_timestamp=timestamp,
                        target_author=source_uuid,
                        emoji=emoji
                    )

                    if success:
                        self.logger.info(f"✅ Sent reaction {emoji} to message from {source_uuid[:8]}")
                    else:
                        self.logger.warning(f"❌ Failed to send reaction to message from {source_uuid[:8]}")
            elif not is_monitored:
                self.logger.info("Not sending reaction - group not monitored")
            else:
                self.logger.info("Not sending reaction - user not configured or frequency check failed")

            return True

        except Exception as e:
            self.logger.error(f"Error processing envelope: {e}", exc_info=True)
            import traceback
            self.logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False

    def _is_group_monitored(self, group_id: str) -> bool:
        """Check if a group is monitored."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT is_monitored FROM groups WHERE group_id = ?",
                    (group_id,)
                )
                result = cursor.fetchone()
                return bool(result and result[0])
        except Exception as e:
            self.logger.error(f"Error checking group monitoring: {e}")
            return False

    def _store_message(self, source_uuid: str, group_id: str, message_text: str, timestamp: int) -> Optional[int]:
        """Store a message in the database."""
        try:
            # Ensure user exists
            self.db.upsert_user(source_uuid, None)

            # Store message
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (sender_uuid, group_id, message_text, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (source_uuid, group_id, message_text, timestamp))

                message_id = cursor.lastrowid
                conn.commit()
                return message_id

        except Exception as e:
            self.logger.error(f"Error storing message: {e}")
            return None

    def _should_react(self, source_uuid: str, group_id: str) -> bool:
        """Check if we should react to a message from this user."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Check if user has reactions configured and is active
                cursor.execute("""
                    SELECT emojis, reaction_mode, is_active
                    FROM user_reactions
                    WHERE uuid = ?
                """, (source_uuid,))

                result = cursor.fetchone()
                if not result:
                    self.logger.info(f"No reaction config for user {source_uuid[:8]}")
                    return False

                emojis, mode, is_active = result

                if not is_active:
                    self.logger.info(f"Reactions disabled for user {source_uuid[:8]}")
                    return False

                if not emojis:
                    self.logger.info(f"No emojis configured for user {source_uuid[:8]}")
                    return False

                # For now, always react if configured and active
                # Could add random chance here
                return True

        except Exception as e:
            self.logger.error(f"Error checking if should react: {e}")
            return False

    def _select_reaction(self, source_uuid: str) -> Optional[str]:
        """Select a reaction emoji for a user."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Get user's configured emojis (stored as comma-separated string)
                cursor.execute("""
                    SELECT emojis, reaction_mode
                    FROM user_reactions
                    WHERE uuid = ? AND is_active = 1
                """, (source_uuid,))

                result = cursor.fetchone()
                if not result:
                    return None

                emojis_str, mode = result
                if not emojis_str:
                    return None

                # Parse emojis (stored as JSON array)
                import json
                try:
                    emojis = json.loads(emojis_str)
                except:
                    # Fallback to comma-separated if not JSON
                    emojis = [e.strip() for e in emojis_str.split(',') if e.strip()]

                if not emojis:
                    return None

                # Select based on mode
                if mode == 'random' or mode is None:
                    selected = random.choice(emojis)
                else:
                    # For sequential or other modes, just use random for now
                    selected = random.choice(emojis)

                self.logger.info(f"Selected emoji '{selected}' from {emojis} for user {source_uuid[:8]}")
                return selected

        except Exception as e:
            self.logger.error(f"Error selecting reaction: {e}")
            return None