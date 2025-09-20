#!/usr/bin/env python3
"""
Signal Bot Management System

A unified management tool for the Signal Bot application.
Replaces multiple shell scripts with a single, modern Python interface.
"""

import os
import sys
import time
import signal
import sqlite3
import argparse
import subprocess
import shutil
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import psutil  # Will need to add to requirements.txt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Config
from utils.common import format_file_size
from models.database import DatabaseManager


class SignalBotManager:
    """Main management class for Signal Bot operations."""

    def __init__(self):
        self.config = Config()
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.python_cmd = str(self.venv_path / "bin" / "python3") if self.venv_path.exists() else "python3"
        self.debug_mode = False
        self.debug_logger = None
        self.setup_debug_logging()

    def setup_debug_logging(self):
        """Configure comprehensive debug logging based on environment variables."""
        # Check for debug mode
        if any([
            os.environ.get('SIGNAL_BOT_DEBUG') == '1',
            os.environ.get('DEBUG') == '1',
            os.environ.get('SIGNAL_BOT_LOG_LEVEL') == 'DEBUG'
        ]):
            self.debug_mode = True

            # Configure root logger for comprehensive logging
            log_format = os.environ.get(
                'LOG_FORMAT',
                '%(asctime)s.%(msecs)03d [%(process)d:%(thread)d] %(name)s.%(funcName)s:%(lineno)d %(levelname)s: %(message)s'
            )
            date_format = os.environ.get('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')

            # Create debug logger
            self.debug_logger = logging.getLogger('SignalBotDebug')
            self.debug_logger.setLevel(logging.DEBUG)

            # File handler for debug log
            debug_log = os.environ.get('DEBUG_LOG', 'signal_bot_debug.log')
            file_handler = logging.handlers.RotatingFileHandler(
                debug_log,
                maxBytes=100*1024*1024,  # 100MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(log_format, datefmt=date_format)
            file_handler.setFormatter(file_formatter)
            self.debug_logger.addHandler(file_handler)

            # Console handler for immediate feedback
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.debug_logger.addHandler(console_handler)

            # Configure all Python loggers to DEBUG level
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
                datefmt=date_format,
                handlers=[file_handler, console_handler]
            )

            # Enable SQL logging if requested
            if os.environ.get('SIGNAL_BOT_SQL_DEBUG') == '1':
                logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
                logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

            self.debug_log("Debug mode initialized", {
                'python_version': sys.version,
                'debug_env_vars': {k: v for k, v in os.environ.items() if 'DEBUG' in k or 'TRACE' in k},
                'working_dir': os.getcwd(),
                'pid': os.getpid()
            })

    def debug_log(self, message: str, data: Optional[Dict] = None):
        """Log a debug message with optional structured data."""
        if self.debug_logger:
            if data:
                import json
                self.debug_logger.debug(f"{message}\nData: {json.dumps(data, indent=2, default=str)}")
            else:
                self.debug_logger.debug(message)

    # ========== Service Management ==========

    def start(self, service: Optional[str] = None, daemon_mode: bool = False, debug: bool = False) -> bool:
        """Start Signal Bot services."""
        # Enable debug if requested or if environment variable is set
        if debug or self.debug_mode:
            debug = True
            os.environ['LOG_LEVEL'] = 'DEBUG'
            os.environ['SIGNAL_BOT_DEBUG'] = '1'
            print("🐛 Debug mode enabled")
            self.debug_log(f"Starting services", {
                'service': service,
                'daemon_mode': daemon_mode,
                'debug': debug,
                'environment': dict(os.environ)
            })
        else:
            os.environ['LOG_LEVEL'] = 'INFO'

        if service == "signal" or service is None:
            print(f"Starting Signal service{'(daemon mode)' if daemon_mode else ''}...")
            self.debug_log(f"Starting Signal service", {'daemon_mode': daemon_mode})
            if daemon_mode:
                self._start_signal_daemon(debug=debug)
            else:
                self._start_signal_service(debug=debug)

        if service == "web" or service is None:
            print("Starting Web server...")
            self.debug_log("Starting Web server", {'debug': debug})
            self._start_web_server(debug=debug)

        if service is None:
            print("\n✅ All services started")
            self.status()
        return True

    def stop(self, service: Optional[str] = None) -> bool:
        """Stop Signal Bot services."""
        print("Stopping services...")

        patterns = []
        if service == "signal":
            patterns = ["signal_service.py", "signal_daemon_service.py"]
        elif service == "web":
            patterns = ["web_server.py"]
        else:
            patterns = ["signal_service.py", "signal_daemon_service.py", "web_server.py"]

        for pattern in patterns:
            self._kill_process(pattern)

        # Also clean up daemon socket if present
        socket_path = "/tmp/signal-cli.socket"
        if Path(socket_path).exists():
            try:
                os.remove(socket_path)
                print("  Removed daemon socket")
            except:
                pass

        print("✅ Services stopped")
        return True

    def restart(self, service: Optional[str] = None, daemon_mode: bool = False, debug: bool = False) -> bool:
        """Restart Signal Bot services."""
        print("Restarting services...")
        self.stop(service)
        time.sleep(2)
        self.start(service, daemon_mode=daemon_mode, debug=debug)
        return True

    def status(self) -> Dict:
        """Show current status of all components."""
        print("\n" + "=" * 80)
        print("SIGNAL BOT STATUS")
        print("=" * 80)
        print(f"Timestamp: {datetime.now()}")

        status = {}

        # Check processes
        print("\n📊 Running Processes:")
        processes = self._get_processes()
        status['processes'] = processes
        for proc in processes:
            print(f"  PID {proc['pid']:6}: {proc['name']} ({proc['cpu']:.1f}% CPU, {proc['memory']:.1f} MB)")

        if not processes:
            print("  No Signal Bot processes running")

        # Check ports
        print("\n🌐 Network Ports:")
        ports = self._check_ports()
        status['ports'] = ports
        for port_info in ports:
            print(f"  Port {port_info['port']}: {port_info['process']}")

        # Check Signal CLI
        print("\n📱 Signal CLI:")
        signal_cli = self._check_signal_cli()
        status['signal_cli'] = signal_cli
        if signal_cli['available']:
            print(f"  ✓ Available at {signal_cli['path']}")
            print(f"  Version: {signal_cli['version']}")
        else:
            print("  ✗ Not found")

        # Check database
        print("\n💾 Database:")
        db_info = self._check_database()
        status['database'] = db_info
        if db_info['exists']:
            print(f"  File: {db_info['path']} ({db_info['size']})")
            print(f"  Tables: {db_info['tables']}")
            print(f"  Users: {db_info['users']}, Groups: {db_info['groups']}, Messages: {db_info['messages']}")
        else:
            print("  Database not found")

        # Check logs
        print("\n📝 Log Files:")
        logs = self._check_logs()
        status['logs'] = logs
        for log in logs:
            print(f"  {log['name']}: {log['size']} ({log['lines']} lines)")

        # Check modules
        print("\n📦 Modules:")
        modules = self._check_modules()
        status['modules'] = modules
        for module, present in modules.items():
            print(f"  {'✓' if present else '✗'} {module}")

        return status

    # ========== Configuration Management ==========

    def config_show(self) -> None:
        """Show current configuration."""
        print("\n" + "=" * 80)
        print("CONFIGURATION")
        print("=" * 80)

        print("\n🔧 Core Settings:")
        print(f"  Signal CLI: {self.config.SIGNAL_CLI_PATH}")
        print(f"  Database: {self.config.DATABASE_PATH}")
        print(f"  Log Level: {self.config.LOG_LEVEL}")

        print("\n🌐 Web Server:")
        print(f"  Host: {self.config.WEB_HOST}")
        print(f"  Port: {self.config.WEB_PORT}")
        print(f"  Debug: {self.config.WEB_DEBUG}")

        print("\n🤖 AI Providers:")
        print(f"  Ollama: {self.config.OLLAMA_HOST}")
        if self.config.OPENAI_API_KEY:
            print(f"  OpenAI: Configured")
        if self.config.ANTHROPIC_API_KEY:
            print(f"  Anthropic: Configured")
        if self.config.GOOGLE_API_KEY:
            print(f"  Gemini: Configured")

        print("\n⚙️  Features:")
        print(f"  Sentiment Analysis: {self.config.ENABLE_SENTIMENT_ANALYSIS}")
        print(f"  Summarization: {self.config.ENABLE_SUMMARIZATION}")
        print(f"  Auto Response: {self.config.ENABLE_AUTO_RESPONSE}")
        print(f"  Group Monitoring: {self.config.ENABLE_GROUP_MONITORING}")

    def config_test(self) -> bool:
        """Test configuration and module imports."""
        print("\n" + "=" * 80)
        print("CONFIGURATION TEST")
        print("=" * 80)

        all_ok = True

        # Test module imports
        print("\n📦 Testing module imports...")
        modules = [
            ('config.settings', 'Configuration'),
            ('utils.common', 'Common utilities'),
            ('utils.logging', 'Logging'),
            ('models.database', 'Database'),
            ('services.setup', 'Setup service'),
            ('services.messaging', 'Messaging service'),
        ]

        for module_name, description in modules:
            try:
                __import__(module_name)
                print(f"  ✓ {description:20} ({module_name})")
            except ImportError as e:
                print(f"  ✗ {description:20} Error: {e}")
                all_ok = False

        # Test database connection
        print("\n💾 Testing database...")
        try:
            db = DatabaseManager()
            print(f"  ✓ Database connection successful")
        except Exception as e:
            print(f"  ✗ Database error: {e}")
            all_ok = False

        return all_ok

    # ========== Maintenance Operations ==========

    def cleanup(self, dry_run: bool = True) -> None:
        """Clean up old files and optimize database."""
        print("\n" + "=" * 80)
        print("CLEANUP" + (" (DRY RUN)" if dry_run else ""))
        print("=" * 80)

        # Clean old logs
        print("\n📝 Log files:")
        for log_file in Path('.').glob('*.log'):
            size = log_file.stat().st_size
            lines = sum(1 for _ in open(log_file))
            if lines > 10000:
                if dry_run:
                    print(f"  Would rotate: {log_file} ({format_file_size(size)}, {lines} lines)")
                else:
                    # Rotate log
                    backup = log_file.with_suffix('.log.old')
                    shutil.move(str(log_file), str(backup))
                    log_file.touch()
                    print(f"  Rotated: {log_file}")
            else:
                print(f"  Keeping: {log_file} ({format_file_size(size)}, {lines} lines)")

        # Clean old database entries
        print("\n💾 Database:")
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Count old messages
                cutoff_date = datetime.now() - timedelta(days=30)
                cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp < ?", (cutoff_date,))
                old_messages = cursor.fetchone()[0]

                if old_messages > 0:
                    if dry_run:
                        print(f"  Would delete {old_messages} messages older than 30 days")
                    else:
                        cursor.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_date,))
                        conn.commit()
                        print(f"  Deleted {old_messages} old messages")

                # Optimize database
                if not dry_run:
                    cursor.execute("VACUUM")
                    print("  Database optimized")
                else:
                    print("  Would optimize database")

        except Exception as e:
            print(f"  Database cleanup failed: {e}")

    def logs(self, follow: bool = False, lines: int = 20) -> None:
        """Show log files."""
        log_files = ['signal_service.log', 'web_server.log', 'signal_bot.log']

        if follow:
            # Follow logs in real-time
            cmd = f"tail -f {' '.join(log_files)}"
            subprocess.run(cmd, shell=True)
        else:
            # Show recent logs
            for log_file in log_files:
                if Path(log_file).exists():
                    print(f"\n=== {log_file} (last {lines} lines) ===")
                    subprocess.run(f"tail -n {lines} {log_file}", shell=True)

    def test(self) -> bool:
        """Run tests to verify system integrity."""
        print("\n" + "=" * 80)
        print("SYSTEM TESTS")
        print("=" * 80)

        all_tests_passed = True

        # Test 1: Module imports
        print("\n1. Module imports...")
        if self.config_test():
            print("  ✅ All modules load correctly")
        else:
            print("  ❌ Some modules failed to load")
            all_tests_passed = False

        # Test 2: Web interface
        print("\n2. Web interface...")
        try:
            import requests
            response = requests.get(f"http://localhost:{self.config.WEB_PORT}/", timeout=5)
            if response.status_code == 200:
                print("  ✅ Web interface accessible")
            else:
                print(f"  ❌ Web interface returned status {response.status_code}")
                all_tests_passed = False
        except:
            print("  ❌ Web interface not accessible")
            all_tests_passed = False

        # Test 3: Database operations
        print("\n3. Database operations...")
        try:
            db = DatabaseManager()
            # Test basic query
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                print(f"  ✅ Database query successful ({count} users)")
        except Exception as e:
            print(f"  ❌ Database test failed: {e}")
            all_tests_passed = False

        print("\n" + "=" * 80)
        if all_tests_passed:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed")

        return all_tests_passed

    # ========== Installation ==========

    def install_signal_cli(self) -> bool:
        """Install signal-cli."""
        print("\n" + "=" * 80)
        print("SIGNAL CLI INSTALLATION")
        print("=" * 80)

        # Check if already installed
        if self._check_signal_cli()['available']:
            print("✅ signal-cli is already installed")
            return True

        print("\nInstalling signal-cli...")

        version = "0.13.4"
        url = f"https://github.com/AsamK/signal-cli/releases/download/v{version}/signal-cli-{version}.tar.gz"

        commands = [
            f"wget {url}",
            f"sudo tar xf signal-cli-{version}.tar.gz -C /opt/",
            f"sudo ln -sf /opt/signal-cli-{version}/bin/signal-cli /usr/local/bin/",
            f"rm signal-cli-{version}.tar.gz"
        ]

        for cmd in commands:
            print(f"  Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True)
            if result.returncode != 0:
                print(f"  ❌ Failed: {result.stderr.decode()}")
                return False

        print("✅ signal-cli installed successfully")
        return True

    # ========== Helper Methods ==========

    def _start_signal_service(self, debug: bool = False) -> None:
        """Start the Signal polling service."""
        cmd = f"{self.python_cmd} signal_service.py --force"
        if debug:
            cmd += " --debug"

        # Prepare environment with debug settings
        env = os.environ.copy()
        if debug or self.debug_mode:
            env.update({
                'SIGNAL_SERVICE_DEBUG': '1',
                'SIGNAL_SERVICE_TRACE': '1',
                'SIGNAL_BOT_VERBOSE': '1'
            })

        self.debug_log(f"Starting signal_service.py", {
            'command': cmd,
            'env_vars': {k: v for k, v in env.items() if 'DEBUG' in k or 'SIGNAL' in k}
        })

        # Redirect output to debug log in debug mode
        if debug or self.debug_mode:
            debug_log_file = open('signal_bot_debug.log', 'a')
            process = subprocess.Popen(cmd, shell=True, stdout=debug_log_file, stderr=subprocess.STDOUT, env=env)
        else:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

        self.debug_log(f"Signal service started", {'pid': process.pid if hasattr(process, 'pid') else 'unknown'})
        time.sleep(2)

    def _start_signal_daemon(self, debug: bool = False) -> None:
        """Start the Signal daemon service (more reliable message handling)."""
        cmd = f"{self.python_cmd} signal_daemon_service.py --force"
        if debug:
            cmd += " --debug"

        # Prepare environment with debug settings
        env = os.environ.copy()
        if debug or self.debug_mode:
            env.update({
                'SIGNAL_SERVICE_DEBUG': '1',
                'SIGNAL_SERVICE_TRACE': '1',
                'SIGNAL_RPC_DEBUG': '1',
                'SIGNAL_RPC_TRACE': '1',
                'SIGNAL_BOT_VERBOSE': '1'
            })

        self.debug_log(f"Starting signal_daemon_service.py", {
            'command': cmd,
            'env_vars': {k: v for k, v in env.items() if 'DEBUG' in k or 'SIGNAL' in k}
        })

        # Redirect output to debug log in debug mode
        if debug or self.debug_mode:
            debug_log_file = open('signal_bot_debug.log', 'a')
            process = subprocess.Popen(cmd, shell=True, stdout=debug_log_file, stderr=subprocess.STDOUT, env=env)
        else:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

        self.debug_log(f"Signal daemon started", {'pid': process.pid if hasattr(process, 'pid') else 'unknown'})
        time.sleep(3)  # Daemon takes longer to initialize

    def _start_web_server(self, debug: bool = False) -> None:
        """Start the web server."""
        cmd = f"{self.python_cmd} web_server.py --host={self.config.WEB_HOST}"
        if debug:
            cmd += " --debug"

        # Prepare environment with debug settings
        env = os.environ.copy()
        if debug or self.debug_mode:
            env.update({
                'WEB_SERVER_DEBUG': '1',
                'WEB_SERVER_TRACE': '1',
                'FLASK_ENV': 'development',
                'FLASK_DEBUG': '1',
                'AI_SERVICE_DEBUG': '1',
                'AI_SERVICE_TRACE': '1'
            })

        self.debug_log(f"Starting web_server.py", {
            'command': cmd,
            'host': self.config.WEB_HOST,
            'port': self.config.WEB_PORT,
            'env_vars': {k: v for k, v in env.items() if 'DEBUG' in k or 'WEB' in k or 'FLASK' in k}
        })

        # Redirect output to debug log in debug mode
        if debug or self.debug_mode:
            debug_log_file = open('signal_bot_debug.log', 'a')
            process = subprocess.Popen(cmd, shell=True, stdout=debug_log_file, stderr=subprocess.STDOUT, env=env)
        else:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

        self.debug_log(f"Web server started", {'pid': process.pid if hasattr(process, 'pid') else 'unknown'})
        time.sleep(2)

    def _kill_process(self, pattern: str) -> None:
        """Kill processes matching pattern."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if pattern in cmdline:
                    print(f"  Stopping PID {proc.info['pid']}: {pattern}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
        except Exception as e:
            # Fallback to pkill
            subprocess.run(f"pkill -f '{pattern}'", shell=True, capture_output=True)

    def _get_processes(self) -> List[Dict]:
        """Get running Signal Bot processes."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(x in cmdline for x in ['signal_service.py', 'signal_daemon_service.py', 'web_server.py']):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': cmdline.split()[-1] if cmdline else proc.info['name'],
                        'memory': proc.info['memory_info'].rss / 1024 / 1024,  # MB
                        'cpu': proc.info['cpu_percent'] or 0
                    })
        except:
            # Fallback to ps
            result = subprocess.run("ps aux | grep -E 'signal_service|signal_daemon_service|web_server|signal_bot' | grep -v grep",
                                  shell=True, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    processes.append({
                        'pid': int(parts[1]),
                        'name': ' '.join(parts[10:]),
                        'memory': 0,
                        'cpu': 0
                    })
        return processes

    def _check_ports(self) -> List[Dict]:
        """Check which ports are in use."""
        ports = []
        for port in range(8080, 8090):
            try:
                result = subprocess.run(f"lsof -i:{port}", shell=True, capture_output=True, text=True)
                if result.stdout:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    if lines:
                        process = lines[0].split()[0]
                        ports.append({'port': port, 'process': process})
            except:
                pass
        return ports

    def _check_signal_cli(self) -> Dict:
        """Check if signal-cli is available."""
        signal_info = {'available': False, 'path': None, 'version': None}

        # Check common signal-cli paths
        paths = [
            '/opt/homebrew/bin/signal-cli',  # Homebrew on Apple Silicon Macs
            '/usr/local/bin/signal-cli',      # Homebrew on Intel Macs or Linux
            '/usr/bin/signal-cli',             # System package manager
            '/snap/bin/signal-cli'             # Snap package
        ]

        # Also check if signal-cli is in PATH
        try:
            result = subprocess.run(['which', 'signal-cli'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                path_from_which = result.stdout.strip()
                if path_from_which not in paths:
                    paths.insert(0, path_from_which)
        except Exception:
            pass

        # Also check the configured path from settings
        if self.config.SIGNAL_CLI_PATH and self.config.SIGNAL_CLI_PATH not in paths:
            paths.insert(0, self.config.SIGNAL_CLI_PATH)

        for path in paths:
            if Path(path).exists():
                signal_info['available'] = True
                signal_info['path'] = path
                try:
                    result = subprocess.run(f"{path} --version", shell=True,
                                         capture_output=True, text=True)
                    signal_info['version'] = result.stdout.strip().split()[-1]
                except:
                    signal_info['version'] = 'unknown'
                break

        return signal_info

    def _check_database(self) -> Dict:
        """Check database status."""
        db_path = self.config.DATABASE_PATH
        db_info = {'exists': False, 'path': db_path}

        if Path(db_path).exists():
            db_info['exists'] = True
            db_info['size'] = format_file_size(Path(db_path).stat().st_size)

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                db_info['tables'] = cursor.fetchone()[0]

                # Count records
                for table in ['users', 'groups', 'messages']:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    db_info[table] = cursor.fetchone()[0]

                conn.close()
            except:
                pass

        return db_info

    def _check_logs(self) -> List[Dict]:
        """Check log files."""
        logs = []
        for log_file in ['signal_service.log', 'web_server.log', 'signal_bot.log']:
            if Path(log_file).exists():
                stat = Path(log_file).stat()
                lines = sum(1 for _ in open(log_file))
                logs.append({
                    'name': log_file,
                    'size': format_file_size(stat.st_size),
                    'lines': lines
                })
        return logs

    def _check_modules(self) -> Dict[str, bool]:
        """Check which modules are present."""
        modules = {}
        for module in ['config', 'utils', 'services', 'models', 'web', 'docs']:
            modules[module] = Path(module).is_dir()
        return modules


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Signal Bot Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start services')
    start_parser.add_argument('service', nargs='?', choices=['signal', 'web'],
                            help='Specific service to start')
    start_parser.add_argument('--daemon', action='store_true',
                            help='Use daemon mode for Signal service (more reliable)')
    start_parser.add_argument('--debug', action='store_true',
                            help='Enable debug logging (shows DEBUG level messages)')

    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop services')
    stop_parser.add_argument('service', nargs='?', choices=['signal', 'web'],
                           help='Specific service to stop')

    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart services')
    restart_parser.add_argument('service', nargs='?', choices=['signal', 'web'],
                              help='Specific service to restart')
    restart_parser.add_argument('--daemon', action='store_true',
                              help='Use daemon mode for Signal service (more reliable)')
    restart_parser.add_argument('--debug', action='store_true',
                              help='Enable debug logging (shows DEBUG level messages)')

    # Status command
    subparsers.add_parser('status', help='Show status')

    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('action', nargs='?', default='show',
                             choices=['show', 'test'], help='Config action')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean old files')
    cleanup_parser.add_argument('--execute', action='store_true',
                              help='Actually perform cleanup (default is dry-run)')

    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show logs')
    logs_parser.add_argument('-f', '--follow', action='store_true',
                           help='Follow logs in real-time')
    logs_parser.add_argument('-n', '--lines', type=int, default=20,
                           help='Number of lines to show')

    # Test command
    subparsers.add_parser('test', help='Run system tests')

    # Install command
    subparsers.add_parser('install-signal-cli', help='Install signal-cli')

    args = parser.parse_args()

    # Initialize manager
    manager = SignalBotManager()

    # Execute command
    try:
        if args.command == 'start':
            manager.start(args.service, daemon_mode=args.daemon, debug=getattr(args, 'debug', False))
        elif args.command == 'stop':
            manager.stop(args.service)
        elif args.command == 'restart':
            manager.restart(args.service, daemon_mode=args.daemon, debug=getattr(args, 'debug', False))
        elif args.command == 'status':
            manager.status()
        elif args.command == 'config':
            if args.action == 'test':
                manager.config_test()
            else:
                manager.config_show()
        elif args.command == 'cleanup':
            manager.cleanup(dry_run=not args.execute)
        elif args.command == 'logs':
            manager.logs(follow=args.follow, lines=args.lines)
        elif args.command == 'test':
            manager.test()
        elif args.command == 'install-signal-cli':
            manager.install_signal_cli()
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()