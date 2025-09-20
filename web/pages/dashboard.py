"""
Comprehensive Dashboard for Signal Bot

A modern, feature-rich dashboard that displays all bot capabilities and real-time status.
"""

import os
# import psutil
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from ..shared.base_page import BasePage


class ComprehensiveDashboard(BasePage):
    """Enhanced dashboard with comprehensive monitoring and statistics."""

    @property
    def title(self) -> str:
        return "📊 Dashboard"

    @property
    def nav_key(self) -> str:
        return "dashboard"

    @property
    def subtitle(self) -> str:
        return "Real-time monitoring, analytics, and control"

    def get_custom_css(self) -> str:
        """Dashboard-specific CSS for grid and charts."""
        return """
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-online { background: #4CAF50; }
        .status-offline { background: #f44336; }
        .status-warning { background: #FF9800; }

        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #f5f5f5;
        }

        .metric-label {
            color: #666;
            font-size: 0.9em;
        }

        .metric-value {
            font-weight: bold;
            color: #333;
        }

        .metric-value.large {
            font-size: 1.8em;
            color: #2196F3;
        }

        .quick-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .stat-box {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            color: #333;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            transition: transform 0.2s;
        }

        .stat-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
            display: block;
        }

        .stat-label {
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
        }

        .activity-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .activity-item {
            padding: 10px;
            border-left: 3px solid #2196F3;
            margin: 10px 0;
            background: #f9f9f9;
        }

        .activity-time {
            font-size: 0.8em;
            color: #999;
        }

        .chart-container {
            height: 200px;
            margin: 15px 0;
        }

        .action-button {
            background: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
            transition: background 0.3s;
        }

        .action-button:hover {
            background: #1976D2;
        }

        .action-button.danger {
            background: #f44336;
        }

        .alert-banner {
            background: #FFF3E0;
            border-left: 4px solid #FF9800;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.3s;
        }
        """

    def get_custom_js(self) -> str:
        """Enhanced dashboard JavaScript with real-time updates."""
        return """
        // Auto-refresh every 30 seconds
        let refreshInterval;

        function initDashboard() {
            loadDashboardData();
            refreshInterval = setInterval(loadDashboardData, 30000);
            initCharts();
        }

        function loadDashboardData() {
            // Get user timezone
            const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Tokyo';

            // Fetch all dashboard data with timezone
            fetch(`/api/dashboard/comprehensive?timezone=${encodeURIComponent(timezone)}`)
                .then(response => response.json())
                .then(data => {
                    updateSystemStatus(data.system);
                    updateStatistics(data.statistics);
                    updateActivity(data.activity);
                    updateAIStatus(data.ai);
                    updateBackupStatus(data.backup);
                    updateAlerts(data.alerts);
                })
                .catch(error => {
                    console.error('Dashboard update failed:', error);
                });
        }

        function updateSystemStatus(system) {
            // Update service statuses
            document.getElementById('signal-status').className =
                'status-indicator status-' + (system.signal_service ? 'online' : 'offline');
            document.getElementById('web-status').className =
                'status-indicator status-' + (system.web_service ? 'online' : 'offline');

            // Update metrics
            document.getElementById('uptime').textContent = system.uptime || 'N/A';
            document.getElementById('cpu-usage').textContent = system.cpu + '%';
            document.getElementById('memory-usage').textContent = system.memory + ' MB';
            document.getElementById('db-size').textContent = system.db_size;

            // Update progress bars
            document.getElementById('cpu-bar').style.width = system.cpu + '%';
            document.getElementById('memory-bar').style.width = system.memory_percent + '%';
        }

        function updateStatistics(stats) {
            // Update stat boxes
            document.getElementById('total-messages').textContent = stats.total_messages || '0';
            document.getElementById('active-groups').textContent = stats.active_groups || '0';
            document.getElementById('total-users').textContent = stats.total_users || '0';
            document.getElementById('messages-today').textContent = stats.messages_today || '0';

            // Update activity chart
            if (stats.hourly_activity) {
                updateActivityChart(stats.hourly_activity);
            }
        }

        function updateActivity(activity) {
            const container = document.getElementById('recent-activity');
            if (activity && activity.length > 0) {
                container.innerHTML = activity.map(item => `
                    <div class="activity-item">
                        <strong>${item.type}</strong>: ${item.description}
                        <div class="activity-time">${item.time}</div>
                    </div>
                `).join('');
            }
        }

        function updateAIStatus(ai) {
            // Update AI provider status
            document.getElementById('ai-provider').textContent = ai.provider || 'None';
            document.getElementById('ai-model').textContent = ai.model || 'N/A';
            document.getElementById('ai-status').className =
                'status-indicator status-' + (ai.available ? 'online' : 'offline');
        }

        function updateBackupStatus(backup) {
            document.getElementById('last-backup').textContent = backup.last || 'Never';
            document.getElementById('backup-size').textContent = backup.size || 'N/A';
            document.getElementById('next-backup').textContent = backup.next || 'Not scheduled';
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            if (alerts && alerts.length > 0) {
                container.innerHTML = alerts.map(alert => `
                    <div class="alert-banner">
                        <strong>${alert.title}</strong>: ${alert.message}
                    </div>
                `).join('');
            } else {
                container.innerHTML = '';
            }
        }

        function initCharts() {
            // Initialize activity chart using simple canvas
            const canvas = document.getElementById('activity-chart');
            if (canvas) {
                // Simple bar chart implementation
            }
        }

        // Quick action functions
        function syncUsers() {
            executeAction('/api/users/sync', 'Syncing users...');
        }

        function syncGroups() {
            executeAction('/api/groups/sync', 'Syncing groups...');
        }

        function runBackup() {
            executeAction('/api/backup/quick', 'Creating backup...');
        }

        function clearCache() {
            executeAction('/api/cache/clear', 'Clearing cache...');
        }

        function executeAction(url, message) {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = message;

            fetch(url, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Success', data.message || 'Operation completed');
                        loadDashboardData(); // Refresh
                    } else {
                        showNotification('Error', data.error || 'Operation failed');
                    }
                })
                .catch(error => {
                    showNotification('Error', 'Request failed: ' + error);
                })
                .finally(() => {
                    btn.disabled = false;
                    btn.textContent = originalText;
                });
        }

        function showNotification(title, message) {
            // Simple notification
            const notification = document.createElement('div');
            notification.className = 'alert-banner';
            notification.innerHTML = `<strong>${title}:</strong> ${message}`;
            document.getElementById('alerts-container').appendChild(notification);

            setTimeout(() => notification.remove(), 5000);
        }

        // Initialize on load
        document.addEventListener('DOMContentLoaded', initDashboard);

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (refreshInterval) clearInterval(refreshInterval);
        });
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        """Render comprehensive dashboard content."""
        # Get user timezone
        user_timezone = self.get_user_timezone(query)

        # Get initial data with timezone
        data = self.get_dashboard_data(user_timezone)

        return f"""
        <!-- Alerts Section -->
        <div id="alerts-container"></div>

        <!-- Quick Stats -->
        <div class="quick-stats">
            <div class="stat-box">
                <div class="stat-value" id="total-messages">{data['statistics']['total_messages']:,}</div>
                <div class="stat-label">Total Messages</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="active-groups">{data['statistics']['active_groups']}</div>
                <div class="stat-label">Active Groups</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="total-users">{data['statistics']['total_users']}</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="messages-today">{data['statistics']['messages_today']}</div>
                <div class="stat-label">Messages Today</div>
            </div>
        </div>

        <!-- Main Dashboard Grid -->
        <div class="dashboard-grid">

            <!-- System Status Card -->
            <div class="card">
                <h3>📊 System Status</h3>
                <div class="metric">
                    <span class="metric-label">Signal Service</span>
                    <span>
                        <span id="signal-status" class="status-indicator status-{'online' if data['system']['signal_service'] else 'offline'}"></span>
                        {'Running' if data['system']['signal_service'] else 'Stopped'}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Web Server</span>
                    <span>
                        <span id="web-status" class="status-indicator status-{'online' if data['system']['web_service'] else 'offline'}"></span>
                        {'Running' if data['system']['web_service'] else 'Stopped'}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value" id="uptime">{data['system']['uptime']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value" id="cpu-usage">{data['system']['cpu']}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: {data['system']['cpu']}%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Memory</span>
                    <span class="metric-value" id="memory-usage">{data['system']['memory']} MB</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width: {data['system']['memory_percent']}%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Database Size</span>
                    <span class="metric-value" id="db-size">{data['system']['db_size']}</span>
                </div>
            </div>

            <!-- AI Integration Card -->
            <div class="card">
                <h3>🤖 AI Integration</h3>
                <div class="metric">
                    <span class="metric-label">Provider</span>
                    <span class="metric-value" id="ai-provider">{data['ai']['provider']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Model</span>
                    <span class="metric-value" id="ai-model">{data['ai']['model']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span>
                        <span id="ai-status" class="status-indicator status-{'online' if data['ai']['available'] else 'offline'}"></span>
                        {'Available' if data['ai']['available'] else 'Unavailable'}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">Host</span>
                    <span class="metric-value" id="ai-host">{data['ai'].get('host', 'N/A')}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Response Time</span>
                    <span class="metric-value" id="ai-response">{data['ai'].get('response_time', 'N/A')}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Analyses Today</span>
                    <span class="metric-value" id="ai-analyses">{data['ai'].get('analyses_today', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Model Loaded</span>
                    <span>
                        <span class="status-indicator status-{'online' if data['ai'].get('model_loaded', False) else 'offline'}"></span>
                        {'Yes' if data['ai'].get('model_loaded', False) else 'No'}
                    </span>
                </div>
            </div>

            <!-- Database & Backup Card -->
            <div class="card">
                <h3>💾 Database & Backup</h3>
                <div class="metric">
                    <span class="metric-label">Last Backup</span>
                    <span class="metric-value" id="last-backup">{data['backup']['last']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Backup Size</span>
                    <span class="metric-value" id="backup-size">{data['backup']['size']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Next Scheduled</span>
                    <span class="metric-value" id="next-backup">{data['backup']['next']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Backups</span>
                    <span class="metric-value">{data['backup']['count']}</span>
                </div>
            </div>

            <!-- Message Statistics Card -->
            <div class="card">
                <h3>📈 Message Statistics</h3>
                <div class="metric">
                    <span class="metric-label">Last 24 Hours</span>
                    <span class="metric-value">{data['statistics']['messages_24h']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Last 7 Days</span>
                    <span class="metric-value">{data['statistics']['messages_7d']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Average per Day</span>
                    <span class="metric-value">{data['statistics']['avg_per_day']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">With Attachments</span>
                    <span class="metric-value">{data['statistics']['with_attachments']}</span>
                </div>
            </div>

        </div>
        """


    def get_dashboard_data(self, user_timezone: str = 'Asia/Tokyo') -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        data = {
            'system': self.get_system_status(),
            'statistics': self.get_statistics(user_timezone),
            'ai': self.get_ai_status(),
            'backup': self.get_backup_status(),
            'alerts': self.get_alerts()
        }
        return data

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        # Check running processes
        signal_running = False
        web_running = False

        try:
            import subprocess
            # Check for signal_service.py
            result = subprocess.run(['pgrep', '-f', 'signal_service.py'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                signal_running = True
            # Check for web_server.py
            result = subprocess.run(['pgrep', '-f', 'web_server.py'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                web_running = True
        except:
            pass

        # Get system metrics (placeholder without psutil)
        cpu_percent = 0
        memory = type('Memory', (), {'percent': 0, 'total': 0, 'available': 0, 'used': 0})()

        # Get database size
        db_path = Path(self.db.db_path)
        db_size = db_path.stat().st_size if db_path.exists() else 0

        # Calculate uptime (from bot_status table if available)
        uptime = "N/A"
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT created_at FROM bot_status ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    start_time = datetime.fromisoformat(result[0])
                    uptime_delta = datetime.now() - start_time
                    hours = int(uptime_delta.total_seconds() // 3600)
                    minutes = int((uptime_delta.total_seconds() % 3600) // 60)
                    uptime = f"{hours}h {minutes}m"
        except:
            pass

        return {
            'signal_service': signal_running,
            'web_service': web_running,
            'uptime': uptime,
            'cpu': cpu_percent,
            'memory': int(memory.used / 1024 / 1024),  # MB
            'memory_percent': memory.percent,
            'db_size': self.format_size(db_size)
        }

    def get_statistics(self, user_timezone: str = 'Asia/Tokyo') -> Dict[str, Any]:
        """Get message and user statistics."""
        stats = {
            'total_messages': 0,
            'messages_today': 0,
            'messages_24h': 0,
            'messages_7d': 0,
            'avg_per_day': 0,
            'with_attachments': 0,
            'total_users': 0,
            'active_groups': 0
        }

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Total messages
                cursor.execute("SELECT COUNT(*) FROM messages")
                stats['total_messages'] = cursor.fetchone()[0]

                # Messages today - with timezone support
                # Get the start of today in the user's timezone
                import pytz
                from datetime import datetime

                try:
                    tz = pytz.timezone(user_timezone)
                    now_tz = datetime.now(tz)
                    start_of_today = now_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                    start_timestamp_ms = int(start_of_today.timestamp() * 1000)

                    cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp >= ?", (start_timestamp_ms,))
                    stats['messages_today'] = cursor.fetchone()[0]
                except Exception:
                    # Fallback to UTC if timezone fails
                    cursor.execute("SELECT COUNT(*) FROM messages WHERE date(timestamp/1000, 'unixepoch') = date('now')")
                    stats['messages_today'] = cursor.fetchone()[0]

                # Messages last 24h (timestamps are in milliseconds)
                cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > (strftime('%s', 'now') - 86400) * 1000")
                stats['messages_24h'] = cursor.fetchone()[0]

                # Messages last 7d
                cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > (strftime('%s', 'now') - 604800) * 1000")
                stats['messages_7d'] = cursor.fetchone()[0]

                # Average per day (last 30 days)
                cursor.execute("""
                    SELECT COUNT(*) / 30.0
                    FROM messages
                    WHERE timestamp > (strftime('%s', 'now') - 2592000) * 1000
                """)
                stats['avg_per_day'] = round(cursor.fetchone()[0], 1)

                # Messages with attachments
                cursor.execute("SELECT COUNT(DISTINCT message_id) FROM attachments")
                stats['with_attachments'] = cursor.fetchone()[0]

                # Total users
                cursor.execute("SELECT COUNT(*) FROM users")
                stats['total_users'] = cursor.fetchone()[0]

                # Active groups (monitored)
                cursor.execute("SELECT COUNT(*) FROM groups WHERE is_monitored = 1")
                stats['active_groups'] = cursor.fetchone()[0]

        except Exception as e:
            print(f"Error getting statistics: {e}")

        return stats


    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI integration status matching AI Config page."""
        ai_status = {
            'provider': 'None',
            'model': 'N/A',
            'available': False,
            'model_loaded': False,
            'host': 'N/A',
            'response_time': 'N/A',
            'analyses_today': 0
        }

        try:
            # Get AI status from the service (same as AI Config page)
            from services.ai_provider import get_ai_status
            status = get_ai_status()

            if status:
                # Get active provider info
                active_provider = status.get('active_provider')
                providers = status.get('providers', [])

                if active_provider:
                    ai_status['provider'] = active_provider.capitalize()

                    # Find the active provider's details
                    for provider in providers:
                        if provider['name'].lower() == active_provider.lower():
                            ai_status['available'] = provider.get('available', False)
                            ai_status['host'] = provider.get('host', 'N/A')
                            ai_status['model'] = provider.get('model', 'N/A')
                            ai_status['model_loaded'] = provider.get('current_model_loaded', False)
                            # Measure response time
                            if ai_status['available']:
                                import requests
                                import time
                                try:
                                    start_time = time.time()
                                    response = requests.get(f"{provider['host']}/api/tags", timeout=2)
                                    if response.status_code == 200:
                                        response_time = (time.time() - start_time) * 1000
                                        ai_status['response_time'] = f"{response_time:.0f}ms"
                                except:
                                    pass
                            break

            # Get analyses count from database
            try:
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM sentiment_analysis
                        WHERE DATE(created_at) = DATE('now', 'localtime')
                    """)
                    ai_status['analyses_today'] = cursor.fetchone()[0]
            except:
                pass

        except Exception as e:
            print(f"Error getting AI status: {e}")

        return ai_status

    def get_backup_status(self) -> Dict[str, Any]:
        """Get backup status information."""
        backup_info = {
            'last': 'Never',
            'size': 'N/A',
            'next': 'Not scheduled',
            'count': 0
        }

        try:
            backup_dir = Path('backups/db')
            if backup_dir.exists():
                backups = list(backup_dir.glob('*backup*.*'))
                if backups:
                    # Sort by modification time
                    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    latest = backups[0]

                    # Format last backup time
                    last_time = datetime.fromtimestamp(latest.stat().st_mtime)
                    backup_info['last'] = last_time.strftime("%Y-%m-%d %H:%M")
                    backup_info['size'] = self.format_size(latest.stat().st_size)
                    backup_info['count'] = len(backups)

                    # Calculate next backup (assuming daily at 2 AM)
                    next_backup = datetime.now().replace(hour=2, minute=0, second=0)
                    if datetime.now().hour >= 2:
                        next_backup += timedelta(days=1)
                    backup_info['next'] = next_backup.strftime("%Y-%m-%d %H:%M")

        except Exception as e:
            print(f"Error getting backup status: {e}")

        return backup_info

    def get_alerts(self) -> List[Dict[str, str]]:
        """Get system alerts and warnings."""
        alerts = []

        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Check for old messages
                cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp < datetime('now', '-180 days')")
                old_messages = cursor.fetchone()[0]
                if old_messages > 100:
                    alerts.append({
                        'title': 'Archive Recommended',
                        'message': f'{old_messages} messages are older than 6 months. Consider archiving.'
                    })

                # Check database size
                db_path = Path(self.db.db_path)
                if db_path.exists() and db_path.stat().st_size > 100 * 1024 * 1024:  # 100MB
                    alerts.append({
                        'title': 'Database Size Warning',
                        'message': 'Database is over 100MB. Consider running optimization.'
                    })

                # Check last backup
                backup_dir = Path('backups/db')
                if backup_dir.exists():
                    backups = list(backup_dir.glob('*backup*.*'))
                    if backups:
                        latest = max(backups, key=lambda x: x.stat().st_mtime)
                        age_days = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
                        if age_days > 7:
                            alerts.append({
                                'title': 'Backup Overdue',
                                'message': f'Last backup was {age_days} days ago.'
                            })

        except Exception as e:
            print(f"Error getting alerts: {e}")

        return alerts

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def register_api_routes(self):
        """Register dashboard API endpoints."""
        from flask import current_app

        @current_app.route('/api/dashboard/comprehensive')
        def api_dashboard_comprehensive():
            """Get comprehensive dashboard data."""
            return jsonify(self.get_dashboard_data())

        @current_app.route('/api/backup/quick', methods=['POST'])
        def api_quick_backup():
            """Create a quick backup."""
            try:
                # Import db_manager
                import subprocess
                result = subprocess.run(
                    ['venv/bin/python', 'db_manager.py', 'backup', 'critical'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return jsonify({'success': True, 'message': 'Backup created successfully'})
                else:
                    return jsonify({'success': False, 'error': result.stderr})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @current_app.route('/api/cache/clear', methods=['POST'])
        def api_clear_cache():
            """Clear cache."""
            try:
                # Clear sentiment analysis cache
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM sentiment_analysis WHERE created_at < datetime('now', '-7 days')")
                    conn.commit()
                    deleted = cursor.rowcount
                return jsonify({'success': True, 'message': f'Cleared {deleted} cached entries'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})