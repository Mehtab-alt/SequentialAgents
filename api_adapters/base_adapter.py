# api_adapters/base_adapter.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator

class BaseAPIAdapter(ABC):
    """Abstract base class for API adapters, defining a common interface."""
    @abstractmethod
    def build_request_config(self, config: 'ConfigManager', messages: List[Dict], stream: bool) -> Dict:
        """Builds the full request configuration (url, headers, data)."""
        pass

    @abstractmethod
    def parse_response(self, response_data: Dict) -> Dict:
        """Parses a complete, non-streaming JSON response from the API."""
        pass

    @abstractmethod
    async def parse_stream(self, response_stream: 'aiohttp.StreamReader') -> AsyncGenerator[str, None]:
        """Asynchronously parses a streaming API response."""
        pass
