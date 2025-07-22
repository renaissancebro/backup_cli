import os
import subprocess
import json
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from ..providers.base import Tool

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_builtin_tools()
    
    def register_tool(self, tool: Tool) -> None:
        """Register a new tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return list(self.tools.values())
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools similar to Claude Code"""
        
        # File operations
        self.register_tool(Tool(
            name="read_file",
            description="Read the contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            },
            handler=self._read_file
        ))
        
        self.register_tool(Tool(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            },
            handler=self._write_file
        ))
        
        self.register_tool(Tool(
            name="list_files",
            description="List files in a directory",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list files from"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files"
                    }
                },
                "required": ["directory"]
            },
            handler=self._list_files
        ))
        
        # Command execution
        self.register_tool(Tool(
            name="run_command",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Working directory for the command"
                    }
                },
                "required": ["command"]
            },
            handler=self._run_command
        ))
        
        # Search tools
        self.register_tool(Tool(
            name="search_files",
            description="Search for text in files",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to include in search"
                    }
                },
                "required": ["pattern", "directory"]
            },
            handler=self._search_files
        ))
    
    async def _read_file(self, file_path: str) -> str:
        """Read file contents"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    async def _write_file(self, file_path: str, content: str) -> str:
        """Write content to file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"
    
    async def _list_files(self, directory: str, pattern: str = None) -> str:
        """List files in directory"""
        try:
            path = Path(directory)
            if not path.exists():
                return f"Directory {directory} does not exist"
            
            if pattern:
                files = list(path.glob(pattern))
            else:
                files = list(path.iterdir())
            
            file_list = []
            for file in files:
                if file.is_file():
                    file_list.append(f"📄 {file.name}")
                elif file.is_dir():
                    file_list.append(f"📁 {file.name}/")
            
            return "\n".join(sorted(file_list))
        except Exception as e:
            return f"Error listing files: {e}"
    
    async def _run_command(self, command: str, working_directory: str = None) -> str:
        """Execute shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            
            output.append(f"Exit code: {result.returncode}")
            
            return "\n\n".join(output)
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {e}"
    
    async def _search_files(self, pattern: str, directory: str, file_pattern: str = "*") -> str:
        """Search for text pattern in files"""
        try:
            import glob
            import re
            
            search_path = os.path.join(directory, "**", file_pattern)
            files = glob.glob(search_path, recursive=True)
            
            results = []
            regex = re.compile(pattern, re.IGNORECASE)
            
            for file_path in files:
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        matches = regex.findall(content)
                        if matches:
                            results.append(f"\n{file_path}:")
                            for i, line in enumerate(content.split('\n'), 1):
                                if regex.search(line):
                                    results.append(f"  {i}: {line.strip()}")
                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary files or files we can't read
                        continue
            
            return "\n".join(results) if results else "No matches found"
        except Exception as e:
            return f"Error searching files: {e}"