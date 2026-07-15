---
name: stock-tools
description: "A股行情查询、技术分析、异动监控、关注股票管理"
triggers:
  - "股票"
  - "行情"
  - "K线"
  - "技术分析"
  - "涨跌停"
---

# 股票工具集

基于腾讯/新浪行情接口的 A 股工具集，零依赖。

**设计原则：Skill = 使用说明，不是代码仓库。** 脚本放 `scripts/`，Skill 只包含用法和注意事项。

## 脚本位置

所有脚本在 `~/AppData/Local/hermes/scripts/`：

| 脚本 | 功能 |
|------|------|
| `stock_utils.py` | 核心库：行情、K线、数据库、推送 |
| `stock_analysis.py` | K线技术分析（MA/RSI/MACD） |
| `stock_monitor.py` | 盘中异动监控 |
| `daily_morning_push.py` | 每日盘前晨报 |
| `watchlist.json` | 关注股票列表 |

## 常用操作

### 查行情
```python
from stock_utils import get_stock_realtime, get_market_overview
info = get_stock_realtime('600519')  # 茅台
overview = get_market_overview()     # 大盘三大指数
```

### 技术分析
```bash
python stock_analysis.py 600519 000858  # 分析指定股票
python stock_analysis.py --push         # 分析并推送
```

### 管理关注列表
```python
from stock_utils import load_watchlist, save_watchlist
codes = load_watchlist()
codes.append('601318')
save_watchlist(codes)
```

## Cron Jobs

| 任务 | 时间 | 脚本 |
|------|------|------|
| 盘前晨报 | 周一~周五 9:25 | `daily_morning_push.py` |
| 异动监控 | 交易时段每3分钟 | `stock_monitor.py` |

## Pitfalls

### 腾讯行情前缀
```python
if code.startswith('6') or code.startswith('5') or code.startswith('000'):
    prefix = 'sh'
else:
    prefix = 'sz'
```

### akshare 不稳定
优先用腾讯/新浪直接接口，akshare 仅作备用。

### Cron 输出中文乱码
Windows 系统用 GBK 显示 UTF-8 中文，脚本输出用英文或静默退出。

### write_file 的 \n 问题
f-string 里的 `\n` 可能被写成真换行符。用 `patch` 工具修复。
