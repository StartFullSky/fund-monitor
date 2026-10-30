"""Unit tests for the intraday project's indicator calculations.

Run from repository root:
    python -m unittest scripts.test_intraday_indicators
"""
import math
import unittest

from scripts.stock_analysis import calculate_macd, calculate_rsi, ema_series


class IndicatorTests(unittest.TestCase):
    def test_ema_uses_sma_seed_and_recurses(self):
        values = [1.0, 2.0, 3.0, 4.0]
        ema = ema_series(values, 3)
        self.assertIsNone(ema[0])
        self.assertIsNone(ema[1])
        self.assertAlmostEqual(ema[2], 2.0)
        self.assertAlmostEqual(ema[3], 3.0)

    def test_rsi_flat_market_is_neutral(self):
        rsi = calculate_rsi([10.0] * 20, 14)
        self.assertTrue(math.isnan(rsi[13]))
        self.assertAlmostEqual(rsi[14], 50.0)
        self.assertAlmostEqual(rsi[-1], 50.0)

    def test_rsi_all_gains_is_100(self):
        rsi = calculate_rsi([float(i) for i in range(20)], 14)
        self.assertAlmostEqual(rsi[-1], 100.0)

    def test_rsi_all_losses_is_zero(self):
        rsi = calculate_rsi([float(20 - i) for i in range(20)], 14)
        self.assertAlmostEqual(rsi[-1], 0.0)

    def test_macd_flat_market_is_zero(self):
        dif, dea, hist = calculate_macd([10.0] * 80)
        self.assertAlmostEqual(dif[-1], 0.0)
        self.assertAlmostEqual(dea[-1], 0.0)
        self.assertAlmostEqual(hist[-1], 0.0)

    def test_macd_returns_aligned_series(self):
        values = [100.0 + i * 0.1 for i in range(80)]
        dif, dea, hist = calculate_macd(values)
        self.assertEqual(len(dif), len(values))
        self.assertEqual(len(dea), len(values))
        self.assertEqual(len(hist), len(values))
        self.assertTrue(math.isfinite(dif[-1]))
        self.assertTrue(math.isfinite(dea[-1]))
        self.assertTrue(math.isfinite(hist[-1]))

    def test_invalid_periods_raise(self):
        with self.assertRaises(ValueError):
            calculate_rsi([1.0, 2.0], 0)
        with self.assertRaises(ValueError):
            calculate_macd([1.0, 2.0], fast=26, slow=12, signal=9)


if __name__ == "__main__":
    unittest.main()
