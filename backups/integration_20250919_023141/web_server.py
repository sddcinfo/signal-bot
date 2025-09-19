#!/usr/bin/env python3
"""
Standalone Web Server for Signal Bot

Runs the web interface independently from the Signal CLI polling service.
This allows restarting the web interface without interrupting message processing.
"""
import os
import sys
import logging
import argparse
import signal
import threading
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.database import DatabaseManager
from services.setup import SetupService
from web.server import ModularWebServer


class StandaloneWebServer:
    """Standalone web server for Signal Bot management interface."""

    def __init__(self, port: int = 8084, host: str = '0.0.0.0', debug: bool = False):
        """Initialize the standalone web server.

        Args:
            port: Port to run the web server on
            host: Host to bind to
            debug: Enable debug logging
        """
        self.port = port
        self.host = host
        self.debug = debug
        self.shutdown_event = threading.Event()

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize database and services
        self.db = DatabaseManager(logger=self.logger)
        self.setup_service = SetupService(self.db, logger=self.logger)

        # Initialize AI provider manager
        from services.ai_provider import initialize_ai_manager
        try:
            self.ai_provider = initialize_ai_manager(db_manager=self.db, logger=self.logger)
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI provider: {e}")
            self.ai_provider = None

        # Initialize web server
        self.web_server = ModularWebServer(
            self.db,
            self.setup_service,
            ai_provider=self.ai_provider,
            port=self.port,
            host=self.host
        )

        # Setup signal handlers
        self._setup_signal_handlers()

        self.logger.info(f"Standalone web server initialized for {host}:{port}")

    def _setup_logging(self):
        """Setup logging for web server."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format=f'%(asctime)s - [WEB-SERVER:{self.port}] - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('web_server.log', mode='a')
            ],
            force=True
        )

        # Set specific log levels for components
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if self.shutdown_event.is_set():
                return
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received signal {signal_name}. Shutting down web server...")
            self.shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self):
        """Start the web server."""
        try:
            self.logger.info(f"Starting web server on {self.host}:{self.port}")
            url = self.web_server.start()
            self.logger.info(f"Web server started at {url}")

            # Keep the main thread alive
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(1.0)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Web server error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown the web server gracefully."""
        if self.shutdown_event.is_set():
            return

        self.logger.info("Shutting down web server...")
        self.shutdown_event.set()

        if self.web_server:
            try:
                self.web_server.stop()
                self.logger.info("Web server stopped")
            except Exception as e:
                self.logger.error(f"Error stopping web server: {e}")


def check_port_in_use(port: int, host: str = 'localhost') -> bool:
    """Check if a port is already in use."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    finally:
        sock.close()


def kill_process_on_port(port: int) -> bool:
    """Kill any process using the specified port."""
    import subprocess
    try:
        # Find process using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], check=True)
                    print(f"Killed process {pid} on port {port}")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False


def main():
    """Main entry point for standalone web server."""
    parser = argparse.ArgumentParser(description='Signal Bot Standalone Web Server')
    parser.add_argument('--testing', action='store_true', help='Use testing port (8085) instead of production port (8084)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Simple port management: 8084 for production, 8085 for testing
    port = 8085 if args.testing else 8084

    # Check if port is in use and handle it
    if check_port_in_use(port, args.host):
        print(f"Port {port} is already in use. Attempting to kill existing process...")
        if kill_process_on_port(port):
            print(f"Successfully killed process on port {port}")
            # Wait a moment for the port to be released
            import time
            time.sleep(2)
        else:
            print(f"Failed to kill process on port {port}")
            sys.exit(1)

    # Create and start the web server
    server = StandaloneWebServer(
        port=port,
        host=args.host,
        debug=args.debug
    )

    print(f"Starting web server on port {port} ({'testing' if args.testing else 'production'} mode)")
    server.start()


if __name__ == "__main__":
    main()