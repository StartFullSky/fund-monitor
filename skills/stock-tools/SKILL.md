---
name: stock-tools
description: "A股行情查询、技术分析、涨跌停监控、关注股票管理"
triggers:
  - "股票"
  - "行情"
  - "K线"
  - "技术分析"
  - "涨跌停"
  - "关注股票"
  - "大盘"
---

# 股票工具 Skill

基于腾讯行情接口 + 新浪K线接口的 A 股工具集，零依赖（不需要 akshare 联网）。

## 脚本位置

所有脚本在 `~/AppData/Local/hermes/scripts/`：

| 脚本 | 功能 |
|---|---|
| `stock_utils.py` | 核心库：行情、K线、MySQL、Bark推送 |
| `stock_analysis.py` | K线技术分析（MA/RSI/MACD） |
| `stock_monitor.py` | 盘中异动监控（涨跌停、大幅波动） |
| `daily_morning_push.py` | 每日盘前晨报 |
| `watchlist.json` | 关注股票列表 |

## 常用操作

### 查行情
```python
import sys; sys.path.insert(0, 'C:/Users/X/AppData/Local/hermes/scripts')
from stock_utils import get_stock_realtime, get_market_overview
info = get_stock_realtime('600519')  # 茅台
overview = get_market_overview()     # 大盘三大指数
```

### 技术分析
```bash
python stock_analysis.py 600519 000858  # 分析指定股票
python stock_analysis.py                # 分析关注列表
python stock_analysis.py --push         # 分析并推送Bark
```

### 管理关注列表
```python
from stock_utils import load_watchlist, save_watchlist
codes = load_watchlist()           # ['600519', '000858', '300750']
codes.append('601318')             # 加平安
save_watchlist(codes)
```

### 查询数据库
```python
from stock_utils import query_db
tables = query_db('SHOW TABLES')
stocks = query_db('SELECT * FROM stock_info LIMIT 5')
```

## Cron Jobs

| 任务 | 时间 | 脚本 |
|---|---|---|
| 盘前晨报 | 周一~周五 9:25 | `daily_morning_push.py` |
| 异动监控 | 交易时段每3分钟 | `stock_monitor.py` |

## 接口说明

- **行情**: 腾讯 `qt.gtimg.cn`（快、稳、免费）← 首选
- **K线**: 新浪 `quotes.sina.cn`（日/周/月线）← 首选
- **akshare**: 仅作备用，东方财富后端经常 `RemoteDisconnected`
- **数据库**: 本地 MySQL `stock_agent`
- **推送**: Bark POST JSON

## Pitfalls

### akshare 东方财富后端不稳定
akshare 的 `stock_zh_a_spot_em()` / `stock_zh_a_hist()` 底层调用东方财富 API，国内网络经常 `RemoteDisconnected`。**优先用腾讯/新浪直接接口**，akshare 仅作备用。

### 腾讯行情前缀逻辑（重要）
代码前缀不能简单按 `6→sh, 其他→sz` 判断，ETF 和指数也需要 SH 前缀：
```python
if code.startswith('6') or code.startswith('5') or code.startswith('000'):
    prefix = 'sh'
else:
    prefix = 'sz'
```
覆盖：A股个股(6xxx=SH, 0xxx/3xxx=SZ)、ETF(5xxx=SH, 15xxx=SZ)、指数(000xxx=SH, 399xxx=SZ)

### pymysql 函数作用域
`import pymysql` 如果写在 `get_db_connection()` 内部，`query_db()` 里看不到 `pymysql` 变量。**必须在每个使用 pymysql 的函数内部都 import 一次**，或者在模块顶部 import。

### Cron Job 输出编码问题
Windows 上 cron job 输出中文会变成乱码（UTF-8 被 GBK 显示）。**解决方案**：cron 脚本中用英文输出，或无告警时静默退出（不输出任何内容）。

### GitHub API 推送文件（无 git）
当 git push 因 SSL/TLS 问题失败时，可用 GitHub REST API 直接上传文件：
```bash
CONTENT=$(cat file.py | base64 -w 0)
SHA=$(curl -s -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/contents/$file" | python -c "import sys,json; print(json.load(sys.stdin).get('sha',''))")
curl -s -X PUT -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/contents/$file" \
  -d "{\"message\":\"update\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\",\"branch\":\"main\"}"
```
注意：terminal 工具会 mask token，需从文件读取。

## Pitfalls

### 腾讯行情前缀逻辑
代码前缀不能简单按 `6→sh, 其他→sz` 判断，ETF 和指数也需要 SH 前缀：
```python
if code.startswith('6') or code.startswith('5') or code.startswith('000'):
    prefix = 'sh'
else:
    prefix = 'sz'
```
覆盖：A股个股(6xxx=SH, 0xxx/3xxx=SZ)、ETF(5xxx=SH, 15xxx=SZ)、指数(000xxx=SH, 399xxx=SZ)

### akshare 东方财富后端不稳定
akshare 的 `stock_zh_a_spot_em()` / `stock_zh_a_hist()` 底层调用东方财富 API，国内网络经常 `RemoteDisconnected`。**优先用腾讯/新浪直接接口**，akshare 仅作备用。

### Windows 写文件 `\\n` 被腐蚀
用 `write_file` 工具写 Python 脚本时，f-string 里的 `\\n` 可能被写成真正的换行符（0x0A），导致 `SyntaxError: unterminated string literal`。**修复方式**：用 `patch` 工具做 find-and-replace，它能正确处理转义。如果 `patch` 也失败，用终端 python 脚本按字节修复（0x0A→0x5C 0x6E）。

### pymysql 函数作用域
`import pymysql` 如果写在 `get_db_connection()` 内部，`query_db()` 里看不到 `pymysql` 变量。**必须在每个使用 pymysql 的函数内部都 import 一次**，或者在模块顶部 import。推荐写法：
```python
def query_db(sql, params=None):
    try:
        import pymysql
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except Exception as e:
        return {'error': str(e)}
```

## 接口详情

见 `references/api-details.md`

## GitHub API 推送

当 git push 失败时，可用 API 直接上传文件。详见 `references/github-api-push.md`
