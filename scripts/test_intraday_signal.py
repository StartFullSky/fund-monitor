"""Tests for the ETF intraday candidate engine."""
import unittest

from scripts.intraday_signal import analyze_intraday_bars


def make_bars(n=40, rising=True):
    bars = []
    price = 1.0
    for i in range(n):
        price += (0.002 if rising else -0.002)
        bars.append({
            "timestamp": f"2026-10-30 09:{30 + i:02d}:00",
            "high": price + 0.003, "low": price - 0.003,
            "close": price, "volume": 1000.0 if i < n - 1 else 1800.0,
        })
    return bars


class IntradaySignalTests(unittest.TestCase):
    def test_insufficient_bars_is_hold(self):
        result = analyze_intraday_bars("510300", make_bars(10))
        self.assertEqual(result["action"], "HOLD")
        self.assertFalse(result["ready"])

    def test_result_never_enables_execution(self):
        result = analyze_intraday_bars("510300", make_bars())
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["requires_human_confirmation"])

    def test_invalid_ohlc_is_rejected(self):
        bars = make_bars()
        bars[-1]["high"] = bars[-1]["close"] - 1
        result = analyze_intraday_bars("510300", bars)
        self.assertEqual(result["reason"], "inconsistent_ohlc")

    def test_unsorted_bars_are_rejected(self):
        bars = make_bars()
        bars[0], bars[1] = bars[1], bars[0]
        result = analyze_intraday_bars("510300", bars)
        self.assertEqual(result["reason"], "bars_not_chronological")


if __name__ == "__main__":
    unittest.main()
