"""
Dashboard page for Signal Bot web interface.

Shows overview statistics and status.
"""

from typing import Dict, Any
from ..shared.base_page import BasePage


class DashboardPage(BasePage):
    """Dashboard page implementation."""

    @property
    def title(self) -> str:
        return "📊 Signal Bot Dashboard"

    @property
    def nav_key(self) -> str:
        return "overview"  # Originally 'overview' for dashboard

    @property
    def subtitle(self) -> str:
        return "UUID-based Signal reaction bot management"

    def get_custom_css(self) -> str:
        """Dashboard-specific CSS - all core styles are in shared templates."""
        return ""

    def get_custom_js(self) -> str:
        return """
                function refreshStatus() {
                    const btn = document.getElementById('refresh-btn');
                    if (btn) {
                        btn.disabled = true;
                        btn.textContent = 'Refreshing...';
                    }

                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            updateStatusDisplay(data);
                        })
                        .catch(error => {
                            console.error('Error refreshing status:', error);
                        })
                        .finally(() => {
                            if (btn) {
                                btn.disabled = false;
                                btn.textContent = 'Refresh Status';
                            }
                        });
                }

                function updateStatusDisplay(data) {
                    // Update bot status
                    const botStatusEl = document.getElementById('bot-status');
                    if (botStatusEl) {
                        botStatusEl.textContent = data.bot_running ? 'Running' : 'Stopped';
                        botStatusEl.className = `status ${data.bot_running ? 'active' : 'inactive'}`;
                    }

                    // Update web server status
                    const webStatusEl = document.getElementById('web-status');
                    if (webStatusEl) {
                        webStatusEl.textContent = data.web_running ? 'Running' : 'Stopped';
                        webStatusEl.className = `status ${data.web_running ? 'active' : 'inactive'}`;
                    }

                    // Update uptime
                    const uptimeEl = document.getElementById('uptime');
                    if (uptimeEl) uptimeEl.textContent = data.uptime || 'N/A';

                    // Update last message
                    const lastMsgEl = document.getElementById('last-message');
                    if (lastMsgEl) lastMsgEl.textContent = data.last_message_time || 'No messages yet';

                    // Update message count
                    const msgCountEl = document.getElementById('message-count-status');
                    if (msgCountEl) msgCountEl.textContent = data.total_messages || '0';

                    // Update active groups
                    const groupsEl = document.getElementById('active-groups-status');
                    if (groupsEl) groupsEl.textContent = data.active_groups || '0';

                    // Update errors
                    const errorsEl = document.getElementById('error-list');
                    if (errorsEl) {
                        if (data.recent_errors && data.recent_errors.length > 0) {
                            errorsEl.innerHTML = data.recent_errors.map(error =>
                                `<li>${error}</li>`
                            ).join('');
                        } else {
                            errorsEl.innerHTML = '<li class="text-muted">No recent errors</li>';
                        }
                    }
                }

                function startBot() {
                    const btn = document.getElementById('start-btn');
                    if (btn) {
                        btn.disabled = true;
                        btn.textContent = 'Starting...';
                    }

                    fetch('/api/bot/start', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                setTimeout(refreshStatus, 2000);
                            } else {
                                alert('Error starting bot: ' + data.message);
                            }
                        })
                        .finally(() => {
                            if (btn) {
                                btn.disabled = false;
                                btn.textContent = 'Start Bot';
                            }
                        });
                }

                function stopBot() {
                    const btn = document.getElementById('stop-btn');
                    if (btn) {
                        btn.disabled = true;
                        btn.textContent = 'Stopping...';
                    }

                    fetch('/api/bot/stop', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                setTimeout(refreshStatus, 2000);
                            } else {
                                alert('Error stopping bot: ' + data.message);
                            }
                        })
                        .finally(() => {
                            if (btn) {
                                btn.disabled = false;
                                btn.textContent = 'Stop Bot';
                            }
                        });
                }

                // Auto-refresh status every 30 seconds
                setInterval(refreshStatus, 30000);

                // Initial load
                document.addEventListener('DOMContentLoaded', refreshStatus);
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        """Render dashboard content with bot status."""
        status = self.setup_service.get_setup_status()
        stats = self.db.get_stats()

        return f"""
            <h2>Bot Status</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Bot Status</div>
                    <span id="bot-status" class="status inactive">Checking...</span>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Web Server</div>
                    <span id="web-status" class="status active">Running</span>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Uptime</div>
                    <div id="uptime" class="stat-number">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Last Message</div>
                    <div id="last-message" class="text-muted">Loading...</div>
                </div>
            </div>

            <div class="user-item">
                <div class="user-name">Bot Controls</div>
                <div class="user-actions">
                    <button id="start-btn" class="btn btn-success" onclick="startBot()">Start Bot</button>
                    <button id="stop-btn" class="btn btn-danger" onclick="stopBot()">Stop Bot</button>
                    <button id="refresh-btn" class="btn btn-secondary" onclick="refreshStatus()">Refresh Status</button>
                </div>
                <div class="user-details">Use these controls to manage the bot's operation.</div>
            </div>

            <h2>Statistics Overview</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{stats['total_groups']}</div>
                    <div class="stat-label">Total Groups</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['monitored_groups']}</div>
                    <div class="stat-label">Monitored Groups</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['total_users']}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['configured_users']}</div>
                    <div class="stat-label">Configured Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['discovered_users']}</div>
                    <div class="stat-label">Discovered Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['recent_messages_24h']}</div>
                    <div class="stat-label">Messages (24h)</div>
                </div>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Total Messages</div>
                    <div id="message-count-status" class="stat-number">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Groups</div>
                    <div id="active-groups-status" class="stat-number">Loading...</div>
                </div>
            </div>

            <h2>Recent Errors</h2>
            <ul id="error-list">
                <li class="text-muted">Loading...</li>
            </ul>
        """