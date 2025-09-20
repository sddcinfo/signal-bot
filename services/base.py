"""
Base Service Class

Provides a common foundation for all service classes in the Signal Bot application.
"""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from config.settings import Config
from utils.logging import setup_logger, get_logger
from utils.decorators import handle_errors
from models.database import DatabaseManager


class BaseService(ABC):
    """
    Abstract base class for all services.

    This class provides common functionality for all services including:
    - Standardized initialization
    - Consistent logging setup
    - Database connection management
    - Configuration access
    - Error handling patterns

    Attributes:
        db: Database manager instance
        config: Configuration object
        logger: Service-specific logger
        _initialized: Flag indicating if service is initialized

    Examples:
        >>> class MyService(BaseService):
        ...     def initialize(self):
        ...         self.my_setting = self.config.get('MY_SETTING')
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        logger: Optional[logging.Logger] = None,
        config: Optional[Config] = None,
        service_name: Optional[str] = None
    ):
        """
        Initialize the base service.

        Args:
            db: Database manager instance (creates new if None)
            logger: Logger instance (creates new if None)
            config: Configuration object (uses default if None)
            service_name: Service name for logging (uses class name if None)
        """
        # Service identification
        self.service_name = service_name or self.__class__.__name__

        # Setup configuration
        self.config = config or Config()

        # Setup logging
        if logger:
            self.logger = logger
        else:
            log_file = self._get_log_file()
            self.logger = setup_logger(
                name=f"{__name__}.{self.service_name}",
                log_file=log_file,
                level=self.config.LOG_LEVEL
            )

        # Setup database
        if db:
            self.db = db
        else:
            try:
                self.db = DatabaseManager(logger=self.logger)
                self.logger.info(f"{self.service_name} initialized with database")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                self.db = None

        # Track initialization state
        self._initialized = False

        # Call child class initialization
        try:
            self.initialize()
            self._initialized = True
            self.logger.info(f"{self.service_name} service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.service_name}: {e}")
            raise

    def _get_log_file(self) -> Optional[str]:
        """
        Get the appropriate log file path for this service.

        Returns:
            Log file path or None
        """
        # Map service names to log files
        log_file_map = {
            'SignalService': self.config.SIGNAL_SERVICE_LOG_FILE,
            'WebServer': self.config.WEB_SERVER_LOG_FILE,
            'SignalBot': self.config.SIGNAL_BOT_LOG_FILE,
        }

        # Check for exact match first
        if self.service_name in log_file_map:
            return log_file_map[self.service_name]

        # Check for partial matches
        for key, value in log_file_map.items():
            if key.lower() in self.service_name.lower():
                return value

        # Default to service-specific file
        return f"{self.service_name.lower()}.log"

    @abstractmethod
    def initialize(self):
        """
        Initialize service-specific components.

        This method must be implemented by child classes to perform
        any service-specific initialization.

        Raises:
            NotImplementedError: If not implemented by child class
        """
        pass

    @handle_errors(default_return=False, log_errors=True)
    def is_healthy(self) -> bool:
        """
        Check if the service is healthy and operational.

        Returns:
            True if healthy, False otherwise
        """
        if not self._initialized:
            return False

        # Check database connection if used
        if self.db:
            try:
                # Simple query to test connection
                self.db.get_config('health_check')
                return True
            except Exception:
                return False

        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status.

        Returns:
            Dictionary containing service status information
        """
        return {
            'service': self.service_name,
            'initialized': self._initialized,
            'healthy': self.is_healthy(),
            'database_connected': self.db is not None,
            'config': {
                'log_level': self.config.LOG_LEVEL,
                'debug': self.config.WEB_DEBUG if hasattr(self.config, 'WEB_DEBUG') else False,
            }
        }

    def reload_config(self):
        """Reload configuration from environment or files."""
        self.config = Config()
        self.logger.info(f"{self.service_name} configuration reloaded")

        # Update logger level if changed
        new_level = getattr(logging, self.config.LOG_LEVEL)
        self.logger.setLevel(new_level)
        for handler in self.logger.handlers:
            handler.setLevel(new_level)

    def shutdown(self):
        """
        Gracefully shutdown the service.

        This method should be called when the service is being stopped
        to ensure proper cleanup of resources.
        """
        self.logger.info(f"Shutting down {self.service_name}")

        # Close database connection if exists
        if self.db:
            try:
                # The database manager should handle its own cleanup
                pass
            except Exception as e:
                self.logger.error(f"Error closing database: {e}")

        self._initialized = False
        self.logger.info(f"{self.service_name} shutdown complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()
        return False


class SingletonService(BaseService):
    """
    Base class for singleton services.

    Services that should only have one instance running at a time
    should inherit from this class.

    This is useful for services that manage system resources or
    maintain global state.
    """

    _instances = {}

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance.

        Returns:
            The singleton instance of this service
        """
        if cls not in cls._instances:
            return None
        return cls._instances[cls]

    @classmethod
    def clear_instance(cls):
        """Clear the singleton instance (useful for testing)."""
        if cls in cls._instances:
            instance = cls._instances[cls]
            if hasattr(instance, 'shutdown'):
                instance.shutdown()
            del cls._instances[cls]