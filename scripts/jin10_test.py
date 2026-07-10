#!/usr/bin/env python3
"""金十数据 MCP 客户端"""
import requests, json, os, sys

def load_token():
    p = os.path.expanduser("~/.jin10_token")
    with open(p) as f:
        return f.read().strip()

TOKEN = load_token()
URL = "https://mcp.jin10.com/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + TOKEN,
    "Accept": "application/json, text/event-stream"
}

sess = requests.Session()
sess.headers.update(HEADERS)

def mcp(method, params=None, rid=1, notif=False):
    body = {"jsonrpc": "2.0", "method": method}
    if not notif: body["id"] = rid
    if params: body["params"] = params
    r = sess.post(URL, json=body, timeout=30)
    sid = r.headers.get("mcp-session-id")
    if sid and "mcp-session-id" not in sess.headers:
        sess.headers["mcp-session-id"] = sid
    if notif: return None
    for line in r.text.strip().split("\n"):
        if line.startswith("data: "): return json.loads(line[6:])
    try: return r.json()
    except: return {"raw": r.text[:500]}

# Handshake
mcp("initialize", {"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hermes","version":"1.0"}})
mcp("notifications/initialized", {}, notif=True)

# List tools
tools = mcp("tools/list", {}, rid=2)
if tools and "result" in tools:
    for t in tools["result"].get("tools", []):
        name = t["name"]
        desc = t.get("description", "")[:100]
        props = t.get("inputSchema", {}).get("properties", {})
        param_str = ", ".join(f"{k}({v.get('type','?')})" for k,v in props.items())
        print(f"TOOL: {name} | {desc}")
        if param_str: print(f"  PARAMS: {param_str}")
else:
    print("ERROR:", json.dumps(tools, ensure_ascii=False)[:500])
