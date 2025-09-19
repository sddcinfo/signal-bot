"""
Modular Web Interface for UUID-based Signal Bot

Demonstrates the new modular architecture with shared templates and individual page modules.
This serves as a proof-of-concept showing how to refactor the monolithic server.py.
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

# Import modular page components
from .pages.dashboard import DashboardPage
from .pages.users import UsersPage
from .pages.groups import GroupsPage
from .pages.messages import MessagesPage
from .pages.settings import SettingsPage
from .pages.setup import SetupPage
from .pages.ai_config import AIConfigPage


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


class ModularWebServer:
    """Modular web server that demonstrates the new architecture."""

    def __init__(self, db: DatabaseManager, setup_service: SetupService, ai_provider=None,
                 port: int = 8084, host: str = '0.0.0.0'):
        self.db = db
        self.setup_service = setup_service
        self.ai_provider = ai_provider
        self.port = port
        self.host = host
        self.server = None

        # Initialize page instances
        self.pages = {
            'dashboard': DashboardPage(db, setup_service, ai_provider),
            'users': UsersPage(db, setup_service, ai_provider),
            'groups': GroupsPage(db, setup_service, ai_provider),
            'messages': MessagesPage(db, setup_service, ai_provider),
            'settings': SettingsPage(db, setup_service, ai_provider),
            'setup': SetupPage(db, setup_service, ai_provider),
            'ai-config': AIConfigPage(db, setup_service, ai_provider),
        }

        # For backward compatibility, keep some old methods temporarily
        self.sentiment_analyzer = SentimentAnalyzer(db) if ai_provider else None
        self.summarizer = MessageSummarizer(db) if ai_provider else None

    def start(self):
        """Start the web server in a separate thread."""
        handler = self._create_handler()
        self.server = HTTPServer((self.host, self.port), handler)

        def run_server():
            logging.info(f"Web server starting on port {self.port}")
            try:
                self.server.serve_forever()
            except Exception as e:
                logging.error(f"Web server error: {e}")

        server_thread = threading.Thread(target=run_server, daemon=True, name="WebServer")
        server_thread.start()

        return f"http://{self.host}:{self.port}"

    def stop(self):
        """Stop the web server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _create_handler(self):
        """Create HTTP request handler with access to server instance."""
        web_server = self

        class RequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress default logging or customize as needed
                pass

            def do_GET(self):
                """Handle GET requests."""
                try:
                    parsed_url = urlparse(self.path)
                    path = parsed_url.path
                    query = parse_qs(parsed_url.query)

                    # Route to appropriate handler - all pages now use modular system
                    if path == '/':
                        response = web_server.pages['dashboard'].render(query)
                        self._send_html_response(response)

                    elif path == '/users':
                        response = web_server.pages['users'].render(query)
                        self._send_html_response(response)

                    elif path == '/groups':
                        response = web_server.pages['groups'].render(query)
                        self._send_html_response(response)

                    elif path == '/messages':
                        response = web_server.pages['messages'].render(query)
                        self._send_html_response(response)

                    elif path == '/settings':
                        response = web_server.pages['settings'].render(query)
                        self._send_html_response(response)

                    elif path == '/setup':
                        response = web_server.pages['setup'].render(query)
                        self._send_html_response(response)

                    elif path == '/ai-config':
                        response = web_server.pages['ai-config'].render(query)
                        self._send_html_response(response)


                    # API endpoints
                    elif path.startswith('/api/'):
                        self._handle_api_request(path, query)

                    # Attachment serving
                    elif path.startswith('/attachment/'):
                        self._serve_attachment(path)

                    else:
                        self._send_error_response(404, "Page not found")

                except Exception as e:
                    logging.error(f"Request handling error: {e}")
                    self._send_error_response(500, "Internal server error")

            def do_POST(self):
                """Handle POST requests."""
                try:
                    parsed_url = urlparse(self.path)
                    path = parsed_url.path

                    # Read POST data
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length).decode('utf-8')

                    if path.startswith('/api/'):
                        self._handle_api_post_request(path, post_data)
                    else:
                        self._send_error_response(404, "Endpoint not found")

                except Exception as e:
                    logging.error(f"POST request handling error: {e}")
                    self._send_error_response(500, "Internal server error")

            def _send_html_response(self, html: str):
                """Send HTML response."""
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _send_json_response(self, data: dict):
                """Send JSON response."""
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))

            def _send_error_response(self, code: int, message: str):
                """Send error response."""
                self.send_response(code)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = f"""
                <!DOCTYPE html>
                <html><head><title>Error {code}</title></head>
                <body><h1>Error {code}</h1><p>{message}</p></body></html>
                """
                self.wfile.write(error_html.encode('utf-8'))

            def _handle_api_request(self, path: str, query: Dict[str, Any]):
                """Handle API GET requests."""
                if path == '/api/user-reactions':
                    user_id = query.get('user_id', [None])[0]
                    if user_id:
                        reactions = web_server.db.get_user_reactions(user_id)
                        data = {
                            'emojis': reactions.emojis if reactions else [],
                            'mode': reactions.reaction_mode if reactions else 'random'
                        }
                        self._send_json_response(data)
                    else:
                        self._send_error_response(400, "Missing user_id parameter")
                elif path == '/api/setup/run':
                    result = web_server.setup_service.run_initial_setup()
                    self._send_json_response(result)
                elif path == '/api/ai-status':
                    self._handle_ai_status()
                elif path == '/api/ai-config':
                    self._handle_ai_config()
                elif path.startswith('/api/ollama-models'):
                    self._handle_ollama_models(query)
                elif path.startswith('/api/ollama-preload'):
                    self._handle_ollama_preload(query)
                elif path.startswith('/api/sentiment-cached'):
                    self._handle_sentiment_cached(query)
                elif path.startswith('/api/sentiment-preview'):
                    self._handle_sentiment_preview(query)
                elif path.startswith('/api/sentiment'):
                    self._handle_sentiment_analysis(query)
                elif path.startswith('/api/summary'):
                    self._handle_summary(query)
                else:
                    self._send_error_response(404, "API endpoint not found")

            def _handle_api_post_request(self, path: str, post_data: str):
                """Handle API POST requests."""
                try:
                    data = json.loads(post_data) if post_data else {}

                    if path == '/api/save-user-reactions':
                        user_id = data.get('user_id')
                        emojis = data.get('emojis', [])
                        mode = data.get('mode', 'random')

                        if user_id:
                            web_server.db.set_user_reactions(user_id, emojis, mode)
                            self._send_json_response({'success': True})
                        else:
                            self._send_error_response(400, "Missing user_id")

                    elif path == '/api/remove-user-reactions':
                        user_id = data.get('user_id')
                        if user_id:
                            web_server.db.remove_user_reactions(user_id)
                            self._send_json_response({'success': True})
                        else:
                            self._send_error_response(400, "Missing user_id")

                    elif path == '/api/setup/sync':
                        # Get setup status to find bot phone
                        status = web_server.setup_service.get_setup_status()
                        bot_phone = status.get('bot_phone_number')

                        if not bot_phone:
                            self._send_json_response({
                                'success': False,
                                'message': 'Bot not configured'
                            })
                            return

                        # Use the enhanced sync_groups_to_database method with JSON output
                        synced_count = web_server.setup_service.sync_groups_to_database()

                        self._send_json_response({
                            'success': True,
                            'synced_count': synced_count
                        })
                    elif path == '/api/setup/sync-users':
                        # Use the new sync_users_to_database method that includes friendly name logic
                        synced_count = web_server.setup_service.sync_users_to_database()

                        # Get updated user counts
                        user_stats = web_server.db.get_user_statistics()

                        self._send_json_response({
                            'success': synced_count > 0,
                            'synced_count': synced_count,
                            'total_users': user_stats['total'],
                            'configured_users': user_stats['configured'],
                            'discovered_users': user_stats['discovered']
                        })
                    elif path == '/api/setup/clean-import':
                        # Use the new clean_import method that combines users and groups
                        result = web_server.setup_service.clean_import()
                        self._send_json_response(result)

                    elif path == '/api/groups/monitor':
                        group_id = data.get('group_id')
                        is_monitored = data.get('is_monitored', False)

                        if group_id:
                            web_server.db.set_group_monitoring(group_id, is_monitored)
                            self._send_json_response({'success': True})
                        else:
                            self._send_error_response(400, "Missing group_id")

                    elif path == '/api/ai-config':
                        self._handle_save_ai_config(post_data)

                    else:
                        self._send_error_response(404, "API endpoint not found")

                except json.JSONDecodeError:
                    self._send_error_response(400, "Invalid JSON data")

            def _serve_attachment(self, path: str):
                """Serve attachment files from the database."""
                try:
                    # Extract attachment ID from path /attachment/{attachment_id}
                    attachment_id = path.split('/attachment/')[-1]
                    if not attachment_id:
                        self._send_error_response(404, "Attachment not found")
                        return

                    # Get attachment data from database using DatabaseManager's context manager
                    with web_server.db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT file_data, content_type, filename
                            FROM attachments
                            WHERE attachment_id = ?
                        """, (attachment_id,))
                        attachment = cursor.fetchone()

                    if not attachment:
                        self._send_error_response(404, "Attachment not found")
                        return

                    file_data = attachment['file_data']
                    if not file_data:
                        logging.warning(f"Attachment {attachment_id} has no file data stored")
                        self._send_error_response(404, "Attachment data not found")
                        return

                    # Determine content type
                    content_type = attachment['content_type'] if attachment['content_type'] else 'application/octet-stream'

                    # Send headers
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(file_data)))

                    if attachment['filename']:
                        self.send_header('Content-Disposition', f'inline; filename="{attachment["filename"]}"')

                    self.end_headers()

                    # Send file data
                    self.wfile.write(file_data)

                    logging.debug(f"Served attachment {attachment_id} ({len(file_data)} bytes) from database")

                except Exception as e:
                    logging.error(f"Error serving attachment {path}: {e}")
                    self._send_error_response(500, "Error serving attachment")

            def _handle_ai_status(self):
                """Handle AI status API request."""
                try:
                    from services.ai_provider import get_ai_status
                    status = get_ai_status()
                    self._send_json_response(status)
                except Exception as e:
                    logging.error(f"Error getting AI status: {e}")
                    self._send_json_response({
                        'error': str(e),
                        'providers': [],
                        'active_provider': None
                    })

            def _handle_ai_config(self):
                """Handle AI config GET API request."""
                try:
                    from services.ai_provider import get_ai_status
                    status = get_ai_status()
                    self._send_json_response({
                        'status': 'success',
                        'configuration': status.get('configuration', {}),
                        'providers': status.get('providers', [])
                    })
                except Exception as e:
                    logging.error(f"Error getting AI config: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_save_ai_config(self, post_data: str):
                """Handle AI config save API request."""
                try:
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
                    logging.error(f"Error saving AI config: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_ollama_models(self, query: Dict[str, Any]):
                """Handle Ollama models API request."""
                try:
                    # Get the host from query params
                    host = query.get('host', [None])[0] if query else None

                    if not host:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'No Ollama host provided',
                            'models': []
                        })
                        return

                    # Fetch models from Ollama
                    import requests
                    try:
                        response = requests.get(f"{host}/api/tags", timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            models = [model['name'] for model in data.get('models', [])]
                            self._send_json_response({
                                'status': 'success',
                                'models': models
                            })
                        else:
                            self._send_json_response({
                                'status': 'error',
                                'error': f'Ollama server returned status {response.status_code}',
                                'models': []
                            })
                    except requests.RequestException as e:
                        self._send_json_response({
                            'status': 'error',
                            'error': f'Connection failed: {str(e)}',
                            'models': []
                        })

                except Exception as e:
                    logging.error(f"Error fetching Ollama models: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e),
                        'models': []
                    })

            def _handle_ollama_preload(self, query: Dict[str, Any]):
                """Handle Ollama preload API request."""
                try:
                    host = query.get('host', [None])[0] if query else None
                    model = query.get('model', [None])[0] if query else None

                    if not host or not model:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Missing host or model parameter'
                        })
                        return

                    # Preload model via Ollama API
                    import requests
                    try:
                        response = requests.post(f"{host}/api/generate",
                                               json={"model": model, "prompt": "test", "stream": False},
                                               timeout=30)
                        if response.status_code == 200:
                            self._send_json_response({
                                'status': 'success',
                                'message': 'Model preloaded successfully'
                            })
                        else:
                            self._send_json_response({
                                'status': 'error',
                                'error': f'Preload failed with status {response.status_code}'
                            })
                    except requests.RequestException as e:
                        self._send_json_response({
                            'status': 'error',
                            'error': f'Preload failed: {str(e)}'
                        })

                except Exception as e:
                    logging.error(f"Error preloading Ollama model: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_sentiment_preview(self, query: Dict[str, Any]):
                """Get message count preview for sentiment analysis."""
                try:
                    group_id = query.get('group_id', [None])[0]
                    if not group_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Group ID is required'
                        })
                        return

                    # Get user's timezone and date using existing method
                    user_timezone = query.get('timezone', [None])[0] or 'Asia/Tokyo'  # Default timezone
                    user_date_str = query.get('date', [None])[0]

                    if user_date_str:
                        from datetime import datetime
                        user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                    else:
                        from datetime import date
                        user_date = date.today()

                    # Get group info
                    group = web_server.db.get_group(group_id)
                    if not group:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Group not found'
                        })
                        return

                    # Get message count for the date
                    if web_server.sentiment_analyzer:
                        messages = web_server.sentiment_analyzer.get_daily_messages(group_id, user_date, user_timezone)

                        # Apply filtering logic
                        filtered_messages = []
                        for msg in messages:
                            text = msg.get('text', '').strip()
                            sender = msg.get('sender', '').strip()

                            if not text or not sender or len(text) < 3:
                                continue
                            if sender.lower() in ['unknown', 'system']:
                                continue
                            if text.lower() in ['ok', 'yes', 'no', 'k', 'thanks', 'thx']:
                                continue

                            filtered_messages.append(msg)

                        # Check for cached sentiment analysis
                        cached_result = web_server.db.get_sentiment_analysis(group_id, user_date)
                        cached_info = None
                        if cached_result:
                            # Get metadata about the cached analysis
                            with web_server.db._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT created_at, message_count FROM sentiment_analysis
                                    WHERE group_id = ? AND analysis_date = ?
                                """, (group_id, user_date.strftime('%Y-%m-%d')))
                                row = cursor.fetchone()

                                if row:
                                    from datetime import datetime
                                    cached_info = {
                                        'has_cached': True,
                                        'analyzed_at': row['created_at'],
                                        'cached_message_count': row['message_count']
                                    }

                        response_data = {
                            'status': 'success',
                            'group_name': group.group_name or 'Unnamed Group',
                            'date': user_date.strftime('%Y-%m-%d'),
                            'timezone': user_timezone or 'UTC',
                            'total_messages': len(messages),
                            'analyzable_messages': len(filtered_messages),
                            'filtered_out': len(messages) - len(filtered_messages)
                        }

                        # Add cached analysis info if available
                        if cached_info:
                            response_data.update(cached_info)
                        else:
                            response_data['has_cached'] = False

                        self._send_json_response(response_data)
                    else:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Sentiment analyzer not available'
                        })

                except Exception as e:
                    logging.error(f"Error getting sentiment preview: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_sentiment_cached(self, query: Dict[str, Any]):
                """Get cached sentiment analysis results."""
                try:
                    group_id = query.get('group_id', [None])[0]
                    if not group_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Group ID is required'
                        })
                        return

                    # Get user's timezone and date using existing method
                    user_timezone = query.get('timezone', [None])[0] or 'Asia/Tokyo'  # Default timezone
                    user_date_str = query.get('date', [None])[0]
                    if user_date_str:
                        from datetime import datetime
                        user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                    else:
                        from datetime import date
                        user_date = date.today()

                    # Try to get cached result
                    cached_result = web_server.db.get_sentiment_analysis(group_id, user_date)

                    if cached_result:
                        # Get additional metadata from database
                        with web_server.db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT created_at, message_count FROM sentiment_analysis
                                WHERE group_id = ? AND analysis_date = ?
                            """, (group_id, user_date.strftime('%Y-%m-%d')))
                            row = cursor.fetchone()

                        # Split header from analysis in cached results
                        # Cached results have format: "Header info...\n\n<actual analysis>"
                        if '\n\n' in cached_result:
                            header_part, analysis_part = cached_result.split('\n\n', 1)

                            # Parse header to extract metadata for consistent formatting
                            # Extract group name, date, timezone, etc. from header lines
                            header_lines = header_part.split('\n')
                            metadata = {}
                            for line in header_lines:
                                if 'Messages analyzed:' in line:
                                    metadata['message_count'] = line.split(':')[1].strip()
                                elif 'Time range:' in line:
                                    metadata['time_range'] = line.split(':', 1)[1].strip()
                                elif 'Timezone:' in line:
                                    metadata['timezone'] = line.split(':', 1)[1].strip()
                                elif 'Provider:' in line:
                                    provider_info = line.split(':', 1)[1].strip()
                                    metadata['provider_info'] = provider_info
                                    metadata['is_local'] = 'Local' in provider_info

                            # Create formatted metadata HTML like new results
                            is_local = metadata.get('is_local', False)
                            privacy_class = 'privacy-local' if is_local else 'privacy-external'
                            privacy_icon = '🏠' if is_local else '☁️'
                            privacy_text = 'Local Processing' if is_local else 'External API'

                            metadata_html = f"""
                            <div class="analysis-metadata" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #007bff;">
                                <h4 style="margin: 0 0 10px 0; color: #495057;">Analysis Details</h4>
                                <p><strong>Messages:</strong> {metadata.get('message_count', 'unknown')}</p>
                                <p><strong>Time Range:</strong> {metadata.get('time_range', 'unknown')}</p>
                                <p><strong>Timezone:</strong> {metadata.get('timezone', 'unknown')}</p>
                                <p class="{privacy_class}"><strong>Privacy Mode:</strong> {privacy_icon} {privacy_text}</p>
                                <p><strong>Provider:</strong> {metadata.get('provider_info', 'unknown')}</p>
                            </div>
                            """

                            # Apply markdown formatting only to the analysis part
                            formatted_analysis = convert_markdown_to_html(analysis_part)
                            combined_result = metadata_html + formatted_analysis
                        else:
                            # Fallback for results without header separation
                            combined_result = convert_markdown_to_html(cached_result)

                        self._send_json_response({
                            'status': 'success',
                            'cached': True,
                            'result': {
                                'analysis': combined_result,
                                'analyzed_at': row['created_at'] if row else None,
                                'message_count': row['message_count'] if row else 0
                            }
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

            def _handle_sentiment_analysis(self, query: Dict[str, Any]):
                """Handle sentiment analysis requests."""
                try:
                    # Check if this is a status check
                    job_id = query.get('job_id', [None])[0]
                    if job_id:
                        return self._handle_sentiment_status(job_id)

                    group_id = query.get('group_id', [None])[0]
                    if not group_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'group_id parameter is required'
                        })
                        return

                    # Check if force refresh is requested
                    force_refresh = query.get('force', [False])[0] == 'true'

                    # Get timezone and date from client using existing method
                    user_timezone = query.get('timezone', [None])[0] or 'Asia/Tokyo'  # Default timezone
                    user_date_str = query.get('date', [None])[0]

                    # Parse user's date
                    if user_date_str:
                        try:
                            from datetime import datetime
                            user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            from datetime import date
                            user_date = date.today()
                    else:
                        from datetime import date
                        user_date = date.today()

                    # Create a unique job ID
                    job_id = str(uuid.uuid4())

                    # Get group info for name
                    group_info = web_server.db.get_group(group_id)
                    group_name = group_info.group_name if group_info else 'Unknown Group'

                    # Store job info in the server instance
                    if not hasattr(web_server, '_analysis_jobs'):
                        web_server._analysis_jobs = {}

                    web_server._analysis_jobs[job_id] = {
                        'status': 'running',
                        'group_id': group_id,
                        'group_name': group_name,
                        'started_at': time.time(),
                        'result': None,
                        'error': None,
                        'current_step': 'Starting analysis'
                    }

                    # Start analysis in background thread
                    def run_analysis():
                        try:
                            # Check if model is loaded for ollama provider
                            if web_server.sentiment_analyzer and hasattr(web_server.sentiment_analyzer, 'ai_provider'):
                                ai_provider = web_server.sentiment_analyzer.ai_provider
                                if hasattr(ai_provider, 'is_model_loaded') and hasattr(ai_provider, 'provider_name'):
                                    if ai_provider.provider_name == 'ollama':
                                        web_server._analysis_jobs[job_id]['current_step'] = 'Checking AI model status'
                                        import time
                                        time.sleep(0.5)  # Brief pause for status to be visible

                                        if not ai_provider.is_model_loaded():
                                            web_server._analysis_jobs[job_id]['current_step'] = 'Loading AI model - this may take a moment'
                                        else:
                                            web_server._analysis_jobs[job_id]['current_step'] = 'AI model ready - analyzing messages'

                            web_server._analysis_jobs[job_id]['current_step'] = 'Processing sentiment analysis'

                            if web_server.sentiment_analyzer:
                                analysis = web_server.sentiment_analyzer.analyze_group_daily_sentiment(
                                    group_id, group_name,
                                    target_date=user_date,
                                    force_refresh=force_refresh,
                                    user_timezone=user_timezone
                                )

                                if analysis:
                                    web_server._analysis_jobs[job_id]['status'] = 'completed'
                                    web_server._analysis_jobs[job_id]['result'] = analysis
                                else:
                                    web_server._analysis_jobs[job_id]['status'] = 'error'
                                    web_server._analysis_jobs[job_id]['error'] = 'Failed to generate sentiment analysis'
                            else:
                                web_server._analysis_jobs[job_id]['status'] = 'error'
                                web_server._analysis_jobs[job_id]['error'] = 'Sentiment analyzer not available'

                        except Exception as e:
                            web_server._analysis_jobs[job_id]['status'] = 'error'
                            web_server._analysis_jobs[job_id]['error'] = str(e)

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
                    logging.error(f"Error starting sentiment analysis: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_sentiment_status(self, job_id: str):
                """Check status of sentiment analysis job."""
                try:
                    if not hasattr(web_server, '_analysis_jobs') or job_id not in web_server._analysis_jobs:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Job not found'
                        })
                        return

                    job = web_server._analysis_jobs[job_id]

                    if job['status'] == 'completed':
                        # Job completed successfully - format result with markdown conversion
                        job_result = job['result']

                        if isinstance(job_result, dict) and 'metadata' in job_result and 'analysis' in job_result:
                            # New structured format - format metadata as HTML and convert analysis markdown
                            metadata = job_result['metadata']

                            # Determine privacy class and info using the correct field
                            is_local = metadata.get('is_local', False)
                            privacy_class = 'privacy-local' if is_local else 'privacy-external'
                            privacy_icon = '🏠' if is_local else '☁️'
                            privacy_text = 'Local Processing' if is_local else 'External API'

                            metadata_html = f"""
                            <div class="analysis-metadata" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #007bff;">
                                <h4 style="margin: 0 0 10px 0; color: #495057;">Analysis Details</h4>
                                <p><strong>Messages:</strong> {metadata.get('message_count', 'unknown')}</p>
                                <p><strong>Time Range:</strong> {metadata.get('time_range', 'unknown')}</p>
                                <p><strong>Timezone:</strong> {metadata.get('timezone', 'unknown')}</p>
                                <p class="{privacy_class}"><strong>Privacy Mode:</strong> {privacy_icon} {privacy_text}</p>
                                <p><strong>Provider:</strong> {metadata.get('provider_info', 'unknown')}</p>
                            </div>
                            """
                            analysis_html = convert_markdown_to_html(job_result['analysis'])
                            combined_html = metadata_html + analysis_html
                        else:
                            # Old format - convert entire string
                            combined_html = convert_markdown_to_html(str(job_result))

                        self._send_json_response({
                            'status': 'completed',
                            'result': combined_html
                        })
                        # Clean up completed job
                        del web_server._analysis_jobs[job_id]
                    elif job['status'] == 'error':
                        # Job failed
                        self._send_json_response({
                            'status': 'error',
                            'error': job['error']
                        })
                        # Clean up failed job
                        del web_server._analysis_jobs[job_id]
                    else:
                        # Job still running
                        self._send_json_response({
                            'status': 'running',
                            'group_name': job['group_name'],
                            'current_step': job.get('current_step', 'Processing')
                        })

                except Exception as e:
                    logging.error(f"Error checking sentiment analysis status: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_summary(self, query: Dict[str, Any]):
                """Handle summary requests."""
                self._send_json_response({
                    'status': 'error',
                    'error': 'Summary analysis not implemented yet'
                })

        return RequestHandler



# Example usage function
def start_modular_server(db: DatabaseManager, setup_service: SetupService, ai_provider=None, port: int = 8085):
    """Start the modular web server for demonstration."""
    server = ModularWebServer(db, setup_service, ai_provider, port)
    url = server.start()
    logging.info(f"Modular web server started at {url}")
    return server