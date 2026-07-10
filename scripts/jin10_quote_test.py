#!/usr/bin/env python3
"""测试 get_quote - 查找浙商积存金代码"""
import requests, json, os

def load_token():
    with open(os.path.expanduser("~/.jin10_token")) as f:
        return f.read().strip()

TOKEN = load_token()
URL = "https://mcp.jin10.com/mcp"
sess = requests.Session()
sess.headers.update({"Content-Type":"application/json","Authorization":"Bearer "+TOKEN,"Accept":"application/json, text/event-stream"})

def mcp(method, params=None, rid=1, notif=False):
    body = {"jsonrpc":"2.0","method":method}
    if not notif: body["id"]=rid
    if params: body["params"]=params
    r = sess.post(URL, json=body, timeout=30)
    sid = r.headers.get("mcp-session-id")
    if sid and "mcp-session-id" not in sess.headers: sess.headers["mcp-session-id"]=sid
    if notif: return None
    for line in r.text.strip().split("\n"):
        if line.startswith("data: "): return json.loads(line[6:])
    try: return r.json()
    except: return {"raw":r.text[:500]}

# Handshake
mcp("initialize", {"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"h","version":"1"}})
mcp("notifications/initialized", {}, notif=True)

# Try different gold codes
codes = ["Au99.99", "GOLD", "XAUUSD", "黄金", "浙商积存金", "ZSJCJ", "AGTD", "AUTD"]
for code in codes:
    print(f"\n--- Testing code: {code} ---")
    result = mcp("tools/call", {"name":"get_quote","arguments":{"code":code}}, rid=10)
    if result:
        content = json.dumps(result, ensure_ascii=False, indent=2)[:500]
        print(content)
