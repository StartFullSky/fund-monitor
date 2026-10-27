# 东方财富基金数据 API

## 基金持仓查询

**URL**: `https://fundf10.eastmoney.com/FundArchivesDatas.aspx`

**参数**:
- `type=jjcc` (基金持仓)
- `code={基金代码}`
- `topline=10` (前N大)
- `year=2026&month=3` (报告期)

**示例**: `https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=017641&topline=10&year=2026&month=3`

**解析**: 返回 HTML，用正则提取重仓股
```python
rows = re.findall(r'<td[^>]*>.*?<a[^>]*>(\d{6})</a>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)
```

## 基金基本信息

**URL**: `https://fundf10.eastmoney.com/jbgk_{基金代码}.html`

**解析**: 用正则提取基金名称、类型、投资方向
```python
name = re.findall(r'<title>(.*?)_', html)
ftype = re.findall(r'基金类型.*?<td.*?>(.*?)</td>', html, re.DOTALL)
```

## 注意事项

- 返回 HTML 而非 JSON，需要正则解析
- 联接基金（ETF联接）不直接披露股票持仓，需要查底层 ETF
- 数据有延迟（季报披露后才有）
- 频率限制：不要太频繁请求，建议间隔 1-2 秒
