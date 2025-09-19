"""
Messages page for Signal Bot web interface.
"""

import logging
from typing import Dict, Any
from urllib.parse import quote
from ..shared.base_page import BasePage
from models.user_display_utils import get_user_display_sql


class MessagesPage(BasePage):
    @property
    def title(self) -> str:
        return "💬 Messages"

    @property
    def nav_key(self) -> str:
        return "messages"

    @property
    def subtitle(self) -> str:
        return "View and manage all messages from monitored groups"

    def get_custom_css(self) -> str:
        """No custom CSS - using shared styling."""
        return ""

    def get_custom_js(self) -> str:
        return """
                function showTab(tabName) {
                    const tabs = document.querySelectorAll('.tab-content');
                    tabs.forEach(tab => tab.classList.remove('active'));

                    const tabButtons = document.querySelectorAll('.tab-btn');
                    tabButtons.forEach(btn => btn.classList.remove('active'));

                    document.getElementById(tabName + '-tab').classList.add('active');
                    event.target.classList.add('active');
                }

                function filterByGroup(groupId) {
                    if (groupId) {
                        window.location.href = `/messages?tab=groups&group_id=${encodeURIComponent(groupId)}`;
                    } else {
                        window.location.href = '/messages?tab=groups';
                    }
                }

                function filterByMember(memberUuid) {
                    const groupId = document.getElementById('group-filter').value;
                    if (memberUuid && groupId) {
                        window.location.href = `/messages?tab=groups&group_id=${encodeURIComponent(groupId)}&member_uuid=${encodeURIComponent(memberUuid)}`;
                    } else if (groupId) {
                        window.location.href = `/messages?tab=groups&group_id=${encodeURIComponent(groupId)}`;
                    }
                }

                function filterByAttachments(checked) {
                    const groupId = document.getElementById('group-filter').value;
                    const memberUuid = document.getElementById('member-filter').value;
                    let url = '/messages?tab=groups';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (memberUuid) url += `&member_uuid=${encodeURIComponent(memberUuid)}`;
                    if (checked) url += '&attachments_only=true';
                    window.location.href = url;
                }

                function filterByDate(date) {
                    const groupId = document.getElementById('group-filter').value;
                    const memberUuid = document.getElementById('member-filter').value;
                    const attachments = document.getElementById('attachments-filter').checked;
                    let url = '/messages?tab=groups';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (memberUuid) url += `&member_uuid=${encodeURIComponent(memberUuid)}`;
                    if (attachments) url += '&attachments_only=true';
                    if (date) url += `&start_date=${date}&end_date=${date}`;
                    window.location.href = url;
                }

                // Functions for All Messages tab filtering
                function filterByGroupAll(groupId) {
                    const senderUuid = document.getElementById('sender-filter').value;
                    const date = document.getElementById('date-filter').value;
                    const attachments = document.getElementById('attachments-filter').checked;
                    let url = '/messages?tab=all';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (senderUuid) url += `&sender_uuid=${encodeURIComponent(senderUuid)}`;
                    if (attachments) url += '&attachments_only=true';
                    if (date) url += `&start_date=${date}&end_date=${date}`;
                    window.location.href = url;
                }

                function filterByMemberAll(senderUuid) {
                    const groupId = document.getElementById('group-filter').value;
                    const date = document.getElementById('date-filter').value;
                    const attachments = document.getElementById('attachments-filter').checked;
                    let url = '/messages?tab=all';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (senderUuid) url += `&sender_uuid=${encodeURIComponent(senderUuid)}`;
                    if (attachments) url += '&attachments_only=true';
                    if (date) url += `&start_date=${date}&end_date=${date}`;
                    window.location.href = url;
                }

                function filterByDateAll(date) {
                    const groupId = document.getElementById('group-filter').value;
                    const senderUuid = document.getElementById('sender-filter').value;
                    const attachments = document.getElementById('attachments-filter').checked;
                    let url = '/messages?tab=all';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (senderUuid) url += `&sender_uuid=${encodeURIComponent(senderUuid)}`;
                    if (attachments) url += '&attachments_only=true';
                    if (date) url += `&start_date=${date}&end_date=${date}`;
                    window.location.href = url;
                }

                function filterByAttachmentsAll(checked) {
                    const groupId = document.getElementById('group-filter').value;
                    const senderUuid = document.getElementById('sender-filter').value;
                    const date = document.getElementById('date-filter').value;
                    let url = '/messages?tab=all';
                    if (groupId) url += `&group_id=${encodeURIComponent(groupId)}`;
                    if (senderUuid) url += `&sender_uuid=${encodeURIComponent(senderUuid)}`;
                    if (checked) url += '&attachments_only=true';
                    if (date) url += `&start_date=${date}&end_date=${date}`;
                    window.location.href = url;
                }

                // Initialize default tab
                document.addEventListener('DOMContentLoaded', function() {
                    const urlParams = new URLSearchParams(window.location.search);
                    const tab = urlParams.get('tab') || 'groups';

                    const tabButton = document.querySelector(`[onclick="showTab('${tab}')"]`);
                    if (tabButton) {
                        tabButton.classList.add('active');
                    }

                    const tabContent = document.getElementById(tab + '-tab');
                    if (tabContent) {
                        tabContent.classList.add('active');
                    }

                    // Show/hide member filter based on group selection
                    const groupFilter = document.getElementById('group-filter');
                    if (groupFilter) {
                        groupFilter.addEventListener('change', function() {
                            const memberContainer = document.getElementById('member-filter-container');
                            if (memberContainer) {
                                if (this.value) {
                                    memberContainer.style.display = 'block';
                                } else {
                                    memberContainer.style.display = 'none';
                                }
                            }
                        });
                    }
                });

                // Activity Tab Functions - Old Version Style
                function loadActivityData() {
                    // Get date from global filter
                    const dateMode = document.getElementById('global-date-mode').value;
                    let date = dateMode === 'specific' ? document.getElementById('global-date').value : '';

                    // If no specific date and using specific mode, default to today
                    if (dateMode === 'specific' && !date) {
                        const today = new Date();
                        date = today.getFullYear() + '-' +
                            String(today.getMonth() + 1).padStart(2, '0') + '-' +
                            String(today.getDate()).padStart(2, '0');
                    }

                    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                    let url = `/api/activity/hourly?date=${date}&timezone=${encodeURIComponent(timezone)}`;

                    // Use global filters
                    const groupId = document.getElementById('global-group-filter').value;
                    if (groupId) {
                        url += `&group_id=${encodeURIComponent(groupId)}`;
                    }

                    fetch(url)
                        .then(response => response.json())
                        .then(data => {
                            renderCharts(data);
                        })
                        .catch(error => {
                            console.error('Error loading activity data:', error);
                            document.getElementById('activity-charts-container').innerHTML =
                                '<div class="text-center text-muted"><p>Error loading activity data</p></div>';
                        });
                }

                function renderCharts(data) {
                    const container = document.getElementById('activity-charts-container');
                    container.innerHTML = '';

                    if (!data.hourly_data || Object.keys(data.hourly_data).length === 0) {
                        container.innerHTML = '<div class="text-center text-muted">No activity data for this date</div>';
                        return;
                    }

                    // Colors for different groups
                    const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14'];
                    let colorIndex = 0;

                    for (const [groupName, hourlyData] of Object.entries(data.hourly_data)) {
                        const color = colors[colorIndex % colors.length];
                        colorIndex++;

                        const chartDiv = document.createElement('div');
                        chartDiv.className = 'chart-container';
                        chartDiv.innerHTML = `
                            <div class="chart" id="chart-${groupName.replace(/[^a-zA-Z0-9]/g, '')}"></div>
                        `;
                        container.appendChild(chartDiv);

                        renderBarChart(`chart-${groupName.replace(/[^a-zA-Z0-9]/g, '')}`, hourlyData, color);
                    }
                }

                function renderBarChart(containerId, data, color) {
                    const container = document.getElementById(containerId);
                    const maxValue = Math.max(...Object.values(data));
                    const totalMessages = Object.values(data).reduce((sum, val) => sum + val, 0);
                    const chartHeight = 200;

                    let chartHtml = `<div class="chart-title">Activity Pattern - ${totalMessages} messages</div><div class="bar-chart">`;

                    for (let hour = 0; hour < 24; hour++) {
                        const value = data[hour] || 0;
                        const barHeight = maxValue > 0 ? (value / maxValue) * chartHeight : 0;

                        chartHtml += `
                            <div class="bar-container">
                                <div class="bar" style="height: ${barHeight}px; background-color: ${color};" title="${hour}:00 - ${value} messages">
                                    ${value > 0 ? `<span class="bar-count" style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #666; white-space: nowrap;">${value}</span>` : ''}
                                </div>
                                <div class="bar-label">${hour}</div>
                            </div>
                        `;
                    }

                    chartHtml += '</div>';
                    container.innerHTML = chartHtml;
                }

                // Auto-load data when activity tab is shown
                document.addEventListener('DOMContentLoaded', function() {
                    if (window.location.href.includes('tab=activity')) {
                        // Load activity data automatically when tab is shown
                        setTimeout(loadActivityData, 500);
                    }
                });

                // Global filter functions
                function toggleDateFilter() {
                    const dateMode = document.getElementById('global-date-mode').value;
                    const dateInput = document.getElementById('global-date');

                    if (dateMode === 'all') {
                        dateInput.style.display = 'none';
                        dateInput.value = '';
                    } else {
                        dateInput.style.display = 'block';
                        // Set to today if no value
                        if (!dateInput.value) {
                            const today = new Date();
                            dateInput.value = today.getFullYear() + '-' +
                                String(today.getMonth() + 1).padStart(2, '0') + '-' +
                                String(today.getDate()).padStart(2, '0');
                        }
                    }
                    applyGlobalFilters();
                }

                function applyGlobalFilters() {
                    const currentUrl = new URL(window.location);
                    const currentTab = currentUrl.searchParams.get('tab') || 'groups';

                    // Get filter values
                    const groupId = document.getElementById('global-group-filter').value;
                    const senderId = document.getElementById('global-sender-filter').value;
                    const dateMode = document.getElementById('global-date-mode').value;
                    const date = dateMode === 'specific' ? document.getElementById('global-date').value : '';
                    const attachmentsOnly = document.getElementById('global-attachments-only').checked;

                    // Build new URL with filters
                    const newUrl = new URL('/messages', window.location.origin);
                    newUrl.searchParams.set('tab', currentTab);

                    if (groupId) newUrl.searchParams.set('group_id', groupId);
                    if (senderId) newUrl.searchParams.set('sender_uuid', senderId);
                    if (date) newUrl.searchParams.set('date', date);
                    if (attachmentsOnly) newUrl.searchParams.set('attachments_only', 'true');

                    window.location.href = newUrl.toString();
                }

                function updateSenderOptions() {
                    // When group changes, update sender dropdown to show only members of that group
                    const groupId = document.getElementById('global-group-filter').value;
                    const currentUrl = new URL(window.location);
                    const currentTab = currentUrl.searchParams.get('tab') || 'groups';

                    // Navigate to update the sender options based on selected group
                    const newUrl = new URL('/messages', window.location.origin);
                    newUrl.searchParams.set('tab', currentTab);
                    if (groupId) newUrl.searchParams.set('group_id', groupId);

                    window.location.href = newUrl.toString();
                }

                function clearGlobalFilters() {
                    const currentUrl = new URL(window.location);
                    const currentTab = currentUrl.searchParams.get('tab') || 'groups';

                    // Navigate to clean URL with just the tab
                    window.location.href = `/messages?tab=${currentTab}`;
                }

                function switchTab(newTab) {
                    // Get current filter values
                    const groupId = document.getElementById('global-group-filter').value;
                    const senderId = document.getElementById('global-sender-filter').value;
                    const dateMode = document.getElementById('global-date-mode').value;
                    const date = dateMode === 'specific' ? document.getElementById('global-date').value : '';
                    const attachmentsOnly = document.getElementById('global-attachments-only').checked;

                    // Build new URL with current filters
                    const newUrl = new URL('/messages', window.location.origin);
                    newUrl.searchParams.set('tab', newTab);

                    if (groupId) newUrl.searchParams.set('group_id', groupId);
                    if (senderId) newUrl.searchParams.set('sender_uuid', senderId);
                    if (date) newUrl.searchParams.set('date', date);
                    if (attachmentsOnly) newUrl.searchParams.set('attachments_only', 'true');

                    window.location.href = newUrl.toString();
                }
        """

    def _render_global_filters(self, query: Dict[str, Any]) -> str:
        """Render global filter controls that work across all tabs."""
        # Get current filter values
        group_filter = query.get('group_id', [None])[0]
        sender_filter = query.get('sender_uuid', [None])[0]
        attachments_only = query.get('attachments_only', [None])[0] == 'true'
        date_param = query.get('date', [query.get('start_date', [None])[0]])[0]

        # Default to empty (All Messages) if no date is specified
        if date_param is None:
            date_param = ''

        # Get only monitored groups for dropdown
        groups = self.db.get_monitored_groups()
        group_options = '<option value="">All Groups</option>'
        for group in groups:
            group_name = group.group_name or group.group_id
            selected = 'selected' if group_filter == group.group_id else ''
            group_options += f'<option value="{group.group_id}" {selected}>{group_name}</option>'

        # Get users for dropdown - if group is selected, only show members of that group
        if group_filter:
            users = self.db.get_group_members(group_filter)
        else:
            users = self.db.get_all_users()

        user_options = '<option value="">All Senders</option>'
        for user in users:
            # Only include users who have messages in the database
            message_count = self.db.get_message_count_filtered(sender_uuid=user.uuid)
            if message_count == 0:
                continue

            if user.friendly_name:
                display_name = user.friendly_name
            elif user.phone_number:
                display_name = user.phone_number
            else:
                display_name = f"User {user.uuid}"

            selected = 'selected' if sender_filter == user.uuid else ''
            user_options += f'<option value="{user.uuid}" {selected}>{display_name}</option>'

        attachments_checked = 'checked' if attachments_only else ''

        return f"""
        <div class="global-filters" style="background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div class="filter-row" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <div class="filter-group" style="min-width: 120px;">
                    <label for="global-group-filter" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">Group:</label>
                    <select id="global-group-filter" onchange="updateSenderOptions()" style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 100%;">
                        {group_options}
                    </select>
                </div>
                <div class="filter-group" style="min-width: 120px;">
                    <label for="global-sender-filter" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">Sender:</label>
                    <select id="global-sender-filter" onchange="applyGlobalFilters()" style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; width: 100%;">
                        {user_options}
                    </select>
                </div>
                <div class="filter-group" style="min-width: 140px;">
                    <label for="global-date" style="display: block; margin-bottom: 3px; font-weight: bold; font-size: 0.9em;">Date:</label>
                    <div style="display: flex; gap: 5px; align-items: center;">
                        <select id="global-date-mode" onchange="toggleDateFilter()" style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; flex: 1;">
                            <option value="all" {'selected' if date_param == '' else ''}>All Messages</option>
                            <option value="specific" {'selected' if date_param != '' else ''}>Specific Date</option>
                        </select>
                        <input type="date" id="global-date" value="{date_param if date_param else ''}" onchange="applyGlobalFilters()" style="padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; flex: 1; {'display: none;' if date_param == '' else ''}" />
                    </div>
                </div>
                <div class="filter-group" style="display: flex; align-items: center; margin-top: 20px;">
                    <label style="display: flex; align-items: center; font-size: 0.9em;">
                        <input type="checkbox" id="global-attachments-only" {attachments_checked} onchange="applyGlobalFilters()" style="margin-right: 5px;" />
                        Attachments Only
                    </label>
                </div>
                <div class="filter-group" style="margin-top: 20px;">
                    <button onclick="clearGlobalFilters()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">Clear</button>
                </div>
            </div>
        </div>
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        tab = query.get('tab', ['groups'])[0]

        # Render different tab contents based on tab parameter
        if tab == 'groups':
            content = self._render_groups_tab(query)
        elif tab == 'senders':
            content = self._render_senders_tab(query)
        elif tab == 'all':
            content = self._render_all_tab(query)
        elif tab == 'sentiment':
            content = self._render_sentiment_tab(query)
        elif tab == 'summary':
            content = self._render_summary_tab(query)
        else:
            content = self._render_groups_tab(query)

        # Generate global filters
        global_filters = self._render_global_filters(query)

        return f"""
            {global_filters}

            <div class="tabs">
                <a href="javascript:void(0)" onclick="switchTab('groups')" class="tab-btn {'active' if tab == 'groups' else ''}">By Group</a>
                <a href="javascript:void(0)" onclick="switchTab('senders')" class="tab-btn {'active' if tab == 'senders' else ''}">By Sender</a>
                <a href="javascript:void(0)" onclick="switchTab('all')" class="tab-btn {'active' if tab == 'all' else ''}">All Messages</a>
                <a href="javascript:void(0)" onclick="switchTab('sentiment')" class="tab-btn {'active' if tab == 'sentiment' else ''}">Sentiment</a>
                <a href="javascript:void(0)" onclick="switchTab('summary')" class="tab-btn {'active' if tab == 'summary' else ''}">Summary</a>
            </div>

            <div id="{tab}-tab" class="tab-content active">
                {content}
            </div>
        """

    def _render_groups_tab(self, query: Dict[str, Any]) -> str:
        """Render the By Group tab content."""
        monitored_groups = self.db.get_monitored_groups()

        if not monitored_groups:
            return """
            <div class="tab-content">
                <div class="no-messages">No monitored groups found. Go to the Groups page to enable monitoring.</div>
            </div>
            """

        # Get filter parameters
        date_param = query.get('date', [query.get('start_date', [None])[0]])[0]
        sender_filter = query.get('sender_uuid', [None])[0]
        attachments_only = query.get('attachments_only', [None])[0] == 'true'
        group_filter = query.get('group_id', [None])[0]

        # Default to empty (All Messages) if no date parameter was provided
        if date_param is None:
            date_param = ''

        # Get user timezone for filtering
        user_timezone = self.get_user_timezone(query)

        # Filter groups based on group_filter parameter
        if group_filter:
            monitored_groups = [g for g in monitored_groups if g.group_id == group_filter]

        groups_html = ""
        groups_with_messages = []

        for group in monitored_groups:
            try:
                # Get message count for this group with ALL current filters applied
                if date_param == "":
                    message_count = self.db.get_message_count_filtered(
                        group_id=group.group_id,
                        sender_uuid=sender_filter,
                        attachments_only=attachments_only,
                        start_date=None,
                        end_date=None,
                        user_timezone=user_timezone
                    )
                else:
                    message_count = self.db.get_message_count_filtered(
                        group_id=group.group_id,
                        sender_uuid=sender_filter,
                        attachments_only=attachments_only,
                        start_date=date_param,
                        end_date=date_param,
                        user_timezone=user_timezone
                    )

                # Only show groups that have messages matching the current filters
                if message_count > 0:
                    groups_with_messages.append((group, message_count))

            except Exception as e:
                logging.error(f"Error getting group stats: {e}")
                continue

        # If no groups have matching messages, show appropriate message
        if not groups_with_messages:
            if sender_filter or attachments_only or date_param or group_filter:
                return """
                <div class="no-messages">
                    No groups found matching the current filters. Try adjusting your filters or clearing them to see all groups.
                </div>
                """
            else:
                return """
                <div class="no-messages">
                    No monitored groups have any messages yet.
                </div>
                """

        # Generate HTML for groups with messages
        for group, message_count in groups_with_messages:
            try:
                # Generate activity chart for this group
                activity_chart = self._generate_activity_chart(
                    group.group_id,
                    date_param,
                    sender_filter,
                    attachments_only,
                    user_timezone
                )

                # Build filter parameters for View Messages link
                view_params = f"tab=all&group_id={quote(group.group_id)}"
                if date_param:
                    view_params += f"&date={date_param}"
                if sender_filter:
                    view_params += f"&sender_uuid={quote(sender_filter)}"
                if attachments_only:
                    view_params += "&attachments_only=true"

                groups_html += f"""
                <div class="group-card" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div>
                            <h4 style="margin: 0 0 5px 0;">{group.group_name or 'Unnamed Group'}</h4>
                            <p style="margin: 0; color: #666;">{message_count} messages • {group.member_count or 0} members</p>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <a href="/messages?{view_params}" class="btn btn-secondary">View Messages</a>
                        </div>
                    </div>
                    {activity_chart}
                </div>
                """
            except Exception as e:
                logging.error(f"Error generating group card for {group.group_id}: {e}")
                continue

        return groups_html

    def _generate_activity_chart(self, group_id: str, date_param: str, sender_filter: str, attachments_only: bool, user_timezone: str) -> str:
        """Generate activity chart HTML for a specific group."""
        try:
            if date_param:
                # For specific date, use the hourly counts method
                from datetime import datetime
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                hourly_data = self.db.get_hourly_message_counts(target_date, user_timezone)

                # Filter for this specific group
                group_data = [d for d in hourly_data if d['group_id'] == group_id]

                # Convert to hour -> count mapping
                activity_data = {}
                for entry in group_data:
                    activity_data[entry['hour']] = entry['message_count']
            else:
                # For all dates, use filtered message count for each hour
                # This is a simplified approach - we'll get total counts by hour across all days
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()

                    # Build WHERE conditions
                    conditions = ["m.group_id = ?"]
                    params = [group_id]

                    if sender_filter:
                        conditions.append("m.sender_uuid = ?")
                        params.append(sender_filter)

                    if attachments_only:
                        conditions.append("EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id)")

                    where_clause = "WHERE " + " AND ".join(conditions)

                    # Get hourly counts across all days with timezone conversion
                    try:
                        from zoneinfo import ZoneInfo
                        from datetime import datetime

                        # Calculate timezone offset for SQL query
                        tz = ZoneInfo(user_timezone)
                        now = datetime.now(tz)
                        offset_seconds = tz.utcoffset(now).total_seconds()

                        cursor.execute(f"""
                            SELECT
                                CAST((m.timestamp / 1000 + ?) / 3600 % 24 AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, [offset_seconds] + params)
                    except ImportError:
                        # Fallback to UTC if zoneinfo not available
                        cursor.execute(f"""
                            SELECT
                                CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, params)

                    activity_data = {}
                    for row in cursor.fetchall():
                        activity_data[row['hour']] = row['message_count']

            if not activity_data:
                return '<div class="activity-chart" style="padding: 10px; text-align: center; color: #666; font-style: italic;">No activity data available</div>'

            # Calculate max count for scaling and total count
            max_count = max(activity_data.values()) if activity_data else 1
            total_count = sum(activity_data.values())

            # Generate chart HTML
            bars_html = ""
            for hour in range(24):
                count = activity_data.get(hour, 0)
                height_percent = (count / max_count * 100) if max_count > 0 else 0

                bars_html += f"""
                <div class="bar-container" title="{hour:02d}:00 - {count} messages">
                    <div class="bar" style="height: {height_percent}%; background-color: #007bff; position: relative;">
                        {'<span class="bar-count" style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #666; white-space: nowrap;">' + str(count) + '</span>' if count > 0 else ''}
                    </div>
                    <div class="bar-label">{hour:02d}</div>
                </div>
                """

            # Handle multi-day data (if date_param is empty, show stacked view)
            chart_title = "Activity Pattern"
            if date_param:
                chart_title += f" ({date_param}) - {total_count} total messages"
            elif max_count > 0:
                chart_title += f" (All Days) - {total_count} total messages"

            return f"""
            <div class="chart-container">
                <div class="chart-title">Activity Pattern - {total_count} messages</div>
                <div class="bar-chart">
                    {bars_html}
                </div>
            </div>
            """

        except Exception as e:
            logging.error(f"Error generating activity chart for group {group_id}: {e}")
            return '<div class="activity-chart" style="padding: 10px; text-align: center; color: #666; font-style: italic;">Error loading activity data</div>'

    def _render_senders_tab(self, query: Dict[str, Any]) -> str:
        """Render the By Sender tab content."""
        # Get filter parameters
        date_param = query.get('date', [query.get('start_date', [None])[0]])[0]
        group_filter = query.get('group_id', [None])[0]
        attachments_only = query.get('attachments_only', [None])[0] == 'true'
        sender_filter = query.get('sender_uuid', [None])[0]

        # Default to empty (All Messages) if no date parameter was provided
        if date_param is None:
            date_param = ''

        # Get user timezone for filtering
        user_timezone = self.get_user_timezone(query)

        # Get sender statistics across all monitored groups
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Use the centralized filter builder for consistency with All Messages tab
                # Convert date_param to proper format for the centralized method
                start_date = date_param if date_param and date_param.strip() else None

                # Use centralized filter builder (same as All Messages tab)
                where_conditions, params = self.db._build_message_query_filters(
                    group_id=group_filter,
                    sender_uuid=sender_filter,
                    start_date=start_date,
                    end_date=start_date,  # For single date filtering
                    user_timezone=user_timezone,
                    attachments_only=attachments_only,
                    monitored_only=not group_filter  # If no specific group, show only monitored
                )

                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)

                # Get sender statistics - use same display logic as All Messages
                query_sql = f"""
                    SELECT
                        m.sender_uuid,
                        {get_user_display_sql('u')} as sender_display,
                        u.phone_number,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT m.group_id) as group_count,
                        MIN(m.timestamp) as first_message,
                        MAX(m.timestamp) as last_message
                    FROM messages m
                    LEFT JOIN users u ON m.sender_uuid = u.uuid
                    LEFT JOIN groups g ON m.group_id = g.group_id
                    {where_clause}
                    GROUP BY m.sender_uuid
                    HAVING COUNT(*) > 0
                    ORDER BY message_count DESC
                """

                cursor.execute(query_sql, params)
                sender_stats = cursor.fetchall()

        except Exception as e:
            logging.error(f"Error getting sender statistics: {e}")
            return f'<div class="error">Error loading sender statistics: {e}</div>'

        if not sender_stats:
            if sender_filter or group_filter or attachments_only or date_param:
                return """
                <div class="no-messages">
                    No senders found matching the current filters. Try adjusting your filters or clearing them to see all senders.
                </div>
                """
            else:
                return """
                <div class="no-messages">
                    No senders found in monitored groups. Make sure groups are being monitored and have messages.
                </div>
                """

        # Generate HTML for each sender
        senders_html = ""
        for sender in sender_stats:
            try:
                sender_uuid = sender['sender_uuid']

                # Use the consistent sender_display from database query (same as All Messages)
                sender_name = sender['sender_display']

                # Create subtitle from additional info
                phone_number = sender['phone_number']
                if phone_number and phone_number != sender_name:
                    sender_subtitle = phone_number
                else:
                    sender_subtitle = f"UUID: {sender_uuid}"

                message_count = sender['message_count']
                group_count = sender['group_count']

                # Format timestamps
                first_msg = self.format_timestamp(sender['first_message'], user_timezone)
                last_msg = self.format_timestamp(sender['last_message'], user_timezone)

                # Generate activity chart for this sender
                activity_chart = self._generate_sender_activity_chart(
                    sender_uuid,
                    date_param,
                    group_filter,
                    attachments_only,
                    user_timezone
                )

                # Build filter parameters for View Messages link
                view_params = f"tab=all&sender_uuid={quote(sender_uuid)}"
                if date_param:
                    view_params += f"&date={date_param}"
                if group_filter:
                    view_params += f"&group_id={quote(group_filter)}"
                if attachments_only:
                    view_params += "&attachments_only=true"

                senders_html += f"""
                <div class="sender-card" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div>
                            <h4 style="margin: 0 0 5px 0;">{sender_name}</h4>
                            <p style="margin: 0; color: #666;">{message_count} messages • {group_count} groups</p>
                            <p style="margin: 5px 0 0 0; color: #888; font-size: 0.9em;">{sender_subtitle}</p>
                            <p style="margin: 5px 0 0 0; color: #888; font-size: 0.85em;">
                                First: {first_msg} • Last: {last_msg}
                            </p>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <a href="/messages?{view_params}" class="btn btn-secondary">View Messages</a>
                        </div>
                    </div>
                    {activity_chart}
                </div>
                """
            except Exception as e:
                logging.error(f"Error generating sender card for {sender_uuid}: {e}")
                continue

        return senders_html

    def _generate_sender_activity_chart(self, sender_uuid: str, date_param: str, group_filter: str, attachments_only: bool, user_timezone: str) -> str:
        """Generate activity chart HTML for a specific sender."""
        try:
            if date_param:
                # For specific date, get hourly counts for this sender
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()

                    # Build conditions for the specific date
                    conditions = ["m.sender_uuid = ?"]
                    params = [sender_uuid]

                    if group_filter:
                        conditions.append("m.group_id = ?")
                        params.append(group_filter)

                    if attachments_only:
                        conditions.append("EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id)")

                    # Add date filter with timezone support
                    conditions.append("DATE(datetime(m.timestamp/1000, 'unixepoch', ?)) = ?")
                    try:
                        from zoneinfo import ZoneInfo
                        from datetime import datetime
                        tz = ZoneInfo(user_timezone)
                        now = datetime.now(tz)
                        offset_hours = int(tz.utcoffset(now).total_seconds() / 3600)
                        offset_str = f"{'+' if offset_hours >= 0 else ''}{offset_hours} hours"
                        params.extend([offset_str, date_param])
                    except:
                        params.extend(['0 hours', date_param])

                    where_clause = "WHERE " + " AND ".join(conditions)

                    # Get hourly counts with timezone conversion
                    try:
                        from zoneinfo import ZoneInfo
                        from datetime import datetime
                        tz = ZoneInfo(user_timezone)
                        now = datetime.now(tz)
                        offset_seconds = tz.utcoffset(now).total_seconds()

                        cursor.execute(f"""
                            SELECT
                                CAST((m.timestamp / 1000 + ?) / 3600 % 24 AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, [offset_seconds] + params)
                    except ImportError:
                        # Fallback to UTC
                        cursor.execute(f"""
                            SELECT
                                CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, params)

                    activity_data = {}
                    for row in cursor.fetchall():
                        activity_data[row['hour']] = row['message_count']
            else:
                # For all dates, use the same logic as groups but for sender
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()

                    # Build WHERE conditions
                    conditions = ["m.sender_uuid = ?"]
                    params = [sender_uuid]

                    if group_filter:
                        conditions.append("m.group_id = ?")
                        params.append(group_filter)

                    if attachments_only:
                        conditions.append("EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id)")

                    where_clause = "WHERE " + " AND ".join(conditions)

                    # Get hourly counts across all days with timezone conversion
                    try:
                        from zoneinfo import ZoneInfo
                        from datetime import datetime

                        # Calculate timezone offset for SQL query
                        tz = ZoneInfo(user_timezone)
                        now = datetime.now(tz)
                        offset_seconds = tz.utcoffset(now).total_seconds()

                        cursor.execute(f"""
                            SELECT
                                CAST((m.timestamp / 1000 + ?) / 3600 % 24 AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, [offset_seconds] + params)
                    except ImportError:
                        # Fallback to UTC if zoneinfo not available
                        cursor.execute(f"""
                            SELECT
                                CAST(strftime('%H', datetime(m.timestamp/1000, 'unixepoch')) AS INTEGER) as hour,
                                COUNT(*) as message_count
                            FROM messages m
                            {where_clause}
                            GROUP BY hour
                            ORDER BY hour
                        """, params)

                    activity_data = {}
                    for row in cursor.fetchall():
                        activity_data[row['hour']] = row['message_count']

            if not activity_data:
                return '<div class="activity-chart" style="padding: 10px; text-align: center; color: #666; font-style: italic;">No activity data available</div>'

            # Calculate max count for scaling and total count
            max_count = max(activity_data.values()) if activity_data else 1
            total_count = sum(activity_data.values())

            # Generate chart HTML using same structure as groups
            bars_html = ""
            for hour in range(24):
                count = activity_data.get(hour, 0)
                height_percent = (count / max_count * 100) if max_count > 0 else 0

                bars_html += f"""
                <div class="bar-container" title="{hour:02d}:00 - {count} messages">
                    <div class="bar" style="height: {height_percent}%; background-color: #007bff; position: relative;">
                        {'<span class="bar-count" style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #666; white-space: nowrap;">' + str(count) + '</span>' if count > 0 else ''}
                    </div>
                    <div class="bar-label">{hour:02d}</div>
                </div>
                """

            # Handle multi-day data (if date_param is empty, show stacked view)
            chart_title = "Activity Pattern"
            if date_param:
                chart_title += f" ({date_param}) - {total_count} total messages"
            elif max_count > 0:
                chart_title += f" (All Days) - {total_count} total messages"

            return f"""
            <div class="chart-container">
                <div class="chart-title">Activity Pattern - {total_count} messages</div>
                <div class="bar-chart">
                    {bars_html}
                </div>
            </div>
            """

        except Exception as e:
            logging.error(f"Error generating sender activity chart for {sender_uuid}: {e}")
            return '<div class="activity-chart" style="padding: 10px; text-align: center; color: #666; font-style: italic;">Error loading activity data</div>'

    def _render_all_tab(self, query: Dict[str, Any]) -> str:
        """Render the All Messages tab content."""
        page = int(query.get('page', [1])[0])
        per_page = 50
        offset = (page - 1) * per_page

        # Get optional filters
        group_filter = query.get('group_id', [None])[0]
        sender_filter = query.get('sender_uuid', [None])[0]
        attachments_only = query.get('attachments_only', [None])[0] == 'true'
        start_date = query.get('start_date', [None])[0]
        end_date = query.get('end_date', [None])[0]

        # Handle 'date' parameter (for unified interface) - convert to start_date/end_date
        date_param = query.get('date', [None])[0]
        if date_param and not start_date and not end_date:
            start_date = date_param
            end_date = date_param
        elif date_param is None and not start_date and not end_date:
            # Default to empty (All Messages) if no date is specified
            date_param = ''
            start_date = None
            end_date = None
        elif date_param == "":
            # Empty string means show all messages (no date filtering)
            start_date = None
            end_date = None

        # Get messages using database filtering
        user_timezone = self.get_user_timezone(query)
        try:
            messages = self.db.get_messages_by_group_with_names_filtered(
                group_id=group_filter,
                sender_uuid=sender_filter,
                attachments_only=attachments_only,
                start_date=start_date,
                end_date=end_date,
                user_timezone=user_timezone,
                limit=per_page,
                offset=offset
            )
            total_messages = self.db.get_message_count_filtered(
                group_id=group_filter,
                sender_uuid=sender_filter,
                attachments_only=attachments_only,
                start_date=start_date,
                end_date=end_date,
                user_timezone=user_timezone
            )
        except Exception as e:
            return f'<div class="error">Database error: {e}</div>'

        total_pages = max(1, (total_messages + per_page - 1) // per_page)

        # Get monitored groups for filter dropdown
        monitored_groups = self.db.get_monitored_groups()

        # Build messages HTML
        messages_html = ""
        if not messages:
            messages_html = '<div class="no-messages">No messages found</div>'
        else:
            for msg in messages:
                message_text = msg.get('message_text', '')
                if not message_text or message_text.strip() == '':
                    continue
                if len(message_text) > 200:
                    message_text = message_text[:200] + '...'

                # Process mentions in message text
                message_id = msg.get('id')
                message_text = self._process_mentions(message_text, message_id)

                # Format timestamp using server-side formatting with user timezone
                timestamp_ms = msg.get('timestamp')
                timestamp_display = self.format_timestamp(timestamp_ms, user_timezone)

                # Get attachments and build attachment HTML
                attachments_html = ""
                attachments = msg.get('attachments', [])
                if attachments:
                    attachments_html = '<div class="attachments">'
                    for attachment in attachments:
                        attachment_id = attachment.get('attachment_id', '')
                        file_name = attachment.get('file_name', attachment.get('filename', 'Unknown'))
                        content_type = attachment.get('content_type', '')
                        if attachment_id and content_type and content_type.startswith('image/'):
                            attachments_html += f'<img src="/attachment/{attachment_id}" alt="{file_name}" class="attachment-image">'
                        elif attachment_id and content_type and content_type.startswith('video/'):
                            attachments_html += f'<video src="/attachment/{attachment_id}" autoplay loop muted playsinline class="attachment-video" title="{file_name}"></video>'
                        elif attachment_id:
                            attachments_html += f'<div class="attachment-file">📎 {file_name}</div>'
                    attachments_html += '</div>'

                sender_display = msg.get('sender_display', f"User {msg.get('sender', 'Unknown')[:8]}...")
                group_display = msg.get('group_display', 'Unnamed Group')

                messages_html += f"""
                <div class="message-item">
                    <div class="message-header">
                        <div class="message-sender">
                            <strong>{sender_display}</strong>
                            <span class="group-indicator">in</span>
                            <strong class="group-name">{group_display}</strong>
                        </div>
                        <span class="timestamp">{timestamp_display}</span>
                    </div>
                    <div class="message-text">{message_text}</div>
                    {attachments_html}
                </div>
                """

        # Pagination
        filter_param = ""
        if group_filter:
            filter_param += f"&group_id={quote(group_filter)}"
        if sender_filter:
            filter_param += f"&sender_uuid={quote(sender_filter)}"
        if attachments_only:
            filter_param += "&attachments_only=true"
        if start_date:
            filter_param += f"&start_date={quote(start_date)}"
        if end_date:
            filter_param += f"&end_date={quote(end_date)}"

        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="pagination">'
            if page > 1:
                pagination_html += f'<a href="/messages?tab=all&page={page-1}{filter_param}" class="page-btn">← Previous</a>'

            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            for p in range(start_page, end_page + 1):
                if p == page:
                    pagination_html += f'<span class="page-btn current">{p}</span>'
                else:
                    pagination_html += f'<a href="/messages?tab=all&page={p}{filter_param}" class="page-btn">{p}</a>'

            if page < total_pages:
                pagination_html += f'<a href="/messages?tab=all&page={page+1}{filter_param}" class="page-btn">Next →</a>'
            pagination_html += '</div>'

        # Build group dropdown options
        group_options = '<option value="">All Groups</option>'
        for group in monitored_groups:
            selected = 'selected' if group.group_id == group_filter else ''
            group_options += f'<option value="{group.group_id}" {selected}>{group.group_name or "Unnamed Group"}</option>'

        # Get group members for sender dropdown if group is selected
        member_options = '<option value="">All Members</option>'
        if group_filter:
            try:
                members = self.db.get_group_members(group_filter)
                for member in members:
                    selected = 'selected' if member.uuid == sender_filter else ''
                    member_name = member.friendly_name or member.phone_number or member.uuid
                    member_options += f'<option value="{member.uuid}" {selected}>{member_name}</option>'
            except Exception as e:
                pass

        return f"""
            <div class="stats">
                <div><strong>Total Messages:</strong> {total_messages}</div>
                <div><strong>Page:</strong> {page} of {total_pages}</div>
            </div>


            <div class="messages-container">
                {messages_html}
            </div>

            {pagination_html}
        """

    def _process_mentions(self, message_text: str, message_id: int = None) -> str:
        """Process mention placeholders in message text with actual user names."""
        if not message_text or not message_id:
            return message_text

        # Get mentions for this message
        mentions = self.db.get_message_mentions(message_id)
        if not mentions:
            # Fallback to generic replacement
            mention_placeholder = '\ufffc'  # Unicode object replacement character
            if mention_placeholder in message_text:
                message_text = message_text.replace(
                    mention_placeholder,
                    '<span class="mention">@mention</span>'
                )
            return message_text

        # Sort mentions by position (reverse order to avoid position shifting)
        mentions.sort(key=lambda m: m['mention_start'], reverse=True)

        # Replace each mention with actual user name
        for mention in mentions:
            start = mention['mention_start']
            length = mention['mention_length']

            # Get user display name - prefer friendly_name, then phone_number, then truncated UUID
            user_name = "unknown"
            if mention.get('friendly_name') and mention['friendly_name'].strip():
                user_name = mention['friendly_name'].strip()
            elif mention.get('phone_number') and mention['phone_number'].strip():
                user_name = mention['phone_number'].strip()
            elif mention.get('uuid'):
                user_name = mention['uuid'][:8] + "..."

            # Replace the mention placeholder at the specific position
            if start + length <= len(message_text):
                before = message_text[:start]
                after = message_text[start + length:]
                mention_html = f'<span class="mention">@{user_name}</span>'
                message_text = before + mention_html + after

        return message_text

    def _render_sentiment_tab(self, query: Dict[str, Any]) -> str:
        """Render the Sentiment Analysis tab content."""
        # Get parameters from global filters
        selected_group_id = query.get('group_id', [None])[0]
        selected_date = query.get('date', [None])[0]
        user_timezone = self.get_user_timezone(query)

        return f"""
            <div class="sentiment-tab-content">
                <h2>Sentiment Analysis</h2>
                <p>AI-powered analysis of group chat emotions and mood using global filters above</p>

                <div class="sentiment-actions" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <button type="button" onclick="showSentimentPreview()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Preview</button>
                        <button type="button" onclick="analyzeSentiment(false)" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Analyze</button>
                        <span style="color: #666; font-size: 0.9em;">Select a group and date using the filters above, then use these buttons to analyze sentiment</span>
                    </div>
                </div>

                <!-- Preview Card -->
                <div id="sentiment-preview" class="card" style="display: none; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <h3>Analysis Preview</h3>
                    <div id="sentiment-preview-content"></div>
                </div>

                <!-- Results Card -->
                <div id="sentiment-results" class="card" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>Sentiment Analysis Results</h3>
                        <button onclick="analyzeSentiment(true)" style="padding: 6px 12px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">Force Refresh</button>
                    </div>
                    <div id="sentiment-analysis-content"></div>
                </div>

                <script>
                    let currentSentimentTimezone = '{user_timezone}';

                    // Auto-load cached results if group and date are already selected from global filters
                    document.addEventListener('DOMContentLoaded', function() {{
                        const groupId = '{selected_group_id or ""}';
                        const date = '{selected_date or ""}';

                        if (groupId && date) {{
                            loadCachedSentimentResults(groupId, date);
                        }}
                    }});

                    function getGlobalFilters() {{
                        // Get current values from global filter form
                        const groupSelect = document.getElementById('global-group-filter');
                        const dateInput = document.getElementById('global-date');

                        return {{
                            groupId: groupSelect ? groupSelect.value : '',
                            date: dateInput ? dateInput.value : ''
                        }};
                    }}

                    function showSentimentPreview() {{
                        const filters = getGlobalFilters();

                        if (!filters.groupId || !filters.date) {{
                            showNotification('Please select both a group and date using the filters above', 'warning');
                            return;
                        }}

                        const url = `/api/sentiment-preview?group_id=${{encodeURIComponent(filters.groupId)}}&date=${{filters.date}}&timezone=${{encodeURIComponent(currentSentimentTimezone)}}`;

                        fetch(url)
                            .then(response => response.json())
                            .then(data => {{
                                if (data.status === 'success') {{
                                    const previewDiv = document.getElementById('sentiment-preview');
                                    const previewContent = document.getElementById('sentiment-preview-content');

                                    if (data.analyzable_messages === 0) {{
                                        previewContent.innerHTML = `
                                            <p><strong>Group:</strong> ${{data.group_name}}</p>
                                            <p><strong>Date:</strong> ${{data.date}}</p>
                                            <p><strong>Total messages:</strong> ${{data.total_messages}}</p>
                                            <p><strong>Analyzable messages:</strong> ${{data.analyzable_messages}}</p>
                                            <div style="color: #dc3545; background: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                                No substantive messages found for analysis on this date
                                            </div>`;
                                    }} else {{
                                        const efficiency = data.total_messages > 0 ? Math.round((data.analyzable_messages / data.total_messages) * 100) : 0;
                                        const efficiencyText = efficiency > 0 ? `<p><strong>Analysis efficiency:</strong> ${{efficiency}}% (${{data.filtered_out}} filtered out)</p>` : '';
                                        const timeRange = data.time_range ? `${{data.time_range.start}} to ${{data.time_range.end}}` : 'Full day';

                                        previewContent.innerHTML = `
                                            <p><strong>Group:</strong> ${{data.group_name}}</p>
                                            <p><strong>Date:</strong> ${{data.date}}</p>
                                            <p><strong>Total messages:</strong> ${{data.total_messages}}</p>
                                            <p><strong>Analyzable messages:</strong> ${{data.analyzable_messages}}</p>
                                            ${{efficiencyText}}
                                            <p><strong>Time range:</strong> ${{timeRange}}</p>
                                            <div style="color: #155724; background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                                Ready for optimized sentiment analysis with ${{data.analyzable_messages}} substantive messages
                                            </div>`;
                                    }}
                                    previewDiv.style.display = 'block';
                                }} else {{
                                    showNotification('Error getting preview: ' + data.error, 'error');
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error getting preview:', error);
                                showNotification('Error getting preview', 'error');
                            }});
                    }}

                    function loadCachedSentimentResults(groupId, date) {{
                        if (!groupId || !date) return;

                        const url = `/api/sentiment-cached?group_id=${{encodeURIComponent(groupId)}}&date=${{date}}&timezone=${{encodeURIComponent(currentSentimentTimezone)}}`;

                        fetch(url)
                            .then(response => response.json())
                            .then(data => {{
                                if (data.status === 'success' && data.cached && data.result) {{
                                    const resultsDiv = document.getElementById('sentiment-results');
                                    const contentDiv = document.getElementById('sentiment-analysis-content');

                                    contentDiv.innerHTML = `
                                        <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; color: #155724;">
                                            Showing cached analysis from ${{new Date(data.result.analyzed_at).toLocaleString()}}
                                        </div>
                                        ${{data.result.analysis}}`;

                                    resultsDiv.style.display = 'block';
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error loading cached results:', error);
                            }});
                    }}

                    function analyzeSentiment(forceRefresh = false) {{
                        const filters = getGlobalFilters();

                        if (!filters.groupId || !filters.date) {{
                            showNotification('Please select both a group and date using the filters above', 'warning');
                            return;
                        }}

                        hideAllSentimentCards();
                        const resultsDiv = document.getElementById('sentiment-results');
                        const contentDiv = document.getElementById('sentiment-analysis-content');
                        resultsDiv.style.display = 'block';

                        const actionText = forceRefresh ? 'Generating new analysis' : 'Starting sentiment analysis';
                        contentDiv.innerHTML = `<div style="text-align: center; padding: 40px; color: #666;">Analyzing sentiment with AI... ${{actionText}}</div>`;

                        // Start analysis
                        const url = forceRefresh
                            ? `/api/sentiment?group_id=${{encodeURIComponent(filters.groupId)}}&force=true&date=${{filters.date}}&timezone=${{encodeURIComponent(currentSentimentTimezone)}}`
                            : `/api/sentiment?group_id=${{encodeURIComponent(filters.groupId)}}&date=${{filters.date}}&timezone=${{encodeURIComponent(currentSentimentTimezone)}}`;

                        fetch(url)
                            .then(response => response.json())
                            .then(data => {{
                                if (data.status === 'started') {{
                                    // Poll for results
                                    pollForSentimentResults(data.job_id);
                                }} else if (data.status === 'success') {{
                                    // Immediate result
                                    contentDiv.innerHTML = data.analysis || 'Analysis completed';
                                }} else {{
                                    contentDiv.innerHTML = `<div style="color: #dc3545;">Error: ${{data.error}}</div>`;
                                }}
                            }})
                            .catch(error => {{
                                contentDiv.innerHTML = `<div style="color: #dc3545;">Error: ${{error.message}}</div>`;
                            }});
                    }}

                    function pollForSentimentResults(jobId) {{
                        const startTime = Date.now();
                        const contentDiv = document.getElementById('sentiment-analysis-content');

                        function checkSentimentStatus() {{
                            fetch(`/api/sentiment?job_id=${{jobId}}`)
                                .then(response => response.json())
                                .then(data => {{
                                    if (data.status === 'completed') {{
                                        contentDiv.innerHTML = data.result;
                                    }} else if (data.status === 'error') {{
                                        contentDiv.innerHTML = `<div style="color: #dc3545;">Error: ${{data.error}}</div>`;
                                    }} else if (data.status === 'running') {{
                                        const elapsed = Math.floor((Date.now() - startTime) / 1000);
                                        let loadingMessage = data.current_step || 'Analyzing sentiment';
                                        if (elapsed > 60) {{
                                            loadingMessage += ' - This may take a few minutes';
                                        }}
                                        contentDiv.innerHTML = `<div style="text-align: center; padding: 40px; color: #666;">${{loadingMessage}}... (${{elapsed}}s)</div>`;
                                        // Poll again in 2 seconds
                                        setTimeout(checkSentimentStatus, 2000);
                                    }}
                                }})
                                .catch(error => {{
                                    contentDiv.innerHTML = `<div style="color: #dc3545;">Failed to check status: ${{error.message}}</div>`;
                                }});
                        }}

                        // Start polling
                        checkSentimentStatus();
                    }}

                    function hideAllSentimentCards() {{
                        document.getElementById('sentiment-preview').style.display = 'none';
                        document.getElementById('sentiment-results').style.display = 'none';
                    }}
                </script>
            </div>
        """

    def _render_summary_tab(self, query: Dict[str, Any]) -> str:
        """Render the Summary tab content."""
        # Get filter parameters using the same logic as other tabs
        date_param = query.get('start_date', [None])[0]
        user_timezone = query.get('timezone', [None])[0]

        return f"""
            <div class="summary-tab-content">
                <h3>Message Summaries</h3>
                <p>AI-powered summaries of conversations.</p>

                <div style="margin-bottom: 20px;">
                    <button id="generate-summary-btn" class="btn btn-primary" onclick="generateSummaryForFilters()">
                        Generate New Summary
                    </button>
                    <small class="text-muted" style="margin-left: 10px;">Generate AI summary for selected date and filters</small>
                </div>

                <div id="summary-container">
                    <div class="text-center text-muted">Select filters and load summary data</div>
                </div>

                <script>
                    function loadSummaryForFilters() {{
                        const date = document.getElementById('date-filter').value;
                        const groupId = document.getElementById('group-filter').value;
                        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

                        if (!date) {{
                            document.getElementById('summary-container').innerHTML = '<div class="text-center text-muted">Please select a date to view summaries</div>';
                            return;
                        }}

                        const container = document.getElementById('summary-container');
                        container.innerHTML = '<div class="text-center">Loading summary...</div>';

                        fetch(`/api/summary?date=${{date}}&timezone=${{encodeURIComponent(timezone)}}${{groupId ? '&group_id=' + encodeURIComponent(groupId) : ''}}`)
                            .then(response => response.json())
                            .then(data => {{
                                renderSummaryData(data);
                            }})
                            .catch(error => {{
                                container.innerHTML = '<div class="text-center text-muted">Error loading summary data</div>';
                            }});
                    }}

                    function renderSummaryData(data) {{
                        const container = document.getElementById('summary-container');
                        container.innerHTML = '';

                        if (!data.summaries || Object.keys(data.summaries).length === 0) {{
                            container.innerHTML = '<div class="text-center text-muted">No messages to summarize for this date</div>';
                            return;
                        }}

                        for (const [groupName, summaryData] of Object.entries(data.summaries)) {{
                            const summaryDiv = document.createElement('div');
                            summaryDiv.style.cssText = 'margin-bottom: 30px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);';

                            const messageCount = summaryData.message_count || 0;
                            const summary = summaryData.summary || 'No summary available';
                            const keyTopics = summaryData.key_topics || [];

                            let topicsHtml = '';
                            if (keyTopics.length > 0) {{
                                topicsHtml = `
                                    <div style="margin-top: 15px;">
                                        <h4 style="margin-bottom: 10px; color: #495057;">Key Topics:</h4>
                                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                            ${{keyTopics.map(topic => `<span style="display: inline-block; padding: 4px 12px; background: #e7f1ff; color: #0056b3; border-radius: 15px; font-size: 0.9em; border: 1px solid #b3d7ff;">${{topic}}</span>`).join('')}}
                                        </div>
                                    </div>
                                `;
                            }}

                            summaryDiv.innerHTML = `
                                <h3 style="margin-bottom: 10px; color: #333;">${{groupName}}</h3>
                                <div style="margin-bottom: 15px; color: #666; font-size: 0.9em;">
                                    ${{messageCount}} messages analyzed
                                </div>
                                <div style="margin-bottom: 15px;">
                                    <h4 style="margin-bottom: 10px; color: #495057;">Summary:</h4>
                                    <div style="line-height: 1.6; color: #333;">${{summary}}</div>
                                </div>
                                ${{topicsHtml}}
                            `;
                            container.appendChild(summaryDiv);
                        }}
                    }}

                    function generateSummaryForFilters() {{
                        const date = document.getElementById('date-filter').value;
                        const groupId = document.getElementById('group-filter').value;
                        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                        const btn = document.getElementById('generate-summary-btn');

                        if (!date) {{
                            alert('Please select a date');
                            return;
                        }}

                        btn.disabled = true;
                        btn.textContent = 'Generating...';

                        fetch('/api/generate-summary', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                date: date,
                                timezone: timezone,
                                group_id: groupId || null
                            }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                loadSummaryForFilters();
                            }} else {{
                                alert('Error generating summary: ' + data.message);
                            }}
                        }})
                        .finally(() => {{
                            btn.disabled = false;
                            btn.textContent = 'Generate New Summary';
                        }});
                    }}

                    // Auto-load when tab is shown if date is selected
                    if (document.getElementById('date-filter').value) {{
                        loadSummaryForFilters();
                    }}
                </script>
            </div>
        """

