"""
Centralized Global Filter System

Provides reusable filter components and JavaScript functions
that work consistently across all pages.
"""

from typing import List, Dict, Any, Optional


class GlobalFilterSystem:
    """Manages global filters across all pages."""

    @staticmethod
    def render_filters(groups: List[Dict[str, Any]],
                      selected_group: Optional[str] = None,
                      selected_date: Optional[str] = None,
                      selected_hours: Optional[int] = None,
                      selected_sender: Optional[str] = None,
                      senders: Optional[List[Dict[str, Any]]] = None,
                      attachments_only: bool = False,
                      date_mode: str = 'all') -> str:
        """
        Render the global filter bar with all options.

        Args:
            groups: List of available groups
            selected_group: Currently selected group ID
            selected_date: Currently selected date (YYYY-MM-DD)
            selected_hours: Currently selected hours (1-168)
            selected_sender: Currently selected sender UUID
            senders: List of available senders (filtered by group if provided)
            attachments_only: Whether to show only messages with attachments
            date_mode: 'all', 'today', or 'specific'

        Returns:
            HTML string for the filter bar
        """
        # Build group options
        group_options = ['<option value="">All Groups</option>']
        for group in groups:
            selected = 'selected' if group.get('group_id') == selected_group else ''
            name = group.get('name', 'Unnamed Group')[:50]
            group_options.append(
                f'<option value="{group.get("group_id")}" {selected}>{name}</option>'
            )

        # Build sender options
        sender_options = ['<option value="">All Senders</option>']
        if senders:
            for sender in senders:
                selected = 'selected' if sender.get('uuid') == selected_sender else ''
                name = sender.get('friendly_name') or sender.get('phone_number', 'Unknown')[:50]
                sender_options.append(
                    f'<option value="{sender.get("uuid")}" {selected}>{name}</option>'
                )

        # Build hours options
        hours_options = [
            (1, "1 hour"),
            (3, "3 hours"),
            (6, "6 hours"),
            (12, "12 hours"),
            (24, "24 hours"),
            (48, "48 hours"),
            (72, "3 days"),
            (168, "7 days"),
        ]

        selected_hours = selected_hours or 24  # Default to 24 hours
        hours_html = []
        for value, label in hours_options:
            selected = 'selected' if value == selected_hours else ''
            hours_html.append(f'<option value="{value}" {selected}>{label}</option>')

        # Date mode selections
        date_all_checked = 'checked' if date_mode == 'all' else ''
        date_today_checked = 'checked' if date_mode == 'today' else ''
        date_specific_checked = 'checked' if date_mode == 'specific' else ''
        date_display = 'inline-block' if date_mode == 'specific' else 'none'
        attachments_checked = 'checked' if attachments_only else ''

        return f"""
        <div id="global-filters-container" class="global-filters" style="background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div class="filter-row" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">

                <!-- Group Filter -->
                <div class="filter-group" style="min-width: 150px;">
                    <label for="global-group-filter" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">
                        Group:
                    </label>
                    <select id="global-group-filter" onchange="GlobalFilters.apply()"
                            style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 100%;">
                        {''.join(group_options)}
                    </select>
                </div>

                <!-- Sender Filter -->
                <div class="filter-group" style="min-width: 150px;">
                    <label for="global-sender-filter" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">
                        Sender:
                    </label>
                    <select id="global-sender-filter" onchange="GlobalFilters.apply()"
                            style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 100%;">
                        {''.join(sender_options)}
                    </select>
                </div>

                <!-- Date Selection -->
                <div class="filter-group">
                    <label style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">
                        Date:
                    </label>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <label style="display: flex; align-items: center; font-size: 0.9em; cursor: pointer;">
                            <input type="radio" name="date-mode" id="global-date-mode-all" value="all" {date_all_checked}
                                   onchange="document.getElementById('global-date').style.display='none'; document.getElementById('global-date').value=''; GlobalFilters.apply();"
                                   style="margin-right: 3px;">
                            All Dates
                        </label>
                        <label style="display: flex; align-items: center; font-size: 0.9em; cursor: pointer;">
                            <input type="radio" name="date-mode" id="global-date-mode-today" value="today" {date_today_checked}
                                   onchange="document.getElementById('global-date').style.display='none'; GlobalFilters.apply();"
                                   style="margin-right: 3px;">
                            Today
                        </label>
                        <label style="display: flex; align-items: center; font-size: 0.9em; cursor: pointer;">
                            <input type="radio" name="date-mode" id="global-date-mode-specific" value="specific" {date_specific_checked}
                                   onchange="document.getElementById('global-date').style.display='inline-block'; if(!document.getElementById('global-date').value) document.getElementById('global-date').value=new Date().toISOString().split('T')[0]; GlobalFilters.apply();"
                                   style="margin-right: 3px;">
                            Pick Date
                        </label>
                        <input type="date" id="global-date" value="{selected_date or ''}" onchange="GlobalFilters.apply()"
                               style="padding: 5px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; display: {date_display};">
                    </div>
                </div>

                <!-- Hours Filter (Recent Messages) -->
                <div class="filter-group" style="min-width: 140px;">
                    <label for="global-hours-filter" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">
                        Recent Hours:
                    </label>
                    <select id="global-hours-filter" onchange="GlobalFilters.apply()"
                            style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 100%;">
                        <option value="0">All Time</option>
                        {''.join(hours_html)}
                    </select>
                </div>

                <!-- Attachments Only -->
                <div class="filter-group">
                    <label style="display: flex; align-items: center; font-size: 0.9em; cursor: pointer; margin-top: 20px;">
                        <input type="checkbox" id="global-attachments-only" {attachments_checked} onchange="GlobalFilters.apply()"
                               style="margin-right: 5px;">
                        Attachments Only
                    </label>
                </div>

                <!-- Reset Button Only -->
                <div class="filter-group" style="margin-left: auto; margin-top: 20px;">
                    <button onclick="GlobalFilters.reset()"
                            style="padding: 8px 16px; background: #6c757d; color: white; border: none;
                                   border-radius: 5px; cursor: pointer;">
                        Reset Filters
                    </button>
                </div>
            </div>
        </div>
        """

    @staticmethod
    def get_javascript() -> str:
        """
        Get the JavaScript code for handling global filters.
        This should be included once per page.
        """
        return """
        // Global Filters JavaScript Module
        const GlobalFilters = {
            // Get all current filter values
            getValues: function() {
                const dateRadio = document.querySelector('input[name="date-mode"]:checked');
                return {
                    groupId: document.getElementById('global-group-filter') ? document.getElementById('global-group-filter').value : '',
                    senderId: document.getElementById('global-sender-filter') ? document.getElementById('global-sender-filter').value : '',
                    dateMode: dateRadio ? dateRadio.value : 'all',
                    date: document.getElementById('global-date') ? document.getElementById('global-date').value : '',
                    hours: document.getElementById('global-hours-filter') ? parseInt(document.getElementById('global-hours-filter').value) : 0,
                    attachmentsOnly: document.getElementById('global-attachments-only') ? document.getElementById('global-attachments-only').checked : false
                };
            },

            // Get filter values for API calls
            getApiParams: function() {
                const filters = this.getValues();
                const params = new URLSearchParams();

                if (filters.groupId) params.append('group_id', filters.groupId);
                if (filters.senderId) params.append('sender_id', filters.senderId);
                if (filters.hours) params.append('hours', filters.hours);
                if (filters.attachmentsOnly) params.append('attachments_only', 'true');

                // Handle date based on mode
                if (filters.dateMode === 'today') {
                    const today = new Date().toISOString().split('T')[0];
                    params.append('date', today);
                } else if (filters.dateMode === 'specific' && filters.date) {
                    params.append('date', filters.date);
                }

                // Add timezone
                const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                params.append('timezone', timezone);

                return params;
            },

            // Apply filters (navigate with parameters)
            apply: function() {
                console.log('GlobalFilters.apply() called');
                const filters = this.getValues();
                console.log('Current filters:', filters);

                const currentUrl = new URL(window.location);
                const params = currentUrl.searchParams;

                // Keep the current tab if it exists
                const currentTab = params.get('tab');

                // Clear all filter params first
                const keysToDelete = ['group_id', 'sender_id', 'date', 'date_mode', 'hours', 'attachments_only'];
                keysToDelete.forEach(key => params.delete(key));

                // Restore tab if it existed
                if (currentTab) {
                    params.set('tab', currentTab);
                }

                // Set new filter parameters
                if (filters.groupId) {
                    params.set('group_id', filters.groupId);
                }

                if (filters.senderId) {
                    params.set('sender_id', filters.senderId);
                }

                params.set('date_mode', filters.dateMode);

                if (filters.dateMode === 'specific' && filters.date) {
                    params.set('date', filters.date);
                } else if (filters.dateMode === 'today') {
                    params.set('date', new Date().toISOString().split('T')[0]);
                }

                // Only set hours if not "All Time" (0)
                if (filters.hours && filters.hours !== 0) {
                    params.set('hours', filters.hours);
                }

                if (filters.attachmentsOnly) {
                    params.set('attachments_only', 'true');
                }

                // Navigate to new URL
                console.log('Navigating to:', currentUrl.toString());
                window.location.href = currentUrl.toString();
            },

            // Reset all filters
            reset: function() {
                const currentUrl = new URL(window.location);
                const tab = currentUrl.searchParams.get('tab');

                // Keep only the tab parameter
                const newUrl = new URL(window.location.pathname, window.location.origin);
                if (tab) {
                    newUrl.searchParams.set('tab', tab);
                }

                window.location.href = newUrl.toString();
            },

            // Handle group change (update sender options)
            onGroupChange: function() {
                const groupId = document.getElementById('global-group-filter').value;

                // For now, just mark that we need to update senders
                // This would typically make an API call to get group members
                if (typeof updateSenderOptions === 'function') {
                    updateSenderOptions();
                }
            },

            // Handle date mode change
            onDateModeChange: function() {
                const dateMode = document.querySelector('input[name="date-mode"]:checked');
                const dateInput = document.getElementById('global-date');

                if (!dateMode || !dateInput) {
                    console.error('Date mode elements not found:', {dateMode, dateInput});
                    return;
                }

                const mode = dateMode.value;
                console.log('Date mode changed to:', mode);

                if (mode === 'specific') {
                    dateInput.style.display = 'inline-block';
                    // Set to today if no date selected
                    if (!dateInput.value) {
                        dateInput.value = new Date().toISOString().split('T')[0];
                    }
                } else {
                    dateInput.style.display = 'none';
                    if (mode === 'all') {
                        dateInput.value = ''; // Clear date for "all dates"
                    } else if (mode === 'today') {
                        dateInput.value = new Date().toISOString().split('T')[0];
                    }
                }
            },

            // Initialize on page load
            init: function() {
                // Set initial state based on URL parameters
                const params = new URLSearchParams(window.location.search);

                // Restore filter values from URL if they exist
                if (params.has('hours')) {
                    const hoursSelect = document.getElementById('global-hours-filter');
                    if (hoursSelect) {
                        hoursSelect.value = params.get('hours');
                    }
                }

                // Initialize date mode display
                this.onDateModeChange();
            }
        };

        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            try {
                GlobalFilters.init();
                console.log('GlobalFilters initialized successfully');
            } catch (e) {
                console.error('Failed to initialize GlobalFilters:', e);
            }
        });

        // Also try to initialize after a short delay as fallback
        setTimeout(function() {
            if (typeof GlobalFilters !== 'undefined' && typeof GlobalFilters.onDateModeChange === 'function') {
                GlobalFilters.onDateModeChange();
                console.log('Fallback initialization of date mode display');
            }
        }, 500);
        """

    @staticmethod
    def parse_query_filters(query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse query parameters into filter values.

        Args:
            query: Query dictionary from URL parameters

        Returns:
            Dictionary with parsed filter values
        """
        date_mode = query.get('date_mode', ['all'])[0]
        date = query.get('date', [''])[0] if 'date' in query else None

        # If date_mode is 'today' but no date is provided, use today's date
        if date_mode == 'today' and not date:
            from datetime import date as dt
            date = dt.today().isoformat()

        return {
            'group_id': query.get('group_id', [''])[0] if 'group_id' in query else None,
            'sender_id': query.get('sender_id', [''])[0] if 'sender_id' in query else None,
            'date': date,
            'hours': int(query.get('hours', ['24'])[0]) if 'hours' in query else 24,
            'date_mode': date_mode,
            'attachments_only': query.get('attachments_only', [''])[0] == 'true',
            'timezone': query.get('timezone', ['UTC'])[0]
        }