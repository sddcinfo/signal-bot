"""
Sentiment Analysis Service

Integrates with AI providers (Ollama local or Gemini external) to provide sentiment
analysis of chat messages. Analyzes mood, tone, and emotional patterns in group conversations.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timezone, timedelta
from .ai_provider import get_ai_response, get_ai_status


class SentimentAnalyzer:
    """Service for analyzing sentiment of chat messages using AI providers."""

    def __init__(self, db_manager):
        """
        Initialize sentiment analyzer.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

    def get_daily_messages(self, group_id: str, target_date: Optional[date] = None, user_timezone: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all messages from a specific group for a given date.

        Args:
            group_id: The group to analyze
            target_date: Date to analyze (defaults to today)
            user_timezone: User's timezone (e.g., 'America/New_York')

        Returns:
            List of message dictionaries with sender and content
        """
        if target_date is None:
            target_date = date.today()

        if user_timezone:
            # Convert the user's date to UTC range for database query
            # User's day starts at 00:00 in their timezone
            # User's day ends at 23:59:59 in their timezone
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(user_timezone)

                # Create start and end of day in user's timezone
                start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
                end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=tz)

                # Convert to UTC timestamps (milliseconds)
                start_timestamp = int(start_of_day.timestamp() * 1000)
                end_timestamp = int(end_of_day.timestamp() * 1000)

                query = """
                SELECT COALESCE(u.display_name, u.friendly_name, m.sender_uuid), m.message_text, datetime(m.timestamp/1000, 'unixepoch') as msg_time,
                       m.timestamp
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ?
                AND m.timestamp >= ? AND m.timestamp <= ?
                ORDER BY m.timestamp
                """
                query_params = (group_id, start_timestamp, end_timestamp)

            except ImportError:
                # Fallback to UTC if zoneinfo not available
                self.logger.warning("zoneinfo not available, falling back to UTC")
                query = """
                SELECT COALESCE(u.display_name, u.friendly_name, m.sender_uuid), m.message_text, datetime(m.timestamp/1000, 'unixepoch') as msg_time,
                       m.timestamp
                FROM messages m
                LEFT JOIN users u ON m.sender_uuid = u.uuid
                WHERE m.group_id = ?
                AND date(m.timestamp/1000, 'unixepoch') = ?
                ORDER BY m.timestamp
                """
                query_params = (group_id, target_date.strftime('%Y-%m-%d'))
        else:
            # No timezone provided, use UTC
            query = """
            SELECT COALESCE(u.display_name, u.friendly_name, m.sender_uuid), m.message_text, datetime(m.timestamp/1000, 'unixepoch') as msg_time,
                   m.timestamp
            FROM messages m
            LEFT JOIN users u ON m.sender_uuid = u.uuid
            WHERE m.group_id = ?
            AND date(m.timestamp/1000, 'unixepoch') = ?
            ORDER BY m.timestamp
            """
            query_params = (group_id, target_date.strftime('%Y-%m-%d'))

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, query_params)
                results = cursor.fetchall()

            messages = []
            for row in results:
                sender = row[0] or 'Unknown'
                text = row[1]
                # Debug: log a few messages to see what we get
                if len(messages) < 3:
                    self.logger.info(f"Raw message: sender='{row[0]}' -> '{sender}', text='{text[:50] if text else 'None'}...'")
                messages.append({
                    'sender': sender,
                    'text': text,
                    'time': row[2],
                    'timestamp': row[3]
                })

            self.logger.info(f"Retrieved {len(messages)} messages from database")
            return messages

        except Exception as e:
            self.logger.error("Failed to get daily messages: %s", e)
            return []

    def format_messages_for_analysis(self, messages: List[Dict[str, Any]], user_timezone: Optional[str] = None, anonymize: bool = True) -> str:
        """
        Format messages for sentiment analysis prompt, filtering out unnecessary content.

        Args:
            messages: List of message dictionaries
            user_timezone: User's timezone for timestamp conversion
            anonymize: Whether to anonymize usernames (True for external AI, False for local AI)

        Returns:
            Formatted string for analysis with optimized content
        """
        if not messages:
            return "No messages found for analysis."

        # Filter out messages with no useful content
        filtered_messages = []
        for msg in messages:
            text = msg.get('text', '').strip()
            sender = msg.get('sender', '').strip()

            # Debug: Log what we're seeing
            if len(filtered_messages) < 5:  # Only log first few for debugging
                self.logger.debug(f"Message: sender='{sender}', text='{text[:50]}...', len={len(text)}")

            # Skip messages with no text content
            if not text:
                if len(filtered_messages) < 5:
                    self.logger.debug("Skipped: no text content")
                continue

            # Skip system messages (but allow UUID-based senders)
            if not sender or sender.lower() in ['system']:
                if len(filtered_messages) < 5:
                    self.logger.debug(f"Skipped: bad sender '{sender}'")
                continue

            # Skip very short messages that don't add sentiment value
            if len(text) < 3:
                if len(filtered_messages) < 5:
                    self.logger.debug(f"Skipped: too short ({len(text)} chars)")
                continue

            # Skip common non-sentiment messages
            if text.lower() in ['ok', 'yes', 'no', 'k', 'thanks', 'thx']:
                if len(filtered_messages) < 5:
                    self.logger.debug(f"Skipped: common phrase '{text.lower()}'")
                continue

            filtered_messages.append(msg)

        if not filtered_messages:
            return "No substantive messages found for sentiment analysis."

        formatted = "Chat Messages for Sentiment Analysis:\n\n"

        # Group messages by sender to reduce redundancy
        sender_messages = {}
        sender_map = {}  # Map real senders to display names
        sender_counter = 1

        for msg in filtered_messages:
            # Convert timestamp to user timezone if provided
            if user_timezone and msg.get('timestamp'):
                try:
                    import zoneinfo
                    utc_dt = datetime.fromtimestamp(msg['timestamp'] / 1000, timezone.utc)
                    user_tz = zoneinfo.ZoneInfo(user_timezone)
                    local_dt = utc_dt.astimezone(user_tz)
                    time_str = local_dt.strftime('%H:%M')
                except (ImportError, Exception):
                    # Fallback to existing time string
                    time_str = msg['time'].split()[1][:5]  # Just HH:MM
            else:
                time_str = msg['time'].split()[1][:5]  # Just HH:MM

            sender = msg['sender']
            text = msg['text']

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

            # Truncate very long messages to avoid token waste
            if len(text) > 150:
                text = text[:147] + "..."

            if display_sender not in sender_messages:
                sender_messages[display_sender] = []
            sender_messages[display_sender].append(f"[{time_str}] {text}")

        # Format grouped messages
        for display_sender, texts in sender_messages.items():
            if len(texts) == 1:
                formatted += f"{display_sender}: {texts[0]}\n"
            else:
                formatted += f"{display_sender}:\n"
                for text in texts:
                    formatted += f"  {text}\n"
                formatted += "\n"

        return formatted

    def analyze_sentiment(self, messages: List[Dict[str, Any]], group_name: str = "Group", user_timezone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze sentiment of messages using AI provider.

        Args:
            messages: List of message dictionaries
            group_name: Name of the group being analyzed
            user_timezone: User's timezone for timestamp conversion

        Returns:
            Dict with sentiment analysis result and metadata, or None if failed
        """
        if not messages:
            return {
                'analysis': "No messages available for sentiment analysis.",
                'is_local': False,
                'provider_info': 'none'
            }

        # First get AI provider info to determine privacy level
        result = get_ai_response("test", timeout=5)  # Quick test to get provider info
        is_local_ai = result.get('is_local', False)

        # Format messages based on AI provider type
        formatted_messages = self.format_messages_for_analysis(messages, user_timezone, anonymize=not is_local_ai)

        # Create prompt with privacy notice
        privacy_note = "Local AI - Full details included" if is_local_ai else "External AI - Anonymized for privacy"

        prompt = f"""
Analyze the sentiment and mood of this chat conversation from the "{group_name}" group on {date.today().strftime('%Y-%m-%d')}:

Privacy Note: {privacy_note}

{formatted_messages}

Please provide:
1. Overall sentiment (positive/negative/neutral/mixed)
2. Dominant emotions and themes
3. Mood progression throughout the day
4. Notable patterns or shifts in conversation tone
5. Key topics that influenced the sentiment
6. Brief summary of the group's emotional state

Keep the analysis concise but insightful, focusing on the emotional undercurrents and social dynamics.
"""

        try:
            self.logger.info(f"Running sentiment analysis with AI provider (Local: {is_local_ai})")
            self.logger.debug("AI prompt: %s", prompt[:500] + "..." if len(prompt) > 500 else prompt)

            # Use the AI provider abstraction layer
            result = get_ai_response(prompt, timeout=60)

            if result['success']:
                provider_name = result.get('provider', 'unknown')
                self.logger.info(f"Sentiment analysis completed using {provider_name} provider")
                return {
                    'analysis': result['response'],
                    'is_local': result.get('is_local', False),
                    'provider_info': f"{provider_name} ({'Local' if result.get('is_local', False) else 'External'})"
                }
            else:
                self.logger.error(f"AI analysis failed: {result.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            self.logger.error("Failed to run sentiment analysis: %s", e)
            return None

    def analyze_group_daily_sentiment(self, group_id: str, group_name: str = None,
                                    target_date: Optional[date] = None, force_refresh: bool = False,
                                    user_timezone: Optional[str] = None) -> Optional[str]:
        """
        Perform complete daily sentiment analysis for a group.

        Args:
            group_id: Group ID to analyze
            group_name: Human-readable group name
            target_date: Date to analyze (defaults to today)
            force_refresh: Force new analysis even if cached result exists
            user_timezone: User's timezone for proper date calculation

        Returns:
            Complete sentiment analysis or None if failed
        """
        if target_date is None:
            target_date = date.today()

        # Create cache key that includes timezone context
        cache_key_date = target_date
        timezone_suffix = f"_{user_timezone}" if user_timezone else "_UTC"

        # Check for cached result first (unless forced refresh)
        if not force_refresh:
            cached_result = self.db.get_sentiment_analysis(group_id, cache_key_date)
            if cached_result:
                self.logger.info("Returning cached sentiment analysis for %s on %s (%s)",
                                group_id[:8], target_date.strftime('%Y-%m-%d'), user_timezone or 'UTC')
                return cached_result

        # Get group name from database if not provided
        if group_name is None:
            group_info = self.db.get_group(group_id)
            group_name = group_info.group_name if group_info else 'Unknown Group'

        # Get messages for analysis with timezone context
        messages = self.get_daily_messages(group_id, target_date, user_timezone)

        if not messages:
            tz_display = user_timezone or 'UTC'
            result = f"No messages found in {group_name} for {target_date.strftime('%Y-%m-%d')} ({tz_display}){timezone_suffix}"
            # Store the "no messages" result to avoid re-checking
            self.db.store_sentiment_analysis(group_id, target_date, 0, result)
            return result

        self.logger.info("Analyzing sentiment for %d messages from %s on %s",
                        len(messages), group_name, target_date.strftime('%Y-%m-%d'))

        # Perform sentiment analysis
        analysis_result = self.analyze_sentiment(messages, group_name, user_timezone)

        if analysis_result and analysis_result.get('analysis'):
            # Prepare metadata
            tz_display = user_timezone or 'UTC'

            # Convert time range to user timezone
            if user_timezone and messages:
                try:
                    import zoneinfo
                    user_tz = zoneinfo.ZoneInfo(user_timezone)

                    # Convert first and last message timestamps
                    first_utc = datetime.fromtimestamp(messages[0]['timestamp'] / 1000, timezone.utc)
                    last_utc = datetime.fromtimestamp(messages[-1]['timestamp'] / 1000, timezone.utc)

                    first_local = first_utc.astimezone(user_tz).strftime('%H:%M')
                    last_local = last_utc.astimezone(user_tz).strftime('%H:%M')
                    time_range = f"{first_local} - {last_local}"
                except (ImportError, Exception):
                    # Fallback to UTC times
                    time_range = f"{messages[0]['time'].split()[1][:5]} - {messages[-1]['time'].split()[1][:5]}"
            else:
                time_range = f"{messages[0]['time'].split()[1][:5]} - {messages[-1]['time'].split()[1][:5]}"

            # Return structured data instead of combined string
            result = {
                'metadata': {
                    'group_name': group_name,
                    'date': target_date.strftime('%Y-%m-%d'),
                    'timezone': tz_display,
                    'message_count': len(messages),
                    'time_range': time_range,
                    'is_local': analysis_result.get('is_local', False),
                    'provider_info': analysis_result.get('provider_info', 'unknown')
                },
                'analysis': analysis_result['analysis']
            }

            # For backward compatibility with database storage, create combined string
            header = f"Sentiment Analysis: {group_name} - {target_date.strftime('%Y-%m-%d')} ({tz_display})\n"
            header += f"Messages analyzed: {len(messages)}\n"
            header += f"Time range: {time_range}\n"
            header += f"Timezone: {tz_display}\n"
            header += f"Provider: {analysis_result.get('provider_info', 'unknown')}\n\n"
            full_result = header + analysis_result['analysis']

            # Store the result in database
            self.db.store_sentiment_analysis(group_id, target_date, len(messages), full_result)

            return result

        return None