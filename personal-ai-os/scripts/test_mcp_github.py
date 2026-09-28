"""Live test of the generic MCP connection against GitHub's real, official
remote MCP server -- the user's ask: "let us build MCP connection plug n
play and test it with a MCP connection with my github."

This script is deliberately NOT GitHub-specific in its logic -- it uses
the same MCPConnection/discover_mcp_tools() any other MCP server would
use (app/tools/mcp_tool.py). GitHub is the first real, live test case, not
special-cased code.

Requires GITHUB_TOKEN in .env (a Personal Access Token with at least
repo/read scope).

Usage:
    PYTHONPATH=. python scripts/test_mcp_github.py
    PYTHONPATH=. python scripts/test_mcp_github.py --call get_me
"""

import argparse

from app.config import require_github_token
from app.tools.mcp_tool import MCPConnection, discover_mcp_tools

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--call", default=None, help="Name of one discovered tool to actually call with empty args, to prove a real round trip.")
    args = parser.parse_args()

    token = require_github_token()

    print(f"Connecting to {GITHUB_MCP_URL} ...")
    connection = MCPConnection(GITHUB_MCP_URL, headers={"Authorization": f"Bearer {token}"}).connect()
    print("Connected and initialized.")

    tools = discover_mcp_tools(connection)
    print(f"\n{len(tools)} real tool(s) discovered from GitHub's MCP server:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:100]}")

    if args.call:
        target_name = f"mcp_{args.call}"
        matching = [t for t in tools if t.name == target_name]
        if not matching:
            print(f"\nNo discovered tool named '{args.call}' (looked for '{target_name}').")
        else:
            tool = matching[0]
            print(f"\nCalling '{tool.name}' with empty args...")
            try:
                result = tool.call({})
                print("Result:")
                print(result[:1000])
            except Exception as exc:
                print(f"Call failed: {exc}")

    connection.close()
    print("\nConnection closed.")


if __name__ == "__main__":
    main()
