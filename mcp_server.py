#!/usr/bin/env python3
"""Start de MCP server voor Claude Desktop, Web of Code.

Gebruik:
    python mcp_server.py                              # zonder Obsidian
    python mcp_server.py --vault ~/Documents/Obsidian  # met Obsidian vault
    python mcp_server.py --vault ~/Documents/Obsidian --db data/agent_memory.db
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Zorg dat src importeerbaar is
sys.path.insert(0, str(Path(__file__).parent))

from src.connectors.mcp_server import run_mcp_server


def main():
    parser = argparse.ArgumentParser(description="AI Business Agent MCP Server")
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Pad naar je Obsidian vault (optioneel)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Pad naar de SQLite database (default: data/agent_memory.db)",
    )
    args = parser.parse_args()

    asyncio.run(run_mcp_server(vault_path=args.vault, db_path=args.db))


if __name__ == "__main__":
    main()
