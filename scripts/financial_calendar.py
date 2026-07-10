"""
财经日历推送 — 每日重要经济事件提醒
配合 cron job：schedule: "0 8 * * 1-5" (周一到周五 8:00)
数据源：东方财富财经日历
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import send_bark, now_str
from urllib.request import urlopen
from datetime import datetime

def get_financial_events():
    """获取今日重要财经事件（东方财富）"""
    today = datetime.now().strftime('%Y-%m-%d')
    url = f'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_ECONOMICDATA_CAL&columns=ALL&filter=(REPORT_DATE%3E%27{today}%27)(REPORT_DATE%3C%27{today} 23:59:59%27)&pageSize=50&sortColumns=REPORT_DATE&sortTypes=1'
    try:
        req = urlopen(url, timeout=10)
        data = json.loads(req.read().decode('utf-8'))
        if data.get('result') and data['result'].get('data'):
            events = []
            for item in data['result']['data']:
                events.append({
                    'time': item.get('REPORT_DATE', ''),
                    'event': item.get('EVENT_TITLE', item.get('INDICATOR_NAME', '')),
                    'country': item.get('COUNTRY', ''),
                    'importance': item.get('STAR', 0),
                })
            return events
    except Exception:
        pass
    return []

def main():
    events = get_financial_events()
    if not events:
        # 没有重要事件，静默退出
        print("今日无重要财经事件")
        return

    # 按重要性排序，只推送3星以上的
    important = [e for e in events if e.get('importance', 0) >= 3]
    if not important:
        print("今日无高重要性财经事件")
        return

    lines = [f"📅 {datetime.now().strftime('%Y-%m-%d %A')}\n"]
    for e in important[:10]:
        stars = '⭐' * e.get('importance', 0)
        lines.append(f"  {stars} {e['event']}")
        if e.get('country'):
            lines.append(f"    🌍 {e['country']}")
    lines.append(f"\n共 {len(important)} 项重要事件")

    content = '\n'.join(lines)
    print(content)
    send_bark("📅 今日财经日历", content)

if __name__ == '__main__':
    main()
