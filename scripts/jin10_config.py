# Shared MCP config loader
import os, requests

def load_token():
    p = os.path.expanduser("~/.jin10_token")
    with open(p) as f:
        return f.read().strip()

TOKEN=*** = "https://mcp.jin10.com/mcp"
