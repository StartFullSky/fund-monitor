"""
基金持仓异动监控 — 已合并到 stock_monitor.py
保留此文件以兼容现有 cron job，实际调用 stock_monitor.main()
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接委托给统一监控
from stock_monitor import main

if __name__ == '__main__':
    main()
