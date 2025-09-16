"""
Message Summarization Service

Uses Gemini AI to provide intelligent summaries of chat messages from the last N hours.
Highlights key topics, decisions, and important information from group conversations.
"""

import subprocess
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class MessageSummarizer:
    """Service for summarizing recent chat messages using Gemini."""

    def __init__(self, db_manager, gemini_path: str = "gemini"):
        """
        Initialize message summarizer.

        Args:
            db_manager: Database manager instance
            gemini_path: Path to gemini CLI command
        """
        self.db = db_manager
        self.gemini_path = gemini_path
        self.logger = logging.getLogger(__name__)

    def get_recent_messages(self, group_id: str, hours: int = 24, user_timezone: str = None) -> str:
        """
        Get messages from the last N hours and format them for analysis.

        Args:
            group_id: The group to analyze
            hours: Number of hours to look back
            user_timezone: User's timezone for consistent timestamp display

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

        # Format messages for analysis (anonymous)
        formatted = []

        # Setup timezone conversion if user timezone is provided
        user_tz = None
        if user_timezone:
            try:
                import zoneinfo
                user_tz = zoneinfo.ZoneInfo(user_timezone)
            except (ImportError, Exception):
                self.logger.warning(f"Could not use timezone {user_timezone}, falling back to UTC")

        for msg in recent_messages:
            # Format timestamp with user's timezone if available
            msg_time = datetime.fromtimestamp(msg['timestamp'] / 1000)

            if user_tz:
                # Convert to user's timezone
                from datetime import timezone as dt_timezone
                msg_time = msg_time.replace(tzinfo=dt_timezone.utc).astimezone(user_tz)

            timestamp = msg_time.strftime('%H:%M')

            # Get message text
            text = msg.get('message_text', '')

            # Skip empty messages
            if not text or text.strip() == '':
                continue

            # Anonymous format - just timestamp and message
            formatted.append(f"[{timestamp}] {text}")

        return "\n".join(formatted)

    def summarize_messages(self, group_id: str, group_name: str, hours: int = 24, user_timezone: str = None) -> Optional[Dict[str, Any]]:
        """
        Summarize messages from the last N hours using Gemini AI.

        Args:
            group_id: The group to analyze
            group_name: Display name of the group
            hours: Number of hours to look back
            user_timezone: User's timezone for consistent timestamp display

        Returns:
            Dictionary with summary results or None if failed
        """
        # Get recent messages with user timezone
        messages_text = self.get_recent_messages(group_id, hours, user_timezone)

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

        # Prepare prompt for Gemini (anonymous version)
        prompt = f"""Analyze the following anonymous chat conversation from the last {hours} hours and provide a comprehensive summary.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Anonymous Messages (timestamps only, no user identifiers):
{messages_text}

Please provide a structured summary including:
1. **Key Topics Discussed**: Main subjects and themes of conversation
2. **Important Information**: Any decisions, announcements, or critical details
3. **Action Items**: Any tasks, commitments, or follow-ups mentioned
4. **Overall Activity**: General conversation patterns and flow
5. **Tone & Sentiment**: Overall mood and energy of the conversation
6. **Notable Moments**: Interesting, funny, or significant exchanges

Important: This is an ANONYMOUS summary. Do NOT attempt to identify or reference specific participants.
Focus only on the content and themes of the conversation itself.

Format the response as clear, concise bullet points under each section.
If a section has no relevant content, you can skip it.
Keep the summary focused on what would be most useful for someone who missed the conversation."""

        try:
            # Run gemini command with the prompt
            result = subprocess.run(
                [self.gemini_path, prompt],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            if result.returncode == 0 and result.stdout:
                summary_text = result.stdout.strip()

                return {
                    'status': 'success',
                    'summary': summary_text,
                    'group_name': group_name,
                    'hours': hours,
                    'message_count': message_count,
                    'analyzed_at': datetime.now().isoformat()
                }
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                self.logger.error(f"Gemini command failed: {error_msg}")
                return {
                    'status': 'error',
                    'error': f"AI analysis failed: {error_msg}",
                    'group_name': group_name,
                    'hours': hours,
                    'message_count': message_count
                }

        except subprocess.TimeoutExpired:
            self.logger.error("Gemini command timed out")
            return {
                'status': 'error',
                'error': "AI analysis timed out",
                'group_name': group_name,
                'hours': hours,
                'message_count': message_count
            }
        except FileNotFoundError:
            self.logger.error(f"Gemini command not found at {self.gemini_path}")
            return {
                'status': 'error',
                'error': "Gemini AI not available",
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

    def check_gemini_available(self) -> bool:
        """Check if gemini CLI is available."""
        try:
            result = subprocess.run(
                [self.gemini_path, "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False