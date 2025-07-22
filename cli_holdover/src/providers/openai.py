import json
from typing import Dict, Any, List, Optional, AsyncIterator
from openai import AsyncOpenAI
from .base import BaseProvider, Message, Tool, ProviderResponse, ProviderType

class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url")
        )
        self.model = config.get("model", "gpt-4-turbo-preview")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.CHATGPT
    
    async def validate_config(self) -> bool:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False
    
    def register_tool(self, tool: Tool) -> None:
        self.tools.append(tool)
    
    def _convert_tools_to_openai_format(self, tools: Optional[List[Tool]]) -> List[Dict[str, Any]]:
        if not tools:
            return []
        
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return openai_tools
    
    def _convert_messages_to_openai_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        return openai_messages
    
    async def chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> ProviderResponse:
        openai_messages = self._convert_messages_to_openai_format(messages)
        openai_tools = self._convert_tools_to_openai_format(tools or self.tools)
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": openai_messages
        }
        
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"
        
        response = await self.client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        content = message.content or ""
        tool_calls = []
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                })
        
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            metadata={
                "usage": response.usage.dict() if response.usage else None,
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason
            }
        )
    
    async def stream_chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> AsyncIterator[str]:
        openai_messages = self._convert_messages_to_openai_format(messages)
        openai_tools = self._convert_tools_to_openai_format(tools or self.tools)
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": openai_messages,
            "stream": True
        }
        
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"
        
        response = await self.client.chat.completions.create(**kwargs)
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content