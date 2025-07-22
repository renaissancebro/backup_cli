#!/usr/bin/env python3
"""
Multi-Provider AI CLI Agent
A CLI tool similar to Claude Code but supporting multiple AI providers (Claude, ChatGPT, Ollama)
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import cli

if __name__ == "__main__":
    cli()