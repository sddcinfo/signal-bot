"""
AI Provider Abstraction Layer

Provides a unified interface for different AI providers including:
- Gemini CLI (external service)
- Ollama (local LLM service)

This allows the signal bot to use either external or local AI services
for sentiment analysis and message summarization.
"""

import subprocess
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the AI provider is available and ready to use."""
        pass

    @abstractmethod
    def generate_response(self, prompt: str, timeout: int = 180) -> Dict[str, Any]:
        """
        Generate a response from the AI provider.

        Args:
            prompt: The prompt to send to the AI
            timeout: Request timeout in seconds

        Returns:
            Dict with 'success', 'response', and optional 'error' keys
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about this provider (version, models, etc.)."""
        pass


class GeminiProvider(AIProvider):
    """Gemini CLI provider (external service)."""

    def __init__(self, gemini_path: str = "gemini", logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.gemini_path = gemini_path

    def is_available(self) -> bool:
        """Check if Gemini CLI is available."""
        try:
            result = subprocess.run(
                [self.gemini_path, "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def generate_response(self, prompt: str, timeout: int = 180) -> Dict[str, Any]:
        """Generate response using Gemini CLI."""
        try:
            result = subprocess.run(
                [self.gemini_path, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0 and result.stdout:
                return {
                    'success': True,
                    'response': result.stdout.strip(),
                    'provider': 'gemini'
                }
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                return {
                    'success': False,
                    'error': f"Gemini CLI failed: {error_msg}",
                    'provider': 'gemini'
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "Gemini CLI timed out",
                'provider': 'gemini'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': "Gemini CLI not found",
                'provider': 'gemini'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'gemini'
            }

    def get_provider_name(self) -> str:
        return "Gemini CLI"

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            'name': 'Gemini CLI',
            'type': 'external',
            'command': self.gemini_path,
            'available': self.is_available()
        }


class OllamaProvider(AIProvider):
    """Ollama provider (local LLM service)."""

    def __init__(self, host: str = None, model: str = None, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        # Use provided host or fallback to localhost
        self.host = (host or "http://localhost:11434").rstrip('/')
        self.model = model or "llama3.2"
        self.api_url = f"{self.host}/api/generate"
        self.models_url = f"{self.host}/api/tags"
        self.ps_url = f"{self.host}/api/ps"

    def is_available(self) -> bool:
        """Check if Ollama service is available and model is installed."""
        try:
            # Check if Ollama service is running
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            # Check if our model is available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]

            # Check exact match or partial match (for versioned models)
            model_available = any(
                self.model == model_name or self.model in model_name
                for model_name in available_models
            )

            if not model_available:
                self.logger.warning(f"Model '{self.model}' not found. Available models: {available_models}")
                return False

            return True

        except Exception as e:
            self.logger.debug(f"Ollama availability check failed: {e}")
            return False

    def is_model_loaded(self) -> bool:
        """Check if the model is currently loaded in memory using /api/ps endpoint."""
        try:
            response = requests.get(self.ps_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                loaded_models = data.get('models', [])

                # Check if our model is in the loaded models list
                for loaded_model in loaded_models:
                    model_name = loaded_model.get('name', '')
                    # Check exact match or partial match (for versioned models)
                    if self.model == model_name or self.model in model_name:
                        self.logger.debug(f"Model {self.model} is already loaded")
                        return True

                self.logger.debug(f"Model {self.model} is not loaded. Loaded models: {[m.get('name') for m in loaded_models]}")
                return False

            return False

        except Exception as e:
            self.logger.debug(f"Failed to check loaded models: {e}")
            return False

    def ensure_model_loaded(self, timeout: int = 60) -> bool:
        """Check if the model is loaded and ready for inference."""
        # Just check if model is already loaded (fast check)
        return self.is_model_loaded()

    def generate_response(self, prompt: str, timeout: int = 180) -> Dict[str, Any]:
        """Generate response using Ollama API with intelligent model loading."""
        max_retries = 3
        retry_delay = 15  # seconds - longer delay for model loading

        for attempt in range(max_retries):
            # Check if model is already loaded (fast check)
            if self.is_model_loaded():
                self.logger.debug(f"Model {self.model} is already loaded, proceeding with inference")
            else:
                self.logger.info(f"Model {self.model} not loaded, will load during inference (attempt {attempt + 1}/{max_retries})")

            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "1h",  # Keep model loaded for 1 hour
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2000
                    }
                }

                # Send the actual user query - Ollama will load the model if needed
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=timeout,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': True,
                        'response': data.get('response', '').strip(),
                        'provider': 'ollama',
                        'model': self.model,
                        'stats': {
                            'eval_count': data.get('eval_count'),
                            'eval_duration': data.get('eval_duration'),
                            'total_duration': data.get('total_duration')
                        }
                    }
                elif response.status_code == 500:
                    # Handle model loading errors
                    try:
                        error_data = response.json()
                        if "llm server loading model" in error_data.get('error', ''):
                            if attempt < max_retries - 1:
                                self.logger.info(f"Model {self.model} is loading, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}...")
                                import time
                                time.sleep(retry_delay)
                                continue  # Retry with the same prompt
                            else:
                                return {
                                    'success': False,
                                    'error': f"Model {self.model} is still loading after {max_retries} attempts. Large models can take several minutes to load. Please try again later.",
                                    'provider': 'ollama'
                                }
                    except:
                        pass

                # Other errors - return immediately
                return {
                    'success': False,
                    'error': f"Ollama API error: {response.status_code} - {response.text}",
                    'provider': 'ollama'
                }

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Request timeout on attempt {attempt + 1}, retrying...")
                    continue
                return {
                    'success': False,
                    'error': "Ollama API timed out after multiple attempts",
                    'provider': 'ollama'
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Request failed on attempt {attempt + 1}: {e}, retrying...")
                    continue
                return {
                    'success': False,
                    'error': str(e),
                    'provider': 'ollama'
                }

        # This shouldn't be reached, but just in case
        return {
            'success': False,
            'error': f"Failed to get response from {self.model} after {max_retries} attempts",
            'provider': 'ollama'
        }

    def get_provider_name(self) -> str:
        return f"Ollama ({self.model})"

    def get_provider_info(self) -> Dict[str, Any]:
        """Get comprehensive Ollama provider information including loaded models."""
        info = {
            'name': 'Ollama',
            'type': 'local',
            'host': self.host,
            'model': self.model,
            'available': self.is_available()
        }

        # Get available models
        try:
            response = requests.get(self.models_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                available_models = data.get('models', [])
                info['available_models'] = [model['name'] for model in available_models]
                info['total_available_models'] = len(available_models)

                # Calculate total size of available models
                total_size = sum(model.get('size', 0) for model in available_models)
                info['total_models_size_gb'] = round(total_size / (1024**3), 2)
            else:
                info['available_models'] = []
                info['total_available_models'] = 0
                info['total_models_size_gb'] = 0
        except Exception:
            info['available_models'] = []
            info['total_available_models'] = 0
            info['total_models_size_gb'] = 0

        # Get currently loaded models with detailed information
        try:
            loaded_models = self.get_loaded_models()
            info['loaded_models'] = []
            info['loaded_models_count'] = len(loaded_models)

            total_vram = 0
            for model in loaded_models:
                model_info = {
                    'name': model.get('name'),
                    'size_gb': round(model.get('size', 0) / (1024**3), 2),
                    'size_vram_gb': round(model.get('size_vram', 0) / (1024**3), 2),
                    'parameter_size': model.get('details', {}).get('parameter_size'),
                    'quantization': model.get('details', {}).get('quantization_level'),
                    'format': model.get('details', {}).get('format'),
                    'family': model.get('details', {}).get('family'),
                    'context_length': model.get('context_length'),
                    'expires_at': model.get('expires_at'),
                    'is_current_model': model.get('name') == self.model
                }
                info['loaded_models'].append(model_info)
                total_vram += model.get('size_vram', 0)

            info['total_vram_usage_gb'] = round(total_vram / (1024**3), 2)
            info['current_model_loaded'] = self.is_model_loaded()

        except Exception as e:
            info['loaded_models'] = []
            info['loaded_models_count'] = 0
            info['total_vram_usage_gb'] = 0
            info['current_model_loaded'] = False
            info['error'] = f"Failed to get loaded models: {str(e)}"

        return info

    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(self.models_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception:
            return []

    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded models with details."""
        try:
            response = requests.get(self.ps_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
        except Exception as e:
            self.logger.debug(f"Failed to get loaded models: {e}")
            return []

    def preload_model(self, timeout: int = 180) -> Dict[str, Any]:
        """Preload the model to ensure it's ready for inference."""
        self.logger.info(f"Preloading model {self.model}...")

        # Check if already loaded
        if self.is_model_loaded():
            self.logger.info(f"Model {self.model} is already loaded")
            return {
                'success': True,
                'message': f"Model {self.model} is already loaded and ready",
                'model': self.model
            }

        try:
            # Send a minimal request to trigger model loading
            payload = {
                "model": self.model,
                "prompt": "Hello",
                "stream": False,
                "keep_alive": "1h",  # Keep model loaded for 1 hour
                "options": {
                    "num_predict": 1
                }
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                self.logger.info(f"Model {self.model} loaded successfully")
                return {
                    'success': True,
                    'message': f"Model {self.model} loaded and ready",
                    'model': self.model
                }
            else:
                error_text = response.text
                if response.status_code == 500:
                    try:
                        error_data = response.json()
                        if "llm server loading model" in error_data.get('error', ''):
                            return {
                                'success': False,
                                'error': f"Model {self.model} is currently loading. This can take several minutes for large models.",
                                'model': self.model
                            }
                    except:
                        pass

                return {
                    'success': False,
                    'error': f"Failed to load model {self.model}: {error_text}",
                    'model': self.model
                }

        except Exception as e:
            self.logger.error(f"Error preloading model {self.model}: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': self.model
            }


class AIProviderManager:
    """Manages multiple AI providers with fallback support."""

    def __init__(self, db_manager=None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.db = db_manager
        self.providers: List[AIProvider] = []
        self._load_providers_from_config()

    def _load_providers_from_config(self):
        """Load providers from configuration or use defaults."""
        if self.db:
            # Try to load settings from database
            ollama_host = self.db.get_config('ai.ollama.host')
            ollama_model = self.db.get_config('ai.ollama.model')
            ollama_enabled = self.db.get_config('ai.ollama.enabled', 'true').lower() == 'true'

            gemini_path = self.db.get_config('ai.gemini.path', 'gemini')
            gemini_enabled = self.db.get_config('ai.gemini.enabled', 'true').lower() == 'true'

            # Add providers based on configuration
            if ollama_enabled and ollama_host:
                self.logger.info(f"Loading Ollama provider with host: {ollama_host}")
                self.providers.append(OllamaProvider(
                    host=ollama_host,
                    model=ollama_model,
                    logger=self.logger
                ))
            elif ollama_enabled:
                # Try default Ollama if enabled but not configured
                self.providers.append(OllamaProvider(logger=self.logger))

            if gemini_enabled:
                self.providers.append(GeminiProvider(
                    gemini_path=gemini_path,
                    logger=self.logger
                ))
        else:
            # No database, use defaults
            self._setup_default_providers()

    def _setup_default_providers(self):
        """Setup default providers when no configuration exists."""
        # Try Ollama first (local, faster, private)
        self.providers.append(OllamaProvider(logger=self.logger))

        # Fallback to Gemini (external, requires internet)
        self.providers.append(GeminiProvider(logger=self.logger))

    def add_provider(self, provider: AIProvider):
        """Add a custom provider."""
        self.providers.append(provider)

    def get_available_provider(self) -> Optional[AIProvider]:
        """Get the first available provider."""
        for provider in self.providers:
            if provider.is_available():
                self.logger.info(f"Using AI provider: {provider.get_provider_name()}")
                return provider

        self.logger.warning("No AI providers are available")
        return None

    def generate_response(self, prompt: str, timeout: int = 180) -> Dict[str, Any]:
        """Generate response using the first available provider."""
        provider = self.get_available_provider()

        if not provider:
            return {
                'success': False,
                'error': 'No AI providers available',
                'provider': 'none'
            }

        result = provider.generate_response(prompt, timeout)

        # Add provider type information for privacy decisions
        if isinstance(provider, OllamaProvider):
            result['provider_type'] = 'local'
            result['is_local'] = True
        elif isinstance(provider, GeminiProvider):
            result['provider_type'] = 'external'
            result['is_local'] = False
        else:
            result['provider_type'] = 'unknown'
            result['is_local'] = False

        return result

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {
            'providers': [],
            'active_provider': None,
            'configuration': {}
        }

        for provider in self.providers:
            provider_info = provider.get_provider_info()
            status['providers'].append(provider_info)

            if provider_info['available'] and status['active_provider'] is None:
                status['active_provider'] = provider_info['name']

        # Add current configuration
        if self.db:
            status['configuration'] = {
                'ollama': {
                    'host': self.db.get_config('ai.ollama.host'),
                    'model': self.db.get_config('ai.ollama.model'),
                    'enabled': self.db.get_config('ai.ollama.enabled', 'true')
                },
                'gemini': {
                    'path': self.db.get_config('ai.gemini.path', 'gemini'),
                    'enabled': self.db.get_config('ai.gemini.enabled', 'true')
                }
            }

        return status

    def reload_configuration(self):
        """Reload AI provider configuration from database."""
        self.logger.info("Reloading AI provider configuration")
        self.providers.clear()
        self._load_providers_from_config()

    def save_configuration(self, ollama_host: str = None, ollama_model: str = None,
                          ollama_enabled: bool = True, gemini_path: str = 'gemini',
                          gemini_enabled: bool = True):
        """Save AI provider configuration to database."""
        if not self.db:
            self.logger.error("Cannot save configuration without database manager")
            return False

        try:
            if ollama_host:
                self.db.set_config('ai.ollama.host', ollama_host)
            if ollama_model:
                self.db.set_config('ai.ollama.model', ollama_model)
            self.db.set_config('ai.ollama.enabled', str(ollama_enabled).lower())

            self.db.set_config('ai.gemini.path', gemini_path)
            self.db.set_config('ai.gemini.enabled', str(gemini_enabled).lower())

            # Reload configuration after saving
            self.reload_configuration()
            return True

        except Exception as e:
            self.logger.error(f"Failed to save AI configuration: {e}")
            return False


# Global AI provider manager instance (initialized lazily)
ai_manager = None


def initialize_ai_manager(db_manager=None, logger=None):
    """Initialize the global AI provider manager."""
    global ai_manager
    ai_manager = AIProviderManager(db_manager=db_manager, logger=logger)
    return ai_manager


def get_ai_manager():
    """Get the global AI provider manager, creating if necessary."""
    global ai_manager
    if ai_manager is None:
        ai_manager = AIProviderManager()
    return ai_manager


def get_ai_response(prompt: str, timeout: int = 180) -> Dict[str, Any]:
    """
    Convenience function to get AI response using the global manager.

    Args:
        prompt: The prompt to send to AI
        timeout: Request timeout in seconds

    Returns:
        Dict with response data and metadata
    """
    return get_ai_manager().generate_response(prompt, timeout)


def get_ai_status() -> Dict[str, Any]:
    """Get status of all AI providers."""
    return get_ai_manager().get_provider_status()


def save_ai_configuration(ollama_host: str = None, ollama_model: str = None,
                         ollama_enabled: bool = True, gemini_path: str = 'gemini',
                         gemini_enabled: bool = True):
    """Save AI configuration and reload providers."""
    return get_ai_manager().save_configuration(
        ollama_host=ollama_host,
        ollama_model=ollama_model,
        ollama_enabled=ollama_enabled,
        gemini_path=gemini_path,
        gemini_enabled=gemini_enabled
    )