"""
Centralized filter utilities for consistent date/time handling.

This module ensures all filter logic uses the same approach for:
- Date selection (specific dates)
- Hours filtering (recent messages)
- Timezone handling
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, Tuple, Optional


def get_date_range_from_filters(filters: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert filter parameters to date range for database queries.

    This is the SINGLE SOURCE OF TRUTH for converting UI filters to database parameters.

    Args:
        filters: Parsed filters from GlobalFilterSystem.parse_query_filters()

    Returns:
        Tuple of (start_date, end_date) as YYYY-MM-DD strings or None
    """
    date_mode = filters.get('date_mode', 'all')
    date_param = filters.get('date')
    hours_filter = filters.get('hours', 0)

    # Priority 1: Specific date selected (from date picker or today button)
    if date_param:
        # Single date - show all messages from that date
        return (date_param, date_param)

    # Priority 2: Hours filter (only when no specific date)
    if date_mode == 'all' and hours_filter and hours_filter > 0:
        # Calculate date range for recent hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_filter)

        # Convert to date strings
        # Note: This may span multiple days
        start_date = start_time.strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')

        return (start_date, end_date)

    # Priority 3: No filters - show all messages
    return (None, None)


def should_use_hours_filter(filters: Dict[str, Any]) -> bool:
    """
    Determine if hours filter should be applied.

    Hours filter is only used when:
    - No specific date is selected
    - Hours value is > 0
    - Date mode is 'all'

    Args:
        filters: Parsed filters

    Returns:
        True if hours filter should be applied
    """
    date_param = filters.get('date')
    hours_filter = filters.get('hours', 0)
    date_mode = filters.get('date_mode', 'all')

    return (
        not date_param and  # No specific date
        hours_filter > 0 and  # Has hours filter
        date_mode == 'all'  # Not in today/specific mode
    )