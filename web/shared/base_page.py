"""
Base page class for Signal Bot web interface.

Provides consistent structure and functionality for all pages.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

from models.database import DatabaseManager
from services.setup import SetupService
from .templates import render_page, get_standard_date_selector


class BasePage(ABC):
    """Base class for all web pages."""

    def __init__(self, db: DatabaseManager, setup_service: SetupService, ai_provider=None):
        self.db = db
        self.setup_service = setup_service
        self.ai_provider = ai_provider
        # AI analysis services are handled by AIAnalysisService
        self.sentiment_analyzer = None
        self.summarizer = None

    @property
    @abstractmethod
    def title(self) -> str:
        """Page title."""
        pass

    @property
    @abstractmethod
    def nav_key(self) -> str:
        """Navigation key for highlighting active nav item."""
        pass

    @property
    @abstractmethod
    def subtitle(self) -> str:
        """Page subtitle."""
        pass

    @abstractmethod
    def render_content(self, query: Dict[str, Any]) -> str:
        """Render the main content of the page."""
        pass

    def get_custom_css(self) -> str:
        """Override to provide page-specific CSS."""
        return ""

    def get_custom_js(self) -> str:
        """Override to provide page-specific JavaScript."""
        return ""

    def render(self, query: Dict[str, Any]) -> str:
        """Render the complete page."""
        content = self.render_content(query)
        return render_page(
            title=self.title,
            subtitle=self.subtitle,
            content=content,
            active_page=self.nav_key,
            extra_css=self.get_custom_css(),
            extra_js=self.get_custom_js()
        )

    def parse_query_string(self, query_string: str) -> Dict[str, Any]:
        """Parse query string into dictionary."""
        return parse_qs(query_string) if query_string else {}

    def get_user_timezone(self, query: Dict[str, Any]) -> Optional[str]:
        """Get user timezone from query parameters."""
        timezone = query.get('timezone', [None])[0]
        if timezone:
            return timezone
        return 'Asia/Tokyo'  # Default to Asia/Tokyo

    def format_user_display(self, user) -> str:
        """Format user display name consistently - prioritize real friendly names, then phone, then UUID."""
        # Handle None user
        if user is None:
            return '<strong>Unknown User</strong><br><small class="text-muted">User not found</small>'

        # Check if friendly name exists and is not the generic fallback
        if (user.friendly_name and
            user.friendly_name != f"User {user.phone_number}" and
            user.friendly_name != f"User {user.uuid}"):
            # Real friendly name exists - use it with phone/UUID in parentheses
            if user.phone_number:
                return f'<strong>{user.friendly_name}</strong><br><small class="text-muted">{user.phone_number}</small>'
            else:
                return f'<strong>{user.friendly_name}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        elif user.phone_number:
            # No real friendly name, show phone number
            return f'<strong>{user.phone_number}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        elif hasattr(user, 'display_name') and user.display_name:
            # No friendly name or phone, show display name with UUID
            return f'<strong>{user.display_name}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        else:
            # Only UUID available
            return f'<strong>UUID: {user.uuid}</strong><br><small class="text-muted">No phone number</small>'

    def get_standard_date_selector(self, input_id: str = "date-input", **kwargs) -> str:
        """Get standardized date selector."""
        return get_standard_date_selector(input_id=input_id, **kwargs)

    def format_timestamp(self, timestamp_ms: Optional[int], user_timezone: Optional[str] = None) -> str:
        """Format timestamp for display using user timezone."""
        if not timestamp_ms:
            return "Unknown time"

        try:
            from datetime import datetime, timezone
            import pytz

            # Convert milliseconds to datetime
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

            # Convert to user timezone
            if user_timezone:
                try:
                    user_tz = pytz.timezone(user_timezone)
                    dt = dt.astimezone(user_tz)
                except Exception:
                    pass  # Fall back to UTC if timezone is invalid

            # Format as readable string
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Unknown time"