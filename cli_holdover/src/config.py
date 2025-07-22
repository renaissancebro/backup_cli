import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()

class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.data: Dict[str, Any] = {}
        self.load()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        home = Path.home()
        config_dir = home / ".aicli"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "config.json")
    
    def load(self) -> None:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.data = json.load(f)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
            self.data = {}
    
    def load_from_file(self, file_path: str) -> None:
        """Load configuration from specific file"""
        self.config_path = file_path
        self.load()
    
    def save(self) -> None:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
    
    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider"""
        return self.data.get("providers", {}).get(provider)
    
    def set_provider_config(self, provider: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific provider"""
        if "providers" not in self.data:
            self.data["providers"] = {}
        self.data["providers"][provider] = config
        self.save()
    
    def interactive_setup(self) -> None:
        """Interactive configuration setup"""
        console.print("[bold]AI CLI Configuration Setup[/bold]")
        console.print("Configure your AI providers. You can skip any provider by leaving fields empty.\n")
        
        # Claude configuration
        if Confirm.ask("Configure Claude provider?", default=True):
            self._configure_claude()
        
        # ChatGPT configuration
        if Confirm.ask("Configure ChatGPT provider?", default=False):
            self._configure_chatgpt()
        
        # Ollama configuration
        if Confirm.ask("Configure Ollama provider?", default=False):
            self._configure_ollama()
        
        self.save()
    
    def _configure_claude(self) -> None:
        """Configure Claude provider"""
        console.print("\n[bold blue]Claude Configuration[/bold blue]")
        
        api_key = Prompt.ask("Claude API key", password=True)
        if not api_key:
            return
        
        model = Prompt.ask(
            "Model", 
            default="claude-3-5-sonnet-20241022",
            choices=[
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022", 
                "claude-3-opus-20240229"
            ]
        )
        
        max_tokens = int(Prompt.ask("Max tokens", default="4096"))
        
        base_url = Prompt.ask("Base URL (optional)", default="")
        
        config = {
            "api_key": api_key,
            "model": model,
            "max_tokens": max_tokens
        }
        
        if base_url:
            config["base_url"] = base_url
        
        # MCP servers configuration
        if Confirm.ask("Configure MCP servers?", default=False):
            config["mcp_servers"] = self._configure_mcp_servers()
        
        self.set_provider_config("claude", config)
        console.print("[green]✓ Claude configured[/green]")
    
    def _configure_chatgpt(self) -> None:
        """Configure ChatGPT provider"""
        console.print("\n[bold blue]ChatGPT Configuration[/bold blue]")
        
        api_key = Prompt.ask("OpenAI API key", password=True)
        if not api_key:
            return
        
        model = Prompt.ask(
            "Model",
            default="gpt-4-turbo-preview",
            choices=[
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
        )
        
        max_tokens = int(Prompt.ask("Max tokens", default="4096"))
        temperature = float(Prompt.ask("Temperature", default="0.7"))
        
        base_url = Prompt.ask("Base URL (optional)", default="")
        
        config = {
            "api_key": api_key,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if base_url:
            config["base_url"] = base_url
        
        self.set_provider_config("chatgpt", config)
        console.print("[green]✓ ChatGPT configured[/green]")
    
    def _configure_ollama(self) -> None:
        """Configure Ollama provider"""
        console.print("\n[bold blue]Ollama Configuration[/bold blue]")
        
        base_url = Prompt.ask("Ollama base URL", default="http://localhost:11434")
        model = Prompt.ask("Model", default="llama2")
        timeout = int(Prompt.ask("Timeout (seconds)", default="120"))
        
        config = {
            "base_url": base_url,
            "model": model,
            "timeout": timeout,
            "options": {}
        }
        
        self.set_provider_config("ollama", config)
        console.print("[green]✓ Ollama configured[/green]")
    
    def _configure_mcp_servers(self) -> list:
        """Configure MCP servers for Claude"""
        servers = []
        
        while Confirm.ask("Add MCP server?", default=False):
            name = Prompt.ask("Server name")
            command = Prompt.ask("Command")
            args = Prompt.ask("Arguments (comma-separated)", default="")
            
            server_config = {
                "name": name,
                "command": command,
                "args": [arg.strip() for arg in args.split(",") if arg.strip()]
            }
            
            servers.append(server_config)
        
        return servers