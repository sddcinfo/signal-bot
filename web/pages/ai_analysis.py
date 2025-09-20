"""
AI Analysis Page - Unified interface for all AI-powered message analysis.

Replaces separate sentiment and summary pages with a flexible, configurable
system that pulls analysis types from the database.
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from ..shared.base_page import BasePage
from ..shared.filters import GlobalFilterSystem


class AIAnalysisPage(BasePage):
    """Unified AI Analysis page."""

    def __init__(self, db_manager, setup_service=None, ai_provider=None):
        super().__init__(db_manager, setup_service, ai_provider)
        self.db = db_manager
        self.logger = logging.getLogger(__name__)

    @property
    def title(self) -> str:
        return "AI Analysis"

    @property
    def nav_key(self) -> str:
        return "ai_analysis"

    @property
    def subtitle(self) -> str:
        return "Use AI to analyze your messages"

    def get_page_scripts(self) -> List[str]:
        """Get page-specific JavaScript files."""
        return ['/static/js/ai-analysis.js']

    def render_content(self, query: Dict[str, Any]) -> str:
        """Render the AI Analysis page content."""
        try:
            # Get available analysis types from database
            analysis_types = self._get_analysis_types()

            # Parse filters
            filters = GlobalFilterSystem.parse_query_filters(query)

            # Get groups for filter
            groups = self._get_groups_for_filters()

            # Get senders if a group is selected
            senders = []
            if filters.get('group_id'):
                senders = self._get_senders_for_group(filters['group_id'])

            # Build the content
            content = f"""
            <!-- Global Filters -->
            {GlobalFilterSystem.render_filters(
                groups=groups,
                selected_group=filters.get('group_id'),
                selected_date=filters.get('date'),
                selected_hours=filters.get('hours', 24),
                selected_sender=filters.get('sender_id'),
                senders=senders,
                attachments_only=filters.get('attachments_only', False),
                date_mode=filters.get('date_mode', 'all')
            )}

            <!-- AI Analysis Content -->
            <div class="content-section">
                <div class="section-header">
                    <h2>🤖 AI Message Analysis</h2>
                    <p class="text-muted">Use AI to analyze and extract insights from your messages</p>
                </div>

                <!-- Analysis Type Selector -->
                <div class="analysis-selector" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <label for="analysis-type-select" style="display: block; margin-bottom: 5px; font-weight: bold;">
                                Analysis Type:
                            </label>
                            <select id="analysis-type-select" class="form-control"
                                    style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                <option value="">-- Select Analysis Type --</option>
                                {self._render_analysis_options(analysis_types)}
                            </select>
                            <small id="analysis-description" class="text-muted" style="display: block; margin-top: 5px;"></small>
                        </div>

                        <div style="display: flex; gap: 10px;">
                            <button onclick="showAnalysisPreview()" class="btn btn-secondary"
                                    style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                <span class="icon">👁️</span> Preview
                            </button>
                            <button onclick="runAnalysis()" class="btn btn-primary"
                                    style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                <span class="icon">🚀</span> Run Analysis
                            </button>
                        </div>
                    </div>

                    <!-- Preview Area -->
                    <div id="analysis-preview" style="display: none; margin-top: 15px; padding: 10px; background: white; border-radius: 5px; border: 1px solid #dee2e6;">
                        <div id="analysis-preview-content"></div>
                    </div>
                </div>

                <!-- Results Area -->
                <div id="analysis-results" style="display: none;">
                    <div class="results-header" style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <h3 id="analysis-title" style="margin: 0;"></h3>
                    </div>
                    <div id="analysis-content" class="results-content"></div>
                </div>
            </div>

            <!-- Analysis Type Descriptions (Hidden) -->
            <script>
                const analysisTypes = {self._get_analysis_types_json()};
            </script>
            """

            return content

        except Exception as e:
            self.logger.error(f"Error rendering AI Analysis page: {e}")
            return self._render_error(str(e))

    def _get_analysis_types(self) -> List[Dict[str, Any]]:
        """Get active AI analysis types from database."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, display_name, description, icon,
                           requires_group, requires_sender, max_hours, min_messages
                    FROM ai_analysis_types
                    WHERE is_active = 1
                    ORDER BY sort_order, display_name
                """)

                types = []
                for row in cursor.fetchall():
                    types.append(dict(row))

                return types

        except Exception as e:
            self.logger.error(f"Error getting analysis types: {e}")
            return []

    def _render_analysis_options(self, analysis_types: List[Dict[str, Any]]) -> str:
        """Render analysis type options for select dropdown."""
        options = []
        for atype in analysis_types:
            icon = atype.get('icon', '🤖')
            display_name = atype.get('display_name', 'Unknown')
            options.append(f'<option value="{atype["id"]}">{icon} {display_name}</option>')
        return '\n'.join(options)

    def _get_analysis_types_json(self) -> str:
        """Get analysis types as JSON for JavaScript."""
        import json
        types = self._get_analysis_types()

        # Create a dictionary keyed by ID for easy lookup in JavaScript
        types_dict = {}
        for atype in types:
            types_dict[str(atype['id'])] = {
                'name': atype['name'],
                'display_name': atype['display_name'],
                'description': atype.get('description', ''),
                'icon': atype.get('icon', '🤖'),
                'requires_group': atype.get('requires_group', True),
                'requires_sender': atype.get('requires_sender', False),
                'min_messages': atype.get('min_messages', 5),
                'max_hours': atype.get('max_hours', 168)
            }

        return json.dumps(types_dict)

    def _get_groups_for_filters(self) -> List[Dict[str, Any]]:
        """Get groups for filter dropdown."""
        try:
            groups = self.db.get_all_groups()
            return [{'group_id': g.group_id, 'name': g.group_name}
                    for g in groups if g.is_monitored]
        except Exception as e:
            self.logger.error(f"Error getting groups: {e}")
            return []

    def _get_senders_for_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Get senders for a specific group."""
        try:
            members = self.db.get_group_members(group_id)
            senders = []
            for member in members:
                user = self.db.get_user(member['uuid'])
                if user:
                    senders.append({
                        'uuid': user.uuid,
                        'friendly_name': user.friendly_name or user.phone_number
                    })
            return senders
        except Exception as e:
            self.logger.error(f"Error getting senders: {e}")
            return []

    def _render_error(self, error_message: str) -> str:
        """Render error message."""
        return f"""
        <div class="alert alert-danger" style="padding: 15px; background: #f8d7da; color: #721c24; border-radius: 5px;">
            <strong>Error:</strong> {error_message}
        </div>
        """