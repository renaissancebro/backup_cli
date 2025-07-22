import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from anthropic import AsyncAnthropic
from .base import BaseProvider, Message, Tool, ProviderResponse, ProviderType

class ClaudeProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.get("api_key"),
            base_url=config.get("base_url")
        )
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.max_tokens = config.get("max_tokens", 4096)
        self.mcp_servers = config.get("mcp_servers", [])
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.CLAUDE
    
    async def validate_config(self) -> bool:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False
    
    def register_tool(self, tool: Tool) -> None:
        self.tools.append(tool)
    
    def _convert_tools_to_anthropic_format(self, tools: Optional[List[Tool]]) -> List[Dict[str, Any]]:
        if not tools:
            return []
        
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            })
        return anthropic_tools
    
    def _convert_messages_to_anthropic_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        return anthropic_messages
    
    async def chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> ProviderResponse:
        anthropic_messages = self._convert_messages_to_anthropic_format(messages)
        anthropic_tools = self._convert_tools_to_anthropic_format(tools or self.tools)
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages
        }
        
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        
        response = await self.client.messages.create(**kwargs)
        
        content = ""
        tool_calls = []
        
        for content_block in response.content:
            if content_block.type == "text":
                content += content_block.text
            elif content_block.type == "tool_use":
                tool_calls.append({
                    "id": content_block.id,
                    "name": content_block.name,
                    "arguments": content_block.input
                })
        
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            metadata={
                "usage": response.usage.dict() if hasattr(response, 'usage') else None,
                "model": response.model,
                "stop_reason": response.stop_reason
            }
        )
    
    async def stream_chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> AsyncIterator[str]:
        anthropic_messages = self._convert_messages_to_anthropic_format(messages)
        anthropic_tools = self._convert_tools_to_anthropic_format(tools or self.tools)
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages,
            "stream": True
        }
        
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        
        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield event.delta.text
    
    async def connect_mcp_servers(self):
        """Connect to configured MCP servers for external data access"""
        # This would implement MCP protocol connections
        # For now, placeholder for MCP integration
        pass