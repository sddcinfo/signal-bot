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
from utils.logging import get_logger


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
        self.logger = logger or get_logger(__name__)

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

            self.logger.info(f"Processing envelope: timestamp={timestamp}, source_uuid={source_uuid}")

            if not timestamp:
                self.logger.debug("Envelope missing timestamp, skipping")
                return True  # Not a failure, just incomplete

            # Log envelope structure to debug bot messages
            self.logger.debug(f"Envelope keys: {list(actual_envelope.keys())}")

            # Handle data messages
            data_message = actual_envelope.get('dataMessage')
            is_sync_message = False
            sync_group_info = None

            if not data_message:
                # Check for sync messages (messages we sent)
                sync_message = actual_envelope.get('syncMessage', {})
                self.logger.debug(f"Sync message keys: {list(sync_message.keys())}")

                sent_message = sync_message.get('sentMessage', {})
                if sent_message:
                    self.logger.debug(f"Sent message keys: {list(sent_message.keys())}")

                # For sync messages, the message content might be in 'message' or we just use the sent message itself
                data_message = sent_message.get('message') if sent_message else None

                # For sync messages, group info, attachments, stickers, and mentions are at the sent message level
                sync_group_info = sent_message.get('groupInfo') or sent_message.get('groupV2') if sent_message else None
                sync_attachments = sent_message.get('attachments', []) if sent_message else []
                sync_sticker = sent_message.get('sticker') if sent_message else None
                sync_mentions = sent_message.get('mentions', []) if sent_message else []

                if sync_group_info:
                    self.logger.debug(f"Sync message group info found: {sync_group_info.get('groupId', 'unknown')}")
                if sync_attachments:
                    self.logger.debug(f"Sync message has {len(sync_attachments)} attachment(s)")
                if sync_sticker:
                    self.logger.debug(f"Sync message has sticker: packId={sync_sticker.get('packId')}, stickerId={sync_sticker.get('stickerId')}")

                # Process sync message if it has content, attachments, or stickers
                if sent_message and (data_message or sync_attachments or sync_sticker):
                    # This is a message we sent - but we want to process it too!
                    self.logger.info("Processing sync message (sent by us)")
                    is_sync_message = True

                    # For sync messages with only attachments or stickers, create a proper data message
                    if not data_message:
                        if sync_attachments:
                            data_message = {'attachments': sync_attachments}  # Create data message with attachments
                        elif sync_sticker:
                            data_message = {'sticker': sync_sticker}  # Create data message with sticker

                    # Extract the actual source UUID from the sent message
                    if not source_uuid:
                        # For sync messages, we need to get our own UUID
                        source_uuid = '03f02292-cc2f-42c6-a271-8ee6abe4755a'
                        self.logger.info(f"Using bot UUID for sync message: {source_uuid}")
                    # Continue processing instead of returning
                elif sync_message:
                    self.logger.debug(f"Sync message but no sent message data")
                    return True

                if not data_message:
                    self.logger.debug("Not a data message (might be reaction, typing, etc.), skipping gracefully")
                    return True  # Not a failure, just a different message type

            # Extract message content and attachments
            if isinstance(data_message, str):
                message_text = data_message
                group_info = sync_group_info if is_sync_message else None
                attachments = []
                mentions = sync_mentions if is_sync_message else []
            else:
                # Debug: log available keys in data_message
                self.logger.debug(f"data_message keys: {list(data_message.keys())}")

                message_text = data_message.get('message', '')
                # Extract mentions from the data message (or use sync mentions if it's a sync message)
                if is_sync_message and sync_mentions:
                    mentions = sync_mentions
                    if mentions:
                        self.logger.info(f"Found {len(mentions)} mentions in sync message: {mentions}")
                else:
                    mentions = data_message.get('mentions', [])
                    if mentions:
                        self.logger.info(f"Found {len(mentions)} mentions in message: {mentions}")

                # Check if message contains mention placeholder but no mentions data
                if not mentions and '\ufffc' in message_text:
                    self.logger.debug(f"Message contains mention placeholder but no mentions data found")

                # For sync messages, use the sync_group_info, otherwise get from data_message
                if is_sync_message:
                    group_info = sync_group_info
                else:
                    group_info = data_message.get('groupInfo') or data_message.get('groupV2')

                # Extract attachments (images, gifs, stickers, etc.)
                # For sync messages, attachments might already be in sync_attachments
                if is_sync_message and sync_attachments:
                    attachments = sync_attachments
                else:
                    attachments = data_message.get('attachments', [])

                # Check for stickers
                sticker = data_message.get('sticker')
                if sticker:
                    # Add sticker as special attachment
                    attachments.append({'type': 'sticker', 'data': sticker})

                # Log attachment info and add to message text if no text provided
                if attachments:
                    self.logger.info(f"Message contains {len(attachments)} attachment(s)")
                    # Debug log attachment details
                    for i, att in enumerate(attachments):
                        if isinstance(att, dict):
                            self.logger.debug(f"Attachment {i}: type={att.get('contentType')}, filename={att.get('filename')}, size={att.get('size')}")

                    # If there's no message text, create descriptive text for attachments
                    if not message_text:
                        attachment_types = []
                        for att in attachments:
                            if isinstance(att, dict):
                                if att.get('type') == 'sticker':
                                    attachment_types.append('[Sticker]')
                                elif att.get('contentType', '').startswith('image'):
                                    attachment_types.append('[Image]')
                                elif att.get('contentType', '').startswith('video'):
                                    attachment_types.append('[Video]')
                                else:
                                    attachment_types.append('[Attachment]')
                        if attachment_types:
                            message_text = ' '.join(attachment_types)
                    else:
                        # Append attachment info to existing message
                        attachment_types = []
                        for att in attachments:
                            if isinstance(att, dict):
                                if att.get('type') == 'sticker':
                                    attachment_types.append('[Sticker]')
                                elif att.get('contentType', '').startswith('image'):
                                    attachment_types.append('[Image]')
                                elif att.get('contentType', '').startswith('video'):
                                    attachment_types.append('[Video]')
                                else:
                                    attachment_types.append('[Attachment]')
                        if attachment_types:
                            message_text = f"{message_text} {' '.join(attachment_types)}"

            # Only process group messages
            if not group_info:
                self.logger.debug(f"Not a group message (is_sync={is_sync_message}), skipping gracefully")
                return True  # Not a failure, just not relevant

            self.logger.debug(f"Group info: {group_info}")

            group_id = group_info.get('groupId')
            if not group_id:
                self.logger.warning("No group ID found in group_info")
                return False

            # Ensure we have the sender info
            if not source_uuid:
                self.logger.debug("No source UUID, skipping message")
                return True  # Not a failure for system messages

            # Check if we've already processed this message (deduplication)
            if self._is_message_processed(timestamp, group_id, source_uuid):
                self.logger.debug(f"Message already processed: {timestamp} from {source_uuid} in {group_id}")
                return True

            self.logger.info(f"Message from {source_uuid} in group {group_id}: {message_text[:50] if message_text else '(no text)'}")

            # Add user to group membership (track who's in which groups)
            self._add_group_member(group_id, source_uuid)

            # Check if group is monitored
            is_monitored = self._is_group_monitored(group_id)
            self.logger.info(f"Group {group_id} monitored status: {is_monitored}")
            if not is_monitored:
                self.logger.info(f"Group {group_id} not monitored, skipping reaction but storing message")
                # Still store the message even if not monitored
                pass  # Continue to store

            # Store the message
            message_id = self._store_message(
                source_uuid=source_uuid,
                group_id=group_id,
                message_text=message_text,
                timestamp=timestamp,
                attachments=attachments,  # Pass attachments to store
                mentions=mentions  # Pass mentions to store
            )

            if not message_id:
                self.logger.warning("Failed to store message")
                return False

            self.logger.info(f"Stored message {message_id} from {source_uuid} in group {group_id}: {message_text[:50] if message_text else '(no text)'}")

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
                        self.logger.info(f"✅ Sent reaction {emoji} to message from {source_uuid}")
                    else:
                        self.logger.warning(f"❌ Failed to send reaction to message from {source_uuid}")
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

    def _store_message(self, source_uuid: str, group_id: str, message_text: str, timestamp: int, attachments: list = None, mentions: list = None) -> Optional[int]:
        """Store a message and its attachments in the database."""
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

                # Store mentions if present
                if mentions and message_id:
                    self.logger.info(f"Storing {len(mentions)} mention(s) for message {message_id}")
                    for mention in mentions:
                        if isinstance(mention, dict):
                            mentioned_uuid = mention.get('uuid')
                            mention_start = mention.get('start', 0)
                            mention_length = mention.get('length', 1)

                            if mentioned_uuid:
                                self.logger.debug(f"Storing mention: uuid={mentioned_uuid}, start={mention_start}, length={mention_length}")
                                cursor.execute("""
                                    INSERT INTO mentions (message_id, mentioned_uuid, mention_start, mention_length)
                                    VALUES (?, ?, ?, ?)
                                """, (message_id, mentioned_uuid, mention_start, mention_length))

                                # Ensure mentioned user exists in database (using same connection)
                                cursor.execute("""
                                    INSERT OR IGNORE INTO users (uuid, last_seen)
                                    VALUES (?, CURRENT_TIMESTAMP)
                                """, (mentioned_uuid,))

                # Store attachments if present
                if attachments and message_id:
                    self.logger.info(f"Storing {len(attachments)} attachment(s) for message {message_id}")
                    for i, att in enumerate(attachments):
                        if isinstance(att, dict):
                            self.logger.debug(f"Attachment {i} keys: {list(att.keys())}")
                            # Handle regular attachments
                            if att.get('type') == 'sticker':
                                # Store sticker
                                sticker_data = att.get('data', {})
                                self.logger.info(f"Storing sticker: packId={sticker_data.get('packId')}, stickerId={sticker_data.get('stickerId')}")
                                cursor.execute("""
                                    INSERT INTO attachments (message_id, content_type, pack_id, sticker_id)
                                    VALUES (?, ?, ?, ?)
                                """, (message_id, 'sticker',
                                      sticker_data.get('packId'),
                                      sticker_data.get('stickerId')))
                            else:
                                # Store regular attachment (image/video/file)
                                attachment_id = att.get('id') or att.get('attachmentId') or att.get('id')
                                filename = att.get('filename') or att.get('fileName')
                                content_type = att.get('contentType')
                                file_size = att.get('size') or att.get('fileSize')

                                self.logger.info(f"Storing attachment: id={attachment_id}, filename={filename}, type={content_type}, size={file_size}")

                                if not attachment_id:
                                    self.logger.warning(f"Attachment {i} missing ID, generating one")
                                    attachment_id = f"att_{message_id}_{i}"

                                cursor.execute("""
                                    INSERT INTO attachments (message_id, attachment_id, filename, content_type, file_size)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (message_id, attachment_id, filename, content_type, file_size))

                conn.commit()

                # After storing metadata, try to download the actual files
                if attachments and message_id:
                    for att in attachments:
                        if isinstance(att, dict):
                            self._download_attachment(att, message_id, timestamp)

                return message_id

        except Exception as e:
            self.logger.error(f"Error storing message: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
                    self.logger.info(f"No reaction config for user {source_uuid}")
                    return False

                emojis, mode, is_active = result

                if not is_active:
                    self.logger.info(f"Reactions disabled for user {source_uuid}")
                    return False

                if not emojis:
                    self.logger.info(f"No emojis configured for user {source_uuid}")
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

                self.logger.info(f"Selected emoji '{selected}' from {emojis} for user {source_uuid}")
                return selected

        except Exception as e:
            self.logger.error(f"Error selecting reaction: {e}")
            return None

    def _is_message_processed(self, timestamp: int, group_id: str, sender_uuid: str) -> bool:
        """Check if a message has already been processed."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM messages
                    WHERE timestamp = ? AND group_id = ? AND sender_uuid = ?
                """, (timestamp, group_id, sender_uuid))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            self.logger.error(f"Error checking if message processed: {e}")
            return False

    def _add_group_member(self, group_id: str, user_uuid: str) -> None:
        """Add a user to a group's membership tracking."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                # First ensure the group exists
                cursor.execute("""
                    INSERT OR IGNORE INTO groups (group_id, group_name, is_monitored)
                    VALUES (?, ?, 0)
                """, (group_id, f"Group {group_id[:8]}..."))

                # Then add the membership
                cursor.execute("""
                    INSERT OR IGNORE INTO group_members (group_id, user_uuid, joined_at)
                    VALUES (?, ?, datetime('now'))
                """, (group_id, user_uuid))

                conn.commit()
                self.logger.debug(f"Added user {user_uuid} to group {group_id} membership")
        except Exception as e:
            self.logger.error(f"Error adding group member: {e}")

    def _download_attachment(self, attachment: Dict[str, Any], message_id: int, timestamp: int) -> None:
        """Try to download and store attachment file data."""
        try:
            import os
            import glob

            is_sticker = attachment.get('type') == 'sticker'

            # For stickers, get the sticker ID from the data
            if is_sticker:
                sticker_data = attachment.get('data', {})
                attachment_id = str(sticker_data.get('stickerId', ''))  # Convert to string
                pack_id = sticker_data.get('packId')
                if not attachment_id:
                    self.logger.debug(f"Sticker missing stickerId: {sticker_data}")
                    return
            else:
                attachment_id = attachment.get('id') or attachment.get('attachmentId')
                if not attachment_id:
                    return

            filename = attachment.get('filename') or attachment.get('fileName') or f"attachment_{timestamp}_{attachment_id}"

            # Look for attachment in signal-cli attachments directory
            attachments_dir = os.path.expanduser("~/.local/share/signal-cli/attachments")

            # For stickers, prioritize sticker-specific directories over general attachments
            if is_sticker:
                # Prioritize pack-specific directory, then general sticker dirs, then attachments as last resort
                search_dirs = []
                if pack_id:
                    search_dirs.append(os.path.expanduser(f"~/.local/share/signal-cli/stickers/{pack_id}"))
                search_dirs.extend([
                    os.path.expanduser("~/.local/share/signal-cli/stickers"),
                    os.path.expanduser("~/.local/share/signal-cli/data/stickers"),
                    attachments_dir  # Last resort
                ])
            else:
                search_dirs = [attachments_dir]

            found_file = None
            self.logger.debug(f"Searching for {'sticker' if is_sticker else 'attachment'} {attachment_id} in {search_dirs}")

            for search_dir in search_dirs:
                if not os.path.exists(search_dir):
                    continue

                # For stickers in pack directories, look for exact sticker ID
                if is_sticker and pack_id and search_dir.endswith(pack_id):
                    # In pack directory, stickers are named just by their ID (0, 1, 2, etc)
                    exact_file = os.path.join(search_dir, attachment_id)
                    if os.path.exists(exact_file):
                        found_file = exact_file
                        self.logger.debug(f"Found exact sticker file: {found_file}")
                        break
                else:
                    # Try to find the attachment file with patterns
                    search_patterns = [
                        os.path.join(search_dir, attachment_id),
                        os.path.join(search_dir, f"{attachment_id}*"),
                        os.path.join(search_dir, f"*{attachment_id}*")
                    ]

                    for pattern in search_patterns:
                        matches = glob.glob(pattern)
                        if matches:
                            found_file = matches[0]
                            self.logger.debug(f"Found file: {found_file}")
                            break

                if found_file:
                    break

            if found_file and os.path.exists(found_file):
                try:
                    with open(found_file, 'rb') as f:
                        file_data = f.read()

                    # Update the attachment record with file data
                    with self.db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE attachments
                            SET file_data = ?, downloaded_at = datetime('now')
                            WHERE message_id = ? AND (attachment_id = ? OR sticker_id = ?)
                        """, (file_data, message_id, attachment_id, attachment_id))
                        conn.commit()

                    self.logger.info(f"Downloaded and stored {'sticker' if is_sticker else 'attachment'}: {os.path.basename(found_file)} ({len(file_data)} bytes)")
                except Exception as e:
                    self.logger.error(f"Error reading attachment file {found_file}: {e}")
            else:
                self.logger.debug(f"Attachment file not found for ID: {attachment_id}")

        except Exception as e:
            self.logger.error(f"Error downloading attachment: {e}")