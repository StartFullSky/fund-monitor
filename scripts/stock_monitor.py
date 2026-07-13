"""
统一股票异动监控 — 基金持仓 + 涨跌停 + 成交量异动
合并 stock_monitor.py 和 fund_monitor.py 的功能
配合 cron job：schedule: "*/3 9-15 * * 1-5"
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import send_bark, pct, now_str, is_trading_time, _tencent_quote
from datetime import datetime

# ============ 板块配置 ============
# 每个板块的关键股票 + 关联基金
SECTORS = {
    '半导体/芯片': {
        'stocks': {
            '688981': '中芯国际', '688041': '海光信息', '688256': '寒武纪',
            '603501': '韦尔股份', '688012': '中微公司', '688008': '澜起科技',
            '002371': '北方华创',
        },
        'funds': '011612/008282/012734',
    },
    '光模块/通信': {
        'stocks': {
            '300308': '中际旭创', '300502': '新易盛', '300394': '天孚通信',
            '600487': '亨通光电', '000063': '中兴通讯', '002281': '光迅科技',
        },
        'funds': '020900/007044/012734',
    },
    '机器人/AI': {
        'stocks': {
            '002230': '科大讯飞', '300124': '汇川技术', '688169': '石头科技',
            '688017': '绿的谐波', '002472': '双环传动', '601689': '拓普集团',
        },
        'funds': '018345/012734',
    },
    '港股科技': {
        'stocks': {
            '09988': '阿里巴巴', '01810': '小米', '00700': '腾讯',
            '09888': '百度', '03690': '美团',
        },
        'funds': '013308',
    },
}

# ============ 告警级别 ============
# 阈值从高到低匹配，第一个命中的级别生效
ALERT_LEVELS = [
    {'name': 'limit',  'threshold': 9.9, 'emoji': '🔴', 'bark_group': '涨停跌停', 'sound': 'alarm'},
    {'name': 'warning','threshold': 5.0, 'emoji': '🟠', 'bark_group': '大幅波动', 'sound': 'bell'},
    {'name': 'info',   'threshold': 3.0, 'emoji': '🟡', 'bark_group': '异动提醒', 'sound': 'bird'},
]

# 成交量异动阈值（换手率倍数，相对上次记录）
VOLUME_SURGE_RATIO = 3.0  # 换手率达到上次的3倍视为异动

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_monitor_state.json')
STARTUP_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.stock_monitor_started')

# ============ 状态管理 ============

def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'last_alerts': {}, 'limit_up_count': 0, 'last_check': None, 'started_today': False, 'today': ''}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

# ============ 启动心跳 ============

def check_startup_heartbeat(state):
    """每天首次运行发送启动通知"""
    today = datetime.now().strftime('%Y-%m-%d')
    if state.get('today') != today:
        state['today'] = today
        state['started_today'] = False
        state['limit_up_count'] = 0
        # 清除昨天的告警记录
        state['last_alerts'] = {}

    if not state.get('started_today'):
        state['started_today'] = True
        # 统计监控范围
        total_stocks = sum(len(s['stocks']) for s in SECTORS.values())
        sector_names = ' / '.join(SECTORS.keys())
        send_bark(
            '✅ 股票监控已启动',
            f'今日监控 {total_stocks} 只股票\n板块: {sector_names}\n时间: {now_str()}',
            group='monitor-status', sound='bell'
        )

# ============ 告警级别判断 ============

def get_alert_level(change_pct):
    """根据涨跌幅返回告警级别，None 表示不需要告警"""
    abs_change = abs(change_pct)
    for level in ALERT_LEVELS:
        if abs_change >= level['threshold']:
            return level
    return None

# ============ 板块异动检测 ============

def check_sectors(state):
    """检查所有板块的异动，返回告警列表"""
    alerts = []

    for sector_name, sector_cfg in SECTORS.items():
        for code, name in sector_cfg['stocks'].items():
            info = _tencent_quote(code)
            if not info or not info.get('price'):
                continue

            change = info['change_pct']
            state_key = code
            last = state['last_alerts'].get(state_key, {})
            last_pct = last.get('pct', 0)
            last_level = last.get('level', '')

            # 获取当前告警级别
            level = get_alert_level(change)
            if not level:
                # 涨跌幅回到阈值以下，清除告警状态
                if last_level:
                    state['last_alerts'][state_key] = {'pct': change, 'level': '', 'time': now_str()}
                continue

            # 判断是否需要触发新告警
            should_alert = False

            if level['name'] == 'limit':
                # 涨停/跌停：只在首次突破时告警
                if change >= 9.9 and last_pct < 9.9:
                    should_alert = True
                elif change <= -9.9 and last_pct > -9.9:
                    should_alert = True
            else:
                # 非涨跌停：级别升级或同级别波动>=1%时告警
                current_level_idx = ALERT_LEVELS.index(level)
                last_level_idx = next((i for i, l in enumerate(ALERT_LEVELS) if l['name'] == last_level), -1)
                if current_level_idx < last_level_idx:
                    # 级别升级（warning->limit 等）
                    should_alert = True
                elif abs(change) - abs(last_pct) >= 1.0:
                    # 同级别内波动超过1%
                    should_alert = True

            if should_alert:
                market_tag = '🇭🇰' if info.get('market') == 'HK' else ''
                direction = '涨' if change > 0 else '跌'
                amount_str = f'{info["amount"]/1e8:.1f}亿' if info.get('amount') else ''

                msg = (f'{level["emoji"]} {market_tag}{name}({code}) '
                       f'{direction}{pct(change)} '
                       f'价格:{info["price"]:.2f}'
                       f'{f" 额:{amount_str}" if amount_str else ""}')

                alerts.append({
                    'level': level, 'sector': sector_name,
                    'funds': sector_cfg['funds'], 'msg': msg,
                    'code': code, 'change': change,
                })

            # 更新状态
            state['last_alerts'][state_key] = {
                'pct': change,
                'level': level['name'] if level else '',
                'time': now_str()
            }

    return alerts

# ============ 涨停板监控 ============

def check_limit_up_pool(state):
    """检查涨停板数量变化"""
    from stock_utils import get_limit_up_down
    try:
        limit_up = get_limit_up_down()
        count = len(limit_up)
        last_count = state.get('limit_up_count', 0)
        alerts = []
        if count > 0 and count != last_count:
            if count >= 50:
                alerts.append({
                    'level': ALERT_LEVELS[0],  # limit
                    'sector': '涨停板', 'funds': '',
                    'msg': f'🔥 涨停板爆发！今日已有 {count} 只涨停',
                    'code': '', 'change': 0,
                })
            elif count >= 20 and last_count < 20:
                alerts.append({
                    'level': ALERT_LEVELS[2],  # info
                    'sector': '涨停板', 'funds': '',
                    'msg': f'📈 涨停板活跃，今日已有 {count} 只涨停',
                    'code': '', 'change': 0,
                })
        state['limit_up_count'] = count
        return alerts
    except Exception:
        return []

# ============ 主逻辑 ============

def main():
    if not is_trading_time() and '--force' not in sys.argv:
        print('skip')
        return

    state = load_state()

    # 1. 每日启动心跳
    check_startup_heartbeat(state)

    # 2. 板块异动检测
    all_alerts = check_sectors(state)

    # 3. 涨停板监控
    all_alerts.extend(check_limit_up_pool(state))

    state['last_check'] = now_str()
    save_state(state)

    if all_alerts:
        # 按板块分组
        by_sector = {}
        for a in all_alerts:
            sector = a['sector']
            if sector not in by_sector:
                by_sector[sector] = []
            by_sector[sector].append(a)

        lines = [f'⏰ {now_str()}']
        total = 0
        for sector, alerts in by_sector.items():
            funds = alerts[0].get('funds', '')
            lines.append(f'\n📂 {sector}' + (f' (基金: {funds})' if funds else ''))
            for a in alerts:
                total += 1
                lines.append(f'  {a["msg"]}')

        lines.append(f'\n共 {total} 条异动，涉及 {len(by_sector)} 个板块')
        content = '\n'.join(lines)

        # 按最高告警级别推送
        max_level = min(all_alerts, key=lambda a: ALERT_LEVELS.index(a['level']))['level']
        send_bark(
            f'{max_level["emoji"]} 股票异动 · {len(all_alerts)}条',
            content,
            group=max_level['bark_group'],
            sound=max_level.get('sound', 'bell'),
        )
        print(content)
    else:
        print('无异动')

if __name__ == '__main__':
    main()
