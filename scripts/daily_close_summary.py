"""
每日收盘汇总 — 收盘后推送当日市场总结
内容：大盘表现 + 板块排名 + 涨跌停统计 + 关注股票
配合 cron job：schedule: "10 15 * * 1-5" (周一到周五 15:10)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import send_bark, pct, now_str, get_market_overview, get_limit_up_down, load_watchlist, _tencent_quote
from datetime import datetime

# ============ 板块配置（复用 stock_monitor.py） ============
SECTORS = {
    '半导体/芯片': {
        'stocks': {
            '688981': '中芯国际', '688041': '海光信息', '688256': '寒武纪',
            '603501': '韦尔股份', '688012': '中微公司', '688008': '澜起科技',
            '002371': '北方华创',
        },
    },
    '光模块/通信': {
        'stocks': {
            '300308': '中际旭创', '300502': '新易盛', '300394': '天孚通信',
            '600487': '亨通光电', '000063': '中兴通讯', '002281': '光迅科技',
        },
    },
    '机器人/AI': {
        'stocks': {
            '002230': '科大讯飞', '300124': '汇川技术', '688169': '石头科技',
            '688017': '绿的谐波', '002472': '双环传动', '601689': '拓普集团',
        },
    },
    '港股科技': {
        'stocks': {
            '09988': '阿里巴巴', '01810': '小米', '00700': '腾讯',
            '09888': '百度', '03690': '美团',
        },
    },
}

def is_after_market():
    """判断是否在收盘后（15:00-15:30）"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周末
        return False
    t = now.hour * 100 + now.minute
    return 1500 <= t <= 1530

def get_sector_performance():
    """获取各板块表现"""
    results = []
    for sector_name, sector_cfg in SECTORS.items():
        stocks = sector_cfg['stocks']
        total_change = 0
        count = 0
        up_count = 0
        down_count = 0
        best_stock = None
        worst_stock = None
        
        for code, name in stocks.items():
            info = _tencent_quote(code)
            if not info or not info.get('price'):
                continue
            change = info['change_pct']
            total_change += change
            count += 1
            if change > 0:
                up_count += 1
            elif change < 0:
                down_count += 1
            
            if best_stock is None or change > best_stock[1]:
                best_stock = (name, change)
            if worst_stock is None or change < worst_stock[1]:
                worst_stock = (name, change)
        
        if count > 0:
            avg_change = total_change / count
            results.append({
                'name': sector_name,
                'avg_change': avg_change,
                'up_count': up_count,
                'down_count': down_count,
                'count': count,
                'best': best_stock,
                'worst': worst_stock,
            })
    
    # 按平均涨跌幅排序
    results.sort(key=lambda x: x['avg_change'], reverse=True)
    return results

def main():
    if not is_after_market() and '--force' not in sys.argv:
        print('skip')
        return

    now = now_str()
    lines = [f'⏰ {now}', '📊 【今日收盘汇总】', '']

    # 1. 大盘概况
    overview = get_market_overview()
    if overview:
        lines.append('📈 【大盘表现】')
        for idx in overview:
            emoji = '🔴' if idx['change_pct'] > 0 else '🟢' if idx['change_pct'] < 0 else '⚪'
            lines.append(f'  {emoji} {idx["name"]}: {idx["price"]:.2f} {pct(idx["change_pct"])}')
        lines.append('')

    # 2. 板块表现排名
    sectors = get_sector_performance()
    if sectors:
        lines.append('🏷️ 【板块排名】')
        for i, s in enumerate(sectors[:4], 1):
            emoji = '📈' if s['avg_change'] > 0 else '📉' if s['avg_change'] < 0 else '➡️'
            lines.append(f'  {i}. {emoji} {s["name"]}: {pct(s["avg_change"])}')
            lines.append(f'     涨{s["up_count"]}只/跌{s["down_count"]}只')
            if s['best']:
                lines.append(f'     领涨: {s["best"][0]} {pct(s["best"][1])}')
        lines.append('')

    # 3. 涨跌停统计
    try:
        limit_up = get_limit_up_down()
        if limit_up:
            lines.append(f'🔴 【涨停板】今日 {len(limit_up)} 只涨停')
            for s in limit_up[:3]:
                lines.append(f'  • {s["name"]}({s["code"]})')
            if len(limit_up) > 3:
                lines.append(f'  ...等 {len(limit_up)} 只')
            lines.append('')
    except Exception:
        lines.append('🔴 【涨停板】数据获取失败')
        lines.append('')

    # 4. 关注股票表现
    watchlist = load_watchlist()
    if watchlist:
        lines.append('⭐ 【关注股票】')
        for code in watchlist:
            info = _tencent_quote(code)
            if info and info.get('price'):
                emoji = '🔴' if info['change_pct'] > 0 else '🟢' if info['change_pct'] < 0 else '⚪'
                amount_str = f'{info["amount"]/1e8:.1f}亿' if info.get('amount') else ''
                lines.append(f'  {emoji} {info["name"]}({code}): {info["price"]:.2f} {pct(info["change_pct"])}')
                if amount_str:
                    lines.append(f'     成交额: {amount_str}')
        lines.append('')

    content = '\n'.join(lines)
    print(content)
    send_bark('📊 今日收盘汇总', content, group='daily-summary', sound='bell')

if __name__ == '__main__':
    main()
