"""Conservative intraday ETF signal candidate engine.

This module only calculates candidate signals from completed intraday bars.
It never places orders. Feed it timestamped 1-minute bars from a verified
real-time source; do not pass daily fallback data.
"""
from math import isfinite


def _ema(values, period):
    if period <= 0 or len(values) < period:
        return []
    alpha = 2.0 / (period + 1)
    current = sum(values[:period]) / period
    result = [current]
    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
        result.append(current)
    return result


def _rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, period + 1)]
    avg_gain = sum(max(x, 0.0) for x in changes) / period
    avg_loss = sum(max(-x, 0.0) for x in changes) / period
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def analyze_intraday_bars(code, bars, min_bars=30, volume_window=20,
                          risk_atr_multiple=1.5, reward_risk=2.0):
    """Return a HOLD/BUY_CANDIDATE/SELL_CANDIDATE object from completed bars.

    Each bar must contain timestamp, high, low, close and volume. Input must
    be sorted oldest-first and contain completed bars only.
    """
    if not code or not isinstance(bars, list) or len(bars) < min_bars:
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "insufficient_intraday_bars"}
    try:
        closes = [float(x["close"]) for x in bars]
        highs = [float(x["high"]) for x in bars]
        lows = [float(x["low"]) for x in bars]
        volumes = [float(x["volume"]) for x in bars]
        timestamps = [str(x["timestamp"]) for x in bars]
    except (KeyError, TypeError, ValueError):
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "invalid_bar_schema"}

    if any(not isfinite(x) for seq in (closes, highs, lows, volumes) for x in seq):
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "non_finite_market_data"}
    if any(x <= 0 for x in closes) or any(x < 0 for x in volumes):
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "invalid_price_or_volume"}
    if timestamps != sorted(timestamps):
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "bars_not_chronological"}
    if any(h < max(l, c) or l > min(h, c) for h, l, c in zip(highs, lows, closes)):
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "inconsistent_ohlc"}

    fast = _ema(closes, 9)
    slow = _ema(closes, 21)
    if not fast or not slow:
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "indicator_warmup"}
    ema_fast, ema_slow = fast[-1], slow[-1]
    rsi = _rsi(closes, 14)

    total_volume = sum(volumes)
    if total_volume <= 0:
        return {"code": code, "action": "HOLD", "ready": False,
                "reason": "zero_volume"}
    vwap = sum(((h + l + c) / 3.0) * v for h, l, c, v
               in zip(highs, lows, closes, volumes)) / total_volume

    recent = volumes[-1]
    prior = volumes[-(volume_window + 1):-1]
    avg_prior_volume = sum(prior) / len(prior) if prior else 0.0
    volume_ratio = recent / avg_prior_volume if avg_prior_volume > 0 else 0.0
    last = closes[-1]

    action = "HOLD"
    reason = "no_confirmed_setup"
    if last > vwap and ema_fast > ema_slow and rsi is not None and 50 <= rsi < 70 and volume_ratio >= 1.2:
        action, reason = "BUY_CANDIDATE", "trend_vwap_rsi_volume_aligned"
    elif last < vwap and ema_fast < ema_slow and rsi is not None and 30 < rsi <= 50 and volume_ratio >= 1.2:
        action, reason = "SELL_CANDIDATE", "downtrend_vwap_rsi_volume_aligned"

    true_ranges = []
    for i in range(1, len(bars)):
        true_ranges.append(max(highs[i] - lows[i],
                               abs(highs[i] - closes[i - 1]),
                               abs(lows[i] - closes[i - 1])))
    atr = sum(true_ranges[-14:]) / min(14, len(true_ranges)) if true_ranges else 0.0
    stop = None
    target = None
    if action == "BUY_CANDIDATE" and atr > 0:
        stop = last - risk_atr_multiple * atr
        target = last + reward_risk * (last - stop)
    elif action == "SELL_CANDIDATE" and atr > 0:
        stop = last + risk_atr_multiple * atr
        target = last - reward_risk * (stop - last)

    return {
        "code": code, "action": action, "ready": True, "reason": reason,
        "as_of": timestamps[-1], "price": last, "vwap": vwap,
        "ema_fast": ema_fast, "ema_slow": ema_slow, "rsi14": rsi,
        "volume_ratio": volume_ratio, "atr14": atr,
        "stop_loss_reference": stop, "target_reference": target,
        "requires_human_confirmation": True,
        "execution_enabled": False,
        "warning": "Candidate only; verify live quote, spread, liquidity, ETF T+0/T+1 rules, fees and risk limits before any order."
    }
