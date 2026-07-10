"""
每日开盘前推送 — 盘前晨报
内容：大盘隔夜消息 + 关注股票预览 + 重要事件
配合 cron job：schedule: "25 9 * * 1-5" (周一到周五 9:25)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import *
from datetime import datetime

def main():
    if not is_pre_market() and '--force' not in sys.argv:
        print("非盘前时间，跳过")
        return

    now = now_str()
    lines = [f"⏰ {now}\n"]

    # 1. 大盘概况（用昨日收盘）
    overview = get_market_overview()
    if overview:
        lines.append("📊 【大盘概况】")
        for idx in overview:
            lines.append(f"  {idx['name']}: {idx['price']:.2f} {pct(idx['change_pct'])}")
        lines.append("")

    # 2. 关注股票
    watchlist = load_watchlist()
    if watchlist:
        lines.append("⭐ 【关注股票】")
        for code in watchlist:
            info = get_stock_realtime(code)
            if info and 'error' not in info:
                emoji = '📈' if info['change_pct'] > 0 else '📉' if info['change_pct'] < 0 else '➡️'
                lines.append(f"  {emoji} {info['name']}({code}): {info['price']:.2f} {pct(info['change_pct'])}")
            else:
                lines.append(f"  ❓ {code}: 获取失败")
        lines.append("")

    # 3. 涨跌停统计
    limit_up = get_limit_up_down()
    if limit_up:
        lines.append(f"🔴 【昨日涨停】{len(limit_up)} 只")
        for s in limit_up[:5]:
            lines.append(f"  {s['name']}({s['code']})")
        if len(limit_up) > 5:
            lines.append(f"  ...等 {len(limit_up)} 只")
        lines.append("")

    # 4. 个股新闻（关注股票的最新新闻）
    lines.append("📰 【关注股票新闻】")
    for code in watchlist[:3]:
        news = get_stock_news(code)
        if news:
            lines.append(f"  [{code}]")
            for n in news[:2]:
                title = n.get('新闻标题', n.get('title', ''))
                if title:
                    lines.append(f"    • {title[:40]}")
    lines.append("")

    content = '\n'.join(lines)
    print(content)
    send_bark("🌅 今日盘前晨报", content)

if __name__ == '__main__':
    main()
