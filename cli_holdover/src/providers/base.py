from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class ProviderType(Enum):
    CLAUDE = "claude"
    CHATGPT = "chatgpt" 
    OLLAMA = "ollama"

@dataclass
class Message:
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Any] = None

@dataclass
class ProviderResponse:
    content: str
    tool_calls: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

class BaseProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools: List[Tool] = []
    
    @abstractmethod
    async def chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> ProviderResponse:
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> AsyncIterator[str]:
        pass
    
    @abstractmethod
    def register_tool(self, tool: Tool) -> None:
        pass
    
    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        pass