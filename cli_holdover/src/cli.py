import asyncio
import click
import json
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .providers.base import BaseProvider, Message, ProviderType
from .providers.claude import ClaudeProvider
from .providers.openai import OpenAIProvider
from .providers.ollama import OllamaProvider
from .tools.registry import ToolRegistry
from .config import Config

console = Console()

class MultiProviderCLI:
    def __init__(self):
        self.config = Config()
        self.current_provider: Optional[BaseProvider] = None
        self.tool_registry = ToolRegistry()
        self.conversation_history: list[Message] = []
    
    def get_provider(self, provider_type: str, config: Dict[str, Any]) -> BaseProvider:
        """Factory method to create providers"""
        if provider_type == "claude":
            return ClaudeProvider(config)
        elif provider_type == "chatgpt":
            return OpenAIProvider(config)
        elif provider_type == "ollama":
            return OllamaProvider(config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    async def switch_provider(self, provider_type: str) -> bool:
        """Switch to a different AI provider"""
        try:
            provider_config = self.config.get_provider_config(provider_type)
            if not provider_config:
                console.print(f"[red]No configuration found for {provider_type}[/red]")
                return False
            
            provider = self.get_provider(provider_type, provider_config)
            
            # Validate provider connection
            if not await provider.validate_config():
                console.print(f"[red]Failed to validate {provider_type} configuration[/red]")
                return False
            
            self.current_provider = provider
            console.print(f"[green]Switched to {provider_type} provider[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error switching to {provider_type}: {e}[/red]")
            return False
    
    async def chat_interactive(self):
        """Interactive chat session"""
        if not self.current_provider:
            console.print("[red]No provider selected. Use --provider to select one.[/red]")
            return
        
        console.print(f"[green]Interactive mode with {self.current_provider.get_provider_type().value}[/green]")
        console.print("[dim]Type 'exit' to quit, '/help' for commands[/dim]\n")
        
        while True:
            try:
                user_input = Prompt.ask("[bold blue]You")
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.startswith('/'):
                    await self._handle_command(user_input)
                    continue
                
                # Add user message to history
                self.conversation_history.append(Message(role="user", content=user_input))
                
                # Get available tools
                tools = self.tool_registry.get_all_tools()
                
                # Stream response
                console.print("[bold green]Assistant:[/bold green]", end="")
                full_response = ""
                
                async for chunk in self.current_provider.stream_chat(
                    self.conversation_history, 
                    tools=tools
                ):
                    console.print(chunk, end="")
                    full_response += chunk
                
                console.print()  # New line after response
                
                # Add assistant response to history
                self.conversation_history.append(Message(role="assistant", content=full_response))
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted by user[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
    
    async def _handle_command(self, command: str):
        """Handle special commands in interactive mode"""
        if command == "/help":
            help_text = """
**Available Commands:**
- `/help` - Show this help message
- `/clear` - Clear conversation history
- `/provider <name>` - Switch provider (claude, chatgpt, ollama)
- `/status` - Show current provider and configuration
- `/tools` - List available tools
            """
            console.print(Panel(Markdown(help_text), title="Help"))
            
        elif command == "/clear":
            self.conversation_history.clear()
            console.print("[green]Conversation history cleared[/green]")
            
        elif command.startswith("/provider "):
            provider_name = command.split(" ", 1)[1]
            await self.switch_provider(provider_name)
            
        elif command == "/status":
            if self.current_provider:
                provider_type = self.current_provider.get_provider_type().value
                console.print(f"[green]Current provider: {provider_type}[/green]")
            else:
                console.print("[red]No provider selected[/red]")
                
        elif command == "/tools":
            tools = self.tool_registry.get_all_tools()
            if tools:
                tool_list = "\n".join([f"- **{t.name}**: {t.description}" for t in tools])
                console.print(Panel(Markdown(tool_list), title="Available Tools"))
            else:
                console.print("[yellow]No tools available[/yellow]")
                
        else:
            console.print(f"[red]Unknown command: {command}[/red]")

@click.group()
def cli():
    """Multi-provider AI CLI agent similar to Claude Code"""
    pass

@cli.command()
@click.option("--provider", "-p", default="claude", help="AI provider to use (claude, chatgpt, ollama)")
@click.option("--model", "-m", help="Model to use (provider-specific)")
@click.option("--config", "-c", help="Configuration file path")
def chat(provider: str, model: Optional[str], config: Optional[str]):
    """Start interactive chat session"""
    async def run_chat():
        app = MultiProviderCLI()
        
        if config:
            app.config.load_from_file(config)
        
        # Override model if specified
        if model:
            provider_config = app.config.get_provider_config(provider)
            if provider_config:
                provider_config["model"] = model
        
        if await app.switch_provider(provider):
            await app.chat_interactive()
    
    asyncio.run(run_chat())

@cli.command()
@click.argument("prompt")
@click.option("--provider", "-p", default="claude", help="AI provider to use")
@click.option("--stream/--no-stream", default=True, help="Stream response")
def ask(prompt: str, provider: str, stream: bool):
    """Ask a single question"""
    async def run_ask():
        app = MultiProviderCLI()
        
        if await app.switch_provider(provider):
            messages = [Message(role="user", content=prompt)]
            
            if stream:
                async for chunk in app.current_provider.stream_chat(messages):
                    console.print(chunk, end="")
                console.print()
            else:
                response = await app.current_provider.chat(messages)
                console.print(response.content)
    
    asyncio.run(run_ask())

@cli.command()
def configure():
    """Configure providers and settings"""
    config = Config()
    config.interactive_setup()
    console.print("[green]Configuration completed![/green]")

@cli.command()
def status():
    """Show current configuration and provider status"""
    async def run_status():
        app = MultiProviderCLI()
        
        console.print("[bold]Provider Status:[/bold]")
        
        for provider_name in ["claude", "chatgpt", "ollama"]:
            config = app.config.get_provider_config(provider_name)
            if config:
                try:
                    provider = app.get_provider(provider_name, config)
                    is_valid = await provider.validate_config()
                    status_color = "green" if is_valid else "red"
                    status_text = "✓ Connected" if is_valid else "✗ Connection failed"
                    console.print(f"  {provider_name}: [{status_color}]{status_text}[/{status_color}]")
                except Exception as e:
                    console.print(f"  {provider_name}: [red]✗ Error: {e}[/red]")
            else:
                console.print(f"  {provider_name}: [dim]Not configured[/dim]")
    
    asyncio.run(run_status())

if __name__ == "__main__":
    cli()