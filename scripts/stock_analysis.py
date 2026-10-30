"""
K线技术分析脚本 — 按需调用
用法：python stock_analysis.py [股票代码] [--push]
默认分析关注列表中的股票
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_utils import *
import numpy as np


def ema_series(values, period):
    """EMA with SMA seed; returns a same-length list with leading None values."""
    if period <= 0:
        raise ValueError("period must be positive")
    result = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    alpha = 2.0 / (period + 1)
    current = seed
    for i in range(period, len(values)):
        current = alpha * values[i] + (1 - alpha) * current
        result[i] = current
    return result


def calculate_rsi(values, period=14):
    """Wilder RSI; returns NaN until the first complete period."""
    if period <= 0:
        raise ValueError("period must be positive")
    result = [float("nan")] * len(values)
    if len(values) <= period:
        return result
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, period + 1)]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, period + 1)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    def to_rsi(gain, loss):
        if gain == 0 and loss == 0:
            return 50.0
        if loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + gain / loss)

    result[period] = to_rsi(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[i] = to_rsi(avg_gain, avg_loss)
    return result


def calculate_macd(values, fast=12, slow=26, signal=9):
    """Return DIF, DEA and histogram series using EMA(12,26,9)."""
    if fast <= 0 or slow <= fast or signal <= 0:
        raise ValueError("invalid MACD periods")
    fast_ema = ema_series(values, fast)
    slow_ema = ema_series(values, slow)
    dif = [float("nan") if f is None or s is None else f - s
           for f, s in zip(fast_ema, slow_ema)]
    start = next((i for i, value in enumerate(dif) if not np.isnan(value)), None)
    dea = [float("nan")] * len(values)
    if start is not None:
        valid_dea = ema_series(dif[start:], signal)
        dea[start:] = [float("nan") if value is None else value for value in valid_dea]
    hist = [float("nan") if np.isnan(d) or np.isnan(e) else 2 * (d - e)
            for d, e in zip(dif, dea)]
    return dif, dea, hist

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

    # Wilder RSI(14)：涨跌幅均以完整周期作平滑，避免只对上涨/下跌样本求均值
    rsi = calculate_rsi(close.tolist(), 14)

    # 标准 MACD(12,26,9)：使用 EMA，不再用末尾窗口简单均值近似
    dif_series, dea_series, macd_hist = calculate_macd(close.tolist())
    dif = dif_series[-1]
    dea = dea_series[-1]
    hist = macd_hist[-1]

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
        f"近5日: {pct(chg_5d)}  近20日: {pct(chg_20d)}",
        f"RSI(14): {rsi:.1f}  {'⚠️超买' if rsi > 70 else '⚠️超卖' if rsi < 30 else '正常'}",
        f"MACD DIF: {dif:.4f} DEA: {dea:.4f} 柱: {hist:.4f}",
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
