"""
Groups page for Signal Bot web interface.
"""

from typing import Dict, Any
from ..shared.base_page import BasePage


class GroupsPage(BasePage):
    @property
    def title(self) -> str:
        return "👥 Groups Management"

    @property
    def nav_key(self) -> str:
        return "groups"

    @property
    def subtitle(self) -> str:
        return "Configure which groups the bot should monitor"

    def get_custom_css(self) -> str:
        """No custom CSS - using shared styling."""
        return ""

    def get_custom_js(self) -> str:
        return """
            function switchTab(tab) {
                // Navigate to the tab URL like Messages page does
                window.location.href = '/groups?tab=' + tab;
            }

            async function toggleGroupMonitoring(groupId, monitor) {
                try {
                    const payload = {group_id: groupId, is_monitored: monitor};

                    const response = await fetch('/api/groups/monitor', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });

                    if (response.ok) {
                        location.reload();
                    } else {
                        const errorText = await response.text();
                        alert('Failed to update group monitoring: ' + errorText);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        tab = query.get('tab', ['monitored'])[0]

        # Get stats for tab labels - filter out groups with 0 members and test groups
        all_groups = self.db.get_all_groups()
        # Filter out groups with 0 members and test groups
        all_groups = [g for g in all_groups if g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]
        monitored_count = len([g for g in all_groups if g.is_monitored])
        unmonitored_count = len([g for g in all_groups if not g.is_monitored])

        return f"""
            <div class="user-tabs">
                <button class="tab-btn {'active' if tab == 'monitored' else ''}" onclick="switchTab('monitored')">Monitored Groups ({monitored_count})</button>
                <button class="tab-btn {'active' if tab == 'unmonitored' else ''}" onclick="switchTab('unmonitored')">Unmonitored Groups ({unmonitored_count})</button>
            </div>

            <div id="{tab}-tab" class="tab-content active">
                {self._render_monitored_tab() if tab == 'monitored' else self._render_unmonitored_tab()}
            </div>
        """

    def _render_monitored_tab(self) -> str:
        """Render the monitored groups tab content."""
        groups = [g for g in self.db.get_all_groups() if g.is_monitored and g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]

        if not groups:
            return """
                <div class="card">
                    <h3>Monitored Groups</h3>
                    <p class="text-muted">Groups that the bot is actively monitoring</p>
                    <div class="no-groups">No monitored groups found. Use the "Unmonitored Groups" tab to enable monitoring.</div>
                </div>
            """

        return f"""
            <div class="card">
                <h3>Monitored Groups</h3>
                <p class="text-muted">Groups that the bot is actively monitoring</p>
                {self._render_groups_table(groups, True)}
            </div>
        """

    def _render_unmonitored_tab(self) -> str:
        """Render the unmonitored groups tab content."""
        groups = [g for g in self.db.get_all_groups() if not g.is_monitored and g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]

        if not groups:
            return """
                <div class="card">
                    <h3>Unmonitored Groups</h3>
                    <p class="text-muted">Groups that are not being monitored by the bot</p>
                    <div class="no-groups">No unmonitored groups found. All discovered groups are being monitored.</div>
                </div>
            """

        return f"""
            <div class="card">
                <h3>Unmonitored Groups</h3>
                <p class="text-muted">Groups that are not being monitored by the bot</p>
                {self._render_groups_table(groups, False)}
            </div>
        """

    def _render_groups_table(self, groups, is_monitored: bool) -> str:
        """Render a table of groups."""
        from urllib.parse import quote

        rows_html = ""
        for group in groups:
            monitor_btn = "Unmonitor" if is_monitored else "Monitor"
            monitor_action = "false" if is_monitored else "true"

            # Get members for this group
            members = self.db.get_group_members(group.group_id)
            members_html = ""
            if members:
                member_details = []
                for member in members:
                    detail = self.format_user_display(member)
                    member_details.append(detail)
                members_html = "<br>".join(member_details)
            else:
                members_html = "No members"

            view_messages_btn = ""
            if is_monitored:
                view_messages_btn = f'<a href="/messages?tab=all&group_id={quote(group.group_id)}" class="btn btn-secondary" style="margin-left: 5px;">View Messages</a>'

            # Escape the group ID for JavaScript
            escaped_group_id = group.group_id.replace("'", "\\'").replace('"', '\\"')

            rows_html += f"""
            <tr>
                <td><strong>{group.group_name or 'Unnamed Group'}</strong></td>
                <td>{group.group_id}</td>
                <td>{group.member_count}</td>
                <td style="max-width: 300px; word-wrap: break-word;">{members_html}</td>
                <td>
                    <button class="btn" onclick="toggleGroupMonitoring('{escaped_group_id}', {monitor_action})">
                        {monitor_btn}
                    </button>
                    {view_messages_btn}
                </td>
            </tr>
            """

        return f"""
            <table>
                <thead>
                    <tr>
                        <th>Group Name</th>
                        <th>Group ID</th>
                        <th>Members</th>
                        <th>Member Details</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="5" class="text-center text-muted">No groups found</td></tr>'}
                </tbody>
            </table>
        """