"""
Message Summarization Service

Uses AI providers (Ollama local or Gemini external) to provide intelligent summaries
of chat messages from the last N hours. Highlights key topics, decisions, and important
information from group conversations.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .ai_provider import get_ai_response, get_ai_status


class MessageSummarizer:
    """Service for summarizing recent chat messages using AI providers."""

    def __init__(self, db_manager):
        """
        Initialize message summarizer.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

    def get_recent_messages(self, group_id: str, hours: int = 24, user_timezone: str = None, anonymize: bool = True) -> str:
        """
        Get messages from the last N hours and format them for analysis.

        Args:
            group_id: The group to analyze
            hours: Number of hours to look back
            user_timezone: User's timezone for consistent timestamp display
            anonymize: Whether to anonymize usernames (True for external AI, False for local AI)

        Returns:
            Formatted string of messages
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000)

        # Get messages from database
        messages = self.db.get_messages_by_group_with_names(group_id=group_id, limit=1000, offset=0)

        # Filter to only messages within time range
        recent_messages = []
        for msg in messages:
            if msg['timestamp'] and msg['timestamp'] >= cutoff_timestamp:
                recent_messages.append(msg)

        if not recent_messages:
            return ""

        # Sort by timestamp (oldest first for chronological order)
        recent_messages.sort(key=lambda x: x['timestamp'] or 0)

        # Format messages for analysis with privacy awareness
        formatted = []

        # Setup timezone conversion if user timezone is provided
        user_tz = None
        if user_timezone:
            try:
                import zoneinfo
                user_tz = zoneinfo.ZoneInfo(user_timezone)
            except (ImportError, Exception):
                self.logger.warning(f"Could not use timezone {user_timezone}, falling back to UTC")

        # Create sender mapping for anonymization if needed
        sender_map = {}
        sender_counter = 1

        for msg in recent_messages:
            # Format timestamp with user's timezone if available
            msg_time = datetime.fromtimestamp(msg['timestamp'] / 1000)

            if user_tz:
                # Convert to user's timezone
                from datetime import timezone as dt_timezone
                msg_time = msg_time.replace(tzinfo=dt_timezone.utc).astimezone(user_tz)

            timestamp = msg_time.strftime('%H:%M')

            # Get message text and sender
            text = msg.get('message_text', '')
            sender = msg.get('friendly_name') or msg.get('sender_uuid', 'Unknown')

            # Skip empty messages
            if not text or text.strip() == '':
                continue

            # Skip system messages
            if not sender or sender.lower() in ['system']:
                continue

            # Create display name based on anonymization setting
            if anonymize:
                # Anonymous mode for external AI
                if sender not in sender_map:
                    sender_map[sender] = f"User{sender_counter}"
                    sender_counter += 1
                display_sender = sender_map[sender]
            else:
                # Detailed mode for local AI - use real names
                display_sender = sender

            # Format message with or without sender based on privacy setting
            if anonymize:
                formatted.append(f"[{timestamp}] {text}")
            else:
                formatted.append(f"[{timestamp}] {display_sender}: {text}")

        return "\n".join(formatted)

    def summarize_messages(self, group_id: str, group_name: str, hours: int = 24, user_timezone: str = None) -> Optional[Dict[str, Any]]:
        """
        Summarize messages from the last N hours using AI provider.

        Args:
            group_id: The group to analyze
            group_name: Display name of the group
            hours: Number of hours to look back
            user_timezone: User's timezone for consistent timestamp display

        Returns:
            Dictionary with summary results or None if failed
        """
        # First get AI provider info to determine privacy level
        result = get_ai_response("test", timeout=5)  # Quick test to get provider info
        is_local_ai = result.get('is_local', False)

        # Get recent messages with privacy setting based on AI provider type
        messages_text = self.get_recent_messages(group_id, hours, user_timezone, anonymize=not is_local_ai)

        if not messages_text:
            return {
                'status': 'no_messages',
                'summary': f"No messages found in the last {hours} hours.",
                'group_name': group_name,
                'hours': hours,
                'message_count': 0
            }

        # Count messages
        message_count = len(messages_text.split('\n'))

        # Create prompt with privacy notice
        privacy_note = "Local AI - Full details included" if is_local_ai else "External AI - Anonymized for privacy"
        anonymous_note = "" if is_local_ai else "\n\nImportant: This is an ANONYMOUS summary. Do NOT attempt to identify or reference specific participants.\nFocus only on the content and themes of the conversation itself."

        prompt = f"""Analyze the following chat conversation from the last {hours} hours and provide a comprehensive summary.

Privacy Note: {privacy_note}

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

{'Chat Messages (with participant details):' if is_local_ai else 'Chat Messages:'}
{messages_text}

Please provide a structured summary including:
1. **Key Topics Discussed**: Main subjects and themes of conversation
2. **Important Information**: Any decisions, announcements, or critical details
3. **Action Items**: Any tasks, commitments, or follow-ups mentioned
4. **Overall Activity**: General conversation patterns and flow
5. **Tone & Sentiment**: Overall mood and energy of the conversation
6. **Notable Moments**: Interesting, funny, or significant exchanges{anonymous_note}

Format the response as clear, concise bullet points under each section.
If a section has no relevant content, you can skip it.
Keep the summary focused on what would be most useful for someone who missed the conversation."""

        try:
            self.logger.info("Running message summarization with AI provider")
            self.logger.debug("AI prompt: %s", prompt[:500] + "..." if len(prompt) > 500 else prompt)

            # Use the AI provider abstraction layer
            result = get_ai_response(prompt, timeout=60)

            if result['success']:
                self.logger.info(f"Summarization completed using {result.get('provider', 'unknown')} provider")
                return {
                    'status': 'success',
                    'summary': result['response'],
                    'group_name': group_name,
                    'hours': hours,
                    'message_count': message_count,
                    'analyzed_at': datetime.now().isoformat(),
                    'ai_provider': result.get('provider', 'unknown'),
                    'is_local': result.get('is_local', False),
                    'provider_info': f"{result.get('provider', 'unknown')} ({'Local' if result.get('is_local', False) else 'External'})"
                }
            else:
                self.logger.error(f"AI summarization failed: {result.get('error', 'Unknown error')}")
                return {
                    'status': 'error',
                    'error': f"AI analysis failed: {result.get('error', 'Unknown error')}",
                    'group_name': group_name,
                    'hours': hours,
                    'message_count': message_count
                }

        except Exception as e:
            self.logger.error(f"Error running summarization: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'group_name': group_name,
                'hours': hours,
                'message_count': message_count
            }

    def check_ai_available(self) -> bool:
        """Check if any AI provider is available."""
        try:
            status = get_ai_status()
            return status.get('active_provider') is not None
        except:
            return False