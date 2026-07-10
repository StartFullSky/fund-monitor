"""
K线技术分析脚本 — 按需调用
用法：python stock_analysis.py [股票代码] [--push]
默认分析关注列表中的股票
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import *
import numpy as np

def analyze_stock(code):
    """对单只股票做技术分析"""
    klines = get_stock_kline(code, days=60)
    if not klines or len(klines) < 20:
        return f"❌ {code} 获取K线数据失败"

    close = np.array([k['close'] for k in klines])
    high = np.array([k['high'] for k in klines])
    low = np.array([k['low'] for k in klines])
    volume = np.array([k['volume'] for k in klines])
    current = close[-1]

    # 均线
    ma5 = close[-5:].mean()
    ma10 = close[-10:].mean()
    ma20 = close[-20:].mean()

    # 趋势判断
    if current > ma5 > ma10 > ma20:
        trend = "📈 多头排列（强势）"
    elif current < ma5 < ma10 < ma20:
        trend = "📉 空头排列（弱势）"
    else:
        trend = "➡️ 震荡整理"

    # 近期涨跌幅
    chg_5d = (close[-1] / close[-5] - 1) * 100 if len(close) >= 5 else 0
    chg_20d = (close[-1] / close[-20] - 1) * 100 if len(close) >= 20 else 0

    # 成交量变化
    vol_avg5 = volume[-5:].mean()
    vol_avg20 = volume[-20:].mean()
    vol_ratio = vol_avg5 / vol_avg20 if vol_avg20 > 0 else 1.0

    # 最高最低
    high_60 = high.max()
    low_60 = low.min()
    pos_pct = (current - low_60) / (high_60 - low_60) * 100 if high_60 != low_60 else 50

    # RSI 简易计算
    deltas = np.diff(close)
    gains = deltas[-14:][deltas[-14:] > 0]
    losses = -deltas[-14:][deltas[-14:] < 0]
    avg_gain = gains.mean() if len(gains) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0.001
    rsi = 100 - 100 / (1 + avg_gain / avg_loss)

    # MACD 简易
    ema12 = close[-12:].mean()
    ema26 = close[-26:].mean() if len(close) >= 26 else close.mean()
    dif = ema12 - ema26

    # 获取股票名称
    info = get_stock_realtime(code)
    name = info.get('name', code) if info else code

    lines = [
        f"📊 【{name}({code}) 技术分析】",
        f"当前价: {current:.2f}  60日高: {high_60:.2f}  60日低: {low_60:.2f}",
        f"",
        f"趋势: {trend}",
        f"MA5: {ma5:.2f}  MA10: {ma10:.2f}  MA20: {ma20:.2f}",
        f"",
        f"近5日: {pct(chg_5d/100)}  近20日: {pct(chg_20d/100)}",
        f"RSI(14): {rsi:.1f}  {'⚠️超买' if rsi > 70 else '⚠️超卖' if rsi < 30 else '正常'}",
        f"MACD DIF: {dif:.2f}  {'🔴多头' if dif > 0 else '🟢空头'}",
        f"",
        f"60日位置: {pos_pct:.0f}%  量比(5/20): {vol_ratio:.2f}x",
        f"{'📊 放量' if vol_ratio > 1.5 else '📉 缩量' if vol_ratio < 0.7 else '➡️ 平量'}",
    ]
    return '\n'.join(lines)

def main():
    args = sys.argv[1:]
    codes = [a for a in args if a.isdigit()] if args else load_watchlist()

    results = []
    for code in codes:
        results.append(analyze_stock(code))

    content = '\n\n'.join(results)
    print(content)

    if '--push' in sys.argv:
        send_bark("📊 技术分析报告", content)

if __name__ == '__main__':
    main()
