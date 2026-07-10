# 基金数据 API

## 东方财富基金 API

### 基金基本信息
```
https://fundf10.eastmoney.com/jbgk_{基金代码}.html
```

### 基金持仓
```
https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={基金代码}&topline=10&year=2026&month=3
```

### 基金净值
```
https://api.fund.eastmoney.com/f10/lsjz?fundCode={基金代码}&pageIndex=1&pageSize=20
```

## 腾讯行情 API

### 实时行情
```
http://qt.gtimg.cn/q={前缀}{代码}
```
前缀：sh（6xxx/5xxx/000xxx）、sz（0xxx/3xxx/15xxx）

### 响应格式
```
v_sh600519="1~贵州茅台~600519~1197.45~1182.19~..."
```
字段：[0]市场 [1]名称 [2]代码 [3]最新价 [4]昨收 [5]今开 [6]成交量 [31]涨跌额 [32]涨跌幅 [33]最高 [34]最低 [37]成交额 [38]换手率

## 新浪 K 线 API

### 日 K 线
```
https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k=/CN_MarketDataService.getKLineData?symbol={前缀}{代码}&scale=240&ma=no&datalen=60
```

### 响应格式
JSONP：`var _k=([{day:"2026-01-01",open:"100",high:"110",low:"90",close:"105",volume:"1000"},...])`

## 金十数据 MCP

通过 jin10_client.py 调用，获取实时金价（CZBJCJ 代码）。

## Bark 推送 API

### POST JSON（推荐，避免中文乱码）
```
POST https://api.day.app/{key}
Content-Type: application/json

{"title": "标题", "body": "内容"}
```

### GET 方式（中文会乱码）
```
GET https://api.day.app/{key}/{标题}/{内容}
```
