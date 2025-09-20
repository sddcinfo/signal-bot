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
# Sentiment and summarization now integrated into AI analysis service
from services.ai_analysis import AIAnalysisService

# Import modular page components
from .pages.dashboard import ComprehensiveDashboard
from .pages.users import UsersPage
from .pages.groups import GroupsPage
from .pages.messages import MessagesPage
from .pages.settings import SettingsPage
from .pages.setup import SetupPage
from .pages.ai_config import AIConfigPage
from .pages.ai_analysis import AIAnalysisPage


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
                 port: int = 8084, host: str = '0.0.0.0', logger=None):
        self.db = db
        self.setup_service = setup_service
        self.ai_provider = ai_provider
        self.port = port
        self.host = host
        self.server = None
        self.logger = logger or logging.getLogger(__name__)

        # Initialize page instances
        self.pages = {
            'dashboard': ComprehensiveDashboard(db, setup_service, ai_provider),
            'users': UsersPage(db, setup_service, ai_provider),
            'groups': GroupsPage(db, setup_service, ai_provider),
            'messages': MessagesPage(db, setup_service, ai_provider),
            'settings': SettingsPage(db, setup_service, ai_provider),
            'setup': SetupPage(db, setup_service, ai_provider),
            'ai-config': AIConfigPage(db, setup_service, ai_provider),
            'ai-analysis': AIAnalysisPage(db, setup_service, ai_provider),
        }

        # For backward compatibility, keep some old methods temporarily
        # Sentiment and summarization now handled by ai_analysis_service

        # Initialize unified AI analysis service
        self.ai_analysis_service = AIAnalysisService(db)

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
                # Log requests when in debug mode
                if web_server.logger.level == logging.DEBUG:
                    web_server.logger.debug(f"[REQUEST] {format % args}")

            def do_GET(self):
                """Handle GET requests."""
                try:
                    parsed_url = urlparse(self.path)
                    path = parsed_url.path
                    query = parse_qs(parsed_url.query)

                    # Debug logging for request details
                    if web_server.logger.level == logging.DEBUG:
                        web_server.logger.debug(f"[GET] Path: {path}")
                        if query:
                            web_server.logger.debug(f"[GET] Query params: {query}")

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

                    elif path == '/ai-analysis':
                        response = web_server.pages['ai-analysis'].render(query)
                        self._send_html_response(response)

                    elif path.startswith('/static/'):
                        # Serve static files
                        file_path = path[1:]  # Remove leading slash
                        static_dir = os.path.join(os.path.dirname(__file__), file_path)

                        if os.path.exists(static_dir) and os.path.isfile(static_dir):
                            try:
                                with open(static_dir, 'rb') as f:
                                    content = f.read()

                                # Determine content type
                                content_type = mimetypes.guess_type(static_dir)[0] or 'application/octet-stream'

                                self.send_response(200)
                                self.send_header('Content-Type', content_type)
                                self.send_header('Content-Length', str(len(content)))
                                self.end_headers()
                                self.wfile.write(content)
                            except Exception as e:
                                self._send_error_response(500, f"Error serving static file: {str(e)}")
                        else:
                            self._send_error_response(404, "File not found")

                    elif path.startswith('/attachment/'):
                        # Serve attachment by ID
                        attachment_id = path.replace('/attachment/', '')
                        if not attachment_id:
                            self._send_error_response(404, "Attachment not found")
                            return

                        # Get attachment data from database
                        with web_server.db._get_connection() as conn:
                            cursor = conn.cursor()
                            # Try both attachment_id and sticker_id
                            cursor.execute("""
                                SELECT file_data, content_type, filename
                                FROM attachments
                                WHERE attachment_id = ? OR sticker_id = ?
                            """, (attachment_id, attachment_id))
                            attachment = cursor.fetchone()

                        if not attachment or not attachment['file_data']:
                            self._send_error_response(404, "Attachment not found")
                            return

                        # Send attachment
                        content_type = attachment['content_type'] or 'application/octet-stream'
                        self.send_response(200)
                        self.send_header('Content-Type', content_type)
                        self.send_header('Content-Length', str(len(attachment['file_data'])))
                        if attachment['filename']:
                            self.send_header('Content-Disposition', f'inline; filename="{attachment["filename"]}"')
                        self.end_headers()
                        self.wfile.write(attachment['file_data'])


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

            def do_DELETE(self):
                """Handle DELETE requests."""
                try:
                    parsed_url = urlparse(self.path)
                    path = parsed_url.path

                    if path.startswith('/api/ai-analysis/type/'):
                        # Extract type ID from path
                        path_parts = path.split('/')
                        if len(path_parts) >= 5:
                            type_id = path_parts[4]
                            self._handle_delete_analysis_type(type_id)
                        else:
                            self._send_error_response(404, "API endpoint not found")
                    else:
                        self._send_error_response(404, "Endpoint not found")

                except Exception as e:
                    logging.error(f"DELETE request handling error: {e}")
                    self._send_error_response(500, "Internal server error")

            def _send_html_response(self, html: str):
                """Send HTML response."""
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _send_json_response(self, data: dict):
                """Send JSON response."""
                # Debug logging for API responses
                if web_server.logger.level == logging.DEBUG:
                    web_server.logger.debug(f"[API RESPONSE] {data}")

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
                elif path.startswith('/api/summary-cached'):
                    self._handle_summary_cached(query)
                elif path.startswith('/api/summary-preview'):
                    self._handle_summary_preview(query)
                elif path.startswith('/api/summary'):
                    self._handle_summary(query)
                elif path == '/api/stats':
                    self._handle_stats(query)
                elif path == '/api/system-status':
                    self._handle_system_status()
                elif path == '/api/backups':
                    self._handle_backups()
                elif path == '/api/ai-analysis/types':
                    self._handle_ai_analysis_types()
                elif path == '/api/ai-analysis/preview':
                    self._handle_ai_analysis_preview(query)
                elif path == '/api/ai-analysis/run':
                    self._handle_ai_analysis_run(query)
                elif path.startswith('/api/ai-analysis/status'):
                    self._handle_ai_analysis_status(query)
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

                    elif path == '/api/generate-summary':
                        self._handle_generate_summary(data)

                    elif path == '/api/ai-analysis/type':
                        self._handle_create_analysis_type(data)

                    elif path.startswith('/api/ai-analysis/type/'):
                        # Extract type ID from path
                        path_parts = path.split('/')
                        if len(path_parts) >= 5:
                            type_id = path_parts[4]
                            if path.endswith('/toggle'):
                                self._handle_toggle_analysis_type(type_id)
                            elif path.endswith('/update'):
                                self._handle_update_analysis_type(type_id, data)
                            else:
                                self._send_error_response(404, "API endpoint not found")
                        else:
                            self._send_error_response(404, "API endpoint not found")

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
                            text = msg.get('text') or ''
                            text = text.strip() if text else ''
                            sender = msg.get('sender') or ''
                            sender = sender.strip() if sender else ''

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

                        # Get AI status without preloading (faster for preview)
                        from services.ai_provider import get_ai_status
                        ai_status = get_ai_status()

                        # Check if AI is ready based on status (don't actually test it)
                        ai_ready = False
                        if ai_status and ai_status.get('providers'):
                            for provider in ai_status['providers']:
                                if provider.get('available'):
                                    ai_ready = True
                                    break

                        response_data = {
                            'status': 'success',
                            'group_name': group.group_name or 'Unnamed Group',
                            'date': user_date.strftime('%Y-%m-%d'),
                            'timezone': user_timezone or 'UTC',
                            'total_messages': len(messages),
                            'analyzable_messages': len(filtered_messages),
                            'filtered_out': len(messages) - len(filtered_messages),
                            'ai_ready': ai_ready,
                            'ai_status': ai_status
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

            def _handle_summary_preview(self, query: Dict[str, Any]):
                """Get real-time message count preview for summary generation."""
                try:
                    # Parse filters using GlobalFilterSystem for consistency
                    from web.shared.filters import GlobalFilterSystem
                    from web.shared.filter_utils import get_date_range_from_filters

                    filters = GlobalFilterSystem.parse_query_filters(query)

                    # Extract filter values
                    group_id = filters.get('group_id')
                    sender_id = filters.get('sender_id')
                    attachments_only = filters.get('attachments_only', False)
                    hours = int(filters.get('hours', 24))

                    # Allow summary without group if sender is provided
                    if not group_id and not sender_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Either Group ID or Sender ID is required'
                        })
                        return

                    # Get user's timezone
                    user_timezone = query.get('timezone', [None])[0] or 'Asia/Tokyo'

                    # Use centralized date range function (handles timezone properly)
                    start_date, end_date = get_date_range_from_filters(filters)

                    # For display purposes, use the end_date (or today if no date specified)
                    if end_date:
                        user_date_str = end_date
                        from datetime import datetime
                        user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                    else:
                        # No date filter - use today in user's timezone
                        try:
                            import zoneinfo
                            from datetime import datetime
                            tz = zoneinfo.ZoneInfo(user_timezone)
                            user_date = datetime.now(tz).date()
                            user_date_str = user_date.isoformat()
                        except (ImportError, Exception):
                            from datetime import date
                            user_date = date.today()
                            user_date_str = user_date.isoformat()

                    # Get group info if group_id provided
                    group = None
                    group_name = "Filtered Messages"
                    if group_id:
                        group = web_server.db.get_group(group_id)
                        if not group:
                            self._send_json_response({
                                'status': 'error',
                                'error': 'Group not found'
                            })
                            return
                        group_name = group.group_name or f"Group {group_id[:8]}"

                    # Get REAL-TIME message count using the same shared database method
                    messages = web_server.db.get_messages_by_group_with_names_filtered(
                        group_id=group_id,
                        sender_uuid=sender_id,
                        attachments_only=attachments_only,
                        start_date=start_date,
                        end_date=end_date,
                        user_timezone=user_timezone,
                        limit=1000,
                        offset=0
                    )

                    # Count actual messages retrieved
                    message_count = len(messages)

                    # Simple response matching sentiment preview style
                    self._send_json_response({
                        'status': 'success',
                        'group_name': group_name,
                        'group_id': group_id or '',
                        'date': user_date.strftime('%Y-%m-%d'),
                        'hours': hours,
                        'message_count': message_count,
                        'preview_text': f"Will summarize {message_count} messages from the last {hours} hours for {group_name}"
                    })

                except Exception as e:
                    logging.error(f"Error in summary preview: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_summary_cached(self, query: Dict[str, Any]):
                """Get cached summary analysis results."""
                try:
                    group_id = query.get('group_id', [None])[0]
                    if not group_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Group ID is required'
                        })
                        return

                    # Get user's timezone and date
                    user_timezone = query.get('timezone', [None])[0] or 'Asia/Tokyo'
                    user_date_str = query.get('date', [None])[0]
                    hours = int(query.get('hours', [24])[0])

                    if user_date_str:
                        from datetime import datetime
                        user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                    else:
                        from datetime import date
                        user_date = date.today()

                    # Try to get cached result
                    cached_result = web_server.db.get_summary_analysis(group_id, user_date, hours)

                    if cached_result:
                        # Get additional metadata from database
                        with web_server.db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT created_at, message_count, is_local_ai FROM summary_analysis
                                WHERE group_id = ? AND analysis_date = ? AND hours = ?
                            """, (group_id, user_date.strftime('%Y-%m-%d'), hours))
                            metadata = cursor.fetchone()

                        # Parse the JSON result
                        try:
                            summary_data = json.loads(cached_result)
                        except:
                            summary_data = {'summary': cached_result}  # Fallback for plain text

                        group = web_server.db.get_group(group_id)
                        group_name = group.group_name if group else "Unknown Group"

                        self._send_json_response({
                            'status': 'cached',
                            'group_name': group_name,
                            'group_id': group_id,
                            'date': user_date.strftime('%Y-%m-%d'),
                            'hours': hours,
                            'summary': summary_data.get('summary', cached_result),
                            'message_count': metadata['message_count'] if metadata else 0,
                            'is_local_ai': metadata['is_local_ai'] if metadata else False,
                            'cached_at': metadata['created_at'] if metadata else None,
                            'key_topics': summary_data.get('key_topics', []),
                            'privacy_mode': 'local' if (metadata and metadata['is_local_ai']) else 'anonymized'
                        })
                    else:
                        self._send_json_response({
                            'status': 'not_cached',
                            'group_id': group_id,
                            'date': user_date.strftime('%Y-%m-%d'),
                            'hours': hours
                        })

                except Exception as e:
                    logging.error(f"Error getting cached summary: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_summary(self, query: Dict[str, Any]):
                """Handle summary analysis requests with async support."""
                try:
                    # Check if this is a status check for an existing job
                    job_id = query.get('job_id', [None])[0]
                    if job_id:
                        return self._handle_summary_status(job_id)

                    # Check if force refresh is requested
                    force_refresh = query.get('force', [False])[0] == 'true'
                    async_mode = query.get('async', [False])[0] == 'true'

                    # Parse filters using GlobalFilterSystem for consistency
                    from web.shared.filters import GlobalFilterSystem
                    from web.shared.filter_utils import get_date_range_from_filters

                    filters = GlobalFilterSystem.parse_query_filters(query)

                    # Extract filter values
                    group_id = filters['group_id']
                    sender_id = filters['sender_id']
                    attachments_only = filters['attachments_only']
                    hours = filters['hours']
                    user_timezone = filters['timezone']

                    # Use centralized date range function (handles timezone properly)
                    start_date, end_date = get_date_range_from_filters(filters)

                    # Get the user date string for the summarizer
                    if filters['date_mode'] == 'today':
                        from datetime import date
                        user_date = date.today()
                        user_date_str = user_date.isoformat()
                    elif filters['date']:
                        user_date_str = filters['date']
                        from datetime import datetime
                        user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
                    else:
                        from datetime import date
                        user_date = date.today()
                        user_date_str = user_date.isoformat()

                    # Allow summary without group if sender is provided
                    if not group_id and not sender_id:
                        # Get first monitored group as default
                        groups = web_server.db.get_all_groups()
                        for g in groups:
                            if g.is_monitored:
                                group_id = g.group_id
                                break

                        if not group_id:
                            self._send_json_response({
                                'status': 'error',
                                'error': 'No monitored groups found'
                            })
                            return

                    # Check for cached result first (unless force refresh)
                    if not force_refresh:
                        cached_result = web_server.db.get_summary_analysis(group_id, user_date, hours)
                        if cached_result:
                            # Return cached result
                            query['date'] = [user_date.strftime('%Y-%m-%d')]
                            query['hours'] = [str(hours)]
                            return self._handle_summary_cached(query)

                    # Get group info if group_id provided
                    group = None
                    group_name = "Filtered Messages"
                    if group_id:
                        group = web_server.db.get_group(group_id)
                        if not group:
                            self._send_json_response({
                                'status': 'error',
                                'error': 'Group not found'
                            })
                            return
                        group_name = group.group_name or "Unknown Group"
                    elif sender_id:
                        # Try to get sender name
                        with web_server.db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT friendly_name FROM user_mappings WHERE uuid = ?", (sender_id,))
                            row = cursor.fetchone()
                            if row and row['friendly_name']:
                                group_name = f"Messages from {row['friendly_name']}"

                    # If async mode, start background job
                    if async_mode:
                        import uuid
                        import threading
                        import time

                        job_id = str(uuid.uuid4())

                        # Initialize jobs dict if needed
                        if not hasattr(web_server, '_summary_jobs'):
                            web_server._summary_jobs = {}

                        web_server._summary_jobs[job_id] = {
                            'status': 'running',
                            'group_id': group_id,
                            'group_name': group_name,
                            'started_at': time.time(),
                            'result': None,
                            'error': None,
                            'current_step': 'Initializing'
                        }

                        def run_summary():
                            try:
                                web_server._summary_jobs[job_id]['current_step'] = 'Preloading AI model'

                                # Preload AI model
                                from services.ai_provider import get_ai_response
                                get_ai_response("test", timeout=5)

                                web_server._summary_jobs[job_id]['current_step'] = 'Fetching messages'

                                # Get messages using the SAME logic as other tabs
                                messages = web_server.db.get_messages_by_group_with_names_filtered(
                                    group_id=group_id,
                                    sender_uuid=sender_id,
                                    attachments_only=attachments_only,
                                    start_date=start_date,
                                    end_date=end_date,
                                    user_timezone=user_timezone,
                                    limit=1000,
                                    offset=0
                                )

                                # Count actual messages retrieved
                                message_count = len(messages)

                                web_server._summary_jobs[job_id]['current_step'] = 'Generating summary'

                                # Now pass the already-filtered messages to the summarizer
                                # Now using AI analysis service for summarization
                                result = summarizer.summarize_from_messages(
                                    messages=messages,
                                    message_count=message_count,
                                    group_name=group_name,
                                    hours=hours,
                                    user_timezone=user_timezone
                                )

                                if result and result.get('status') != 'error':
                                    # Cache the result
                                    summary_json = json.dumps(result)
                                    is_local = result.get('is_local', False)
                                    message_count = result.get('message_count', 0)

                                    web_server.db.store_summary_analysis(
                                        group_id,
                                        user_date,
                                        hours,
                                        message_count,
                                        summary_json,
                                        is_local
                                    )

                                    web_server._summary_jobs[job_id]['status'] = 'completed'
                                    web_server._summary_jobs[job_id]['result'] = result
                                else:
                                    web_server._summary_jobs[job_id]['status'] = 'error'
                                    web_server._summary_jobs[job_id]['error'] = result.get('error', 'Failed to generate summary') if result else 'Failed to generate summary'

                            except Exception as e:
                                web_server._summary_jobs[job_id]['status'] = 'error'
                                web_server._summary_jobs[job_id]['error'] = str(e)

                        # Start background thread
                        thread = threading.Thread(target=run_summary, daemon=True)
                        thread.start()

                        # Return job ID immediately
                        self._send_json_response({
                            'status': 'started',
                            'job_id': job_id,
                            'group_name': group_name,
                            'message': 'Summary generation started in background'
                        })
                    else:
                        # Synchronous mode - generate immediately
                        # Get messages using the SAME logic as other tabs
                        messages = web_server.db.get_messages_by_group_with_names_filtered(
                            group_id=group_id,
                            sender_uuid=sender_id,
                            attachments_only=attachments_only,
                            start_date=start_date,
                            end_date=end_date,
                            user_timezone=user_timezone,
                            limit=1000,
                            offset=0
                        )

                        # Count actual messages retrieved
                        message_count = len(messages)

                        # Generate summary from the already-filtered messages
                        # Now using AI analysis service for summarization
                        result = summarizer.summarize_from_messages(
                            messages=messages,
                            message_count=message_count,
                            group_name=group_name,
                            hours=hours,
                            user_timezone=user_timezone
                        )

                        if result and result.get('status') != 'error':
                            # Cache the result
                            summary_json = json.dumps(result)
                            is_local = result.get('is_local', False)
                            message_count = result.get('message_count', 0)

                            web_server.db.store_summary_analysis(
                                group_id,
                                user_date,
                                hours,
                                message_count,
                                summary_json,
                                is_local
                            )

                            self._send_json_response(result)
                        else:
                            self._send_json_response(result if result else {
                                'status': 'error',
                                'error': 'Failed to generate summary'
                            })

                except Exception as e:
                    logging.error(f"Error in summary analysis: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_generate_summary(self, data: Dict[str, Any]):
                """Handle POST request to generate a new summary with async support."""
                try:
                    # Convert POST data to query format for GlobalFilterSystem
                    query = {}
                    for key, value in data.items():
                        query[key] = [value] if not isinstance(value, list) else value

                    # Parse filters using GlobalFilterSystem
                    from web.shared.filters import GlobalFilterSystem
                    filters = GlobalFilterSystem.parse_query_filters(query)

                    group_id = filters.get('group_id')
                    if not group_id:
                        # Get first monitored group
                        groups = web_server.db.get_all_groups()
                        for g in groups:
                            if g.is_monitored:
                                group_id = g.group_id
                                break

                    if not group_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'No group specified or found'
                        })
                        return

                    # Force refresh with async mode by default for POST requests
                    query = {
                        'group_id': [group_id],
                        'timezone': [filters['timezone']],
                        'date': [filters['date']] if filters['date'] else [],
                        'hours': [str(filters['hours'])],
                        'date_mode': [filters['date_mode']],
                        'sender_id': [filters['sender_id']] if filters['sender_id'] else [],
                        'attachments_only': ['true'] if filters['attachments_only'] else ['false'],
                        'force': ['true'],
                        'async': ['true']  # Use async mode for POST requests
                    }
                    self._handle_summary(query)

                except Exception as e:
                    logging.error(f"Error generating summary: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_summary_status(self, job_id: str):
                """Check status of summary generation job."""
                try:
                    if not hasattr(web_server, '_summary_jobs') or job_id not in web_server._summary_jobs:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Job not found'
                        })
                        return

                    job = web_server._summary_jobs[job_id]

                    if job['status'] == 'completed':
                        # Job completed successfully - return result
                        self._send_json_response(job['result'])
                        # Clean up completed job
                        del web_server._summary_jobs[job_id]
                    elif job['status'] == 'error':
                        # Job failed
                        self._send_json_response({
                            'status': 'error',
                            'error': job['error']
                        })
                        # Clean up failed job
                        del web_server._summary_jobs[job_id]
                    else:
                        # Job still running
                        self._send_json_response({
                            'status': 'running',
                            'group_name': job['group_name'],
                            'current_step': job.get('current_step', 'Processing')
                        })

                except Exception as e:
                    logging.error(f"Error checking summary status: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_stats(self, query: dict = None):
                """Handle statistics API request."""
                try:
                    stats = {}

                    # Get user timezone from query
                    user_timezone = 'Asia/Tokyo'
                    if query:
                        timezone_param = query.get('timezone', [None])[0]
                        if timezone_param:
                            user_timezone = timezone_param

                    # Get message statistics
                    with web_server.db._get_connection() as conn:
                        cursor = conn.cursor()

                        # Total messages
                        cursor.execute("SELECT COUNT(*) as count FROM messages")
                        stats['total_messages'] = cursor.fetchone()['count']

                        # Messages today - with timezone support
                        try:
                            import pytz
                            from datetime import datetime

                            tz = pytz.timezone(user_timezone)
                            now_tz = datetime.now(tz)
                            start_of_today = now_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                            start_timestamp_ms = int(start_of_today.timestamp() * 1000)

                            cursor.execute("SELECT COUNT(*) as count FROM messages WHERE timestamp >= ?", (start_timestamp_ms,))
                            stats['messages_today'] = cursor.fetchone()['count']
                        except Exception:
                            # Fallback to UTC if timezone fails
                            cursor.execute("""
                                SELECT COUNT(*) as count FROM messages
                                WHERE date(timestamp/1000, 'unixepoch') = date('now')
                            """)
                            stats['messages_today'] = cursor.fetchone()['count']

                        # Active groups
                        cursor.execute("""
                            SELECT COUNT(DISTINCT group_id) as count
                            FROM messages
                            WHERE timestamp > (strftime('%s', 'now') - 86400) * 1000
                        """)
                        stats['active_groups'] = cursor.fetchone()['count']

                        # Total users
                        cursor.execute("SELECT COUNT(*) as count FROM users")
                        stats['total_users'] = cursor.fetchone()['count']

                        # Total groups
                        cursor.execute("SELECT COUNT(*) as count FROM groups")
                        stats['total_groups'] = cursor.fetchone()['count']

                        # Database size
                        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                        db_size = cursor.fetchone()['size']
                        stats['database_size'] = f"{db_size / (1024*1024):.1f} MB"

                    self._send_json_response(stats)

                except Exception as e:
                    logging.error(f"Error getting stats: {e}")
                    self._send_json_response({'error': str(e)})

            def _handle_system_status(self):
                """Handle system status API request."""
                try:
                    import psutil
                    import os

                    # Get system info
                    status = {
                        'cpu_percent': psutil.cpu_percent(interval=1),
                        'memory': {
                            'total': psutil.virtual_memory().total,
                            'used': psutil.virtual_memory().used,
                            'percent': psutil.virtual_memory().percent
                        },
                        'disk': {
                            'total': psutil.disk_usage('/').total,
                            'used': psutil.disk_usage('/').used,
                            'percent': psutil.disk_usage('/').percent
                        },
                        'processes': []
                    }

                    # Check for bot processes
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                        try:
                            pinfo = proc.info
                            if pinfo['cmdline'] and any('signal' in str(arg).lower() for arg in pinfo['cmdline']):
                                status['processes'].append({
                                    'pid': pinfo['pid'],
                                    'name': pinfo['name'],
                                    'cpu_percent': pinfo['cpu_percent'],
                                    'memory_mb': pinfo['memory_info'].rss / (1024*1024) if pinfo['memory_info'] else 0,
                                    'type': 'bot' if 'bot.py' in str(pinfo['cmdline']) else 'web' if 'web_server' in str(pinfo['cmdline']) else 'other'
                                })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    self._send_json_response(status)

                except Exception as e:
                    logging.error(f"Error getting system status: {e}")
                    self._send_json_response({'error': str(e)})

            def _handle_backups(self):
                """Handle backups API request."""
                try:
                    import os
                    from datetime import datetime

                    backups = []
                    backup_dir = 'backups/db'

                    if os.path.exists(backup_dir):
                        for filename in os.listdir(backup_dir):
                            if filename.endswith('.db') or filename.endswith('.db.gz'):
                                filepath = os.path.join(backup_dir, filename)
                                stat = os.stat(filepath)

                                # Parse backup type from filename
                                backup_type = 'unknown'
                                if 'critical' in filename:
                                    backup_type = 'critical'
                                elif 'full' in filename:
                                    backup_type = 'full'
                                elif 'incremental' in filename:
                                    backup_type = 'incremental'

                                backups.append({
                                    'filename': filename,
                                    'size': stat.st_size,
                                    'size_formatted': f"{stat.st_size / (1024*1024):.1f} MB",
                                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    'type': backup_type
                                })

                    # Sort by creation date, newest first
                    backups.sort(key=lambda x: x['created'], reverse=True)

                    # Get last backup time
                    last_backup = backups[0]['created'] if backups else None

                    self._send_json_response({
                        'backups': backups[:10],  # Return only last 10
                        'total_count': len(backups),
                        'last_backup': last_backup
                    })

                except Exception as e:
                    logging.error(f"Error getting backups: {e}")
                    self._send_json_response({'error': str(e)})

            def _handle_ai_analysis_types(self):
                """Get list of available AI analysis types."""
                try:
                    types = web_server.ai_analysis_service.get_analysis_types(active_only=False)
                    self._send_json_response({
                        'status': 'success',
                        'types': types
                    })
                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_ai_analysis_preview(self, query: Dict[str, Any]):
                """Preview AI analysis (real-time count, no caching)."""
                try:
                    # Get parameters
                    analysis_type = query.get('analysis_type', [None])[0]
                    user_timezone = query.get('timezone', ['UTC'])[0]

                    if not analysis_type:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Analysis type required'
                        })
                        return

                    # Get analysis config
                    config = web_server.ai_analysis_service.get_analysis_config(analysis_type)
                    if not config:
                        self._send_json_response({
                            'status': 'error',
                            'error': f'Analysis type {analysis_type} not found'
                        })
                        return

                    # Get date range based on filters
                    from .shared.filters import GlobalFilterSystem

                    # Parse full filters using GlobalFilterSystem to handle date transformations
                    filters = GlobalFilterSystem.parse_query_filters(query)

                    # Debug: Log the parsed filters
                    import logging
                    logging.info(f"[AI Analysis Preview] Parsed filters: {filters}")
                    logging.info(f"[AI Analysis Preview] Date type: {type(filters.get('date'))}, value: {filters.get('date')}")

                    try:
                        start_date, end_date = GlobalFilterSystem.get_date_range_from_filters(filters, user_timezone)
                    except Exception as e:
                        import traceback
                        logging.error(f"[AI Analysis Preview] Error in get_date_range_from_filters: {e}")
                        logging.error(f"[AI Analysis Preview] Traceback: {traceback.format_exc()}")
                        raise

                    # Get messages using shared backend API
                    # Extract filter values from parsed filters
                    group_id = filters.get('group_id')
                    sender_id = filters.get('sender_id')
                    attachments_only = filters.get('attachments_only', False)
                    hours = filters.get('hours', 24)  # Extract hours from filters

                    # Convert datetime objects to strings for database method
                    # The database method expects YYYY-MM-DD format strings
                    if start_date:
                        start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)[:10]
                    else:
                        start_date_str = None

                    if end_date:
                        end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)[:10]
                    else:
                        end_date_str = None

                    messages = web_server.db.get_messages_by_group_with_names_filtered(
                        group_id=group_id,
                        sender_uuid=sender_id,
                        attachments_only=attachments_only,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        user_timezone=user_timezone,
                        limit=1000,
                        offset=0
                    )

                    # Get group name
                    group = web_server.db.get_group(group_id) if group_id else None
                    group_name = group.group_name if group else 'Unknown'

                    # Return preview info
                    self._send_json_response({
                        'status': 'success',
                        'message_count': len(messages),
                        'group_name': group_name,
                        'hours': hours,
                        'display_name': config['display_name'],
                        'icon': config.get('icon', '🤖'),
                        'min_messages': config.get('min_messages', 5),
                        'max_hours': config.get('max_hours', 168)
                    })

                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_ai_analysis_run(self, query: Dict[str, Any]):
                """Run AI analysis."""
                try:
                    # Get parameters
                    group_id = query.get('group_id', [None])[0]
                    sender_id = query.get('sender_id', [None])[0]
                    analysis_type = query.get('analysis_type', [None])[0]
                    user_timezone = query.get('timezone', ['UTC'])[0]
                    hours = int(query.get('hours', [24])[0])
                    date_str = query.get('date', [None])[0]
                    date_mode = query.get('date_mode', ['all'])[0]
                    attachments_only = query.get('attachments_only', ['false'])[0] == 'true'
                    async_mode = query.get('async', ['false'])[0] == 'true'

                    if not analysis_type:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Analysis type required'
                        })
                        return

                    # Get date range based on filters
                    from .shared.filters import GlobalFilterSystem

                    # Parse full filters using GlobalFilterSystem to handle date transformations
                    filters = GlobalFilterSystem.parse_query_filters(query)
                    start_date, end_date = GlobalFilterSystem.get_date_range_from_filters(filters, user_timezone)

                    # Get messages using shared backend API
                    # Extract filter values from parsed filters
                    group_id = filters.get('group_id')
                    sender_id = filters.get('sender_id')
                    attachments_only = filters.get('attachments_only', False)
                    hours = filters.get('hours', 24)  # Extract hours from filters

                    # Convert datetime objects to strings for database method
                    # The database method expects YYYY-MM-DD format strings
                    if start_date:
                        start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)[:10]
                    else:
                        start_date_str = None

                    if end_date:
                        end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)[:10]
                    else:
                        end_date_str = None

                    messages = web_server.db.get_messages_by_group_with_names_filtered(
                        group_id=group_id,
                        sender_uuid=sender_id,
                        attachments_only=attachments_only,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        user_timezone=user_timezone,
                        limit=1000,
                        offset=0
                    )

                    # Get group name
                    group = web_server.db.get_group(group_id) if group_id else None
                    group_name = group.group_name if group else 'Unknown'

                    if async_mode:
                        # Create job ID
                        job_id = str(uuid.uuid4())

                        # Initialize job tracking
                        if not hasattr(web_server, '_analysis_jobs'):
                            web_server._analysis_jobs = {}

                        web_server._analysis_jobs[job_id] = {
                            'status': 'running',
                            'step': 'Analyzing messages...',
                            'created': time.time()
                        }

                        def run_analysis():
                            try:
                                # Run analysis
                                result = web_server.ai_analysis_service.analyze_messages(
                                    messages=messages,
                                    analysis_type=analysis_type,
                                    group_name=group_name,
                                    hours=hours
                                )

                                if result and result.get('status') == 'success':
                                    web_server._analysis_jobs[job_id]['status'] = 'completed'
                                    web_server._analysis_jobs[job_id]['result'] = result
                                else:
                                    web_server._analysis_jobs[job_id]['status'] = 'error'
                                    web_server._analysis_jobs[job_id]['error'] = result.get('error', 'Analysis failed')

                            except Exception as e:
                                web_server._analysis_jobs[job_id]['status'] = 'error'
                                web_server._analysis_jobs[job_id]['error'] = str(e)

                        # Start background thread
                        thread = threading.Thread(target=run_analysis, daemon=True)
                        thread.start()

                        # Return job ID immediately
                        self._send_json_response({
                            'status': 'started',
                            'job_id': job_id
                        })
                    else:
                        # Synchronous mode
                        result = web_server.ai_analysis_service.analyze_messages(
                            messages=messages,
                            analysis_type=analysis_type,
                            group_name=group_name,
                            hours=hours
                        )
                        self._send_json_response(result)

                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_ai_analysis_status(self, query: Dict[str, Any]):
                """Check AI analysis job status."""
                try:
                    job_id = query.get('job_id', [None])[0]

                    if not job_id:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Job ID required'
                        })
                        return

                    if not hasattr(web_server, '_analysis_jobs'):
                        self._send_json_response({
                            'status': 'error',
                            'error': 'No jobs found'
                        })
                        return

                    job = web_server._analysis_jobs.get(job_id)
                    if not job:
                        self._send_json_response({
                            'status': 'error',
                            'error': f'Job {job_id} not found'
                        })
                        return

                    # Clean up old completed jobs (older than 5 minutes)
                    current_time = time.time()
                    for old_job_id, old_job in list(web_server._analysis_jobs.items()):
                        if old_job['status'] in ['completed', 'error'] and current_time - old_job['created'] > 300:
                            del web_server._analysis_jobs[old_job_id]

                    self._send_json_response(job)

                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_create_analysis_type(self, config: Dict[str, Any]):
                """Create new AI analysis type."""
                try:
                    success = web_server.ai_analysis_service.save_analysis_type(config)
                    if success:
                        self._send_json_response({'status': 'success'})
                    else:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Failed to save analysis type'
                        })
                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_toggle_analysis_type(self, type_id: str):
                """Toggle active status of an analysis type."""
                try:
                    # Get current state
                    with web_server.db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT is_active FROM ai_analysis_types WHERE id = ?", (type_id,))
                        row = cursor.fetchone()

                        if not row:
                            self._send_json_response({
                                'status': 'error',
                                'error': 'Analysis type not found'
                            })
                            return

                        # Toggle state
                        new_state = 0 if row['is_active'] else 1
                        cursor.execute("UPDATE ai_analysis_types SET is_active = ? WHERE id = ?", (new_state, type_id))
                        conn.commit()

                    self._send_json_response({'status': 'success'})

                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_update_analysis_type(self, type_id: str, config: Dict[str, Any]):
                """Update an existing AI analysis type."""
                try:
                    # Get the existing type to check if it's built-in
                    types = web_server.ai_analysis_service.get_analysis_types(active_only=False)
                    existing_type = next((t for t in types if t['id'] == int(type_id)), None)

                    if not existing_type:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Analysis type not found'
                        })
                        return

                    if existing_type.get('is_builtin'):
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Cannot edit built-in analysis types'
                        })
                        return

                    # Update the analysis type
                    with web_server.db._get_connection() as conn:
                        cursor = conn.cursor()

                        # Build update query dynamically
                        update_fields = []
                        values = []

                        # Update allowed fields
                        allowed_fields = ['display_name', 'description', 'prompt_template',
                                        'icon', 'min_messages', 'max_hours',
                                        'requires_group', 'requires_sender']

                        for field in allowed_fields:
                            if field in config:
                                # Map frontend field names to database columns
                                db_field = field
                                if field == 'max_hours':
                                    db_field = 'default_hours'

                                update_fields.append(f"{db_field} = ?")
                                values.append(config[field])

                        if update_fields:
                            values.append(int(type_id))
                            query = f"""UPDATE ai_analysis_types
                                      SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                                      WHERE id = ? AND is_builtin = 0"""

                            cursor.execute(query, values)
                            conn.commit()

                            if cursor.rowcount > 0:
                                self._send_json_response({'status': 'success'})
                            else:
                                self._send_json_response({
                                    'status': 'error',
                                    'error': 'Failed to update analysis type'
                                })
                        else:
                            self._send_json_response({
                                'status': 'error',
                                'error': 'No fields to update'
                            })

                except Exception as e:
                    logging.error(f"Error updating analysis type: {e}")
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

            def _handle_delete_analysis_type(self, type_id: str):
                """Delete an AI analysis type."""
                try:
                    success = web_server.ai_analysis_service.delete_analysis_type(int(type_id))
                    if success:
                        self._send_json_response({'status': 'success'})
                    else:
                        self._send_json_response({
                            'status': 'error',
                            'error': 'Failed to delete analysis type (may be built-in)'
                        })
                except Exception as e:
                    self._send_json_response({
                        'status': 'error',
                        'error': str(e)
                    })

        return RequestHandler



# Example usage function
def start_modular_server(db: DatabaseManager, setup_service: SetupService, ai_provider=None, port: int = 8085):
    """Start the modular web server for demonstration."""
    server = ModularWebServer(db, setup_service, ai_provider, port)
    url = server.start()
    logging.info(f"Modular web server started at {url}")
    return server