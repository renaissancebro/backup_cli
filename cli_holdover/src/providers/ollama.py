import json
import httpx
from typing import Dict, Any, List, Optional, AsyncIterator
from .base import BaseProvider, Message, Tool, ProviderResponse, ProviderType
from ..ssh_tunnel import SSHTunnel, SSHConfig

class OllamaProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama2")
        self.timeout = config.get("timeout", 120)
        self.options = config.get("options", {})
        self.ssh_tunnel: Optional[SSHTunnel] = None
        
        # Set up SSH tunnel if configured
        ssh_config = config.get("ssh")
        if ssh_config:
            self._setup_ssh_tunnel(ssh_config)
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    async def validate_config(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def register_tool(self, tool: Tool) -> None:
        self.tools.append(tool)
    
    def _convert_messages_to_ollama_format(self, messages: List[Message]) -> str:
        # Ollama typically uses a single prompt format
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"Human: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    async def chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> ProviderResponse:
        prompt = self._convert_messages_to_ollama_format(messages)
        
        # Add tool information to prompt if tools are available
        if tools or self.tools:
            available_tools = tools or self.tools
            tool_descriptions = []
            for tool in available_tools:
                tool_descriptions.append(f"- {tool.name}: {tool.description}")
            
            tool_prompt = f"\n\nAvailable tools:\n{chr(10).join(tool_descriptions)}\n\nIf you need to use a tool, respond with JSON format: {{\"tool_call\": {{\"name\": \"tool_name\", \"arguments\": {{...}}}}}}"
            prompt += tool_prompt
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.options
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
        
        content = result.get("response", "")
        tool_calls = []
        
        # Try to parse tool calls from response
        try:
            if content.strip().startswith("{") and "tool_call" in content:
                tool_data = json.loads(content)
                if "tool_call" in tool_data:
                    tool_calls.append({
                        "id": f"call_{hash(content)}",
                        "name": tool_data["tool_call"]["name"],
                        "arguments": tool_data["tool_call"]["arguments"]
                    })
                    content = ""  # Clear content if it's a tool call
        except json.JSONDecodeError:
            pass  # Not a tool call, keep as regular content
        
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            metadata={
                "model": result.get("model"),
                "created_at": result.get("created_at"),
                "done": result.get("done")
            }
        )
    
    async def stream_chat(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> AsyncIterator[str]:
        prompt = self._convert_messages_to_ollama_format(messages)
        
        if tools or self.tools:
            available_tools = tools or self.tools
            tool_descriptions = []
            for tool in available_tools:
                tool_descriptions.append(f"- {tool.name}: {tool.description}")
            
            tool_prompt = f"\n\nAvailable tools:\n{chr(10).join(tool_descriptions)}\n\nIf you need to use a tool, respond with JSON format: {{\"tool_call\": {{\"name\": \"tool_name\", \"arguments\": {{...}}}}}}"
            prompt += tool_prompt
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": self.options
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            continue
    
    def _setup_ssh_tunnel(self, ssh_config: Dict[str, Any]) -> None:
        """Set up SSH tunnel for remote Ollama access"""
        config = SSHConfig(
            host=ssh_config["host"],
            port=ssh_config.get("port", 22),
            username=ssh_config.get("username"),
            key_file=ssh_config.get("key_file"),
            local_port=ssh_config.get("local_port"),
            remote_port=ssh_config.get("remote_port", 11434),
            remote_host=ssh_config.get("remote_host", "localhost")
        )
        
        self.ssh_tunnel = SSHTunnel(config)
        if self.ssh_tunnel.start():
            # Update base_url to use the tunnel
            self.base_url = self.ssh_tunnel.get_local_url()
        else:
            raise ConnectionError(f"Failed to establish SSH tunnel to {config.host}")
    
    def close_ssh_tunnel(self) -> None:
        """Close the SSH tunnel if active"""
        if self.ssh_tunnel:
            self.ssh_tunnel.stop()
            self.ssh_tunnel = None
    
    def __del__(self):
        """Cleanup SSH tunnel on deletion"""
        self.close_ssh_tunnel()