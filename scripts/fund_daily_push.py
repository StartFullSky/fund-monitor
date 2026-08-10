"""
基金收盘前涨跌播报 — 交易日 14:40 推送持仓基金当日估算涨跌
数据源：场内ETF实时行情（腾讯 qt.gtimg.cn，与指数高度一致）；美股QDII无当日估算，显示最近净值
配合 Hermes cron job：schedule: "40 14 * * 1-5"（交易日 14:40，脚本内含休市检测）
"""
import sys, os, json, re
from datetime import datetime
from urllib.request import urlopen, Request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import send_bark, now_str

FUNDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_funds.json')

# 基金代码 → 场内ETF（腾讯代码），ETF 与基金跟踪同一指数，盘中涨跌即基金估算涨跌
ETF_MAP = {
    '007044': 'sh510300',   # 沪深300ETF 华泰柏瑞
    '011612': 'sh588000',   # 科创50ETF 华夏
    '012734': 'sz159819',   # 人工智能ETF 易方达
    '018345': 'sh562500',   # 机器人ETF 华夏
    '020900': 'sh515880',   # 通信ETF 国泰
    '008282': 'sh512760',   # 芯片ETF 国泰
}
# 美股 QDII：A股 14:40 时美股未开盘，无当日估算
US_QDII = {'017641', '019547', '016452'}


def tencent_quote(tencent_code):
    """腾讯行情，返回现价/涨跌幅/行情时间"""
    try:
        url = f'http://qt.gtimg.cn/q={tencent_code}'
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req, timeout=10).read().decode('gbk', errors='ignore')
        m = re.search(r'="(.*?)"', data)
        if not m:
            return None
        f = m.group(1).split('~')
        if len(f) < 33:
            return None
        return {
            'name': f[1],
            'price': float(f[3]),
            'change_pct': float(f[32]),   # 涨跌幅（-2.33 即 -2.33%）
            'time': f[30],                # YYYYMMDDHHMMSS
        }
    except Exception:
        return None


def fund_latest_nav(code):
    """天天基金历史净值，取最后一条（QDII 显示最近净值用）"""
    try:
        url = f'https://fund.eastmoney.com/pingzhongdata/{code}.js'
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        text = urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        m = re.search(r'Data_netWorthTrend = (\[.*?\]);', text)
        if not m:
            return None
        items = json.loads(m.group(1))
        if not items:
            return None
        last = items[-1]
        dt = datetime.fromtimestamp(last['x'] / 1000).strftime('%m-%d')
        return {'nav': last['y'], 'date': dt}
    except Exception:
        return None


def is_holiday_today():
    """用任一 ETF 的行情时间戳判断今天是否开市（休市时时间戳停留在上一交易日）"""
    for code in list(ETF_MAP.values()):
        info = tencent_quote(code)
        if info and info['time']:
            return info['time'][:8] != datetime.now().strftime('%Y%m%d')
    return False


def main():
    if '--force' not in sys.argv and is_holiday_today():
        # 休市日静默退出（Hermes cron 空输出=不推送）
        return

    with open(FUNDS_FILE, 'r', encoding='utf-8') as f:
        funds = json.load(f)['funds']

    lines = [f"⏰ {now_str()} 收盘前播报（估算）", f"📊 【基金涨跌】今日 {len(funds)} 只持仓", ""]

    up = down = flat = 0
    results = []
    for code, meta in funds.items():
        name = meta['name']
        if code in US_QDII:
            nav = fund_latest_nav(code)
            if nav:
                results.append((code, name, None, f"最近净值 {nav['nav']}（{nav['date']}）美股未开盘"))
            else:
                results.append((code, name, None, "净值获取失败"))
            continue
        etf = ETF_MAP.get(code)
        if not etf:
            results.append((code, name, None, "无估算源"))
            continue
        info = tencent_quote(etf)
        if not info:
            results.append((code, name, None, "行情获取失败"))
            continue
        change = info['change_pct']
        results.append((code, name, change, info['price']))
        if change > 0:
            up += 1
        elif change < 0:
            down += 1
        else:
            flat += 1

    for code, name, change, detail in results:
        if change is not None:
            emoji = '🔴' if change > 0 else '🟢' if change < 0 else '⚪'
            lines.append(f"  {emoji} {name}({code}): {change:+.2f}%")
        else:
            lines.append(f"  ⚪ {name}({code}): {detail}")

    lines.append("")
    lines.append(f"统计：涨 {up} 只 / 跌 {down} 只 / 平 {flat} 只（估算仅供参考，以今晚官方净值为准）")
    content = '\n'.join(lines)
    print(content)
    if '--bark' in sys.argv:
        send_bark('📊 基金涨跌播报', content)


if __name__ == '__main__':
    main()
