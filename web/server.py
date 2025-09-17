"""
Clean Web Interface for UUID-based Signal Bot

Simple, REST-like interface for managing the Signal bot:
- Setup wizard for initial configuration
- Group management (monitor/unmonitor)
- User management (configure emoji reactions)
- Statistics and status monitoring

Follows the new UUID-based architecture.
"""
import json
import logging
from datetime import datetime, date
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from typing import Optional, Dict, Any
import threading
import uuid
import time

# Try to import markdown library, fallback if not available
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
import os
import mimetypes

from models.database import DatabaseManager
from services.setup import SetupService
from services.sentiment import SentimentAnalyzer
from services.summarization import MessageSummarizer


def convert_markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML using Python markdown library."""
    if not MARKDOWN_AVAILABLE or not text:
        return text

    try:
        # Configure markdown with table extension
        md = markdown.Markdown(extensions=['tables', 'fenced_code'])
        return md.convert(text)
    except Exception:
        # Fallback to original text if conversion fails
        return text


class WebHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the web interface."""

    # Class-level storage for analysis jobs
    _analysis_jobs = {}

    def __init__(self, *args, db_manager: DatabaseManager, setup_service: SetupService, **kwargs):
        self.db = db_manager
        self.setup_service = setup_service
        self.logger = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)


    def format_user_display(self, user) -> str:
        """
        Format user display consistently across the interface.
        Priority: friendly_name, then phone_number, then UUID.
        """
        # Check if friendly name exists and is not the generic fallback
        if (user.friendly_name and
            user.friendly_name != f"User {user.phone_number}" and
            user.friendly_name != f"User {user.uuid}"):
            # Real friendly name exists - use it with phone/UUID in parentheses
            if user.phone_number:
                return f"{user.friendly_name} ({user.phone_number})"
            else:
                return f"{user.friendly_name} (UUID: {user.uuid[:8]}...)"
        elif user.phone_number:
            # No real friendly name, show phone number
            return user.phone_number
        elif user.display_name:
            # No friendly name or phone, show display name with UUID
            return f"{user.display_name} (UUID: {user.uuid[:8]}...)"
        else:
            # Only UUID available
            return f"UUID: {user.uuid}"

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        try:
            if path == '/':
                self._serve_dashboard()
            elif path == '/setup':
                self._serve_setup()
            elif path == '/groups':
                self._serve_groups()
            elif path == '/users':
                self._serve_users()
            elif path == '/messages':
                self._serve_messages(query)
            elif path == '/all-messages':
                self._serve_all_messages(query)
            elif path == '/messages/by-sender':
                self._serve_messages_by_sender(query)
            elif path == '/sender-messages':
                self._serve_sender_messages(query)
            elif path == '/sentiment':
                self._serve_sentiment(query)
            elif path == '/summary':
                self._serve_summary(query)
            elif path == '/activity':
                self._serve_activity_visualization(query)
            elif path == '/ai-config':
                self._serve_ai_config(query)
            elif path == '/api/status':
                self._api_status()
            elif path == '/api/activity/hourly':
                self._api_activity_hourly(query)
            elif path == '/api/setup/run':
                self._api_run_setup()
            elif path == '/api/groups':
                self._api_groups()
            elif path == '/api/group-members':
                self._api_group_members(query)
            elif path == '/api/users':
                self._api_users()
            elif path == '/api/stats':
                self._api_stats()
            elif path.startswith('/api/generate-link-qr'):
                self._api_generate_link_qr()
            elif path.startswith('/api/sentiment-cached'):
                self._api_sentiment_cached(query)
            elif path.startswith('/api/sentiment-preview'):
                self._api_sentiment_preview(query)
            elif path.startswith('/api/sentiment'):
                self._api_sentiment_analysis(query)
            elif path.startswith('/api/summary'):
                self._api_summary(query)
            elif path.startswith('/api/ai-status'):
                self._api_ai_status(query)
            elif path.startswith('/api/ai-config'):
                self._api_ai_config(query)
            elif path.startswith('/api/ollama-models'):
                self._api_ollama_models(query)
            elif path.startswith('/api/ollama-preload'):
                self._api_ollama_preload(query)
            elif path.startswith('/api/ollama-status'):
                self._api_ollama_status(query)
            elif path.startswith('/attachment/'):
                self._serve_attachment(path)
            else:
                self._send_404()
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected during GET %s: %s", path, e)
        except Exception as e:
            self.logger.error(f"Error handling GET {path}: {e}")
            self._send_error(500, str(e))

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            if path == '/api/groups/monitor':
                self._api_set_group_monitoring(post_data)
            elif path == '/api/users/reactions':
                self._api_set_user_reactions(post_data)
            elif path == '/api/setup/sync':
                self._api_sync_groups()
            elif path == '/api/sync-groups':
                self._api_sync_groups()
            elif path == '/api/link-account':
                self._api_link_account(post_data)
            elif path == '/api/database/clear':
                self._api_clear_database()
            elif path == '/api/database/consolidate':
                self._api_consolidate_users()
            elif path == '/api/ai-config':
                self._api_save_ai_config(post_data)
            else:
                self._send_404()
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected during POST %s: %s", path, e)
        except Exception as e:
            self.logger.error(f"Error handling POST {path}: {e}")
            self._send_error(500, str(e))

    def _send_html_response(self, html: str):
        """Send HTML response."""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected while sending response: %s", e)
        except Exception as e:
            self.logger.error("Error sending HTML response: %s", e)

    def _send_json_response(self, data: Dict[str, Any]):
        """Send JSON response."""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected while sending response: %s", e)
        except Exception as e:
            self.logger.error("Error sending JSON response: %s", e)

    def _send_404(self):
        """Send 404 response."""
        try:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 Not Found</h1>')
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected while sending 404: %s", e)
        except Exception as e:
            self.logger.error("Error sending 404 response: %s", e)

    def _send_error(self, code: int, message: str):
        """Send error response."""
        try:
            self.send_response(code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': message}).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError) as e:
            # Client disconnected, log and ignore
            self.logger.debug("Client disconnected while sending error: %s", e)
        except Exception as e:
            self.logger.error("Error sending error response: %s", e)

    def _get_standard_css(self):
        """Get standardized CSS styling for all pages."""
        return """
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }
                .container { max-width: 1200px; margin: 0 auto; }
                .card {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }
                .nav {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-bottom: 30px;
                }
                .nav-item {
                    padding: 12px 24px;
                    background: #f8f9fa;
                    border-radius: 25px;
                    text-decoration: none;
                    color: #495057;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }
                .nav-item:hover { background: #e9ecef; transform: translateY(-2px); }
                .nav-item.active { background: #007bff; color: white; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
                th { background: #f8f9fa; font-weight: 600; }
                .btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 5px;
                    background: #007bff;
                    color: white;
                    cursor: pointer;
                    transition: background 0.3s;
                    margin-right: 5px;
                    text-decoration: none;
                    display: inline-block;
                }
                .btn:hover { background: #0056b3; }
                .btn-danger { background: #dc3545; }
                .btn-danger:hover { background: #c82333; }
                .btn-success { background: #28a745; }
                .btn-success:hover { background: #218838; }
                .btn-warning { background: #ffc107; color: #212529; }
                .btn-warning:hover { background: #e0a800; }
                .text-muted { color: #6c757d; }

                /* Form elements */
                .form-group { margin-bottom: 20px; }
                .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
                .form-group input, .form-group select, .form-group textarea {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    font-size: 14px;
                }
                .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                }

                /* Status and alerts */
                .alert {
                    padding: 12px 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }
                .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
                .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

                /* Loading states */
                .loading {
                    text-align: center;
                    padding: 40px;
                    color: #6c757d;
                }

                /* Message displays */
                .messages-container { margin-top: 20px; }
                .message-item {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                    background: white;
                }
                .message-header {
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                }
                .message-time, .timestamp {
                    color: #6c757d;
                    font-size: 0.85em;
                }
                .message-content {
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .no-messages {
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px;
                }

                /* Pagination */
                .pagination {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }
                .pagination a, .pagination span {
                    padding: 8px 12px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    text-decoration: none;
                    color: #495057;
                    background: white;
                }
                .pagination a:hover { background: #e9ecef; }
                .pagination .current { background: #007bff; color: white; border-color: #007bff; }

                /* Stats and metrics */
                .stats {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                    gap: 10px;
                }
                .stats > div {
                    flex: 1;
                    min-width: 200px;
                }

                /* Mobile responsiveness */
                @media (max-width: 768px) {
                    .container { padding: 10px; }
                    .card { padding: 20px; margin-bottom: 20px; }
                    .nav { flex-direction: column; gap: 10px; }
                    .nav-item { text-align: center; }
                    .stats { flex-direction: column; }
                    .message-header { flex-direction: column; align-items: flex-start; gap: 5px; }
                    table, thead, tbody, th, td, tr { display: block; }
                    thead tr { position: absolute; top: -9999px; left: -9999px; }
                    tr { border: 1px solid #ccc; margin-bottom: 10px; }
                    td { border: none; position: relative; padding-left: 50%; }
                    td:before {
                        content: attr(data-label) ": ";
                        position: absolute;
                        left: 6px;
                        width: 45%;
                        padding-right: 10px;
                        white-space: nowrap;
                        font-weight: bold;
                    }
                }
        """

    def _get_page_header(self, title, subtitle, active_page=''):
        """Get standardized page header with navigation for all pages."""
        nav_items = [
            ('/', 'Overview'),
            ('/groups', 'Groups'),
            ('/users', 'Users'),
            ('/all-messages', 'All Messages'),
            ('/sentiment', 'Sentiment'),
            ('/summary', 'Summary'),
            ('/activity', 'Activity'),
            ('/ai-config', 'AI Config')
        ]

        nav_html = ''
        for href, label in nav_items:
            # Check if this is the active page
            is_active = ''
            if active_page == label.lower().replace(' ', '-'):
                is_active = ' active'
            elif href == '/' and active_page == 'overview':
                is_active = ' active'

            nav_html += f'<a href="{href}" class="nav-item{is_active}">{label}</a>\n'

        return f"""
            <div class="container">
                <div class="card">
                    <h1>{title}</h1>
                    <p>{subtitle}</p>
                    <div class="nav">
                        {nav_html.strip()}
                    </div>
                </div>
        """

    def _serve_dashboard(self):
        """Serve main dashboard."""
        status = self.setup_service.get_setup_status()
        stats = self.db.get_stats()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Signal Bot - Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {self._get_standard_css()}

                /* Dashboard-specific styles */
                .header {{ text-align: center; margin-bottom: 30px; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .stat-label {{ margin-top: 5px; color: #666; }}
                .status-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .status-good {{ background: #28a745; }}
                .status-warning {{ background: #ffc107; }}
                .status-error {{ background: #dc3545; }}
            </style>
        </head>
        <body>
            {self._get_page_header('📊 Signal Bot Dashboard', 'UUID-based Signal reaction bot management', 'overview')}

                <div class="card">
                    <h2>Bot Status</h2>
                    <p>
                        <span class="status-indicator {'status-good' if status['bot_configured'] else 'status-warning'}"></span>
                        Bot: {'Configured' if status['bot_configured'] else 'Not Configured'}
                        {f"({status['bot_phone_number']})" if status.get('bot_phone_number') else ''}
                    </p>
                    <p>
                        <span class="status-indicator {'status-good' if status['signal_cli_available'] else 'status-error'}"></span>
                        Signal CLI: {'Available' if status['signal_cli_available'] else 'Not Available'}
                    </p>

                    {'<a href="/setup" class="btn btn-warning">Complete Setup</a>' if not status['bot_configured'] else ''}
                </div>

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
            </div>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_setup(self):
        """Serve setup page."""
        status = self.setup_service.get_setup_status()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Signal Bot - Setup</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {self._get_standard_css()}

                /* Setup-specific styles */
                .container {{ max-width: 800px; margin: 0 auto; }}
                .btn:disabled {{ background: #6c757d; cursor: not-allowed; }}
                .setup-step {{
                    margin: 20px 0;
                    padding: 20px;
                    border: 1px solid #dee2e6;
                    border-radius: 10px;
                }}
                .step-complete {{ background: #d4edda; border-color: #c3e6cb; }}
                .step-pending {{ background: #fff3cd; border-color: #ffeaa7; }}
                .status-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .status-good {{ background: #28a745; }}
                .status-warning {{ background: #ffc107; }}
                .status-error {{ background: #dc3545; }}
                #setup-output {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 15px;
                    min-height: 100px;
                    font-family: monospace;
                    white-space: pre-wrap;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>Signal Bot Setup</h1>
                    <div class="nav">
                        <a href="/" class="nav-item">Dashboard</a>
                        <a href="/setup" class="nav-item active">Setup</a>
                        <a href="/groups" class="nav-item">Groups</a>
                        <a href="/users" class="nav-item">Users</a>
                        <a href="/all-messages" class="nav-item">All Messages</a>
                        <a href="/sentiment" class="nav-item">Sentiment</a>
                        <a href="/activity" class="nav-item">Activity</a>
                    </div>
                </div>

                <div class="card">
                    <h2>Setup Status</h2>

                    <div class="setup-step {'step-complete' if status['signal_cli_available'] else 'step-pending'}">
                        <h3>
                            <span class="status-indicator {'status-good' if status['signal_cli_available'] else 'status-error'}"></span>
                            Signal CLI Detection
                        </h3>
                        <p>Path: {status['signal_cli_path']}</p>
                        <p>Status: {'Available' if status['signal_cli_available'] else 'Not Available'}</p>
                    </div>

                    <div class="setup-step {'step-complete' if status['bot_configured'] else 'step-pending'}">
                        <h3>
                            <span class="status-indicator {'status-good' if status['bot_configured'] else 'status-warning'}"></span>
                            Bot Configuration
                        </h3>
                        <p>Phone: {status.get('bot_phone_number', 'Not configured')}</p>
                        <p>UUID: {status.get('bot_uuid', 'Not configured')}</p>
                    </div>

                    <div class="setup-step {'step-complete' if status['total_groups'] > 0 else 'step-pending'}">
                        <h3>
                            <span class="status-indicator {'status-good' if status['total_groups'] > 0 else 'status-warning'}"></span>
                            Group Discovery
                        </h3>
                        <p>Total Groups: {status['total_groups']}</p>
                        <p>Monitored: {status['monitored_groups']}</p>
                    </div>

                    <div class="setup-step {'step-complete' if status['total_users'] > 0 else 'step-pending'}">
                        <h3>
                            <span class="status-indicator {'status-good' if status['total_users'] > 0 else 'status-warning'}"></span>
                            User Discovery
                        </h3>
                        <p>Total Users: {status['total_users']}</p>
                        <p>Configured: {status['configured_users']}</p>
                        <p>Discovered: {status['discovered_users']}</p>
                    </div>

                    <button id="run-setup" class="btn" onclick="runSetup()">
                        {'Re-run Setup' if status['bot_configured'] else 'Run Initial Setup'}
                    </button>

                    <button id="sync-groups" class="btn" onclick="syncGroups()" style="margin-left: 10px;">
                        Sync Groups
                    </button>

                    <div id="setup-output"></div>
                </div>
            </div>

            <script>
                async function runSetup() {{
                    const btn = document.getElementById('run-setup');
                    const output = document.getElementById('setup-output');

                    btn.disabled = true;
                    btn.textContent = 'Running Setup...';
                    output.textContent = 'Starting setup...\\n';

                    try {{
                        const response = await fetch('/api/setup/run');
                        const result = await response.json();

                        output.textContent += `Setup completed:\\n`;
                        output.textContent += `Success: ${{result.success}}\\n`;
                        output.textContent += `Steps: ${{result.steps_completed.join(', ')}}\\n`;

                        if (result.errors.length > 0) {{
                            output.textContent += `Errors: ${{result.errors.join(', ')}}\\n`;
                        }}

                        // Display QR code if available
                        if (result.linking_qr) {{
                            output.innerHTML += `<br><strong>Device Linking Required:</strong><br>`;
                            output.innerHTML += `<p>Scan this QR code with your Signal app to link this device:</p>`;


                            if (result.linking_qr.qr_code) {{
                                output.innerHTML += `<div style="text-align: center; margin: 20px 0;"><img src="${{result.linking_qr.qr_code}}" alt="QR Code" style="max-width: 300px; border: 1px solid #ccc; display: block; margin: 0 auto;"></div>`;
                            }} else {{
                                output.innerHTML += `<p><strong>Error:</strong> QR code not generated</p>`;
                            }}

                            if (result.linking_qr.linking_uri) {{
                                output.innerHTML += `<p><strong>Link URI:</strong> <code style="word-break: break-all;">${{result.linking_qr.linking_uri}}</code></p>`;
                            }}

                            output.innerHTML += `<p><em>After scanning with your Signal app, the setup will automatically complete. This page will refresh when done.</em></p>`;
                        }} else if (result.success) {{
                            output.textContent += '\\nSetup completed successfully! Refreshing page...';
                            setTimeout(() => location.reload(), 2000);
                        }}
                    }} catch (error) {{
                        output.textContent += `Error: ${{error.message}}\\n`;
                    }} finally {{
                        btn.disabled = false;
                        btn.textContent = 'Run Setup';
                    }}
                }}

                async function syncGroups() {{
                    const btn = document.getElementById('sync-groups');
                    const output = document.getElementById('setup-output');

                    btn.disabled = true;
                    btn.textContent = 'Syncing...';
                    output.textContent = 'Syncing groups...\\n';

                    try {{
                        const response = await fetch('/api/setup/sync', {{ method: 'POST' }});
                        const result = await response.json();

                        output.textContent += `Groups synced: ${{result.synced_count}}\\n`;
                        output.textContent += 'Sync completed! Refreshing page...';
                        setTimeout(() => location.reload(), 2000);
                    }} catch (error) {{
                        output.textContent += `Error: ${{error.message}}\\n`;
                    }} finally {{
                        btn.disabled = false;
                        btn.textContent = 'Sync Groups';
                    }}
                }}
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_groups(self):
        """Serve groups management page."""
        groups = self.db.get_all_groups()

        groups_html = ""
        for group in groups:
            status_class = "status-good" if group.is_monitored else "status-warning"
            monitor_btn = "Unmonitor" if group.is_monitored else "Monitor"
            monitor_action = "false" if group.is_monitored else "true"

            # Get members for this group
            members = self.db.get_group_members(group.group_id)
            members_html = ""
            if members:
                member_details = []
                for member in members:
                    # Use consistent formatting across interface
                    detail = self.format_user_display(member)
                    member_details.append(detail)

                # Show all members with line breaks for readability
                members_html = "<br>".join(member_details)
            else:
                members_html = "No members"

            groups_html += f"""
            <tr>
                <td>
                    <span class="status-indicator {status_class}"></span>
                    <strong>{group.group_name or 'Unnamed Group'}</strong>
                </td>
                <td>{group.group_id}</td>
                <td>{group.member_count}</td>
                <td>
                    <div class="members-list">
                        {members_html}
                    </div>
                </td>
                <td>{'Yes' if group.is_monitored else 'No'}</td>
                <td>
                    <button class="btn" onclick="toggleGroupMonitoring('{group.group_id}', {monitor_action})">
                        {monitor_btn}
                    </button>
                    {f'<button class="btn btn-secondary" onclick="viewGroupMessages(\'{group.group_id}\')">View Messages</button>' if group.is_monitored else ''}
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Signal Bot - Groups</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {self._get_standard_css()}

                /* Groups-specific styles */
                .status-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .status-good {{ background: #28a745; }}
                .status-warning {{ background: #ffc107; }}
                .btn-secondary {{
                    background: #6c757d;
                }}
                .btn-secondary:hover {{ background: #5a6268; }}
                .members-list {{
                    max-width: 300px;
                    font-size: 0.85em;
                    color: #555;
                    line-height: 1.4;
                    word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            {self._get_page_header('👥 Groups Management', 'Configure which groups the bot should monitor', 'groups')}

                <div class="card">
                    <h2>Signal Groups</h2>
                    <p>Configure which groups the bot should monitor for messages.</p>

                    <table>
                        <thead>
                            <tr>
                                <th>Group Name</th>
                                <th>Group ID</th>
                                <th>Count</th>
                                <th>Member Details</th>
                                <th>Monitored</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {groups_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <script>
                async function toggleGroupMonitoring(groupId, monitor) {{
                    try {{
                        const response = await fetch('/api/groups/monitor', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{group_id: groupId, is_monitored: monitor}})
                        }});

                        if (response.ok) {{
                            location.reload();
                        }} else {{
                            alert('Failed to update group monitoring');
                        }}
                    }} catch (error) {{
                        alert('Error: ' + error.message);
                    }}
                }}

                function viewGroupMessages(groupId) {{
                    window.location.href = '/messages?group_id=' + encodeURIComponent(groupId);
                }}
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_users(self):
        """Serve users management page."""
        configured_users = self.db.get_configured_users()
        discovered_users = self.db.get_discovered_users()

        def render_user_row(user, is_configured=False):
            reactions = self.db.get_user_reactions(user.uuid) if is_configured else None
            groups = self.db.get_user_groups(user.uuid)

            user_display = self.format_user_display(user)

            emojis_display = ""
            if reactions and reactions.emojis:
                emojis_display = "".join([f'<span class="emoji-badge">{emoji}</span>' for emoji in reactions.emojis])
            else:
                emojis_display = '<span class="text-muted">None</span>'

            # Format groups display
            groups_display = ""
            if groups:
                group_names = [group.group_name or f"Group {group.group_id}" for group in groups]
                groups_display = "<br>".join(group_names)
            else:
                groups_display = '<span class="text-muted">No groups</span>'

            return f"""
            <tr>
                <td>{user_display}</td>
                <td>{user.message_count}</td>
                <td>{emojis_display}</td>
                <td>
                    <div class="groups-list">
                        {groups_display}
                    </div>
                </td>
                <td>
                    <button class="btn" onclick="editUserReactions('{user.uuid}')">{('Edit' if is_configured else 'Add')}</button>
                    {f'<button class="btn btn-danger" onclick="removeUserReactions(\'{user.uuid}\')">Remove</button>' if is_configured else ''}
                </td>
            </tr>
            """

        configured_html = ""
        for user in configured_users:
            configured_html += render_user_row(user, True)

        discovered_html = ""
        for user in discovered_users:
            discovered_html += render_user_row(user, False)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Signal Bot - Users</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {self._get_standard_css()}

                /* Users-specific styles */
                .btn-danger {{ background: #dc3545; }}
                .btn-danger:hover {{ background: #c82333; }}
                .emoji-badge {{
                    display: inline-block;
                    padding: 2px 6px;
                    margin: 2px;
                    background: #f8f9fa;
                    border-radius: 15px;
                    font-size: 1.2em;
                }}
                .text-muted {{ color: #6c757d; }}
                .groups-list {{
                    font-size: 0.9em;
                    color: #6c757d;
                    line-height: 1.4;
                }}

                /* Emoji Picker Styles */
                .emoji-modal {{
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.5);
                    justify-content: center;
                    align-items: center;
                }}

                .emoji-modal-content {{
                    background: white;
                    border-radius: 8px;
                    max-width: 600px;
                    width: 90%;
                    max-height: 80vh;
                    display: flex;
                    flex-direction: column;
                }}

                .emoji-modal-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 20px;
                    border-bottom: 1px solid #ddd;
                }}

                .close-btn {{
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #999;
                }}

                .close-btn:hover {{
                    color: #333;
                }}

                .emoji-selected {{
                    padding: 15px 20px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 10px;
                }}

                .emoji-categories {{
                    display: flex;
                    padding: 10px 20px;
                    gap: 10px;
                    flex-wrap: wrap;
                    border-bottom: 1px solid #eee;
                }}

                .emoji-category-btn {{
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    background: #f8f9fa;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 14px;
                    white-space: nowrap;
                }}

                .emoji-category-btn:hover,
                .emoji-category-btn.active {{
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }}

                .emoji-container {{
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                }}

                .emoji-category {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
                    gap: 8px;
                    max-height: 300px;
                    overflow-y: auto;
                }}

                .emoji-category.hidden {{
                    display: none;
                }}

                .emoji-btn {{
                    font-size: 1.5em;
                    padding: 8px;
                    border: 1px solid #ddd;
                    background: white;
                    cursor: pointer;
                    border-radius: 4px;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 40px;
                }}

                .emoji-btn:hover {{
                    background: #f0f0f0;
                    transform: scale(1.1);
                    border-color: #007bff;
                }}

                .emoji-btn.selected {{
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }}

                .emoji-badge {{
                    display: inline-block;
                    font-size: 1.2em;
                    margin: 2px;
                    padding: 4px 8px;
                    background: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    border-radius: 15px;
                    cursor: pointer;
                }}

                .emoji-badge:hover {{
                    background: #ffcccc;
                    border-color: #ff9999;
                }}

                /* Mobile responsiveness */
                @media (max-width: 768px) {{
                    .emoji-modal-content {{
                        width: 95%;
                        max-height: 90vh;
                    }}

                    .emoji-category {{
                        grid-template-columns: repeat(auto-fill, minmax(35px, 1fr));
                    }}

                    .emoji-selected {{
                        flex-direction: column;
                        align-items: flex-start;
                    }}

                    .emoji-categories {{
                        justify-content: center;
                    }}
                }}
                .tabs {{ margin-bottom: 20px; }}
                .tab-btn {{
                    padding: 12px 24px;
                    border: none;
                    background: #f8f9fa;
                    color: #495057;
                    cursor: pointer;
                    border-radius: 25px 25px 0 0;
                    margin-right: 5px;
                }}
                .tab-btn.active {{ background: #007bff; color: white; }}
                .tab-content {{ display: none; }}
                .tab-content.active {{ display: block; }}
            </style>
        </head>
        <body>
            {self._get_page_header('👤 Users Management', 'Configure emoji reactions for users', 'users')}

                <div class="card">
                    <div class="tabs">
                        <button class="tab-btn active" onclick="showTab('configured')">Configured Users ({len(configured_users)})</button>
                        <button class="tab-btn" onclick="showTab('discovered')">Discovered Users ({len(discovered_users)})</button>
                    </div>

                    <div id="configured-tab" class="tab-content active">
                        <h2>Configured Users</h2>
                        <p>Users with emoji reaction preferences configured.</p>

                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Messages</th>
                                    <th>Emoji Reactions</th>
                                    <th>Groups</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {configured_html or '<tr><td colspan="5">No configured users yet.</td></tr>'}
                            </tbody>
                        </table>
                    </div>

                    <div id="discovered-tab" class="tab-content">
                        <h2>Discovered Users</h2>
                        <p>Users found in monitored groups but not yet configured.</p>

                        <div style="margin: 20px 0;">
                            <button onclick="consolidateUsers()" class="btn btn-warning" style="margin-right: 10px;">
                                🔧 Consolidate Duplicate UUIDs
                            </button>
                            <span style="font-size: 12px; color: #666;">
                                Remove duplicate entries where the same person has multiple UUIDs
                            </span>
                        </div>

                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Messages</th>
                                    <th>Emoji Reactions</th>
                                    <th>Groups</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {discovered_html or '<tr><td colspan="5">No discovered users yet.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Emoji Picker Modal -->
            <div id="emojiModal" class="emoji-modal" onclick="closeEmojiModal(event)">
                <div class="emoji-modal-content" onclick="event.stopPropagation()">
                    <div class="emoji-modal-header">
                        <h3>Select Emojis</h3>
                        <button onclick="closeEmojiModal()" class="close-btn">&times;</button>
                    </div>
                    <div class="emoji-selected">
                        <h4>Selected: <span id="selectedEmojis"></span></h4>
                        <button onclick="clearSelectedEmojis()" class="btn btn-secondary">Clear</button>
                        <button onclick="saveSelectedEmojis()" class="btn btn-primary">Save</button>
                    </div>
                    <div class="emoji-categories">
                        <button class="emoji-category-btn active" onclick="showEmojiCategory(event, 'faces')">😀 Faces</button>
                        <button class="emoji-category-btn" onclick="showEmojiCategory(event, 'hearts')">❤️ Hearts</button>
                        <button class="emoji-category-btn" onclick="showEmojiCategory(event, 'hands')">👍 Hands</button>
                        <button class="emoji-category-btn" onclick="showEmojiCategory(event, 'activities')">🎉 Activities</button>
                        <button class="emoji-category-btn" onclick="showEmojiCategory(event, 'popular')">🔥 Popular</button>
                    </div>
                    <div class="emoji-container">
                        <div id="faces-emojis" class="emoji-category"></div>
                        <div id="hearts-emojis" class="emoji-category hidden"></div>
                        <div id="hands-emojis" class="emoji-category hidden"></div>
                        <div id="activities-emojis" class="emoji-category hidden"></div>
                        <div id="popular-emojis" class="emoji-category hidden"></div>
                    </div>
                </div>
            </div>

            <script>
                function showTab(tabName) {{
                    // Hide all tabs
                    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
                    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

                    // Show selected tab
                    document.getElementById(tabName + '-tab').classList.add('active');
                    event.target.classList.add('active');
                }}

                // Emoji Picker Variables
                let selectedEmojis = [];
                let currentEditingUser = null;

                // Comprehensive emoji collection
                const emojiCategories = {{
                    faces: [
                        '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩',
                        '😘', '😗', '☺️', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔',
                        '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😔', '😪', '🤤', '😴', '😷', '🤒',
                        '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '😎', '🤓', '🧐'
                    ],
                    hearts: [
                        '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝'
                    ],
                    hands: [
                        '👍', '👎', '👌', '🤌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️',
                        '👋', '🤚', '🖐️', '✋', '🖖', '👏', '🙌', '🤲', '🤝', '🙏', '✍️', '💅', '🤳', '💪'
                    ],
                    activities: [
                        '⚡', '💥', '💫', '💦', '💨', '🔥', '✨', '🌟', '⭐', '🌠', '☄️', '🎯', '💯', '🎉', '🎊', '🎈',
                        '🎁', '🎀', '🎂', '🍰', '🧁', '🚀', '💎', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🏵️', '🌹'
                    ],
                    popular: [
                        '👍', '❤️', '😂', '🔥', '💯', '😍', '🎉', '👏', '😊', '🚀', '💪', '✨', '🙌', '😎', '🤔',
                        '👌', '😀', '💕', '🙏', '🎯', '💎', '🏆', '⚡', '💥', '😉', '🥰', '🤩', '💖', '🌟', '⭐'
                    ]
                }};

                function editUserReactions(userUuid) {{
                    currentEditingUser = userUuid;
                    selectedEmojis = [];

                    // Load existing emojis if any
                    const existingEmojis = getExistingEmojisForUser(userUuid);
                    if (existingEmojis) {{
                        selectedEmojis = [...existingEmojis];
                    }}

                    populateEmojiCategories();
                    updateSelectedEmojisDisplay();
                    showEmojiCategory(null, 'faces');

                    const modal = document.getElementById('emojiModal');
                    modal.style.display = 'flex';
                }}

                function getExistingEmojisForUser(userUuid) {{
                    // Extract existing emojis from the page
                    const userRows = document.querySelectorAll('tr');
                    for (let row of userRows) {{
                        const editBtn = row.querySelector(`button[onclick*="${{userUuid}}"]`);
                        if (editBtn) {{
                            const emojiCell = row.children[2]; // Emoji Reactions column
                            const emojiBadges = emojiCell.querySelectorAll('.emoji-badge');
                            if (emojiBadges.length > 0) {{
                                return Array.from(emojiBadges).map(badge => badge.textContent);
                            }}
                            break;
                        }}
                    }}
                    return [];
                }}

                function populateEmojiCategories() {{
                    Object.keys(emojiCategories).forEach(category => {{
                        const container = document.getElementById(category + '-emojis');
                        if (container) {{
                            container.innerHTML = '';
                            emojiCategories[category].forEach(emoji => {{
                                const btn = document.createElement('button');
                                btn.type = 'button';
                                btn.className = 'emoji-btn';
                                btn.textContent = emoji;
                                btn.onclick = () => selectEmoji(emoji);
                                container.appendChild(btn);
                            }});
                        }}
                    }});
                }}

                function showEmojiCategory(event, category) {{
                    // Hide all categories
                    const categories = ['faces', 'hearts', 'hands', 'activities', 'popular'];
                    categories.forEach(cat => {{
                        const element = document.getElementById(cat + '-emojis');
                        if (element) {{
                            element.classList.add('hidden');
                        }}
                    }});

                    // Show selected category
                    const targetElement = document.getElementById(category + '-emojis');
                    if (targetElement) {{
                        targetElement.classList.remove('hidden');
                    }}

                    // Update button states
                    document.querySelectorAll('.emoji-category-btn').forEach(btn => {{
                        btn.classList.remove('active');
                    }});

                    if (event && event.target) {{
                        event.target.classList.add('active');
                    }} else {{
                        // Find the button for this category and make it active
                        const categoryBtn = document.querySelector(`[onclick*="${{category}}"]`);
                        if (categoryBtn) {{
                            categoryBtn.classList.add('active');
                        }}
                    }}

                    updateEmojiButtonStates();
                }}

                function selectEmoji(emoji) {{
                    if (selectedEmojis.includes(emoji)) {{
                        // Remove emoji
                        const index = selectedEmojis.indexOf(emoji);
                        selectedEmojis.splice(index, 1);
                    }} else {{
                        // Add emoji (limit to 10)
                        if (selectedEmojis.length < 10) {{
                            selectedEmojis.push(emoji);
                        }}
                    }}
                    updateSelectedEmojisDisplay();
                    updateEmojiButtonStates();
                }}

                function updateSelectedEmojisDisplay() {{
                    const display = document.getElementById('selectedEmojis');
                    if (display) {{
                        if (selectedEmojis.length === 0) {{
                            display.textContent = 'None selected';
                        }} else {{
                            display.textContent = selectedEmojis.join(' ');
                        }}
                    }}
                }}

                function updateEmojiButtonStates() {{
                    document.querySelectorAll('.emoji-btn').forEach(btn => {{
                        if (selectedEmojis.includes(btn.textContent)) {{
                            btn.classList.add('selected');
                        }} else {{
                            btn.classList.remove('selected');
                        }}
                    }});
                }}

                function clearSelectedEmojis() {{
                    selectedEmojis = [];
                    updateSelectedEmojisDisplay();
                    updateEmojiButtonStates();
                }}

                function saveSelectedEmojis() {{
                    if (currentEditingUser) {{
                        setUserReactions(currentEditingUser, selectedEmojis);
                        closeEmojiModal();
                    }}
                }}

                function closeEmojiModal(event) {{
                    if (event && event.target !== event.currentTarget) return;

                    const modal = document.getElementById('emojiModal');
                    modal.style.display = 'none';
                    currentEditingUser = null;
                    selectedEmojis = [];
                }}

                function removeUserReactions(userUuid) {{
                    if (confirm('Remove all emoji reactions for this user?')) {{
                        setUserReactions(userUuid, []);
                    }}
                }}

                async function setUserReactions(userUuid, emojis) {{
                    try {{
                        const response = await fetch('/api/users/reactions', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{uuid: userUuid, emojis: emojis}})
                        }});

                        if (response.ok) {{
                            location.reload();
                        }} else {{
                            alert('Failed to update user reactions');
                        }}
                    }} catch (error) {{
                        alert('Error: ' + error.message);
                    }}
                }}

                async function consolidateUsers() {{
                    if (!confirm('This will consolidate duplicate user entries using UUID-first approach with timestamp resolution. This process removes malformed phone-based UUIDs and merges group memberships. Continue?')) {{
                        return;
                    }}

                    const button = event.target;
                    const originalText = button.textContent;
                    button.textContent = '🔄 Consolidating...';
                    button.disabled = true;

                    try {{
                        const response = await fetch('/api/database/consolidate', {{
                            method: 'POST'
                        }});

                        const result = await response.json();

                        if (response.ok) {{
                            alert(`✅ Consolidation complete! Removed ${{result.duplicates_removed}} duplicate entries.`);
                            location.reload();
                        }} else {{
                            alert('❌ Consolidation failed: ' + (result.error || 'Unknown error'));
                        }}
                    }} catch (error) {{
                        alert('Error during consolidation: ' + error.message);
                    }} finally {{
                        button.textContent = originalText;
                        button.disabled = false;
                    }}
                }}
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_messages(self, query: Dict[str, Any]):
        """Serve messages display page for a specific group."""
        group_id = query.get('group_id', [None])[0]
        if not group_id:
            self._send_error(400, "Group ID is required")
            return

        # Debug logging
        self.logger.debug(f"Requested group_id: {group_id}")

        # Get group info
        group = self.db.get_group(group_id)
        if not group:
            self.logger.error(f"Group not found: {group_id}")
            self._send_error(404, "Group not found")
            return

        if not group.is_monitored:
            self._send_error(403, "Group is not monitored")
            return

        # Pagination parameters
        page = int(query.get('page', ['1'])[0])
        per_page = 50
        offset = (page - 1) * per_page

        # Get messages and total count
        messages = self.db.get_group_messages(group_id, limit=per_page, offset=offset)
        total_messages = self.db.get_group_message_count(group_id)
        total_pages = (total_messages + per_page - 1) // per_page

        # Format messages as HTML
        messages_html = ""
        if messages:
            for msg in messages:
                timestamp_ms = msg['timestamp']
                message_text = msg['message_text'] or '<em>No text content</em>'
                # Escape HTML in message text
                message_text = message_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                timestamp_attr = f'data-timestamp="{timestamp_ms}"' if timestamp_ms else ''
                timestamp_display = '' if timestamp_ms else 'Unknown time'

                messages_html += f"""
                <div class="message-item">
                    <div class="message-header">
                        <strong>{msg['sender_name']}</strong>
                        <span class="message-time timestamp" {timestamp_attr}>{timestamp_display}</span>
                    </div>
                    <div class="message-content">
                        {message_text}
                    </div>
                </div>
                """
        else:
            messages_html = '<div class="no-messages">No messages found for this group.</div>'

        # Pagination HTML
        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="pagination">'

            # Previous button
            if page > 1:
                pagination_html += f'<a href="/messages?group_id={quote(group_id)}&page={page-1}" class="page-btn">← Previous</a>'

            # Page numbers
            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            for p in range(start_page, end_page + 1):
                if p == page:
                    pagination_html += f'<span class="page-btn current">{p}</span>'
                else:
                    pagination_html += f'<a href="/messages?group_id={quote(group_id)}&page={p}" class="page-btn">{p}</a>'

            # Next button
            if page < total_pages:
                pagination_html += f'<a href="/messages?group_id={quote(group_id)}&page={page+1}" class="page-btn">Next →</a>'

            pagination_html += '</div>'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Messages - {group.group_name or 'Unnamed Group'}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .card {{
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }}
                .nav {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-bottom: 30px;
                }}
                .nav-item {{
                    padding: 12px 24px;
                    background: #f8f9fa;
                    border-radius: 25px;
                    text-decoration: none;
                    color: #495057;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .nav-item:hover {{ background: #e9ecef; transform: translateY(-2px); }}
                .back-btn {{
                    background: #6c757d;
                    color: white;
                }}
                .back-btn:hover {{ background: #5a6268; }}
                .message-item {{
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                    background: white;
                }}
                .message-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                }}
                .message-time {{
                    color: #6c757d;
                    font-size: 0.85em;
                }}
                .message-content {{
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .no-messages {{
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px;
                }}
                .pagination {{
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }}
                .page-btn {{
                    padding: 8px 12px;
                    text-decoration: none;
                    background: #f8f9fa;
                    color: #495057;
                    border-radius: 5px;
                    transition: background 0.3s;
                }}
                .page-btn:hover {{
                    background: #e9ecef;
                }}
                .page-btn.current {{
                    background: #007bff;
                    color: white;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>Messages from {group.group_name or 'Unnamed Group'}</h1>
                    <div class="nav">
                        <a href="/groups" class="nav-item back-btn">← Back to Groups</a>
                        <a href="/messages/by-sender?group_id={quote(group_id)}" class="nav-item">View by Sender</a>
                        <a href="/" class="nav-item">Dashboard</a>
                        <a href="/users" class="nav-item">Users</a>
                    </div>
                </div>

                <div class="card">
                    <div class="stats">
                        <div>
                            <strong>Group ID:</strong> {group_id[:24]}...
                        </div>
                        <div>
                            <strong>Total Messages:</strong> {total_messages}
                        </div>
                        <div>
                            <strong>Page:</strong> {page} of {total_pages}
                        </div>
                    </div>

                    {pagination_html}

                    <div class="messages-container">
                        {messages_html}
                    </div>

                    {pagination_html}
                </div>
            </div>
            <script>
                function convertTimestamps() {{
                    const timestampElements = document.querySelectorAll('.timestamp[data-timestamp]');
                    timestampElements.forEach(element => {{
                        const timestamp = parseInt(element.getAttribute('data-timestamp'));
                        if (timestamp) {{
                            const date = new Date(timestamp);
                            const localTime = date.toLocaleString();
                            element.textContent = element.textContent.replace('', localTime);
                        }}
                    }});
                }}
                document.addEventListener('DOMContentLoaded', convertTimestamps);
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_all_messages(self, query: Dict[str, Any]):
        """Serve all messages from all groups with source information."""
        page = int(query.get('page', [1])[0])
        per_page = 50
        offset = (page - 1) * per_page

        # Get optional filters
        group_filter = query.get('group_id', [None])[0]
        sender_filter = query.get('sender_uuid', [None])[0]
        attachments_only = query.get('attachments_only', [None])[0] == 'true'

        # Get messages - use the original working method
        try:
            if group_filter and sender_filter:
                messages = self.db.get_messages_by_group_and_sender(group_id=group_filter, sender_uuid=sender_filter, limit=per_page, offset=offset)
                total_messages = self.db.get_message_count_by_group_and_sender(group_filter, sender_filter)
            elif group_filter:
                messages = self.db.get_messages_with_attachments(group_id=group_filter, limit=per_page, offset=offset)
                total_messages = self.db.get_message_count_by_group(group_filter)
            else:
                messages = self.db.get_messages_with_attachments(limit=per_page, offset=offset)
                total_messages = self.db.get_total_message_count()

            # Simple post-filter for attachments if requested
            if attachments_only:
                messages = [msg for msg in messages if msg.get('attachments') and len(msg['attachments']) > 0]
        except Exception as e:
            self.logger.error("Error getting all messages: %s", e)
            self._send_error(500, f"Database error: {e}")
            return

        total_pages = max(1, (total_messages + per_page - 1) // per_page)

        # Get monitored groups for filter dropdown
        monitored_groups = self.db.get_monitored_groups()

        # Build messages HTML
        messages_html = ""
        if not messages:
            messages_html = '<div class="no-messages">No messages found</div>'
        else:
            for msg in messages:
                timestamp_ms = msg['timestamp'] if msg['timestamp'] else None

                message_text = msg.get('message_text')
                if not message_text or message_text.strip() == '':
                    # Skip messages with no meaningful text content
                    continue

                if len(message_text) > 200:
                    message_text = message_text[:200] + '...'

                timestamp_attr = f'data-timestamp="{timestamp_ms}"' if timestamp_ms else ''
                timestamp_display = 'Unknown time' if not timestamp_ms else ''

                # Generate attachments HTML
                attachments_html = ""
                if msg.get('attachments') and len(msg['attachments']) > 0:
                    attachments_html = '<div class="message-attachments">'
                    for attachment in msg['attachments']:
                        file_name = attachment.get('filename', 'Unknown file')
                        content_type = attachment.get('content_type', 'unknown')
                        file_size = attachment.get('file_size', 0)
                        attachment_id = attachment.get('attachment_id')

                        # Format file size
                        size_str = f"{file_size:,} bytes" if file_size < 1024 else f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"

                        # Generate attachment display based on content type
                        if content_type.startswith('image/'):
                            if attachment_id:
                                attachments_html += f'''
                                <div class="attachment attachment-image">
                                    <img src="/attachment/{attachment_id}" alt="{file_name}" style="max-width: 200px; max-height: 200px; border-radius: 4px;">
                                    <div class="attachment-info">📷 {file_name} ({size_str})</div>
                                </div>'''
                            else:
                                attachments_html += f'<div class="attachment">📷 {file_name} ({size_str})</div>'
                        elif content_type.startswith('video/'):
                            attachments_html += f'<div class="attachment">🎥 {file_name} ({size_str})</div>'
                        elif content_type.startswith('audio/'):
                            attachments_html += f'<div class="attachment">🎵 {file_name} ({size_str})</div>'
                        else:
                            attachments_html += f'<div class="attachment">📎 {file_name} ({size_str})</div>'
                    attachments_html += '</div>'

                messages_html += f"""
                <div class="message-item">
                    <div class="message-header">
                        <strong>From:</strong> {msg['sender_display']}
                        <strong>In Group:</strong> {msg['group_display']}
                        <span class="timestamp" {timestamp_attr}>{timestamp_display}</span>
                    </div>
                    <div class="message-content">
                        {message_text}
                        {attachments_html}
                    </div>
                </div>
                """

        # Build pagination
        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="pagination">'

            # Build query string with filters
            filter_params = []
            if group_filter:
                filter_params.append(f"group_id={quote(group_filter)}")
            if sender_filter:
                filter_params.append(f"sender_uuid={quote(sender_filter)}")
            if attachments_only:
                filter_params.append("attachments_only=true")
            filter_param = ("&" + "&".join(filter_params)) if filter_params else ""

            if page > 1:
                pagination_html += f'<a href="/all-messages?page={page-1}{filter_param}" class="page-btn">← Previous</a>'

            # Show page numbers (simple version)
            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            for p in range(start_page, end_page + 1):
                if p == page:
                    pagination_html += f'<span class="page-btn current">{p}</span>'
                else:
                    pagination_html += f'<a href="/all-messages?page={p}{filter_param}" class="page-btn">{p}</a>'

            if page < total_pages:
                pagination_html += f'<a href="/all-messages?page={page+1}{filter_param}" class="page-btn">Next →</a>'

            pagination_html += '</div>'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>All Messages - Signal Bot</title>
            <style>
                {self._get_standard_css()}
                .message-item {{
                    background: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                }}
                .message-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                    font-size: 14px;
                    color: #666;
                }}
                .message-content {{
                    background: white;
                    padding: 10px;
                    border-radius: 4px;
                    border-left: 4px solid #007cba;
                }}
                .timestamp {{
                    font-weight: normal;
                    color: #888;
                }}
                .stats {{
                    display: flex;
                    gap: 30px;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                }}
                .no-messages {{
                    text-align: center;
                    color: #666;
                    padding: 40px;
                    font-style: italic;
                }}
                .pagination {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .page-btn {{
                    display: inline-block;
                    padding: 8px 12px;
                    margin: 0 4px;
                    background: #007cba;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                }}
                .page-btn:hover {{
                    background: #005a87;
                }}
                .page-btn.current {{
                    background: #333;
                }}
                .message-attachments {{
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid #eee;
                }}
                .attachment {{
                    display: inline-block;
                    margin: 5px 10px 5px 0;
                    padding: 8px 12px;
                    background: #f0f8ff;
                    border: 1px solid #b0d4f1;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                .attachment-image {{
                    text-align: center;
                    padding: 10px;
                }}
                .attachment-info {{
                    margin-top: 5px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            {self._get_page_header('💬 All Messages', 'View all messages from monitored groups', 'all-messages')}

                <div class="card">
                    <div class="stats">
                        <div>
                            <strong>Total Messages:</strong> {total_messages}
                        </div>
                        <div>
                            <strong>Page:</strong> {page} of {total_pages}
                        </div>
                        <div>
                            <label for="group-filter"><strong>Filter by Group:</strong></label>
                            <select id="group-filter" onchange="filterByGroup(this.value)" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc;">
                                <option value="">All Monitored Groups</option>
                                {"".join([f'<option value="{g.group_id}" {"selected" if g.group_id == group_filter else ""}>{g.group_name or g.group_id[:16]}</option>' for g in monitored_groups])}
                            </select>
                        </div>
                        <div id="member-filter-container" style="{"display: none;" if not group_filter else ""}">
                            <label for="member-filter"><strong>Filter by Member:</strong></label>
                            <select id="member-filter" onchange="filterByMember(this.value)" style="padding: 5px; border-radius: 4px; border: 1px solid #ccc;">
                                <option value="">All Members</option>
                            </select>
                        </div>
                        <div>
                            <label for="attachments-filter" style="display: flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="attachments-filter" onchange="filterByAttachments(this.checked)" {"checked" if attachments_only else ""} style="margin: 0;">
                                <strong>Show only messages with attachments</strong>
                            </label>
                        </div>
                    </div>
                    <script>
                    let currentGroupId = '{group_filter or ""}';
                    let currentSenderUuid = '{sender_filter or ""}';
                    let currentAttachmentsOnly = {'true' if attachments_only else 'false'};

                    function buildUrl() {{
                        let url = '/all-messages?';
                        let params = [];

                        if (currentGroupId) {{
                            params.push('group_id=' + encodeURIComponent(currentGroupId));
                        }}

                        if (currentSenderUuid) {{
                            params.push('sender_uuid=' + encodeURIComponent(currentSenderUuid));
                        }}

                        if (currentAttachmentsOnly) {{
                            params.push('attachments_only=true');
                        }}

                        return url + params.join('&');
                    }}

                    function filterByGroup(groupId) {{
                        currentGroupId = groupId;
                        if (groupId) {{
                            // Load members for this group
                            loadGroupMembers(groupId);
                        }} else {{
                            // Clear member filter when no group selected
                            document.getElementById('member-filter-container').style.display = 'none';
                            currentSenderUuid = '';
                        }}
                        window.location.href = buildUrl();
                    }}

                    function loadGroupMembers(groupId) {{
                        if (!groupId) return;

                        fetch('/api/group-members?group_id=' + encodeURIComponent(groupId))
                            .then(response => response.json())
                            .then(data => {{
                                if (data.status === 'success') {{
                                    const memberSelect = document.getElementById('member-filter');
                                    memberSelect.innerHTML = '<option value="">All Members</option>';

                                    data.members.forEach(member => {{
                                        const option = document.createElement('option');
                                        option.value = member.uuid;
                                        option.textContent = member.display_name;
                                        if (member.uuid === currentSenderUuid) {{
                                            option.selected = true;
                                        }}
                                        memberSelect.appendChild(option);
                                    }});

                                    document.getElementById('member-filter-container').style.display = 'block';
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error loading group members:', error);
                            }});
                    }}

                    function filterByMember(senderUuid) {{
                        currentSenderUuid = senderUuid;
                        window.location.href = buildUrl();
                    }}

                    function filterByAttachments(attachmentsOnly) {{
                        currentAttachmentsOnly = attachmentsOnly;
                        window.location.href = buildUrl();
                    }}

                    // Load members on page load if group is selected
                    if (currentGroupId) {{
                        loadGroupMembers(currentGroupId);
                    }}
                    </script>
                </div>

                <div class="card">
                    {pagination_html}

                    <div class="messages-container">
                        {messages_html}
                    </div>

                    {pagination_html}
                </div>
            </div>
            <script>
                function convertTimestamps() {{
                    const timestampElements = document.querySelectorAll('.timestamp[data-timestamp]');
                    timestampElements.forEach(element => {{
                        const timestamp = parseInt(element.getAttribute('data-timestamp'));
                        if (timestamp) {{
                            const date = new Date(timestamp);
                            const localTime = date.toLocaleString();
                            element.textContent = element.textContent.replace('', localTime);
                        }}
                    }});
                }}
                document.addEventListener('DOMContentLoaded', convertTimestamps);
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_messages_by_sender(self, query: Dict[str, Any]):
        """Serve messages organized by sender for a specific group."""
        group_id = query.get('group_id', [None])[0]
        if not group_id:
            self._send_error(400, "Group ID is required")
            return

        # Get group info
        group = self.db.get_group(group_id)
        if not group:
            self._send_error(404, "Group not found")
            return

        if not group.is_monitored:
            self._send_error(403, "Group is not monitored")
            return

        # Get sender statistics
        sender_stats = self.db.get_group_sender_stats(group_id)
        total_messages = sum(stat['total_messages'] for stat in sender_stats)

        # Build sender cards HTML
        sender_cards_html = ""
        if sender_stats:
            for stat in sender_stats:
                last_message_timestamp = stat['last_message_timestamp']
                last_message_attr = f'data-timestamp="{last_message_timestamp}"' if last_message_timestamp else ''
                last_message_time = '' if not last_message_timestamp else ''

                sender_cards_html += f"""
                <div class="sender-card">
                    <div class="sender-header">
                        <div class="sender-info">
                            <strong>{stat['sender_name']}</strong>
                            {f'<br><span class="phone-number">{stat["sender_phone"]}</span>' if stat['sender_phone'] else ''}
                        </div>
                        <div class="sender-stats">
                            <div class="stat-item">
                                <span class="stat-number">{stat['total_messages']}</span>
                                <span class="stat-label">messages</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-number">{stat['avg_message_length']}</span>
                                <span class="stat-label">avg length</span>
                            </div>
                        </div>
                    </div>
                    <div class="sender-actions">
                        <span class="last-message timestamp" {last_message_attr}>Last: {last_message_time}</span>
                        <a href="/sender-messages?group_id={quote(group_id)}&sender_uuid={stat['sender_uuid']}" class="btn btn-primary">View Messages</a>
                    </div>
                </div>
                """
        else:
            sender_cards_html = '<div class="no-senders">No message senders found for this group.</div>'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Messages by Sender - {group.group_name or 'Unnamed Group'}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .card {{
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }}
                .nav {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-bottom: 30px;
                }}
                .nav-item {{
                    padding: 12px 24px;
                    background: #f8f9fa;
                    border-radius: 25px;
                    text-decoration: none;
                    color: #495057;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .nav-item:hover {{ background: #e9ecef; transform: translateY(-2px); }}
                .back-btn {{
                    background: #6c757d;
                    color: white;
                }}
                .back-btn:hover {{ background: #5a6268; }}
                .sender-card {{
                    border: 1px solid #dee2e6;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    padding: 20px;
                    background: white;
                    transition: box-shadow 0.3s ease;
                }}
                .sender-card:hover {{ box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .sender-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 15px;
                }}
                .sender-info {{
                    flex: 1;
                }}
                .phone-number {{
                    color: #6c757d;
                    font-size: 0.9em;
                }}
                .sender-stats {{
                    display: flex;
                    gap: 20px;
                }}
                .stat-item {{
                    text-align: center;
                }}
                .stat-number {{
                    display: block;
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #007bff;
                }}
                .stat-label {{
                    display: block;
                    font-size: 0.8em;
                    color: #6c757d;
                    text-transform: uppercase;
                }}
                .sender-actions {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .last-message {{
                    color: #6c757d;
                    font-size: 0.9em;
                }}
                .btn {{
                    padding: 8px 16px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .btn-primary {{
                    background: #007bff;
                    color: white;
                }}
                .btn-primary:hover {{ background: #0056b3; }}
                .no-senders {{
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px;
                }}
                .stats-summary {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 30px;
                    display: flex;
                    justify-content: space-around;
                    text-align: center;
                }}
                .summary-stat {{
                    flex: 1;
                }}
                .summary-number {{
                    display: block;
                    font-size: 2em;
                    font-weight: bold;
                    color: #28a745;
                }}
                .summary-label {{
                    display: block;
                    color: #6c757d;
                    text-transform: uppercase;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>Messages by Sender - {group.group_name or 'Unnamed Group'}</h1>
                    <div class="nav">
                        <a href="/messages?group_id={quote(group_id)}" class="nav-item back-btn">← All Messages</a>
                        <a href="/groups" class="nav-item">Groups</a>
                        <a href="/" class="nav-item">Dashboard</a>
                    </div>
                </div>

                <div class="card">
                    <div class="stats-summary">
                        <div class="summary-stat">
                            <span class="summary-number">{total_messages}</span>
                            <span class="summary-label">Total Messages</span>
                        </div>
                        <div class="summary-stat">
                            <span class="summary-number">{len(sender_stats)}</span>
                            <span class="summary-label">Active Senders</span>
                        </div>
                        <div class="summary-stat">
                            <span class="summary-number">{group.group_name or group_id}</span>
                            <span class="summary-label">Group Name</span>
                        </div>
                    </div>

                    <h2>Message Senders</h2>
                    <div class="senders-container">
                        {sender_cards_html}
                    </div>
                </div>
            </div>
            <script>
                function convertTimestamps() {{
                    const timestampElements = document.querySelectorAll('.timestamp[data-timestamp]');
                    timestampElements.forEach(element => {{
                        const timestamp = parseInt(element.getAttribute('data-timestamp'));
                        if (timestamp) {{
                            const date = new Date(timestamp);
                            const localTime = date.toLocaleString();
                            element.textContent = element.textContent.replace('Last: ', 'Last: ' + localTime);
                        }}
                    }});
                }}
                document.addEventListener('DOMContentLoaded', convertTimestamps);
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    def _serve_sender_messages(self, query: Dict[str, Any]):
        """Serve all messages from a specific sender in a group."""
        group_id = query.get('group_id', [None])[0]
        sender_uuid = query.get('sender_uuid', [None])[0]

        if not group_id or not sender_uuid:
            self._send_error(400, "Group ID and Sender UUID are required")
            return

        # Get group info
        group = self.db.get_group(group_id)
        if not group:
            self._send_error(404, "Group not found")
            return

        if not group.is_monitored:
            self._send_error(403, "Group is not monitored")
            return

        # Get user info
        user = self.db.get_user(sender_uuid)
        sender_name = "Unknown User"
        if user:
            sender_name = user.friendly_name or user.display_name or user.phone_number or sender_uuid[:8]

        # Pagination
        page = int(query.get('page', ['1'])[0])
        per_page = 30
        offset = (page - 1) * per_page

        # Get messages from this sender
        messages = self.db.get_sender_messages(group_id, sender_uuid, limit=per_page, offset=offset)

        # Get total count for pagination
        all_messages = self.db.get_sender_messages(group_id, sender_uuid, limit=1000, offset=0)  # Simple way to get count
        total_messages = len(all_messages)
        total_pages = (total_messages + per_page - 1) // per_page

        # Format messages
        messages_html = ""
        if messages:
            for msg in messages:
                timestamp_ms = msg['timestamp']
                message_text = msg['message_text'] or '<em>No text content</em>'
                message_text = message_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                timestamp_attr = f'data-timestamp="{timestamp_ms}"' if timestamp_ms else ''
                timestamp_display = '' if timestamp_ms else 'Unknown time'

                messages_html += f"""
                <div class="message-item">
                    <div class="message-header">
                        <span class="message-time timestamp" {timestamp_attr}>{timestamp_display}</span>
                    </div>
                    <div class="message-content">
                        {message_text}
                    </div>
                </div>
                """
        else:
            messages_html = '<div class="no-messages">No messages found from this sender.</div>'

        # Pagination HTML
        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="pagination">'
            if page > 1:
                pagination_html += f'<a href="/sender-messages?group_id={quote(group_id)}&sender_uuid={sender_uuid}&page={page-1}" class="page-btn">← Previous</a>'

            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            for p in range(start_page, end_page + 1):
                if p == page:
                    pagination_html += f'<span class="page-btn current">{p}</span>'
                else:
                    pagination_html += f'<a href="/sender-messages?group_id={quote(group_id)}&sender_uuid={sender_uuid}&page={p}" class="page-btn">{p}</a>'

            if page < total_pages:
                pagination_html += f'<a href="/sender-messages?group_id={quote(group_id)}&sender_uuid={sender_uuid}&page={page+1}" class="page-btn">Next →</a>'

            pagination_html += '</div>'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Messages from {sender_name} - {group.group_name or 'Unnamed Group'}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .card {{
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }}
                .nav {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-bottom: 30px;
                }}
                .nav-item {{
                    padding: 12px 24px;
                    background: #f8f9fa;
                    border-radius: 25px;
                    text-decoration: none;
                    color: #495057;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }}
                .nav-item:hover {{ background: #e9ecef; transform: translateY(-2px); }}
                .back-btn {{
                    background: #6c757d;
                    color: white;
                }}
                .back-btn:hover {{ background: #5a6268; }}
                .message-item {{
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                    background: white;
                }}
                .message-header {{
                    margin-bottom: 10px;
                }}
                .message-time {{
                    color: #6c757d;
                    font-size: 0.85em;
                }}
                .message-content {{
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .no-messages {{
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px;
                }}
                .pagination {{
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }}
                .page-btn {{
                    padding: 8px 12px;
                    text-decoration: none;
                    background: #f8f9fa;
                    color: #495057;
                    border-radius: 5px;
                    transition: background 0.3s;
                }}
                .page-btn:hover {{ background: #e9ecef; }}
                .page-btn.current {{
                    background: #007bff;
                    color: white;
                }}
                .sender-info {{
                    background: #e3f2fd;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>Messages from {sender_name}</h1>
                    <div class="nav">
                        <a href="/messages/by-sender?group_id={quote(group_id)}" class="nav-item back-btn">← Back to Senders</a>
                        <a href="/messages?group_id={quote(group_id)}" class="nav-item">All Messages</a>
                        <a href="/groups" class="nav-item">Groups</a>
                    </div>
                </div>

                <div class="card">
                    <div class="sender-info">
                        <h3>{sender_name}</h3>
                        <p>in {group.group_name or 'Unnamed Group'}</p>
                        <p><strong>{total_messages}</strong> total messages | Page {page} of {total_pages}</p>
                    </div>

                    {pagination_html}

                    <div class="messages-container">
                        {messages_html}
                    </div>

                    {pagination_html}
                </div>
            </div>
            <script>
                function convertTimestamps() {{
                    const timestampElements = document.querySelectorAll('.timestamp[data-timestamp]');
                    timestampElements.forEach(element => {{
                        const timestamp = parseInt(element.getAttribute('data-timestamp'));
                        if (timestamp) {{
                            const date = new Date(timestamp);
                            const localTime = date.toLocaleString();
                            element.textContent = element.textContent.replace('', localTime);
                        }}
                    }});
                }}
                document.addEventListener('DOMContentLoaded', convertTimestamps);
            </script>
        </body>
        </html>
        """
        self._send_html_response(html)

    # API Endpoints
    def _api_status(self):
        """Get setup status."""
        status = self.setup_service.get_setup_status()
        self._send_json_response(status)

    def _api_run_setup(self):
        """Run initial setup."""
        result = self.setup_service.run_initial_setup()
        self._send_json_response(result)

    def _api_sync_groups(self):
        """Sync groups and user profiles from Signal."""
        # Get bot configuration
        status = self.setup_service.get_setup_status()
        bot_phone = status.get('bot_phone_number')

        if not bot_phone:
            self._send_json_response({
                'error': 'Bot not configured',
                'synced_count': 0,
                'profiles_updated': 0
            })
            return

        # Sync groups
        synced_count = self.setup_service.sync_groups_to_database()

        # Sync user profiles
        profiles_success = self.setup_service.sync_user_profiles(bot_phone)
        profiles_updated = 0  # TODO: Return actual count from sync_user_profiles

        self._send_json_response({
            'synced_count': synced_count,
            'profiles_updated': profiles_updated,
            'profiles_success': profiles_success
        })

    def _api_groups(self):
        """Get all groups."""
        groups = self.db.get_all_groups()
        groups_data = []
        for group in groups:
            groups_data.append({
                'group_id': group.group_id,
                'group_name': group.group_name,
                'is_monitored': group.is_monitored,
                'member_count': group.member_count
            })
        self._send_json_response({'groups': groups_data})

    def _api_group_members(self, query):
        """Get members of a specific group."""
        group_id = query.get('group_id', [None])[0]

        if not group_id:
            self._send_json_response({
                'status': 'error',
                'error': 'Group ID required'
            })
            return

        # Get group members from database
        members = self.db.get_group_members(group_id)

        members_data = []
        for member in members:
            # Get user info if available
            user_info = self.db.get_user(member.uuid)
            display_name = 'Unknown'

            if user_info:
                if user_info.display_name:
                    display_name = user_info.display_name
                elif user_info.friendly_name:
                    display_name = user_info.friendly_name
                else:
                    display_name = member.uuid[:8] + '...'
            else:
                display_name = member.uuid[:8] + '...'

            members_data.append({
                'uuid': member.uuid,
                'display_name': display_name,
                'is_configured': bool(self.db.get_user_reactions(member.uuid))
            })

        self._send_json_response({
            'status': 'success',
            'members': members_data
        })

    def _api_set_group_monitoring(self, post_data):
        """Set group monitoring status."""
        data = json.loads(post_data)
        group_id = data.get('group_id')
        is_monitored = data.get('is_monitored', False)

        self.db.set_group_monitoring(group_id, is_monitored)
        self._send_json_response({'success': True})

    def _api_users(self):
        """Get all users."""
        configured = self.db.get_configured_users()
        discovered = self.db.get_discovered_users()

        def user_to_dict(user):
            reactions = self.db.get_user_reactions(user.uuid)
            return {
                'uuid': user.uuid,
                'phone_number': user.phone_number,
                'friendly_name': user.friendly_name,
                'display_name': user.display_name,
                'message_count': user.message_count,
                'is_configured': user.is_configured,
                'emojis': reactions.emojis if reactions else []
            }

        self._send_json_response({
            'configured_users': [user_to_dict(user) for user in configured],
            'discovered_users': [user_to_dict(user) for user in discovered]
        })

    def _api_set_user_reactions(self, post_data):
        """Set user emoji reactions."""
        data = json.loads(post_data)
        user_uuid = data.get('uuid')
        emojis = data.get('emojis', [])

        if emojis:
            self.db.set_user_reactions(user_uuid, emojis)
        else:
            self.db.remove_user_reactions(user_uuid)

        self._send_json_response({'success': True})

    def _api_stats(self):
        """Get bot statistics."""
        stats = self.db.get_stats()
        self._send_json_response(stats)

    def _api_generate_link_qr(self):
        """Generate QR code for Signal account linking."""
        try:
            # Parse query parameters for optional phone number
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            phone_number = query_params.get('phone', [''])[0] or None

            # Use setup service to generate linking QR (phone number is optional)
            result = self.setup_service.generate_linking_qr(phone_number)

            if result['success']:
                self._send_json_response({
                    'status': 'success',
                    'linking_uri': result['linking_uri'],
                    'qr_code': result.get('qr_code'),
                    'instructions': result['instructions']
                })
            else:
                self._send_json_response({
                    'status': 'error',
                    'error': result['error']
                })

        except Exception as e:
            self.logger.error(f"Error generating link QR: {e}")
            self._send_error(500, str(e))

    def _api_link_account(self, post_data):
        """Complete Signal account linking process."""
        try:
            data = json.loads(post_data)
            phone_number = data.get('phone_number', '').strip()

            if not phone_number:
                self._send_error(400, 'Phone number is required')
                return

            # Use setup service to complete device linking
            result = self.setup_service.complete_device_linking(phone_number)

            if result['success']:
                self._send_json_response({
                    'status': 'success',
                    'message': f'Account {phone_number} linked successfully',
                    'phone_number': result['phone_number'],
                    'uuid': result['uuid']
                })
            else:
                self._send_json_response({
                    'status': 'error',
                    'error': result['error']
                })

        except Exception as e:
            self.logger.error(f"Error linking Signal account: {e}")
            self._send_error(500, str(e))

    def _api_clear_database(self):
        """Clear all data from the database for a fresh start."""
        try:
            self.logger.info("Database clear requested via web interface")

            success = self.db.clear_database()

            if success:
                self._send_json_response({
                    'status': 'success',
                    'message': 'Database cleared successfully - all tables are empty',
                    'timestamp': datetime.now().isoformat()
                })
                self.logger.info("Database cleared successfully via web interface")
            else:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Failed to clear database - check logs for details'
                })

        except Exception as e:
            self.logger.error(f"Error clearing database: {e}")
            self._send_error(500, str(e))

    def _api_consolidate_users(self):
        """Consolidate duplicate user entries using UUID-first approach."""
        try:
            self.logger.info("UUID consolidation requested via web interface")

            duplicates_removed = self.db.consolidate_duplicate_users()

            self._send_json_response({
                'status': 'success',
                'message': f'UUID consolidation complete. Removed {duplicates_removed} duplicate entries',
                'duplicates_removed': duplicates_removed,
                'timestamp': datetime.now().isoformat()
            })
            self.logger.info(f"UUID consolidation completed via web interface - removed {duplicates_removed} duplicates")

        except Exception as e:
            self.logger.error(f"Error consolidating users: {e}")
            self._send_error(500, str(e))

    def _serve_sentiment(self, query):
        """Serve the sentiment analysis page."""
        try:
            # Get monitored groups for dropdown
            groups = self.db.get_all_groups()
            monitored_groups = [g for g in groups if g.is_monitored]

            # Get selected group from query
            selected_group_id = query.get('group_id', [None])[0]

            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sentiment Analysis - Signal Bot</title>
    <style>
        {self._get_standard_css()}
        .form-group {{ margin-bottom: 15px; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group select, .form-group button {{ padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
        .form-group button {{ background: #007cba; color: white; cursor: pointer; border: none; }}
        .form-group button:hover {{ background: #005a87; }}
        .analysis-result {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
        }}
        .analysis-result h1, .analysis-result h2, .analysis-result h3 {{
            color: #495057;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .analysis-result h1 {{ font-size: 1.5em; }}
        .analysis-result h2 {{ font-size: 1.3em; }}
        .analysis-result h3 {{ font-size: 1.1em; }}
        .analysis-result ul, .analysis-result ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        .analysis-result li {{ margin: 5px 0; }}
        .analysis-result strong {{ color: #2c3e50; }}
        .analysis-result em {{ color: #7f8c8d; }}
        .analysis-result p {{ margin: 10px 0; }}
        .analysis-result blockquote {{
            border-left: 4px solid #007cba;
            margin: 15px 0;
            padding: 10px 20px;
            background: #f1f8ff;
        }}
        .analysis-metadata {{
            background: #e9ecef;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #007cba;
        }}
        .analysis-metadata h3 {{
            margin-top: 0;
            margin-bottom: 10px;
            color: #007cba;
        }}
        .analysis-metadata p {{
            margin: 5px 0;
            color: #495057;
        }}
        .privacy-local {{
            color: #28a745 !important;
            font-weight: bold;
        }}
        .privacy-external {{
            color: #ffc107 !important;
            font-weight: bold;
        }}
        .loading {{ text-align: center; padding: 40px; color: #666; }}
        .error {{ color: #dc3545; background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; }}
    </style>
</head>
<body>
    {self._get_page_header('🧠 Sentiment Analysis', 'AI-powered analysis of group chat emotions and mood', 'sentiment')}

        <div class="card">
            <h2>Analyze Group Sentiment</h2>
            <form id="sentimentForm">
                <div class="form-group">
                    <label for="group-select">Select Group:</label>
                    <select id="group-select" name="group_id" required>
                        <option value="">Choose a monitored group...</option>"""

            for group in monitored_groups:
                group_id = group.group_id
                display_name = group.group_name or group_id[:8] + '...'
                selected = 'selected' if group_id == selected_group_id else ''
                html += f'<option value="{group_id}" {selected}>{display_name}</option>'

            html += """
                    </select>
                </div>
                <div class="form-group">
                    <label for="date-select">Select Date:</label>
                    <input type="date" id="date-select" name="date" style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                </div>
                <div class="form-group">
                    <button type="submit">Analyze Sentiment</button>
                    <button type="button" id="forceRefreshBtn" style="margin-left: 10px; background: #dc3545;">Force Refresh</button>
                </div>
            </form>
        </div>

        <div class="card" id="preview" style="display: none;">
            <h2>Analysis Preview</h2>
            <div id="preview-content"></div>
            <div style="margin-top: 15px;">
                <button type="button" id="proceedBtn" style="background: #28a745;">Proceed with Analysis</button>
                <button type="button" id="cancelBtn" style="background: #6c757d; margin-left: 10px;">Cancel</button>
            </div>
        </div>

        <div class="card" id="results" style="display: none;">
            <h2>Analysis Results</h2>
            <div id="analysis-content" class="analysis-result"></div>
        </div>
    </div>

    <script>

        let currentGroupId = null;
        let currentTimezone = null;
        let currentDate = null;

        function loadCachedResults(groupId) {
            if (!groupId) return;

            currentGroupId = groupId;
            currentTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

            // Use selected date or default to today
            const dateSelect = document.getElementById('date-select');
            currentDate = dateSelect.value || new Date().toISOString().split('T')[0];

            const url = `/api/sentiment-cached?group_id=${encodeURIComponent(groupId)}&timezone=${encodeURIComponent(currentTimezone)}&date=${currentDate}`;

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.cached) {
                        const resultsDiv = document.getElementById('results');
                        const contentDiv = document.getElementById('analysis-content');

                        resultsDiv.style.display = 'block';
                        contentDiv.innerHTML = `<div class="cached-notice" style="background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; color: #155724;">
                            📋 Showing cached analysis from ${currentDate}
                        </div>` +
                        convertMarkdownToHtml(data.result);
                    }
                })
                .catch(error => {
                    console.error('Error loading cached results:', error);
                });
        }

        function showPreview(groupId) {
            if (!groupId) return;

            const url = `/api/sentiment-preview?group_id=${encodeURIComponent(groupId)}&timezone=${encodeURIComponent(currentTimezone)}&date=${currentDate}`;

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const previewDiv = document.getElementById('preview');
                        const previewContent = document.getElementById('preview-content');

                        if (data.analyzable_messages === 0) {
                            previewContent.innerHTML = `
                                <div class="preview-stats">
                                    <h3>${data.group_name}</h3>
                                    <p><strong>Date:</strong> ${data.date} (${data.timezone})</p>
                                    <p><strong>Total messages found:</strong> ${data.total_messages}</p>
                                    <p><strong>Analyzable messages:</strong> ${data.analyzable_messages}</p>
                                    <p><strong>Filtered out:</strong> ${data.filtered_out} (empty, system, or trivial messages)</p>
                                    <div style="color: #856404; background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                        ⚠️ No substantive messages found for this date. Analysis would return "No messages" result.
                                    </div>
                                </div>`;
                        } else {
                            const timeRange = data.time_range ? `${data.time_range.start} - ${data.time_range.end}` : 'N/A';
                            const efficiency = data.filtered_out > 0 ?
                                `<p><strong>Filtered out:</strong> ${data.filtered_out} non-substantive messages for efficiency</p>` :
                                '';
                            previewContent.innerHTML = `
                                <div class="preview-stats">
                                    <h3>${data.group_name}</h3>
                                    <p><strong>Date:</strong> ${data.date} (${data.timezone})</p>
                                    <p><strong>Total messages found:</strong> ${data.total_messages}</p>
                                    <p><strong>Analyzable messages:</strong> ${data.analyzable_messages}</p>
                                    ${efficiency}
                                    <p><strong>Time range:</strong> ${timeRange}</p>
                                    <div style="color: #155724; background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                        ✅ Ready for optimized sentiment analysis with ${data.analyzable_messages} substantive messages
                                    </div>
                                </div>`;
                        }

                        previewDiv.style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error('Error getting preview:', error);
                });
        }

        function hideAllCards() {
            document.getElementById('preview').style.display = 'none';
            document.getElementById('results').style.display = 'none';
        }

        function performAnalysis(forceRefresh = false) {
            if (!currentGroupId) return;

            hideAllCards();
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('analysis-content');

            resultsDiv.style.display = 'block';
            const actionText = forceRefresh ? 'Generating new analysis' : 'Starting sentiment analysis';
            contentDiv.innerHTML = `<div class="loading">🤖 ${actionText} with AI...</div>`;

            // Start analysis
            const url = forceRefresh
                ? `/api/sentiment?group_id=${encodeURIComponent(currentGroupId)}&force=true&timezone=${encodeURIComponent(currentTimezone)}&date=${currentDate}`
                : `/api/sentiment?group_id=${encodeURIComponent(currentGroupId)}&timezone=${encodeURIComponent(currentTimezone)}&date=${currentDate}`;

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'started') {
                        // Poll for results
                        pollForResults(data.job_id);
                    } else {
                        contentDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                    }
                })
                .catch(error => {
                    contentDiv.innerHTML = `<div class="error">Failed to start analysis: ${error}</div>`;
                });

            function pollForResults(jobId) {
                const startTime = Date.now();

                function checkStatus() {
                    fetch(`/api/sentiment?job_id=${jobId}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                contentDiv.innerHTML = data.analysis;
                            } else if (data.status === 'error') {
                                contentDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                            } else if (data.status === 'running') {
                                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                                contentDiv.innerHTML = `<div class="loading">🤖 Analyzing sentiment... (${elapsed}s)</div>`;
                                // Poll again in 2 seconds
                                setTimeout(checkStatus, 2000);
                            }
                        })
                        .catch(error => {
                            contentDiv.innerHTML = `<div class="error">Failed to check status: ${error}</div>`;
                        });
                }

                // Start polling
                setTimeout(checkStatus, 1000);
            }
        }

        // Event handlers
        document.getElementById('group-select').addEventListener('change', function(e) {
            const groupId = e.target.value;
            hideAllCards();
            if (groupId) {
                loadCachedResults(groupId);
            }
        });

        document.getElementById('date-select').addEventListener('change', function(e) {
            const groupId = document.getElementById('group-select').value;
            hideAllCards();
            if (groupId) {
                loadCachedResults(groupId);
            }
        });

        document.getElementById('sentimentForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const groupId = document.getElementById('group-select').value;
            const selectedDate = document.getElementById('date-select').value;

            if (!groupId) {
                alert('Please select a group');
                return;
            }
            if (!selectedDate) {
                alert('Please select a date');
                return;
            }

            currentGroupId = groupId;
            currentTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            currentDate = selectedDate;

            hideAllCards();
            showPreview(groupId);
        });

        document.getElementById('proceedBtn').addEventListener('click', function() {
            performAnalysis(false);
        });

        document.getElementById('cancelBtn').addEventListener('click', function() {
            hideAllCards();
        });

        document.getElementById('forceRefreshBtn').addEventListener('click', function() {
            const groupId = document.getElementById('group-select').value;
            const selectedDate = document.getElementById('date-select').value;

            if (!groupId) {
                alert('Please select a group');
                return;
            }
            if (!selectedDate) {
                alert('Please select a date');
                return;
            }

            currentGroupId = groupId;
            currentTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            currentDate = selectedDate;

            performAnalysis(true);
        });

        // Load cached results on page load if a group is pre-selected
        document.addEventListener('DOMContentLoaded', function() {
            // Set default date to today
            document.getElementById('date-select').valueAsDate = new Date();

            const groupSelect = document.getElementById('group-select');
            if (groupSelect.value) {
                loadCachedResults(groupSelect.value);
            }
        });
    </script>
</body>
</html>"""

            self._send_html_response(html)

        except Exception as e:
            self.logger.error(f"Error serving sentiment page: {e}")
            self._send_error(500, str(e))

    def _api_sentiment_analysis(self, query):
        """API endpoint for sentiment analysis."""
        try:
            # Check if this is a status check
            job_id = query.get('job_id', [None])[0]
            if job_id:
                return self._api_sentiment_status(job_id)

            group_id = query.get('group_id', [None])[0]
            if not group_id:
                self._send_json_response({
                    'status': 'error',
                    'error': 'group_id parameter is required'
                })
                return

            # Check if force refresh is requested
            force_refresh = query.get('force', [False])[0] == 'true'

            # Get timezone and date from client
            user_timezone = query.get('timezone', [None])[0]
            user_date_str = query.get('date', [None])[0]

            # Parse user's date
            if user_date_str:
                try:
                    user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                except ValueError:
                    user_date = date.today()
            else:
                user_date = date.today()

            # Create a unique job ID
            job_id = str(uuid.uuid4())

            # Get group info for name
            group_info = self.db.get_group(group_id)
            group_name = group_info.group_name if group_info else 'Unknown Group'

            # Store job info
            WebHandler._analysis_jobs[job_id] = {
                'status': 'running',
                'group_id': group_id,
                'group_name': group_name,
                'started_at': time.time(),
                'result': None,
                'error': None
            }

            # Start analysis in background thread
            def run_analysis():
                try:
                    analyzer = SentimentAnalyzer(self.db)
                    analysis = analyzer.analyze_group_daily_sentiment(
                        group_id, group_name,
                        target_date=user_date,
                        force_refresh=force_refresh,
                        user_timezone=user_timezone
                    )

                    if analysis:
                        WebHandler._analysis_jobs[job_id]['status'] = 'completed'
                        WebHandler._analysis_jobs[job_id]['result'] = analysis
                    else:
                        WebHandler._analysis_jobs[job_id]['status'] = 'error'
                        WebHandler._analysis_jobs[job_id]['error'] = 'Failed to generate sentiment analysis'

                except Exception as e:
                    WebHandler._analysis_jobs[job_id]['status'] = 'error'
                    WebHandler._analysis_jobs[job_id]['error'] = str(e)

            # Start background thread
            thread = threading.Thread(target=run_analysis, daemon=True)
            thread.start()

            # Return job ID immediately
            self._send_json_response({
                'status': 'started',
                'job_id': job_id,
                'group_name': group_name
            })

        except Exception as e:
            self.logger.error(f"Error starting sentiment analysis: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_sentiment_status(self, job_id):
        """Check status of sentiment analysis job."""
        try:
            if job_id not in WebHandler._analysis_jobs:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Job not found'
                })
                return

            job = WebHandler._analysis_jobs[job_id]

            if job['status'] == 'completed':
                # Clean up job after returning result
                job_result = job['result']

                # Handle new structured format vs old string format
                if isinstance(job_result, dict) and 'metadata' in job_result and 'analysis' in job_result:
                    # New structured format - format metadata as HTML and convert analysis markdown
                    metadata = job_result['metadata']

                    # Privacy indicator
                    is_local = metadata.get('is_local', False)
                    privacy_class = 'privacy-local' if is_local else 'privacy-external'
                    privacy_text = 'Local AI (Full Details)' if is_local else 'External AI (Anonymized)'
                    privacy_icon = '🏠' if is_local else '🌐'

                    metadata_html = f"""
                    <div class="analysis-metadata">
                        <h3>Sentiment Analysis: {metadata['group_name']} - {metadata['date']} ({metadata['timezone']})</h3>
                        <p><strong>Messages analyzed:</strong> {metadata['message_count']}</p>
                        <p><strong>Time range:</strong> {metadata['time_range']}</p>
                        <p><strong>Timezone:</strong> {metadata['timezone']}</p>
                        <p class="{privacy_class}"><strong>Privacy Mode:</strong> {privacy_icon} {privacy_text}</p>
                        <p><strong>Provider:</strong> {metadata.get('provider_info', 'unknown')}</p>
                    </div>
                    """
                    analysis_html = convert_markdown_to_html(job_result['analysis'])
                    combined_html = metadata_html + analysis_html
                else:
                    # Old format - convert entire string
                    combined_html = convert_markdown_to_html(job_result)

                result = {
                    'status': 'success',
                    'analysis': combined_html,
                    'group_id': job['group_id'],
                    'group_name': job['group_name']
                }
                del WebHandler._analysis_jobs[job_id]
                self._send_json_response(result)

            elif job['status'] == 'error':
                # Clean up job after returning error
                result = {
                    'status': 'error',
                    'error': job['error']
                }
                del WebHandler._analysis_jobs[job_id]
                self._send_json_response(result)

            else:
                # Still running
                self._send_json_response({
                    'status': 'running',
                    'elapsed': time.time() - job['started_at']
                })

        except Exception as e:
            self.logger.error(f"Error checking sentiment analysis status: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_sentiment_cached(self, query):
        """Get cached sentiment analysis for a group and date."""
        try:
            group_id = query.get('group_id', [None])[0]
            if not group_id:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Group ID is required'
                })
                return

            # Get user's timezone and date
            user_timezone = query.get('timezone', [None])[0]
            user_date_str = query.get('date', [None])[0]

            if user_date_str:
                from datetime import datetime
                user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
            else:
                from datetime import date
                user_date = date.today()

            # Get cached result
            cached_result = self.db.get_sentiment_analysis(group_id, user_date)

            if cached_result:
                self._send_json_response({
                    'status': 'success',
                    'cached': True,
                    'result': cached_result
                })
            else:
                self._send_json_response({
                    'status': 'success',
                    'cached': False,
                    'result': None
                })

        except Exception as e:
            self.logger.error(f"Error getting cached sentiment: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_sentiment_preview(self, query):
        """Get message count preview for sentiment analysis."""
        try:
            group_id = query.get('group_id', [None])[0]
            if not group_id:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Group ID is required'
                })
                return

            # Get user's timezone and date
            user_timezone = query.get('timezone', [None])[0]
            user_date_str = query.get('date', [None])[0]

            if user_date_str:
                from datetime import datetime
                user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
            else:
                from datetime import date
                user_date = date.today()

            # Get group info
            group = self.db.get_group(group_id)
            if not group:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Group not found'
                })
                return

            # Get message count for the date
            analyzer = SentimentAnalyzer(self.db)
            messages = analyzer.get_daily_messages(group_id, user_date, user_timezone)

            # Apply the same filtering logic as the sentiment analysis
            filtered_messages = []
            for msg in messages:
                text = msg.get('text', '').strip()
                sender = msg.get('sender', '').strip()

                # Skip messages with no text content
                if not text:
                    continue

                # Skip system messages or empty sender names
                if not sender or sender.lower() in ['unknown', 'system']:
                    continue

                # Skip very short messages that don't add sentiment value
                if len(text) < 3:
                    continue

                # Skip common non-sentiment messages
                if text.lower() in ['ok', 'yes', 'no', 'k', 'thanks', 'thx']:
                    continue

                filtered_messages.append(msg)

            self._send_json_response({
                'status': 'success',
                'group_name': group.group_name or 'Unnamed Group',
                'date': user_date.strftime('%Y-%m-%d'),
                'timezone': user_timezone or 'UTC',
                'total_messages': len(messages),
                'analyzable_messages': len(filtered_messages),
                'filtered_out': len(messages) - len(filtered_messages),
                'time_range': self._get_timezone_aware_time_range(filtered_messages, user_timezone) if filtered_messages else None
            })

        except Exception as e:
            self.logger.error(f"Error getting sentiment preview: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _get_timezone_aware_time_range(self, messages, user_timezone):
        """Convert message time range to user timezone."""
        if not messages:
            return None

        try:
            if user_timezone:
                from datetime import datetime, timezone
                import zoneinfo

                user_tz = zoneinfo.ZoneInfo(user_timezone)

                # Convert first and last message timestamps
                first_utc = datetime.fromtimestamp(messages[0]['timestamp'] / 1000, timezone.utc)
                last_utc = datetime.fromtimestamp(messages[-1]['timestamp'] / 1000, timezone.utc)

                first_local = first_utc.astimezone(user_tz).strftime('%H:%M')
                last_local = last_utc.astimezone(user_tz).strftime('%H:%M')

                return {'start': first_local, 'end': last_local}
            else:
                # Fallback to UTC times
                return {
                    'start': messages[0]['time'].split()[1][:5],
                    'end': messages[-1]['time'].split()[1][:5]
                }
        except Exception:
            # Fallback to UTC times on any error
            return {
                'start': messages[0]['time'].split()[1][:5],
                'end': messages[-1]['time'].split()[1][:5]
            }

    def _serve_activity_visualization(self, query):
        """Serve the activity visualization page with hourly message charts."""
        try:
            # Get monitored groups for display
            groups = self.db.get_all_groups()
            monitored_groups = [g for g in groups if g.is_monitored]

            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Activity Visualization - Signal Bot</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_standard_css()}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .date-selector {{
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }}
        .chart-title {{
            text-align: center;
            margin-bottom: 20px;
            color: #333;
            font-size: 18px;
            font-weight: bold;
        }}
        canvas {{
            max-height: 400px;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    {self._get_page_header('📊 Activity Visualization', 'Hourly message activity patterns by group', 'activity')}

        <div class="card">
            <div class="date-selector">
                <label for="date-input">Select Date:</label>
                <input type="date" id="date-input" value="" style="margin-left: 10px; padding: 8px; border-radius: 4px; border: 1px solid #ddd;">
                <button onclick="loadActivityData()" style="margin-left: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Load Activity</button>
            </div>

            <div id="charts-container">
                <div class="loading">
                    <p>Select a date to view hourly message activity</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let activityCharts = [];

        // Set default date to today
        document.getElementById('date-input').valueAsDate = new Date();

        // Auto-load today's data
        window.onload = function() {{
            loadActivityData();
        }};

        async function loadActivityData() {{
            const dateInput = document.getElementById('date-input');
            const selectedDate = dateInput.value;

            if (!selectedDate) {{
                alert('Please select a date');
                return;
            }}

            const container = document.getElementById('charts-container');
            container.innerHTML = '<div class="loading"><p>Loading activity data...</p></div>';

            try {{
                // Get user's timezone
                const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

                const response = await fetch(`/api/activity/hourly?date=${{selectedDate}}&timezone=${{encodeURIComponent(userTimezone)}}`);
                const data = await response.json();

                if (data.status === 'error') {{
                    container.innerHTML = `<div class="alert alert-error">${{data.error}}</div>`;
                    return;
                }}

                if (!data.groups || data.groups.length === 0) {{
                    container.innerHTML = `<div class="alert alert-info">No activity data found for ${{selectedDate}}</div>`;
                    return;
                }}

                // Clear previous charts
                activityCharts.forEach(chart => chart.destroy());
                activityCharts = [];

                // Create container HTML
                let chartsHtml = '';
                data.groups.forEach((group, index) => {{
                    chartsHtml += `
                        <div class="chart-container">
                            <div class="chart-title">${{group.group_name}} - ${{group.total_messages}} messages</div>
                            <canvas id="chart-${{index}}" width="400" height="200"></canvas>
                        </div>
                    `;
                }});

                container.innerHTML = chartsHtml;

                // Create charts
                data.groups.forEach((group, index) => {{
                    const ctx = document.getElementById(`chart-${{index}}`).getContext('2d');
                    const chart = new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: Array.from({{length: 24}}, (_, i) => `${{i.toString().padStart(2, '0')}}:00`),
                            datasets: [{{
                                label: 'Messages per Hour',
                                data: group.hourly_data,
                                backgroundColor: `hsl(${{(index * 137.5) % 360}}, 70%, 60%)`,
                                borderColor: `hsl(${{(index * 137.5) % 360}}, 70%, 50%)`,
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    ticks: {{
                                        stepSize: 1
                                    }}
                                }}
                            }},
                            plugins: {{
                                legend: {{
                                    display: false
                                }}
                            }}
                        }}
                    }});
                    activityCharts.push(chart);
                }});

            }} catch (error) {{
                console.error('Error loading activity data:', error);
                container.innerHTML = `<div class="alert alert-error">Error loading activity data: ${{error.message}}</div>`;
            }}
        }}
    </script>
</body>
</html>"""

            self._send_html_response(html)

        except Exception as e:
            self.logger.error(f"Error serving activity visualization: {e}")
            self._send_error(500, str(e))

    def _api_activity_hourly(self, query):
        """API endpoint for hourly activity data."""
        try:
            # Get date and timezone from query
            target_date_str = query.get('date', [None])[0]
            user_timezone = query.get('timezone', [None])[0]

            if not target_date_str:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Date parameter required'
                })
                return

            # Parse the date
            from datetime import date
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                })
                return

            # Get hourly data from database
            hourly_data = self.db.get_hourly_message_counts(target_date, user_timezone)

            if not hourly_data:
                self._send_json_response({
                    'status': 'success',
                    'groups': [],
                    'total_messages': 0,
                    'date': target_date_str,
                    'timezone': user_timezone or 'UTC'
                })
                return

            # Group data by group_id
            groups_data = {}
            total_messages = 0

            for row in hourly_data:
                group_name = row['group_name'] or 'Unnamed Group'
                group_id = row['group_id']
                hour = row['hour']
                count = row['message_count']

                if group_id not in groups_data:
                    groups_data[group_id] = {
                        'group_name': group_name,
                        'hourly_data': [0] * 24,  # Initialize 24 hours with 0
                        'total_messages': 0
                    }

                groups_data[group_id]['hourly_data'][hour] = count
                groups_data[group_id]['total_messages'] += count
                total_messages += count

            # Convert to list format for frontend
            result_groups = []
            for group_id, data in groups_data.items():
                result_groups.append({
                    'group_id': group_id,
                    'group_name': data['group_name'],
                    'hourly_data': data['hourly_data'],
                    'total_messages': data['total_messages']
                })

            # Sort by total messages (most active first)
            result_groups.sort(key=lambda x: x['total_messages'], reverse=True)

            self._send_json_response({
                'status': 'success',
                'groups': result_groups,
                'total_messages': total_messages,
                'date': target_date_str,
                'timezone': user_timezone or 'UTC'
            })

        except Exception as e:
            self.logger.error(f"Error getting hourly activity data: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _serve_attachment(self, path: str):
        """Serve attachment files from the database."""
        try:
            # Extract attachment ID from path /attachment/{attachment_id}
            attachment_id = path.split('/attachment/')[-1]
            if not attachment_id:
                self._send_404()
                return

            # Get attachment data from database
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT filename, content_type, file_size, file_data
                    FROM attachments
                    WHERE attachment_id = ?
                """, (attachment_id,))
                attachment = cursor.fetchone()

            if not attachment:
                self._send_404()
                return

            # Check if we have file data in database
            file_data = attachment['file_data']
            if not file_data:
                self.logger.warning(f"Attachment {attachment_id} has no file data stored")
                self._send_404()
                return

            # Determine content type
            content_type = attachment['content_type'] if attachment['content_type'] else 'application/octet-stream'

            # If no content type from database, try to guess from filename
            if content_type == 'application/octet-stream' or not content_type:
                filename = attachment.get('filename')
                if filename:
                    guessed_type, _ = mimetypes.guess_type(filename)
                    if guessed_type:
                        content_type = guessed_type

            # Send the file data from database
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(file_data)))

            # Add filename header if available
            if attachment['filename']:
                self.send_header('Content-Disposition', f'inline; filename="{attachment["filename"]}"')

            self.end_headers()
            self.wfile.write(file_data)

            self.logger.debug(f"Served attachment {attachment_id} ({len(file_data)} bytes) from database")

        except Exception as e:
            self.logger.error(f"Error serving attachment {path}: {e}")
            self._send_error(500, "Internal server error")

    def _serve_summary(self, query):
        """Serve the message summarization page."""
        try:
            # Get monitored groups for dropdown
            groups = self.db.get_all_groups()
            monitored_groups = [g for g in groups if g.is_monitored]

            # Get selected group from query
            selected_group_id = query.get('group_id', [None])[0]

            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Message Summary - Signal Bot</title>
    <style>
        {self._get_standard_css()}
        .form-group {{ margin-bottom: 15px; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group input, .form-group select, .form-group button {{ padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
        .form-group button {{ background: #007cba; color: white; cursor: pointer; border: none; }}
        .form-group button:hover {{ background: #005a87; }}
        .summary-result {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.8;
        }}
        .summary-result h1, .summary-result h2, .summary-result h3 {{
            color: #495057;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .summary-result h1 {{ font-size: 1.5em; }}
        .summary-result h2 {{ font-size: 1.3em; }}
        .summary-result h3 {{ font-size: 1.1em; }}
        .summary-result ul, .summary-result ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        .summary-result li {{ margin: 5px 0; }}
        .summary-result strong {{ color: #2c3e50; }}
        .summary-result em {{ color: #7f8c8d; }}
        .summary-result p {{ margin: 10px 0; }}
        .summary-result blockquote {{
            border-left: 4px solid #007cba;
            margin: 15px 0;
            padding: 10px 20px;
            background: #f1f8ff;
        }}
        .loading {{ text-align: center; padding: 40px; color: #666; }}
        .error {{ color: #dc3545; background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; }}
        .time-preset {{ display: inline-block; margin: 5px; }}
        .time-preset button {{ background: #6c757d; font-size: 13px; padding: 8px 12px; }}
        .time-preset button:hover {{ background: #5a6268; }}
        .time-preset button.active {{ background: #28a745; }}
        .summary-meta {{ background: #e9ecef; padding: 10px; border-radius: 4px; margin-bottom: 15px; font-size: 14px; }}
        .summary-meta strong {{ color: #495057; }}
        .privacy-local {{
            color: #28a745 !important;
            font-weight: bold;
        }}
        .privacy-external {{
            color: #ffc107 !important;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    {self._get_page_header('📝 Message Summary', 'AI-powered summaries of recent conversations', 'summary')}

    <div class="card">
        <h2>Summarize Recent Messages</h2>
        <form id="summaryForm">
            <div class="form-group">
                <label for="group-select">Select Group:</label>
                <select id="group-select" name="group_id" required>
                    <option value="">Choose a monitored group...</option>"""

            for group in monitored_groups:
                group_id = group.group_id
                display_name = group.group_name or group_id[:8] + '...'
                selected = 'selected' if group_id == selected_group_id else ''
                html += f'<option value="{group_id}" {selected}>{display_name}</option>'

            html += """
                </select>
            </div>
            <div class="form-group">
                <label for="hours-input">Time Range:</label>
                <input type="number" id="hours-input" name="hours" min="1" max="168" value="24" required>
                <span style="margin-left: 10px;">hours</span>
                <div class="time-preset">
                    <button type="button" onclick="setHours(1)">1 hour</button>
                    <button type="button" onclick="setHours(3)">3 hours</button>
                    <button type="button" onclick="setHours(6)">6 hours</button>
                    <button type="button" onclick="setHours(12)">12 hours</button>
                    <button type="button" onclick="setHours(24)" class="active">24 hours</button>
                    <button type="button" onclick="setHours(48)">2 days</button>
                    <button type="button" onclick="setHours(72)">3 days</button>
                    <button type="button" onclick="setHours(168)">1 week</button>
                </div>
            </div>
            <div class="form-group">
                <button type="submit">Generate Summary</button>
            </div>
        </form>
    </div>

    <div class="card" id="loading" style="display: none;">
        <div class="loading">
            <h3>⏳ Analyzing messages...</h3>
            <p>This may take a few moments depending on the number of messages.</p>
        </div>
    </div>

    <div class="card" id="results" style="display: none;">
        <h2>Summary Results</h2>
        <div id="summary-meta" class="summary-meta"></div>
        <div id="summary-content" class="summary-result"></div>
    </div>
</div>

<script src="/static/markdown.js"></script>
<script>
    function setHours(hours) {
        document.getElementById('hours-input').value = hours;
        // Update button states
        document.querySelectorAll('.time-preset button').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
    }

    document.getElementById('summaryForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const groupId = document.getElementById('group-select').value;
        const hours = document.getElementById('hours-input').value;

        if (!groupId) {
            alert('Please select a group');
            return;
        }

        // Show loading, hide results
        document.getElementById('loading').style.display = 'block';
        document.getElementById('results').style.display = 'none';

        try {
            const response = await fetch(`/api/summary?group_id=${encodeURIComponent(groupId)}&hours=${hours}`);
            const data = await response.json();

            document.getElementById('loading').style.display = 'none';

            if (data.status === 'success' || data.status === 'no_messages') {
                // Privacy indicator based on AI provider
                const isLocal = data.is_local || false;
                const privacyClass = isLocal ? 'privacy-local' : 'privacy-external';
                const privacyText = isLocal ? 'Local AI (Full Details)' : 'External AI (Anonymized)';
                const privacyIcon = isLocal ? '🏠' : '🌐';

                const metaHtml = `
                    <strong>Group:</strong> ${data.group_name}<br>
                    <strong>Time Period:</strong> Last ${data.hours} hour${data.hours > 1 ? 's' : ''}<br>
                    <strong>Messages Analyzed:</strong> ${data.message_count}<br>
                    <strong>Generated:</strong> ${data.analyzed_at ? new Date(data.analyzed_at).toLocaleString() : 'Just now'}<br>
                    <strong class="${privacyClass}">Privacy Mode:</strong> <span class="${privacyClass}">${privacyIcon} ${privacyText}</span><br>
                    <strong>Provider:</strong> ${data.provider_info || data.ai_provider || 'unknown'}
                `;
                document.getElementById('summary-meta').innerHTML = metaHtml;
                document.getElementById('summary-content').innerHTML = data.summary;
                document.getElementById('results').style.display = 'block';
            } else {
                document.getElementById('summary-content').innerHTML = `<div class="error">Error: ${data.error || 'Failed to generate summary'}</div>`;
                document.getElementById('results').style.display = 'block';
            }
        } catch (error) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('summary-content').innerHTML = `<div class="error">Error: ${error.message}</div>`;
            document.getElementById('results').style.display = 'block';
        }
    });
</script>
</body>
</html>"""

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())

        except Exception as e:
            self.logger.error(f"Error serving summary page: {e}")
            self._send_error(500, "Internal server error")

    def _api_summary(self, query):
        """API endpoint for message summarization."""
        try:
            # Get parameters
            group_id = query.get('group_id', [None])[0]
            hours = int(query.get('hours', [24])[0])
            user_timezone = query.get('timezone', [None])[0]

            if not group_id:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Group ID required'
                })
                return

            # Get group info
            group = self.db.get_group(group_id)
            if not group:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Group not found'
                })
                return

            group_name = group.group_name or f"Group {group_id[:8]}..."

            # Create summarizer
            summarizer = MessageSummarizer(self.db)

            # Check if AI is available
            if not summarizer.check_ai_available():
                self._send_json_response({
                    'status': 'error',
                    'error': 'No AI providers are available. Please install Ollama or Gemini CLI to use this feature.'
                })
                return

            # Generate summary with user timezone
            result = summarizer.summarize_messages(group_id, group_name, hours, user_timezone)

            # Convert markdown to HTML if successful
            if result and result.get('status') == 'success' and 'summary' in result:
                result['summary'] = convert_markdown_to_html(result['summary'])

            # Return result
            self._send_json_response(result)

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _serve_ai_config(self, query):
        """Serve the AI configuration page."""
        try:
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>AI Configuration - Signal Bot</title>
    <style>
        {self._get_standard_css()}
        .provider-card {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .provider-available {{ border-left: 4px solid #28a745; }}
        .provider-unavailable {{ border-left: 4px solid #dc3545; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
        .status-available {{ background: #d4edda; color: #155724; }}
        .status-unavailable {{ background: #f8d7da; color: #721c24; }}
        .provider-details {{ margin-top: 15px; }}
        .provider-details dt {{ font-weight: bold; margin-top: 10px; }}
        .provider-details dd {{ margin-left: 20px; color: #666; }}
        .refresh-btn {{ background: #007cba; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #005a87; }}
    </style>
</head>
<body>
    {self._get_page_header('🤖 AI Configuration', 'Manage local and external AI providers', 'ai-config')}

    <div class="card">
        <h2>AI Provider Configuration</h2>
        <p style="color: #666; margin-bottom: 20px;">Configure local and external AI providers for message summarization and sentiment analysis.</p>

        <button class="refresh-btn" onclick="refreshStatus()">🔄 Refresh Status</button>

        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007cba;">
            <h3 style="margin-top: 0; color: #007cba;">🏠 Ollama (Local AI - Recommended)</h3>
            <p style="color: #666; margin-bottom: 15px;">Run AI models locally for privacy and faster responses. No internet required.</p>

            <div class="form-group">
                <label style="font-weight: bold;">Server URL:</label>
                <input type="text" id="ollama-host" placeholder="http://192.168.10.160:11434" style="width: 350px; margin-top: 5px;">
                <button onclick="testOllama()" style="margin-left: 10px; padding: 8px 15px;">Test Connection</button>
            </div>

            <div class="form-group">
                <label style="font-weight: bold;">AI Model:</label>
                <select id="ollama-model" style="width: 250px; margin-top: 5px;">
                    <option value="">Select a model...</option>
                </select>
                <small style="display: block; color: #666; margin-top: 5px;">Available models will load after entering a valid server URL</small>
            </div>

            <div class="form-group">
                <label style="font-weight: bold;">
                    <input type="checkbox" id="ollama-enabled" style="margin-right: 8px;">
                    Enable Ollama Provider
                </label>
            </div>
        </div>

        <div style="margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #ffc107;">
            <h3 style="margin-top: 0; color: #856404;">🌐 Gemini (External AI)</h3>
            <p style="color: #666; margin-bottom: 15px;">Use Google's Gemini AI service. Requires internet connection and API key setup.</p>

            <div class="form-group">
                <label style="font-weight: bold;">CLI Command Path:</label>
                <input type="text" id="gemini-path" value="gemini" style="width: 250px; margin-top: 5px;">
                <small style="display: block; color: #666; margin-top: 5px;">Path to the gemini CLI command (usually just "gemini")</small>
            </div>

            <div class="form-group">
                <label style="font-weight: bold;">
                    <input type="checkbox" id="gemini-enabled" style="margin-right: 8px;">
                    Enable Gemini Provider
                </label>
            </div>
        </div>

        <div style="margin-top: 30px;">
            <button class="refresh-btn" onclick="saveConfiguration()" style="background: #28a745; padding: 12px 25px; font-size: 16px;">💾 Save Configuration</button>
            <button class="refresh-btn" onclick="preloadModel()" style="background: #17a2b8; padding: 12px 25px; font-size: 16px; margin-left: 10px;">🚀 Preload Selected Model</button>
            <button class="refresh-btn" onclick="refreshStatus()" style="background: #6c757d; padding: 12px 25px; font-size: 16px; margin-left: 10px;">🔄 Refresh Status</button>
        </div>

        <div id="config-message" style="margin-top: 15px;"></div>
    </div>

    <div class="card">
        <h2>Provider Status</h2>
        <div id="providers-container">
            <div class="loading" style="text-align: center; padding: 40px; color: #666;">
                Loading AI provider status...
            </div>
        </div>
    </div>

</div>

<script>

    let currentConfig = {{}};

    async function refreshStatus() {{
        const container = document.getElementById('providers-container');
        container.innerHTML = '<div class="loading" style="text-align: center; padding: 40px; color: #666;">Loading AI provider status...</div>';

        try {{
            const response = await fetch('/api/ai-status');
            const data = await response.json();
            displayProviders(data);
            loadConfiguration(data.configuration);
        }} catch (error) {{
            container.innerHTML = `<div class="error">Error loading AI status: ${{error.message}}</div>`;
        }}
    }}

    function loadConfiguration(config) {{
        if (!config) return;
        currentConfig = config;

        // Load Ollama configuration
        if (config.ollama) {{
            document.getElementById('ollama-host').value = config.ollama.host || '';
            document.getElementById('ollama-enabled').checked = config.ollama.enabled === 'true';

            // Load models if host is configured
            if (config.ollama.host) {{
                loadOllamaModels(config.ollama.host, config.ollama.model);
            }}
        }}

        // Load Gemini configuration
        if (config.gemini) {{
            document.getElementById('gemini-path').value = config.gemini.path || 'gemini';
            document.getElementById('gemini-enabled').checked = config.gemini.enabled === 'true';
        }}
    }}

    async function loadOllamaModels(host, selectedModel) {{
        const select = document.getElementById('ollama-model');

        try {{
            // Use our proxy endpoint to avoid CORS issues
            const response = await fetch(`/api/ollama-models?host=${{encodeURIComponent(host)}}`);
            if (response.ok) {{
                const data = await response.json();
                const models = data.models || [];

                select.innerHTML = models.length > 0
                    ? '<option value="">Select a model...</option>'
                    : '<option value="">No models available</option>';

                models.forEach(model => {{
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    if (model === selectedModel) {{
                        option.selected = true;
                    }}
                    select.appendChild(option);
                }});
            }} else {{
                select.innerHTML = '<option value="">Failed to load models</option>';
            }}
        }} catch (error) {{
            select.innerHTML = '<option value="">Error loading models</option>';
        }}
    }}

    async function testOllama() {{
        const host = document.getElementById('ollama-host').value;
        if (!host) {{
            alert('Please enter Ollama host URL');
            return;
        }}

        try {{
            // Use our proxy endpoint to test connection
            const response = await fetch(`/api/ollama-models?host=${{encodeURIComponent(host)}}`);
            if (response.ok) {{
                const data = await response.json();
                if (data.status === 'success') {{
                    loadOllamaModels(host);
                    alert(`✅ Connected successfully! Found ${{data.models?.length || 0}} models.`);
                }} else {{
                    alert(`❌ Failed to connect: ${{data.error}}`);
                }}
            }} else {{
                alert(`❌ Failed to connect: HTTP ${{response.status}}`);
            }}
        }} catch (error) {{
            alert(`❌ Connection failed: ${{error.message}}`);
        }}
    }}

    async function saveConfiguration() {{
        const config = {{
            ollama: {{
                host: document.getElementById('ollama-host').value,
                model: document.getElementById('ollama-model').value,
                enabled: document.getElementById('ollama-enabled').checked
            }},
            gemini: {{
                path: document.getElementById('gemini-path').value,
                enabled: document.getElementById('gemini-enabled').checked
            }}
        }};

        const messageDiv = document.getElementById('config-message');
        messageDiv.innerHTML = '<div style="color: blue;">Saving configuration...</div>';

        try {{
            const response = await fetch('/api/ai-config', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify(config)
            }});

            const data = await response.json();

            if (data.status === 'success') {{
                messageDiv.innerHTML = '<div style="color: green;">✅ Configuration saved successfully!</div>';
                setTimeout(() => refreshStatus(), 1000);
            }} else {{
                messageDiv.innerHTML = `<div style="color: red;">❌ Error: ${{data.error}}</div>`;
            }}
        }} catch (error) {{
            messageDiv.innerHTML = `<div style="color: red;">❌ Error: ${{error.message}}</div>`;
        }}
    }}

    function displayProviders(data) {{
        const container = document.getElementById('providers-container');

        if (!data.providers || data.providers.length === 0) {{
            container.innerHTML = '<div class="error">No AI providers configured</div>';
            return;
        }}

        let html = '';

        if (data.active_provider) {{
            html += `<div style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
                <strong>✅ Active Provider:</strong> ${{data.active_provider}}
            </div>`;
        }} else {{
            html += `<div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin-bottom: 20px;">
                <strong>❌ No AI providers available</strong><br>
                Please install and configure Ollama or Gemini CLI below.
            </div>`;
        }}

        data.providers.forEach(provider => {{
            const isAvailable = provider.available;
            const statusClass = isAvailable ? 'provider-available' : 'provider-unavailable';
            const badgeClass = isAvailable ? 'status-available' : 'status-unavailable';
            const statusText = isAvailable ? 'Available' : 'Unavailable';

            html += `
                <div class="provider-card ${{statusClass}}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">${{provider.name}}</h3>
                        <span class="status-badge ${{badgeClass}}">${{statusText}}</span>
                    </div>
                    <dl class="provider-details">
                        <dt>Type:</dt>
                        <dd>${{provider.type === 'local' ? '🏠 Local' : '🌐 External'}}</dd>
                        ${{provider.host ? `<dt>Host:</dt><dd>${{provider.host}}</dd>` : ''}}
                        ${{provider.model ? `<dt>Current Model:</dt><dd>${{provider.model}} ${{provider.current_model_loaded ? '✅' : '⏸️'}}</dd>` : ''}}
                        ${{provider.command ? `<dt>Command:</dt><dd>${{provider.command}}</dd>` : ''}}

                        ${{provider.type === 'local' && provider.available ? `
                            <dt>Memory Usage:</dt>
                            <dd>📊 ${{provider.total_vram_usage_gb || 0}} GB VRAM (${{provider.loaded_models_count || 0}} models loaded)</dd>

                            ${{provider.loaded_models && provider.loaded_models.length > 0 ? `
                                <dt>Loaded Models:</dt>
                                <dd>
                                    ${{provider.loaded_models.map(model => `
                                        <div style="background: #f8f9fa; padding: 8px; margin: 4px 0; border-radius: 3px; border-left: 3px solid ${{model.is_current_model ? '#28a745' : '#6c757d'}};">
                                            <strong>${{model.name}}</strong> ${{model.is_current_model ? '🎯' : ''}}
                                            <br><small>📏 ${{model.parameter_size}} | 💾 ${{model.size_vram_gb}}GB VRAM | 🔧 ${{model.quantization || 'N/A'}} | 📝 ${{(model.context_length / 1000).toFixed(0)}}K context</small>
                                        </div>
                                    `).join('')}}
                                </dd>
                            ` : ''}}

                            <dt>Available Models:</dt>
                            <dd>📦 ${{provider.total_available_models || 0}} models (${{provider.total_models_size_gb || 0}} GB total)</dd>
                        ` : ''}}

                        ${{provider.available_models && provider.type !== 'local' ? `<dt>Available Models:</dt><dd>${{provider.available_models.join(', ') || 'None'}}</dd>` : ''}}
                    </dl>
                </div>
            `;
        }});

        container.innerHTML = html;
    }}

    async function preloadModel() {{
        const model = document.getElementById('ollama-model').value;
        if (!model) {{
            document.getElementById('config-message').innerHTML = '<div style="color: red;">Please select an Ollama model first</div>';
            return;
        }}

        const messageDiv = document.getElementById('config-message');
        messageDiv.innerHTML = '<div style="color: blue;">🚀 Loading model... This may take several minutes for large models.</div>';

        try {{
            const response = await fetch(`/api/ollama-preload?model=${{encodeURIComponent(model)}}`);
            const data = await response.json();

            if (data.status === 'success') {{
                messageDiv.innerHTML = `<div style="color: green;">✅ Model ${{model}} loaded successfully!</div>`;
            }} else {{
                messageDiv.innerHTML = `<div style="color: red;">❌ Failed to load model: ${{data.error}}</div>`;
            }}
        }} catch (error) {{
            messageDiv.innerHTML = `<div style="color: red;">❌ Error loading model: ${{error.message}}</div>`;
        }}
    }}

    // Load status on page load
    document.addEventListener('DOMContentLoaded', refreshStatus);
</script>
</body>
</html>"""

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())

        except Exception as e:
            self.logger.error(f"Error serving AI config page: {e}")
            self._send_error(500, "Internal server error")

    def _api_ai_status(self, query):
        """API endpoint for AI provider status."""
        try:
            from services.ai_provider import get_ai_status
            status = get_ai_status()
            self._send_json_response(status)
        except Exception as e:
            self.logger.error(f"Error getting AI status: {e}")
            self._send_json_response({
                'error': str(e),
                'providers': [],
                'active_provider': None
            })

    def _api_ai_config(self, query):
        """API endpoint for getting AI configuration."""
        try:
            from services.ai_provider import get_ai_status
            status = get_ai_status()
            self._send_json_response({
                'status': 'success',
                'configuration': status.get('configuration', {}),
                'providers': status.get('providers', [])
            })
        except Exception as e:
            self.logger.error(f"Error getting AI config: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_save_ai_config(self, post_data):
        """API endpoint for saving AI configuration."""
        try:
            import json
            data = json.loads(post_data) if post_data else {}

            from services.ai_provider import save_ai_configuration

            # Extract configuration from request
            ollama_config = data.get('ollama', {})
            gemini_config = data.get('gemini', {})

            success = save_ai_configuration(
                ollama_host=ollama_config.get('host'),
                ollama_model=ollama_config.get('model'),
                ollama_enabled=ollama_config.get('enabled', True),
                gemini_path=gemini_config.get('path', 'gemini'),
                gemini_enabled=gemini_config.get('enabled', True)
            )

            if success:
                # Get updated status
                from services.ai_provider import get_ai_status
                status = get_ai_status()
                self._send_json_response({
                    'status': 'success',
                    'message': 'AI configuration saved successfully',
                    'providers': status.get('providers', []),
                    'active_provider': status.get('active_provider')
                })
            else:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Failed to save AI configuration'
                })

        except Exception as e:
            self.logger.error(f"Error saving AI config: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_ollama_models(self, query):
        """API endpoint to fetch Ollama models through our server (avoids CORS)."""
        try:
            # Get the host from query params or use configured one
            host = None
            if query and 'host' in query:
                host = query['host'][0]
            else:
                # Get from database configuration
                host = self.db.get_config('ai.ollama.host')

            if not host:
                self._send_json_response({
                    'status': 'error',
                    'error': 'No Ollama host configured',
                    'models': []
                })
                return

            # Fetch models from Ollama
            import requests
            try:
                response = requests.get(f"{host}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self._send_json_response({
                        'status': 'success',
                        'models': [model['name'] for model in data.get('models', [])]
                    })
                else:
                    self._send_json_response({
                        'status': 'error',
                        'error': f'Failed to fetch models: HTTP {response.status_code}',
                        'models': []
                    })
            except Exception as e:
                self._send_json_response({
                    'status': 'error',
                    'error': str(e),
                    'models': []
                })

        except Exception as e:
            self.logger.error(f"Error fetching Ollama models: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e),
                'models': []
            })

    def _api_ollama_preload(self, query):
        """API endpoint to preload an Ollama model."""
        try:
            model = query.get('model', [None])[0]
            if not model:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Model parameter required'
                })
                return

            # Get AI provider manager
            from services.ai_provider import get_ai_manager
            manager = get_ai_manager()

            # Find Ollama provider
            ollama_provider = None
            for provider in manager.providers:
                if hasattr(provider, 'preload_model'):
                    ollama_provider = provider
                    break

            if not ollama_provider:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Ollama provider not available'
                })
                return

            # Update the provider's model and preload it
            ollama_provider.model = model
            result = ollama_provider.preload_model(timeout=120)  # 2 minute timeout for large models

            self._send_json_response({
                'status': 'success' if result['success'] else 'error',
                **result
            })

        except Exception as e:
            self.logger.error(f"Error preloading Ollama model: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e)
            })

    def _api_ollama_status(self, query):
        """API endpoint to get currently loaded Ollama models."""
        try:
            # Get AI provider manager
            from services.ai_provider import get_ai_manager
            manager = get_ai_manager()

            # Find Ollama provider
            ollama_provider = None
            for provider in manager.providers:
                if hasattr(provider, 'get_loaded_models'):
                    ollama_provider = provider
                    break

            if not ollama_provider:
                self._send_json_response({
                    'status': 'error',
                    'error': 'Ollama provider not available',
                    'loaded_models': []
                })
                return

            loaded_models = ollama_provider.get_loaded_models()

            self._send_json_response({
                'status': 'success',
                'loaded_models': loaded_models,
                'count': len(loaded_models)
            })

        except Exception as e:
            self.logger.error(f"Error getting Ollama status: {e}")
            self._send_json_response({
                'status': 'error',
                'error': str(e),
                'loaded_models': []
            })

    def _serve_markdown_js(self):
        """Serve the external markdown JavaScript file."""
        try:
            js_content = """
// Simple markdown to HTML converter
function convertMarkdownToHtml(markdown) {
    let html = markdown;

    // Headers
    html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*)$/gm, '<h1>$1</h1>');

    // Tables - process markdown tables line by line
    let lines = html.split('\\n');
    let result = [];
    let i = 0;

    while (i < lines.length) {
        let line = lines[i];

        // Check if this looks like a table row
        if (line.trim().startsWith('|') && line.trim().endsWith('|') && line.includes('|')) {
            // Found potential table start
            let tableLines = [];
            let j = i;

            // Collect all consecutive table-like lines
            while (j < lines.length) {
                let currentLine = lines[j].trim();
                if (currentLine.startsWith('|') && currentLine.endsWith('|')) {
                    tableLines.push(currentLine);
                    j++;
                } else {
                    break;
                }
            }

            // If we have at least 2 lines (header + separator minimum), process as table
            if (tableLines.length >= 2) {
                let tableHtml = '<table style="border-collapse: collapse; margin: 15px 0; width: 100%;">';
                let headerProcessed = false;

                for (let k = 0; k < tableLines.length; k++) {
                    let tableLine = tableLines[k];

                    // Skip separator rows (contain dashes)
                    if (tableLine.includes('-')) {
                        continue;
                    }

                    // Extract cells
                    let cells = tableLine.slice(1, -1).split('|').map(cell => cell.trim());

                    // Determine if this is header row
                    let isHeader = !headerProcessed;
                    if (!headerProcessed) headerProcessed = true;

                    let tag = isHeader ? 'th' : 'td';
                    let style = isHeader ?
                        'border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;' :
                        'border: 1px solid #ddd; padding: 8px;';

                    tableHtml += '<tr>';
                    cells.forEach(cell => {
                        tableHtml += '<' + tag + ' style="' + style + '">' + cell + '</' + tag + '>';
                    });
                    tableHtml += '</tr>';
                }

                tableHtml += '</table>';
                result.push(tableHtml);
                i = j; // Skip past the table
            } else {
                // Not a table, just add the line
                result.push(line);
                i++;
            }
        } else {
            // Regular line
            result.push(line);
            i++;
        }
    }

    html = result.join('\\n');

    // Bold text (double asterisks)
    let parts = html.split('**');
    html = '';
    for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
            html += '<strong>' + parts[i] + '</strong>';
        } else {
            html += parts[i];
        }
    }

    // Italic text (single asterisks, but not part of bold)
    html = html.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');

    // Lists
    html = html.replace(/^[\\*\\-] (.*)$/gm, '<li>$1</li>');
    html = html.replace(/^\\d+\\. (.*)$/gm, '<li>$1</li>');

    // Wrap consecutive list items in ul tags
    html = html.replace(/(<li>.*?<\\/li>)(\\s*<li>.*?<\\/li>)*/gs, '<ul>$&</ul>');

    // Line breaks and paragraphs
    html = html.replace(/\\n\\n/g, '</p><p>');
    html = html.replace(/\\n/g, '<br>');

    // Wrap in paragraphs if not already wrapped
    if (!html.startsWith('<h') && !html.startsWith('<ul>') && !html.startsWith('<table>')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}
"""

            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript')
            self.send_header('Cache-Control', 'public, max-age=3600')  # Cache for 1 hour
            self.end_headers()
            self.wfile.write(js_content.encode())

        except Exception as e:
            self.logger.error(f"Error serving markdown.js: {e}")
            self._send_error(500, "Internal server error")



class WebServer:
    """Web server for UUID-based Signal bot."""

    def __init__(self, db_manager: DatabaseManager, setup_service: SetupService,
                 port: int = 8084, logger: Optional[logging.Logger] = None):
        """
        Initialize web server.

        Args:
            db_manager: Database manager instance
            setup_service: Setup service instance
            port: Port to listen on
            logger: Optional logger instance
        """
        self.db = db_manager
        self.setup_service = setup_service
        self.port = port
        self.logger = logger or logging.getLogger(__name__)
        self.server = None
        self.server_thread = None
        self.shutdown_event = threading.Event()

    def start(self) -> str:
        """Start the web server."""
        def handler(*args, **kwargs):
            return WebHandler(*args, db_manager=self.db, setup_service=self.setup_service, **kwargs)

        self.server = HTTPServer(('0.0.0.0', self.port), handler)

        def run_server():
            self.logger.info("Web server starting on port %d", self.port)
            try:
                while not self.shutdown_event.is_set():
                    self.server.handle_request()
            except Exception as e:
                if not self.shutdown_event.is_set():
                    self.logger.error("Web server error: %s", e)
            finally:
                self.logger.debug("Web server thread stopped")

        # Set server timeout for responsive shutdown
        self.server.timeout = 1.0

        self.server_thread = threading.Thread(
            target=run_server,
            name=f"WebServer-{self.port}",
            daemon=True
        )
        self.server_thread.start()

        url = f"http://localhost:{self.port}"
        self.logger.info("Web interface available at: %s", url)
        return url

    def stop(self):
        """Stop the web server gracefully."""
        if self.server:
            try:
                self.logger.debug("Stopping web server...")
                self.shutdown_event.set()

                # Wait for server thread to complete
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=5.0)
                    if self.server_thread.is_alive():
                        self.logger.warning("Web server thread did not stop gracefully")

                self.server.server_close()
                self.logger.info("Web server stopped")
            except Exception as e:
                self.logger.error("Error stopping web server: %s", e)