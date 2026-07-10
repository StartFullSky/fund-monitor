#!/usr/bin/env python3
"""金十数据 MCP 客户端 - 测试连接"""

import requests
import json
import os

# 从文件读取 token
token_file = os.path.expanduser("~/.jin10_token")
with open(token_file) as f:
    TOKEN = f.read().strip()

BASE_URL = "https://mcp.jin10.com/mcp"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream"
}


def mcp_call(method, params=None, req_id=1):
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params:
        payload["params"] = params
    r = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
    text = r.text
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    try:
        return r.json()
    except:
        return {"raw": text[:500]}


def main():
    # Initialize
    print("=== Initialize ===")
    init = mcp_call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "hermes", "version": "1.0"}
    })
    print(json.dumps(init, ensure_ascii=False, indent=2))

    # List tools
    print("\n=== Tools ===")
    tools = mcp_call("tools/list", {})
    if "result" in tools and "tools" in tools["result"]:
        for t in tools["result"]["tools"]:
            print(f"  - {t['name']}: {t.get('description', '')[:80]}")
    else:
        print(json.dumps(tools, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
