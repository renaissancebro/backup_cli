# Multi-Provider AI CLI Agent

A CLI tool similar to Claude Code that supports multiple AI providers including Claude (with MCP support), ChatGPT, and Ollama. Switch between providers seamlessly while maintaining the same powerful toolset for code generation, file operations, and command execution.

## Features

- **Multiple AI Providers**: Switch between Claude, ChatGPT, and Ollama
- **Interactive Chat Mode**: Real-time conversations with streaming responses
- **Built-in Tools**: File operations, command execution, search capabilities
- **MCP Support**: Model Context Protocol integration for Claude (external data sources)
- **Provider Switching**: Change AI providers mid-conversation
- **Configuration Management**: Easy setup and provider configuration
- **Rich CLI Interface**: Beautiful terminal interface with syntax highlighting

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd multi-provider-ai-cli
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Quick Start

1. **Configure your providers:**
```bash
python main.py configure
```

2. **Start interactive chat:**
```bash
python main.py chat
```

3. **Ask a quick question:**
```bash
python main.py ask "Explain Python decorators"
```

## Usage

### Commands

#### Interactive Chat
Start a conversation with your AI provider:
```bash
python main.py chat --provider claude
python main.py chat --provider chatgpt
python main.py chat --provider ollama
```

#### One-off Questions
Ask a single question without starting interactive mode:
```bash
python main.py ask "How do I create a REST API in Python?" --provider claude
```

#### Configuration
Set up your API keys and provider settings:
```bash
python main.py configure
```

#### Status Check
Verify your provider configurations:
```bash
python main.py status
```

### Interactive Commands

Within chat mode, use these commands:
- `/help` - Show available commands
- `/provider <name>` - Switch providers (claude, chatgpt, ollama)
- `/clear` - Clear conversation history
- `/status` - Show current provider
- `/tools` - List available tools
- `exit` or `quit` - Exit chat mode

### Configuration

The tool stores configuration in `~/.aicli/config.json`. You can also specify a custom config file:

```bash
python main.py chat --config /path/to/config.json
```

#### Example Configuration

```json
{
  "providers": {
    "claude": {
      "api_key": "your_claude_api_key",
      "model": "claude-3-5-sonnet-20241022",
      "max_tokens": 4096,
      "mcp_servers": []
    },
    "chatgpt": {
      "api_key": "your_openai_api_key", 
      "model": "gpt-4-turbo-preview",
      "max_tokens": 4096,
      "temperature": 0.7
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama2",
      "timeout": 120
    }
  }
}
```

## Built-in Tools

The CLI includes several built-in tools that work across all providers:

- **read_file**: Read file contents
- **write_file**: Write content to files
- **list_files**: List directory contents
- **run_command**: Execute shell commands
- **search_files**: Search for text patterns in files

These tools give the AI the ability to:
- Read and modify your codebase
- Execute commands and scripts
- Search through project files
- Navigate directory structures

## Provider-Specific Features

### Claude
- Full Anthropic API support
- MCP (Model Context Protocol) integration
- Streaming responses
- Advanced tool usage

### ChatGPT  
- OpenAI API support
- Function calling
- Streaming responses
- Temperature control

### Ollama
- Local model support
- Custom model configurations
- Streaming responses
- Offline operation

## MCP Integration (Claude)

Model Context Protocol allows Claude to access external data sources. Configure MCP servers in your Claude provider settings:

```json
{
  "claude": {
    "api_key": "your_key",
    "model": "claude-3-5-sonnet-20241022",
    "mcp_servers": [
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@anthropic/mcp-server-filesystem", "/path/to/project"]
      }
    ]
  }
}
```

## Examples

### Code Generation
```bash
python main.py ask "Create a Python function that calculates fibonacci numbers"
```

### File Operations
In interactive mode, the AI can read, write, and search through your files:
```
You: Read the contents of main.py and suggest improvements
Assistant: I'll read the file and analyze it for you...
```

### Command Execution
```
You: Run the tests and fix any failures
Assistant: I'll execute the test suite and help resolve any issues...
```

### Provider Switching
```
You: /provider ollama
Assistant: Switched to ollama provider
You: Now explain the same concept using a local model
```

## Development

The project structure:
```
├── src/
│   ├── providers/          # AI provider implementations
│   ├── tools/             # Built-in tools and registry
│   ├── cli.py            # Main CLI interface
│   └── config.py         # Configuration management
├── main.py               # Entry point
├── requirements.txt      # Dependencies
└── setup.py             # Package setup
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.