"""
Message Polling Service for Signal Bot

Handles receiving messages from Signal CLI and processing them according to
the UUID-first architecture with proper group monitoring.
"""
import json
import subprocess
import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from models.database import DatabaseManager


class MessagingService:
    """Service for handling Signal message polling and reactions."""

    def __init__(self, db: DatabaseManager, signal_cli_path: str = "/usr/local/bin/signal-cli",
                 logger: Optional[logging.Logger] = None):
        """Initialize messaging service."""
        self.db = db
        self.signal_cli_path = signal_cli_path
        self.logger = logger or logging.getLogger(__name__)

        # Get bot phone number from database
        self.bot_phone = self.db.get_config('bot_phone_number')
        if not self.bot_phone:
            raise ValueError("Bot not configured - no phone number found")

    def receive_messages(self, timeout_seconds: int = 5) -> List[Dict[str, Any]]:
        """
        Poll for new messages using signal-cli receive with immediate return.

        Args:
            timeout_seconds: Not used anymore - kept for compatibility

        Returns:
            List of message dictionaries with parsed envelope data
        """
        try:
            cmd = [
                self.signal_cli_path,
                "-a", self.bot_phone,
                "--output=json",
                "receive"
            ]

            self.logger.debug("Polling for messages (non-blocking)")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                self.logger.warning("signal-cli receive failed with code %d", result.returncode)
                if result.stderr:
                    self.logger.warning("signal-cli receive stderr: %s", result.stderr.strip())
                if result.stdout:
                    self.logger.warning("signal-cli receive stdout: %s", result.stdout.strip())
                return []

            if not result.stdout.strip():
                self.logger.debug("No messages available")
                return []
            else:
                self.logger.debug("Signal-cli output received: %s", result.stdout.strip()[:200])

            # Parse JSON output - signal-cli returns one JSON object per line
            messages = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        envelope = json.loads(line)
                        messages.append(envelope)
                    except json.JSONDecodeError as e:
                        self.logger.warning("Failed to parse JSON line: %s - %s", line, e)

            return messages

        except subprocess.TimeoutExpired:
            self.logger.debug("Message polling timeout after %ds", timeout_seconds)
            return []
        except Exception as e:
            self.logger.error("Error receiving messages: %s", e)
            return []

    def process_message(self, envelope: Dict[str, Any]) -> bool:
        """
        Process a single message envelope from signal-cli.

        Args:
            envelope: JSON envelope from signal-cli receive

        Returns:
            True if message was processed successfully
        """
        try:
            # Extract message data from envelope
            timestamp = envelope.get('envelope', {}).get('timestamp')
            if not timestamp:
                self.logger.debug("Envelope missing timestamp, skipping")
                return False

            # Check if this is a data message or sync message with data
            envelope_data = envelope.get('envelope', {})
            data_message = envelope_data.get('dataMessage')

            # Track if this is a sync message (sent by us)
            is_sync_message = False
            sync_destination = None

            # If no direct dataMessage, check for sync message containing sent message
            if not data_message:
                sync_message = envelope_data.get('syncMessage', {})
                if sync_message:
                    self.logger.debug("Found sync message with keys: %s", list(sync_message.keys()))
                sent_message = sync_message.get('sentMessage', {})
                data_message = sent_message.get('message')

                # If it's a sync message, we need to get the destination info
                if data_message and sent_message:
                    is_sync_message = True
                    sync_destination = sent_message.get('destinationUuid') or sent_message.get('destination')
                    # For sync messages, we are the sender
                    source_uuid = self.db.get_config('bot_uuid')
                    if not source_uuid:
                        # Try to get UUID from phone number
                        bot_user = self.db.get_user_by_phone(self.bot_phone)
                        if bot_user:
                            source_uuid = bot_user.uuid
                            # Save bot UUID for future use
                            self.db.set_config('bot_uuid', source_uuid)
                        else:
                            # Get the source UUID from the envelope (this is our UUID)
                            source_uuid = envelope_data.get('sourceUuid')
                            if source_uuid:
                                # Create user entry for ourselves and save UUID
                                self.db.upsert_user(source_uuid, self.bot_phone)
                                self.db.set_config('bot_uuid', source_uuid)
                    self.logger.info("SYNC MESSAGE: Processing message we sent to destination %s, message: %s",
                                    sync_destination[:8] if sync_destination else "unknown",
                                    str(data_message)[:100])
                elif sync_message:
                    self.logger.debug("Found sync message but no sent message data. Keys: %s", list(sync_message.keys()))
                    return False

            if not data_message:
                # Log envelope structure for debugging
                envelope_keys = list(envelope_data.keys())
                self.logger.debug("Not a data message, skipping. Envelope keys: %s", envelope_keys)
                return False

            # Get sender UUID - for regular messages from envelope, for sync messages we already set it
            if not is_sync_message:
                source_uuid = envelope_data.get('sourceUuid')
                if not source_uuid:
                    self.logger.debug("Message missing source UUID, skipping")
                    return False

            # Check if this is a group message
            # Handle different data_message formats
            if isinstance(data_message, str):
                # If data_message is just the text content, we need to get group info from envelope
                message_text = data_message
                # Try to find group info in the envelope itself
                group_info = envelope_data.get('groupInfo') or envelope_data.get('groupV2')

                if not group_info and is_sync_message:
                    # For sync messages, check the sentMessage for group info
                    sync_message = envelope_data.get('syncMessage', {})
                    sent_message = sync_message.get('sentMessage', {})
                    group_info = sent_message.get('groupInfo') or sent_message.get('groupV2')
                    if group_info:
                        self.logger.debug("Found group info in sync message for string message: %s",
                                        group_info.get('groupId', '')[:8] if group_info.get('groupId') else "unknown")

                if not group_info:
                    self.logger.debug("String message but no group info in envelope: %s", message_text[:50] if message_text else "(empty)")
                    # This might be a direct message, not a group message
                    return False

                self.logger.debug("Processing string message: %s", message_text[:50] if message_text else "(empty)")
            else:
                # Normal dict format
                message_text = data_message.get('message', '')
                group_info = data_message.get('groupInfo') or data_message.get('groupV2')

                # Check for other message types if no text
                if not message_text:
                    if data_message.get('attachments'):
                        attachments = data_message.get('attachments', [])
                        attachment_details = []
                        for att in attachments:
                            if isinstance(att, dict):
                                filename = att.get('filename', 'unknown')
                                content_type = att.get('contentType', 'unknown')
                                size = att.get('size', 0)
                                attachment_details.append(f"{filename} ({content_type}, {size} bytes)")
                            else:
                                attachment_details.append(str(att))
                        if attachment_details:
                            message_text = f"[Attachments: {', '.join(attachment_details)}]"
                        else:
                            message_text = f"[Attachment: {len(attachments)} file(s)]"
                    elif data_message.get('sticker'):
                        sticker = data_message.get('sticker', {})
                        pack_id = sticker.get('packId', 'unknown')
                        sticker_id = sticker.get('stickerId', 'unknown')
                        message_text = f"[Sticker from pack {pack_id[:8]}... id: {sticker_id}]"
                    elif data_message.get('reaction'):
                        # This is a reaction, not a message - skip it
                        reaction_info = data_message.get('reaction', {})
                        self.logger.debug("Skipping reaction from %s: %s to message %s",
                                        source_uuid[:8],
                                        reaction_info.get('emoji', 'unknown'),
                                        reaction_info.get('targetTimestamp', 'unknown'))
                        return False
                    elif data_message.get('remoteDelete'):
                        message_text = "[Message deleted]"
                    else:
                        # Log what type of message this is for debugging
                        message_keys = list(data_message.keys()) if isinstance(data_message, dict) else []
                        self.logger.debug("Message from %s with no text has keys: %s", source_uuid[:8], message_keys)
                        # Set a descriptive message for unknown types
                        if message_keys:
                            message_text = f"[Unknown message type with keys: {', '.join(message_keys)}]"
                        else:
                            message_text = "[Empty message]"

            # For sync messages, we need to check if it was sent to a group
            if not group_info and is_sync_message:
                # For sync messages, the group info might be in the sentMessage
                sync_message = envelope_data.get('syncMessage', {})
                sent_message = sync_message.get('sentMessage', {})

                # First check if there's explicit group info in the sent message
                sent_group_info = sent_message.get('groupInfo') or sent_message.get('groupV2')
                if sent_group_info:
                    group_info = sent_group_info
                    self.logger.debug("Found group info in sync message: %s",
                                    group_info.get('groupId', '')[:8] if group_info.get('groupId') else "unknown")
                elif sync_destination:
                    # Check if destination looks like a group ID (base64 encoded)
                    # Group IDs are typically longer base64 strings
                    if len(sync_destination) > 20 and '=' in sync_destination:
                        group_info = {'groupId': sync_destination}
                        self.logger.debug("Using sync message destination as group ID: %s", sync_destination[:8])
                    else:
                        self.logger.debug("Sync message appears to be a direct message to %s", sync_destination[:8])

            if not group_info:
                self.logger.debug("Not a group message, skipping. Data message keys: %s", list(data_message.keys()))
                return False

            # Extract group ID (handle both v1 and v2 groups)
            group_id = group_info.get('groupId')
            if not group_id:
                self.logger.debug("Group message missing group ID, skipping")
                return False

            # Check if we've already processed this message
            if self.db.is_message_processed(timestamp, group_id, source_uuid):
                self.logger.debug("Message already processed: %s from %s in %s",
                                timestamp, source_uuid[:8], group_id[:8])
                return True

            # Check if this group is monitored
            if not self.db.is_group_monitored(group_id):
                self.logger.debug("Group %s not monitored, marking processed but not reacting",
                                group_id[:8])
                # Still add user to group membership and upsert user
                self.db.upsert_user(source_uuid)
                self.db.add_group_member(group_id, source_uuid)
                self.db.mark_message_processed(timestamp, group_id, source_uuid, message_text)
                return True

            # Log the message details - don't shorten
            if message_text:
                display_text = message_text
            else:
                display_text = "(no text content)"
            self.logger.info("Processing message from %s in group %s: %s",
                           source_uuid[:8], group_id[:8], display_text)

            # Upsert user information
            self.db.upsert_user(source_uuid)

            # Add user to group membership (if not already there)
            self.db.add_group_member(group_id, source_uuid)

            # Mark message as processed with text
            message_id = self.db.mark_message_processed(timestamp, group_id, source_uuid, message_text)

            # Download and store attachments if present
            if isinstance(data_message, dict) and data_message.get('attachments'):
                self._download_and_store_attachments(data_message['attachments'], message_id, timestamp)

            # Check if user has reactions configured and send reaction
            user_reactions = self.db.get_user_reactions(source_uuid)
            if user_reactions and user_reactions.emojis and user_reactions.is_active:
                emoji = self._select_emoji(user_reactions.emojis, user_reactions.reaction_mode)
                if emoji:
                    success = self.send_reaction(group_id, timestamp, source_uuid, emoji)
                    if success:
                        self.logger.info("Sent reaction %s to message from %s", emoji, source_uuid[:8])
                    else:
                        self.logger.warning("Failed to send reaction to message from %s", source_uuid[:8])

            return True

        except Exception as e:
            self.logger.error("Error processing message envelope: %s", e, exc_info=True)
            return False

    def send_reaction(self, group_id: str, target_timestamp: int, target_author: str, emoji: str) -> bool:
        """
        Send a reaction to a message using signal-cli.

        Args:
            group_id: Group ID where the message was sent
            target_timestamp: Timestamp of the message to react to
            target_author: UUID of the message author
            emoji: Emoji to send as reaction

        Returns:
            True if reaction was sent successfully
        """
        try:
            cmd = [
                self.signal_cli_path,
                "-a", self.bot_phone,
                "sendReaction",
                "-g", group_id,
                "--target-timestamp", str(target_timestamp),
                "--target-author", target_author,
                "-e", emoji
            ]

            self.logger.debug("Sending reaction %s to message %s from %s",
                            emoji, target_timestamp, target_author[:8])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return True
            else:
                self.logger.warning("Failed to send reaction: %s", result.stderr.strip() if result.stderr else "Unknown error")
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning("Reaction send timeout")
            return False
        except Exception as e:
            self.logger.error("Error sending reaction: %s", e)
            return False

    def _download_and_store_attachments(self, attachments, message_id, timestamp):
        """Download and store attachments for a message."""
        for att in attachments:
            try:
                if not isinstance(att, dict):
                    continue

                attachment_id = att.get('id')
                filename = att.get('filename') or f"attachment_{timestamp}_{attachment_id}"
                content_type = att.get('contentType', 'unknown')
                file_size = att.get('size', 0)

                if not attachment_id:
                    self.logger.warning("Attachment missing ID, skipping")
                    continue

                # Look for attachment in signal-cli attachments directory
                import os
                import glob

                attachments_dir = os.path.expanduser("~/.local/share/signal-cli/attachments")
                file_data = None
                actual_filename = filename

                # Try to find the attachment file
                potential_paths = [
                    os.path.join(attachments_dir, attachment_id),
                    os.path.join(attachments_dir, f"{attachment_id}*"),
                ]

                # Also search for files containing the attachment_id
                search_patterns = [
                    os.path.join(attachments_dir, f"*{attachment_id}*"),
                    os.path.join(attachments_dir, filename) if filename else None
                ]

                found_file = None
                for pattern in search_patterns:
                    if pattern:
                        matches = glob.glob(pattern)
                        if matches:
                            found_file = matches[0]  # Take first match
                            break

                if found_file and os.path.exists(found_file):
                    try:
                        with open(found_file, 'rb') as f:
                            file_data = f.read()
                        actual_filename = os.path.basename(found_file)

                        # Store in database
                        with self.db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO attachments (
                                    message_id, attachment_id, filename, content_type,
                                    file_size, file_data
                                ) VALUES (?, ?, ?, ?, ?, ?)
                            """, (message_id, attachment_id, actual_filename, content_type, file_size, file_data))

                        self.logger.info("Found and stored attachment: %s (%s, %d bytes)", actual_filename, content_type, len(file_data))

                    except Exception as read_error:
                        self.logger.error("Error reading attachment file %s: %s", found_file, read_error)

                else:
                    self.logger.warning("Attachment file not found for ID: %s (searched in %s)", attachment_id, attachments_dir)

            except Exception as e:
                self.logger.error("Error downloading attachment: %s", e)

    def _select_emoji(self, emojis: List[str], mode: str) -> Optional[str]:
        """
        Select an emoji based on the reaction mode.

        Args:
            emojis: List of available emojis
            mode: Selection mode ('random', 'sequential', 'ai')

        Returns:
            Selected emoji or None
        """
        if not emojis:
            return None

        if mode == 'random':
            return random.choice(emojis)
        elif mode == 'sequential':
            # For sequential, we'd need to track position per user
            # For now, just use random as a fallback
            return random.choice(emojis)
        elif mode == 'ai':
            # AI selection would analyze message content
            # For now, just use random as a fallback
            return random.choice(emojis)
        else:
            return random.choice(emojis)

    def poll_and_process_messages(self, timeout_seconds: int = 15) -> int:
        """
        Poll for messages and process them all.

        Args:
            timeout_seconds: How long to wait for messages

        Returns:
            Number of messages processed
        """
        try:
            messages = self.receive_messages(timeout_seconds)
            processed_count = 0

            for envelope in messages:
                if self.process_message(envelope):
                    processed_count += 1

            if processed_count > 0:
                self.logger.info("Processed %d messages", processed_count)

            return processed_count

        except Exception as e:
            self.logger.error("Error in poll and process cycle: %s", e)
            return 0

    def sync_group_memberships(self) -> bool:
        """
        Sync group memberships from Signal's listGroups command.

        Returns:
            True if sync was successful
        """
        try:
            cmd = [
                self.signal_cli_path,
                "-a", self.bot_phone,
                "listGroups",
                "-d"  # detailed output with member lists
            ]

            self.logger.info("Syncing group memberships from Signal...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                self.logger.error("Failed to get group list: %s", result.stderr.strip() if result.stderr else "Unknown error")
                return False

            # Parse the output to extract group memberships
            lines = result.stdout.strip().split('\n')
            synced_groups = 0
            synced_members = 0

            for line in lines:
                if not line.strip() or not line.startswith('Id: '):
                    continue

                try:
                    # Parse group information from line
                    # Format: Id: <id> Name: <name> Description: <desc> Active: <bool> Blocked: <bool> Members: [<members>] ...
                    parts = line.split(' Members: ')
                    if len(parts) < 2:
                        continue

                    # Extract group ID
                    id_part = parts[0]
                    if not id_part.startswith('Id: '):
                        continue

                    # Find group ID (between "Id: " and " Name:")
                    id_start = id_part.find('Id: ') + 4
                    name_start = id_part.find(' Name: ')
                    if name_start == -1:
                        continue

                    group_id = id_part[id_start:name_start]

                    # Extract members list (between [ and ])
                    members_part = parts[1]
                    bracket_start = members_part.find('[')
                    bracket_end = members_part.find(']')
                    if bracket_start == -1 or bracket_end == -1:
                        continue

                    members_str = members_part[bracket_start+1:bracket_end]
                    if not members_str.strip():
                        continue

                    # Parse member phone numbers and UUIDs
                    members = [m.strip() for m in members_str.split(',')]

                    synced_groups += 1
                    group_member_count = 0

                    for member in members:
                        if not member:
                            continue

                        # Try to find user by phone number or UUID
                        user_uuid = None

                        if member.startswith('+'):
                            # Phone number - look up UUID
                            user_uuid = self.db.get_user_uuid_by_phone(member)
                            if not user_uuid:
                                # Create user entry if not exists
                                user = self.db.upsert_user(uuid=None, phone_number=member)
                                user_uuid = user.uuid
                        else:
                            # Already a UUID - validate it exists
                            if self.db.get_user_by_uuid(member):
                                user_uuid = member
                            else:
                                # Create user entry for unknown UUID
                                user = self.db.upsert_user(uuid=member)
                                user_uuid = user.uuid

                        if user_uuid:
                            # Add to group membership
                            self.db.add_group_member(group_id, user_uuid)
                            group_member_count += 1

                    if group_member_count > 0:
                        synced_members += group_member_count
                        self.logger.debug("Synced %d members for group %s", group_member_count, group_id[:8])

                except Exception as e:
                    self.logger.warning("Error parsing group line: %s - %s", line[:100], e)
                    continue

            self.logger.info("Group membership sync complete: %d groups, %d total members", synced_groups, synced_members)
            return True

        except subprocess.TimeoutExpired:
            self.logger.error("Group membership sync timeout")
            return False
        except Exception as e:
            self.logger.error("Error syncing group memberships: %s", e)
            return False