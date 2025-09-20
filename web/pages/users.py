"""
Users page for Signal Bot web interface.

Manages user emoji reaction configurations.
"""

from typing import Dict, Any
from ..shared.base_page import BasePage
from ..shared.templates import get_emoji_picker_for_reactions


class UsersPage(BasePage):
    """Users page implementation."""

    @property
    def title(self) -> str:
        return "👤 Users Management"

    @property
    def nav_key(self) -> str:
        return "users"

    @property
    def subtitle(self) -> str:
        return "Configure emoji reactions for users"

    def get_custom_css(self) -> str:
        """No custom CSS - using shared styling."""
        return ""

    def get_custom_js(self) -> str:
        """JavaScript for user management functionality."""
        return """
            function switchTab(tab) {
                // Navigate to the tab URL like Messages page does
                window.location.href = '/users?tab=' + tab;
            }

            function saveReactions(userId) {
                const selectedEmojis = Array.from(document.querySelectorAll('#emoji-' + userId + ' .emoji-item.selected'))
                    .map(item => item.dataset.emoji);
                const mode = document.getElementById('mode-' + userId).value;

                fetch('/api/save-user-reactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, emojis: selectedEmojis, mode: mode })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Reactions saved successfully!');
                        location.reload();
                    } else {
                        alert('Error saving reactions');
                    }
                });
            }

            function removeReactions(userId) {
                if (confirm('Remove all emoji reactions for this user?')) {
                    fetch('/api/remove-user-reactions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Reactions removed successfully!');
                            location.reload();
                        } else {
                            alert('Error removing reactions');
                        }
                    });
                }
            }

            function toggleEmoji(element) {
                element.classList.toggle('selected');
            }

            function openEmojiPicker(userId) {
                fetch('/api/user-reactions?user_id=' + userId)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('selectedEmojis').innerHTML = '';
                        document.getElementById('reactionMode').value = data.mode || 'random';

                        if (data.emojis) {
                            data.emojis.forEach(emoji => {
                                const span = document.createElement('span');
                                span.className = 'emoji-badge';
                                span.textContent = emoji;
                                span.onclick = function() { this.remove(); };
                                document.getElementById('selectedEmojis').appendChild(span);
                            });
                        }

                        document.getElementById('currentUserId').value = userId;
                        document.getElementById('emojiModal').style.display = 'block';
                    });
            }

            function closeEmojiPicker() {
                document.getElementById('emojiModal').style.display = 'none';
            }

            function addEmoji(emoji) {
                const selectedDiv = document.getElementById('selectedEmojis');
                const span = document.createElement('span');
                span.className = 'emoji-badge';
                span.textContent = emoji;
                span.onclick = function() { this.remove(); };
                selectedDiv.appendChild(span);
            }

            function saveFromModal() {
                const userId = document.getElementById('currentUserId').value;
                const emojis = Array.from(document.querySelectorAll('#selectedEmojis .emoji-badge'))
                    .map(span => span.textContent);
                const mode = document.getElementById('reactionMode').value;

                fetch('/api/save-user-reactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, emojis: emojis, mode: mode })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Reactions saved successfully!');
                        location.reload();
                    } else {
                        alert('Error saving reactions');
                    }
                });
                closeEmojiPicker();
            }
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        """Render the users page content."""
        # Get the active tab from query params
        tab = query.get('tab', ['configured'])[0]

        # Get users from database
        configured_users = self.db.get_configured_users()
        discovered_users = self.db.get_discovered_users()

        # Calculate stats
        total_users = len(configured_users) + len(discovered_users)
        total_configured = len(configured_users)
        total_discovered = len(discovered_users)

        # Render only the active tab content
        if tab == 'discovered':
            tab_content = f"""
                <div id="{tab}-tab" class="tab-content active">
                    <div class="content-card">
                        <h3>Discovered Users</h3>
                        <p class="text-muted">Users found in groups but not yet configured</p>
                        {self.render_user_list(discovered_users, False)}
                    </div>
                </div>
            """
        else:  # configured (default)
            tab_content = f"""
                <div id="{tab}-tab" class="tab-content active">
                    <div class="content-card">
                        <h3>Configured Users</h3>
                        <p class="text-muted">Users with custom emoji reactions configured</p>
                        {self.render_user_list(configured_users, True)}
                    </div>
                </div>
            """

        content = f"""
            <div class="user-tabs">
                <button class="tab-btn {'active' if tab == 'configured' else ''}" onclick="switchTab('configured')">Configured Users ({total_configured})</button>
                <button class="tab-btn {'active' if tab == 'discovered' else ''}" onclick="switchTab('discovered')">Discovered Users ({total_discovered})</button>
            </div>

            {tab_content}

            {self.render_emoji_modal()}
        """

        return content

    def render_user_list(self, users, is_configured: bool) -> str:
        """Render a list of users in table format."""
        if not users:
            return f"""
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            {'<th>UUID</th>' if not is_configured else ''}
                            <th>Phone</th>
                            <th>Messages</th>
                            <th>Groups</th>
                            {'<th>Reactions</th>' if is_configured else ''}
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="{'6' if is_configured else '6'}" class="text-center text-muted">No {'configured' if is_configured else 'discovered'} users found</td></tr>
                    </tbody>
                </table>
            """

        rows_html = ""
        for user in users:
            rows_html += self.render_user_row(user, is_configured)

        return f"""
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        {'<th>UUID</th>' if not is_configured else ''}
                        <th>Phone</th>
                        <th>Messages</th>
                        <th>Groups</th>
                        {'<th>Reactions</th>' if is_configured else ''}
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        """

    def render_user_row(self, user, is_configured: bool) -> str:
        """Render a single user as a table row."""
        # Get user display info - prefer phone number, fall back to UUID if empty
        display_name = user.friendly_name or user.phone_number or f"User {user.uuid}"
        phone_display = user.phone_number or "Not available"

        # Get user groups - don't truncate, show all groups
        groups = self.db.get_user_groups(user.uuid)
        groups_text = ", ".join([g.group_name or "Unnamed Group" for g in groups]) or "None"

        # Get message count
        message_count = self.db.get_message_count_filtered(sender_uuid=user.uuid)

        # Add UUID column for discovered users
        uuid_cell = f'<td><small>{user.uuid}</small></td>' if not is_configured else ''

        # Render emoji column for configured users
        emoji_cell = ""
        if is_configured:
            reactions = self.db.get_user_reactions(user.uuid)
            if reactions and reactions.emojis:
                emojis = reactions.emojis
                emoji_badges = ''.join([f'<span class="emoji-badge">{emoji}</span>' for emoji in emojis])
                mode_text = reactions.reaction_mode or 'random'
                emoji_cell = f'<td>{emoji_badges}<br><small class="text-muted">{mode_text}</small></td>'
            else:
                emoji_cell = '<td class="text-muted">None</td>'

        # Action buttons
        if is_configured:
            actions = f"""
                <button class="btn" onclick="openEmojiPicker('{user.uuid}')">Edit</button>
                <button class="btn btn-danger" onclick="removeReactions('{user.uuid}')">Remove</button>
            """
        else:
            actions = f"""
                <button class="btn" onclick="openEmojiPicker('{user.uuid}')">Configure</button>
            """

        return f"""
            <tr>
                <td><strong>{display_name}</strong></td>
                {uuid_cell}
                <td>{phone_display}</td>
                <td>{message_count}</td>
                <td style="max-width: 300px; word-wrap: break-word;">{groups_text}</td>
                {emoji_cell}
                <td>{actions}</td>
            </tr>
        """

    def render_emoji_modal(self) -> str:
        """Render the emoji picker modal using shared component."""
        return get_emoji_picker_for_reactions()