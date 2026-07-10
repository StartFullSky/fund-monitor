#!/usr/bin/env python3
"""浙商积存金价格监控 - 趋势跟踪 + 里程碑通知"""
import requests, json, os, sys

from datetime import datetime
def load_token():
    p = os.path.expanduser("~/.jin10_token")
    with open(p) as f:
        return f.read().strip()

TOKEN = load_token()
URL = "https://mcp.jin10.com/mcp"
sess = requests.Session()
sess.headers.update({"Content-Type":"application/json","Authorization":"Bearer "+TOKEN,"Accept":"application/json, text/event-stream"})

from urllib.parse import quote as urlquote

STATE_FILE = os.path.expanduser("~/.jin10_gold_state.json")
GOLD_CODE = "CZBJCJ"
THRESHOLD = 0.01  # 1%
BARK_KEY = "G4dSERuAhUrN7WBg9rpKcS"
BARK_URL = "https://api.day.app/" + BARK_KEY + "/"

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
    except: return None

def get_quote(code):
    mcp("initialize", {"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"h","version":"1"}})
    mcp("notifications/initialized", {}, notif=True)
    result = mcp("tools/call", {"name":"get_quote","arguments":{"code":code}}, rid=2)
    if result and "result" in result:
        content = result["result"].get("content", [])
        if content:
            data = json.loads(content[0].get("text","{}"))
            if data.get("status")==200: return data["data"]
    return None

def bark(title, body_text):
    try:
        requests.get(BARK_URL + urlquote(title) + "/" + urlquote(body_text), timeout=10)
    except:
        try:
            requests.get(BARK_URL + urlquote(title) + "/" + urlquote(body_text), timeout=10,
                         proxies={"http":"http://127.0.0.1:7897","https":"http://127.0.0.1:7897"})
        except: pass

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except:
        return {"price":0,"base_price":0,"trend_direction":None,"trend_peak":0,"trend_valley":999999,"last_milestone":0,"time":""}

def save_state(state):
    with open(STATE_FILE,"w") as f: json.dump(state,f,ensure_ascii=False,indent=2)

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quote = get_quote(GOLD_CODE)
    if not quote:
        bark("❌ 浙商积存金", "获取报价失败，请检查网络或API")
        return

    price = float(quote.get("close",0))
    state = load_state()
    base = state["base_price"]

    if base == 0:
        state.update({"price":price,"base_price":price,"trend_peak":price,"trend_valley":price,"time":now})
        save_state(state)
        return

    diff_pct = (price - base) / base
    trend = state["trend_direction"]

    if trend is None:
        if diff_pct >= THRESHOLD:
            state["trend_direction"] = "up"
            state["trend_peak"] = price
            state["last_milestone"] = 1
            bark("📈 浙商积存金上涨趋势", f"基准价:{base} 当前:{price} 涨幅:{diff_pct*100:.2f}%")
        elif diff_pct <= -THRESHOLD:
            state["trend_direction"] = "down"
            state["trend_valley"] = price
            state["last_milestone"] = 1
            bark("📉 浙商积存金下跌趋势", f"基准价:{base} 当前:{price} 跌幅:{diff_pct*100:.2f}%")

    elif trend == "up":
        if price > state["trend_peak"]:
            state["trend_peak"] = price
            peak_diff = (price - base) / base
            milestone = int(peak_diff / THRESHOLD)
            if milestone > state["last_milestone"]:
                state["last_milestone"] = milestone
                bark("📈 浙商积存金持续上涨", f"基准价:{base} 当前:{price} 涨幅:{peak_diff*100:.2f}%")
        else:
            retracement = (state["trend_peak"] - price) / state["trend_peak"]
            if retracement >= THRESHOLD:
                bark("⚠️ 浙商积存金上涨回调", f"最高:{state['trend_peak']} 当前:{price} 回撤:{retracement*100:.2f}%")
                state.update({"trend_direction":None,"base_price":price,"trend_peak":price,"trend_valley":price,"last_milestone":0})

    elif trend == "down":
        if price < state["trend_valley"]:
            state["trend_valley"] = price
            valley_diff = (base - price) / base
            milestone = int(valley_diff / THRESHOLD)
            if milestone > state["last_milestone"]:
                state["last_milestone"] = milestone
                bark("📉 浙商积存金持续下跌", f"基准价:{base} 当前:{price} 跌幅:{valley_diff*100:.2f}%")
        else:
            rebound = (price - state["trend_valley"]) / state["trend_valley"]
            if rebound >= THRESHOLD:
                bark("⚠️ 浙商积存金下跌反弹", f"最低:{state['trend_valley']} 当前:{price} 反弹:{rebound*100:.2f}%")
                state.update({"trend_direction":None,"base_price":price,"trend_peak":price,"trend_valley":price,"last_milestone":0})

    state["price"] = price
    state["time"] = now
    save_state(state)

if __name__ == "__main__":
    main()
