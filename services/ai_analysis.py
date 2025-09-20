"""
Unified AI Analysis Service

Handles all types of AI analysis (summary, sentiment, etc.) using
configurations stored in the database. This replaces the separate
summarization and sentiment services.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .ai_provider import get_ai_response, get_ai_status


class AIAnalysisService:
    """Unified service for all AI-powered message analysis."""

    def __init__(self, db_manager):
        """
        Initialize AI analysis service.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

    def get_analysis_types(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get available AI analysis types from database.

        Args:
            active_only: Whether to return only active types

        Returns:
            List of analysis type configurations
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT id, name, display_name, description, icon,
                           requires_group, requires_sender, max_hours, min_messages,
                           sort_order
                    FROM ai_analysis_types
                    WHERE 1=1
                """
                params = []

                if active_only:
                    query += " AND is_active = ?"
                    params.append(1)

                query += " ORDER BY sort_order, display_name"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                types = []
                for row in rows:
                    types.append({
                        'id': row['id'],
                        'name': row['name'],
                        'display_name': row['display_name'],
                        'description': row['description'],
                        'icon': row['icon'],
                        'requires_group': bool(row['requires_group']),
                        'requires_sender': bool(row['requires_sender']),
                        'max_hours': row['max_hours'],
                        'min_messages': row['min_messages'],
                        'sort_order': row['sort_order']
                    })

                return types

        except Exception as e:
            self.logger.error(f"Error getting analysis types: {e}")
            return []

    def get_analysis_config(self, analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific analysis type.

        Args:
            analysis_type: Name or ID of the analysis type

        Returns:
            Analysis configuration or None if not found
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Try both ID and name
                query = """
                    SELECT * FROM ai_analysis_types
                    WHERE (name = ? OR id = ?) AND is_active = 1
                """

                # Handle both string IDs and names
                try:
                    type_id = int(analysis_type)
                    cursor.execute(query, (analysis_type, type_id))
                except ValueError:
                    cursor.execute(query, (analysis_type, -1))

                row = cursor.fetchone()

                if row:
                    return dict(row)

                return None

        except Exception as e:
            self.logger.error(f"Error getting analysis config: {e}")
            return None

    def analyze_messages(self, messages: List[Dict[str, Any]], analysis_type: str,
                        group_name: str = None, hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        Analyze messages using specified analysis type.

        Args:
            messages: List of message dictionaries
            analysis_type: Type of analysis to perform
            group_name: Name of the group
            hours: Hours of data being analyzed

        Returns:
            Analysis results or None if failed
        """
        # Get analysis configuration
        config = self.get_analysis_config(analysis_type)
        if not config:
            self.logger.error(f"Analysis type '{analysis_type}' not found or inactive")
            return {
                'status': 'error',
                'error': f"Analysis type '{analysis_type}' not found"
            }

        # Check minimum message requirement
        if len(messages) < config.get('min_messages', 5):
            return {
                'status': 'no_messages',
                'error': f"Not enough messages. Need at least {config.get('min_messages', 5)} messages.",
                'message_count': len(messages)
            }

        # Format messages for AI
        formatted_messages = self._format_messages(
            messages,
            anonymize=config.get('anonymize_external', True),
            include_names=config.get('include_sender_names', True)
        )

        if not formatted_messages:
            return {
                'status': 'no_messages',
                'error': 'No valid messages to analyze',
                'message_count': 0
            }

        # Prepare prompt from template
        prompt_template = config.get('prompt_template', '')
        prompt = prompt_template.format(
            group_name=group_name or 'Unknown Group',
            hours=hours,
            message_count=len(messages),
            messages=formatted_messages
        )

        # Send to AI provider
        try:
            self.logger.info(f"Running {config['display_name']} analysis with AI provider")
            result = get_ai_response(prompt, timeout=60)

            if result['success']:
                self.logger.info(f"Analysis completed using {result.get('provider', 'unknown')} provider")
                return {
                    'status': 'success',
                    'analysis_type': config['name'],
                    'display_name': config['display_name'],
                    'result': result['response'],
                    'group_name': group_name,
                    'hours': hours,
                    'message_count': len(messages),
                    'analyzed_at': datetime.now().isoformat(),
                    'ai_provider': result.get('provider', 'unknown'),
                    'is_local': result.get('is_local', False)
                }
            else:
                self.logger.error(f"AI analysis failed: {result.get('error', 'Unknown error')}")
                return {
                    'status': 'error',
                    'error': f"AI analysis failed: {result.get('error', 'Unknown error')}"
                }

        except Exception as e:
            self.logger.error(f"Error running analysis: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _format_messages(self, messages: List[Dict[str, Any]],
                        anonymize: bool = True, include_names: bool = True) -> str:
        """
        Format messages for AI analysis.

        Args:
            messages: List of message dictionaries
            anonymize: Whether to anonymize sender names
            include_names: Whether to include names at all

        Returns:
            Formatted string of messages
        """
        # Sort messages by timestamp
        messages.sort(key=lambda x: x.get('timestamp', 0))

        formatted = []
        sender_map = {}
        sender_counter = 1

        for msg in messages:
            # Format timestamp
            msg_time = datetime.fromtimestamp(msg['timestamp'] / 1000)
            timestamp = msg_time.strftime('%H:%M')

            # Get message text and sender
            text = msg.get('message_text', '')
            sender = msg.get('friendly_name') or msg.get('sender_uuid', 'Unknown')

            # Skip empty or system messages
            if not text or text.strip() == '':
                continue
            if not sender or sender.lower() in ['system']:
                continue

            # Handle sender names based on settings
            if include_names:
                if anonymize:
                    # Create anonymous mapping
                    if sender not in sender_map:
                        sender_map[sender] = f"User{sender_counter}"
                        sender_counter += 1
                    display_sender = sender_map[sender]
                    formatted.append(f"[{timestamp}] {display_sender}: {text}")
                else:
                    # Use real names
                    formatted.append(f"[{timestamp}] {sender}: {text}")
            else:
                # No names at all
                formatted.append(f"[{timestamp}] {text}")

        return "\n".join(formatted)

    def save_analysis_type(self, config: Dict[str, Any]) -> bool:
        """
        Save or update an AI analysis type configuration.

        Args:
            config: Analysis type configuration

        Returns:
            True if successful
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Check if exists
                if 'id' in config:
                    # Update existing
                    cursor.execute("""
                        UPDATE ai_analysis_types SET
                            display_name = ?,
                            description = ?,
                            prompt_template = ?,
                            requires_group = ?,
                            requires_sender = ?,
                            max_hours = ?,
                            min_messages = ?,
                            icon = ?,
                            color = ?,
                            sort_order = ?,
                            anonymize_external = ?,
                            include_sender_names = ?,
                            is_active = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        config.get('display_name'),
                        config.get('description'),
                        config.get('prompt_template'),
                        config.get('requires_group', 1),
                        config.get('requires_sender', 0),
                        config.get('max_hours', 168),
                        config.get('min_messages', 5),
                        config.get('icon', '🤖'),
                        config.get('color', '#007bff'),
                        config.get('sort_order', 0),
                        config.get('anonymize_external', 1),
                        config.get('include_sender_names', 1),
                        config.get('is_active', 1),
                        config['id']
                    ))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO ai_analysis_types (
                            name, display_name, description, prompt_template,
                            requires_group, requires_sender, max_hours, min_messages,
                            icon, color, sort_order, anonymize_external,
                            include_sender_names, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        config.get('name'),
                        config.get('display_name'),
                        config.get('description'),
                        config.get('prompt_template'),
                        config.get('requires_group', 1),
                        config.get('requires_sender', 0),
                        config.get('max_hours', 168),
                        config.get('min_messages', 5),
                        config.get('icon', '🤖'),
                        config.get('color', '#007bff'),
                        config.get('sort_order', 0),
                        config.get('anonymize_external', 1),
                        config.get('include_sender_names', 1),
                        config.get('is_active', 1)
                    ))

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error saving analysis type: {e}")
            return False

    def delete_analysis_type(self, type_id: int) -> bool:
        """
        Delete an AI analysis type (only if not built-in).

        Args:
            type_id: ID of the analysis type

        Returns:
            True if successful
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Check if built-in
                cursor.execute("SELECT is_builtin FROM ai_analysis_types WHERE id = ?", (type_id,))
                row = cursor.fetchone()

                if row and row['is_builtin']:
                    self.logger.warning(f"Cannot delete built-in analysis type {type_id}")
                    return False

                # Delete
                cursor.execute("DELETE FROM ai_analysis_types WHERE id = ?", (type_id,))
                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Error deleting analysis type: {e}")
            return False

    def check_ai_available(self) -> bool:
        """Check if any AI provider is available."""
        try:
            status = get_ai_status()
            return status.get('active_provider') is not None
        except:
            return False