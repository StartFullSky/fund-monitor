"""
基金持仓异动监控 — 按板块汇总推送
监控用户持有的 8 只基金涉及的核心股票，按板块分组告警
配合 cron job：schedule: "*/5 9-15 * * 1-5"
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import send_bark, pct, now_str, is_trading_day, is_trading_time, _tencent_quote
import hithink_client

# ============ 基金持仓映射 ============
# 每个板块的关键股票（从基金重仓股中提取的高频标的）
SECTORS = {
    '🇺🇸 美股科技': {
        'stocks': {
            'NVDA': '英伟达', 'AAPL': '苹果', 'MSFT': '微软',
            'AMZN': '亚马逊', 'TSLA': '特斯拉', 'META': 'Meta',
            'AVGO': '博通', 'GOOG': '谷歌',
        },
        'funds': '017641/019547/016452/017091',
        'alert_pct': 3.0,  # 美股波动大，±3%告警
    },
    '🇨🇳 半导体/芯片': {
        'stocks': {
            '688981': '中芯国际', '688041': '海光信息', '688256': '寒武纪',
            '603501': '韦尔股份', '688012': '中微公司', '688008': '澜起科技',
            '002371': '北方华创',
        },
        'funds': '011612/008282/012734',
        'alert_pct': 3.0,
    },
    '🔌 光模块/通信': {
        'stocks': {
            '300308': '中际旭创', '300502': '新易盛', '300394': '天孚通信',
            '600487': '亨通光电', '000063': '中兴通讯', '002281': '光迅科技',
        },
        'funds': '012734',
        'alert_pct': 3.0,
    },
    '🤖 机器人/AI': {
        'stocks': {
            '002230': '科大讯飞', '300124': '汇川技术', '688169': '石头科技',
            '688017': '绿的谐波', '002472': '双环传动', '601689': '拓普集团',
        },
        'funds': '018345/012734',
        'alert_pct': 3.0,
    },
}

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fund_monitor_state.json')

def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

def merge_holdings(fund_codes, base_stocks):
    """同花顺基金真实重仓股合并进配置的核心股票（主数据源；失败保留配置兜底）"""
    merged = dict(base_stocks)
    if not hithink_client.is_available():
        return merged
    for fc in fund_codes.split('/'):
        fc = fc.strip()
        if not fc:
            continue
        hold = hithink_client.fund_holdings(fc)
        if not hold:
            continue
        for s in hold.get('stocks', []):
            code = s.get('code')
            if code and code.isdigit() and code not in merged:
                merged[code] = s.get('name') or code
    return merged


def check_sector(sector_name, sector_cfg, state):
    """检查一个板块的异动，返回告警列表"""
    alerts = []
    stocks = merge_holdings(sector_cfg['funds'], sector_cfg['stocks'])
    threshold = sector_cfg['alert_pct']
    fund_codes = sector_cfg['funds']

    # A股行情：同花顺批量快照优先，腾讯兜底
    hithink_quotes = {}
    if hithink_client.is_available():
        try:
            hithink_quotes = hithink_client.a_share_quotes([c for c in stocks if c.isdigit()])
        except Exception:
            hithink_quotes = {}

    for code, name in stocks.items():
        if code.isdigit():
            # A股：同花顺优先，腾讯兜底
            info = hithink_quotes.get(code) or _tencent_quote(code)
        else:
            # 美股，跳过（非交易时段）
            continue

        if not info:
            continue

        change = info.get('change_pct')
        if change is None:
            continue
        state_key = f"{code}"
        last = state.get(state_key, {}).get('pct', 0)
        last_alert = state.get(state_key, {}).get('alerted_at', '')

        # 判断是否需要告警
        should_alert = False
        reason = ''

        if abs(change) >= threshold and abs(change) - abs(last) >= 0.5:
            should_alert = True
            reason = f"{'📈 大涨' if change > 0 else '📉 大跌'} {pct(change)}"
        elif abs(change) >= 9.9 and abs(last) < 9.9:
            should_alert = True
            reason = f"{'🔴 涨停' if change > 0 else '🟢 跌停'}！"
        elif change >= 5 and last < 5:
            should_alert = True
            reason = f"📈 突破 +5%"
        elif change <= -5 and last > -5:
            should_alert = True
            reason = f"📉 跌破 -5%"

        if should_alert:
            alerts.append({
                'name': name, 'code': code,
                'price': info['price'], 'change': change,
                'reason': reason, 'funds': fund_codes,
            })
            state[state_key] = {'pct': change, 'alerted_at': now_str()}
        else:
            state[state_key] = {'pct': change, 'alerted_at': last_alert}

    return alerts

def main():
    if '--force' not in sys.argv:
        if not is_trading_day():
            return  # 周末/法定节假日休市，静默跳过（不输出，避免推送到飞书）
        if not is_trading_time():
            return  # 非交易时段，静默跳过

    state = load_state()
    all_alerts = {}  # sector -> alerts

    for sector_name, sector_cfg in SECTORS.items():
        alerts = check_sector(sector_name, sector_cfg, state)
        if alerts:
            all_alerts[sector_name] = alerts

    save_state(state)

    if all_alerts:
        lines = [f"⏰ {now_str()}\n"]
        total = 0
        for sector, alerts in all_alerts.items():
            lines.append(f"\n{sector} (关联基金: {SECTORS[sector]['funds']})")
            for a in alerts:
                total += 1
                lines.append(f"  {a['reason']} {a['name']}({a['code']}) {a['price']:.2f}")
            lines.append("")

        lines.append(f"共 {total} 条异动，涉及 {len(all_alerts)} 个板块")
        content = '\n'.join(lines)
        print(content)
        send_bark("⚡ 基金持仓异动", content)
    else:
        print("无异动")

if __name__ == '__main__':
    main()
