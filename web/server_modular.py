"""
Modular Web Server for Signal Bot

This module provides the ModularWebServer class that uses the new modular architecture
with shared templates and individual page modules.
"""

# Import the ModularWebServer from the main server module
from .server import ModularWebServer, start_modular_server

# Re-export for easier access
__all__ = ['ModularWebServer', 'start_modular_server']