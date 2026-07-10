"""
股票异动监控 — 盘中实时监控
监控：涨跌停、大幅波动、成交量异动
配合 cron job：schedule: "*/3 9-15 * * 1-5" (交易时段每3分钟)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import *
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_monitor_state.json')

def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'last_alerts': {}, 'limit_up_count': 0, 'last_check': None}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

def check_watchlist(state):
    """检查关注股票的异动"""
    alerts = []
    watchlist = load_watchlist()
    for code in watchlist:
        info = get_stock_realtime(code)
        if not info or 'error' in info:
            continue
        name = info['name']
        pct_chg = info['change_pct']
        last_alert = state['last_alerts'].get(code, {})
        last_pct = last_alert.get('pct', 0)

        # 大幅波动告警（±5%）
        if abs(pct_chg) >= 5 and abs(pct_chg) - abs(last_pct) >= 1:
            emoji = '🔴' if pct_chg > 0 else '🟢'
            alerts.append({
                'type': 'big_move', 'code': code, 'name': name,
                'msg': f"{emoji} {name}({code}) 大幅{'上涨' if pct_chg > 0 else '下跌'} {pct(pct_chg)}\n当前价: {info['price']:.2f} 成交额: {info['amount']/1e8:.2f}亿"
            })

        # 涨停/跌停告警
        if pct_chg >= 9.9 and last_pct < 9.9:
            alerts.append({'type': 'limit_up', 'code': code, 'name': name, 'msg': f"🔴 {name}({code}) 涨停！ {pct(pct_chg)} 价格: {info['price']:.2f}"})
        elif pct_chg <= -9.9 and last_pct > -9.9:
            alerts.append({'type': 'limit_down', 'code': code, 'name': name, 'msg': f"🟢 {name}({code}) 跌停！ {pct(pct_chg)} 价格: {info['price']:.2f}"})

        state['last_alerts'][code] = {'pct': pct_chg, 'time': now_str()}

    return alerts

def check_limit_up_pool(state):
    """检查涨停板数量变化"""
    limit_up = get_limit_up_down()
    count = len(limit_up)
    last_count = state.get('limit_up_count', 0)
    alerts = []
    if count > 0 and count != last_count:
        if count >= 50:
            alerts.append({'type': 'limit_pool', 'msg': f"🔥 涨停板爆发！今日已有 {count} 只涨停"})
        elif count >= 20 and last_count < 20:
            alerts.append({'type': 'limit_pool', 'msg': f"📈 涨停板活跃，今日已有 {count} 只涨停"})
    state['limit_up_count'] = count
    return alerts

def main():
    if not is_trading_time() and '--force' not in sys.argv:
        print("skip")
        return

    state = load_state()
    all_alerts = []

    # 1. 关注股票异动
    all_alerts.extend(check_watchlist(state))

    # 2. 涨停板监控
    all_alerts.extend(check_limit_up_pool(state))

    state['last_check'] = now_str()
    save_state(state)

    if all_alerts:
        content = '\n\n'.join(a['msg'] for a in all_alerts)
        print(content)
        send_bark("⚡ 股票异动提醒", content)
    else:
        print("无异动")

if __name__ == '__main__':
    main()
