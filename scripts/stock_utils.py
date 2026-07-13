"""
股票工具库 — 供其他脚本调用
提供：行情查询、新闻获取、涨跌停监控、技术分析、Bark推送、MySQL连接
"""
import json
import sys
import os
from datetime import datetime, timedelta
from urllib.request import urlopen, Request, ProxyHandler, build_opener

# ============ 配置 ============
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
BARK_KEY = ''
DB_CONFIG = {'host': '127.0.0.1', 'port': 3306, 'user': 'root', 'password': '123456', 'db': 'stock_agent', 'charset': 'utf8mb4'}

def load_config():
    global BARK_KEY
    try:
        import yaml
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f)
        BARK_KEY = (raw.get('bark') or {}).get('key', '')
    except Exception:
        pass

load_config()

# ============ Bark 推送 ============
def send_bark(title, content, **kwargs):
    """发送 Bark 推送。支持额外参数如 group, sound, url, icon 等。"""
    if not BARK_KEY:
        print(f"❌ Bark未配置\n{title}\n{content}")
        return False
    url = f'https://api.day.app/{BARK_KEY}'
    payload = {'title': title, 'body': content, 'group': 'fund-monitor'}
    payload.update(kwargs)
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = Request(url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"❌ Bark推送失败: {e}")
        return False

# ============ AKShare 股票数据 ============
def _tencent_quote(code):
    """腾讯行情接口（轻量、稳定）。支持 A股 和 港股（5位数字前缀）。"""
    # 港股：5位数字，腾讯格式 hk{code}
    if code.isdigit() and len(code) == 5:
        prefix = 'hk'
    elif code.startswith('6') or code.startswith('5') or code.startswith('000'):
        prefix = 'sh'
    else:
        prefix = 'sz'
    url = f'http://qt.gtimg.cn/q={prefix}{code}'
    try:
        resp = urlopen(url, timeout=8)
        raw = resp.read().decode('gbk', errors='ignore')
        parts = raw.split('~')
        if len(parts) < 35:
            return None
        # 港股字段布局与A股略有不同
        if prefix == 'hk':
            name = parts[1] if len(parts) > 1 else code
            try:
                price = float(parts[3])
                prev_close = float(parts[4])
                change_pct = float(parts[32]) if parts[32] else 0
                change_amt = float(parts[31]) if parts[31] else 0
                volume = float(parts[6]) if parts[6] else 0
                amount = float(parts[37]) if len(parts) > 37 and parts[37] else 0
            except (ValueError, IndexError):
                return None
            return {
                'code': code, 'name': name,
                'price': price, 'prev_close': prev_close,
                'open': float(parts[5]) if parts[5] else price,
                'volume': volume, 'amount': amount,
                'high': float(parts[33]) if len(parts) > 33 and parts[33] else price,
                'low': float(parts[34]) if len(parts) > 34 and parts[34] else price,
                'change_pct': change_pct, 'change_amt': change_amt,
                'turnover': float(parts[38]) if len(parts) > 38 and parts[38] else 0,
                'market': 'HK',
            }
        return {
            'code': code, 'name': parts[1],
            'price': float(parts[3]), 'prev_close': float(parts[4]),
            'open': float(parts[5]), 'volume': float(parts[6]),
            'high': float(parts[33]) if parts[33] else float(parts[3]),
            'low': float(parts[34]) if parts[34] else float(parts[3]),
            'change_pct': float(parts[32]) if parts[32] else 0,
            'change_amt': float(parts[31]) if parts[31] else 0,
            'amount': float(parts[37]) if parts[37] else 0,
            'turnover': float(parts[38]) if parts[38] else 0,
            'market': 'A',
        }
    except Exception:
        return None

def get_stock_realtime(code):
    """获取单只股票实时行情，返回 dict"""
    import akshare as ak
    # 优先用腾讯接口（快、稳）
    result = _tencent_quote(code)
    if result:
        return result
    # 备用：akshare 日线
    try:
        df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
        if df is not None and not df.empty:
            r = df.iloc[-1]
            return {
                'code': code, 'name': str(r.get('股票代码', code)),
                'price': float(r['收盘']), 'change_pct': float(r.get('涨跌幅', 0)),
                'change_amt': float(r.get('涨跌额', 0)), 'volume': float(r.get('成交量', 0)),
                'amount': float(r.get('成交额', 0)), 'high': float(r.get('最高', 0)),
                'low': float(r.get('最低', 0)), 'open': float(r.get('今开', r['收盘'])),
                'prev_close': float(r.get('昨收', r['收盘'])), 'turnover': float(r.get('换手率', 0)),
            }
    except Exception:
        pass
    return None

def get_stock_kline(code, period='daily', days=60):
    """获取K线数据 — 新浪接口，返回 list of dict"""
    prefix = 'sh' if code.startswith('6') or code.startswith('5') or code.startswith('000') else 'sz'
    scale_map = {'daily': 240, 'weekly': 1200, 'monthly': 7200}
    scale = scale_map.get(period, 240)
    url = f'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_k=/CN_MarketDataService.getKLineData?symbol={prefix}{code}&scale={scale}&ma=no&datalen={days}'
    try:
        resp = urlopen(url, timeout=10)
        raw = resp.read().decode('utf-8', errors='ignore')
        # 解析 JSONP: var _k=([{...}]);
        start = raw.find('([')
        end = raw.rfind('])')
        if start < 0 or end < 0:
            return None
        import json
        data = json.loads(raw[start+1:end+1])
        return [{'date': d['day'], 'open': float(d['open']), 'high': float(d['high']),
                 'low': float(d['low']), 'close': float(d['close']), 'volume': int(d['volume'])} for d in data]
    except Exception:
        return None

def get_stock_news(code):
    """获取个股新闻"""
    import akshare as ak
    try:
        df = ak.stock_news_em(symbol=code)
        return df.head(10).to_dict('records') if df is not None else []
    except Exception:
        return []

def get_market_overview():
    """获取大盘概况（上证/深证/创业板）— 腾讯接口"""
    indices = [('上证指数', 'sh000001'), ('深证成指', 'sz399001'), ('创业板指', 'sz399006')]
    codes = ','.join(c for _, c in indices)
    try:
        resp = urlopen(f'http://qt.gtimg.cn/q={codes}', timeout=8)
        raw = resp.read().decode('gbk', errors='ignore')
        result = []
        for line in raw.strip().split('\n'):
            line = line.strip().rstrip(';')
            if '=' not in line:
                continue
            parts = line.split('=', 1)[1].strip('"').split('~')
            if len(parts) < 35:
                continue
            result.append({
                'name': parts[1], 'code': parts[2],
                'price': float(parts[3]), 'change_pct': float(parts[32]) if parts[32] else 0
            })
        return result
    except Exception as e:
        return []

def get_limit_up_down():
    """获取涨跌停股票列表"""
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
        up_list = []
        if df is not None and not df.empty:
            for _, r in df.head(20).iterrows():
                up_list.append({'code': r['代码'], 'name': r['名称'], 'price': float(r['最新价']), 'change_pct': float(r['涨跌幅'])})
        return up_list
    except Exception:
        return []

def get_financial_calendar():
    """获取财经日历（今日重要事件）"""
    import akshare as ak
    try:
        today = datetime.now().strftime('%Y%m%d')
        df = ak.macro_china_cx_pmi()
        # 备用：用东方财富财经日历
        return []
    except Exception:
        return []

# ============ MySQL 操作 ============
def get_db_connection():
    """获取 MySQL 连接"""
    try:
        import pymysql
        conn = pymysql.connect(**DB_CONFIG, connect_timeout=5)
        return conn
    except Exception as e:
        return None

def query_db(sql, params=None):
    """执行查询，返回结果列表"""
    try:
        import pymysql
        conn = get_db_connection()
        if not conn:
            return {'error': '数据库连接失败'}
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except Exception as e:
        return {'error': str(e)}
    finally:
        if conn:
            conn.close()

# ============ 关注股票列表 ============
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watchlist.json')

def load_watchlist():
    """加载关注股票列表"""
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return ['600519', '000858', '300750']  # 默认：茅台、五粮液、宁德时代

def save_watchlist(codes):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False)

# ============ 工具函数 ============
def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def pct(value):
    return f"{'+' if value >= 0 else ''}{value:.2f}%"

def is_trading_time():
    """判断当前是否为交易时间"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time
    morning = (time(9, 30), time(11, 30))
    afternoon = (time(13, 0), time(15, 0))
    return (morning[0] <= t <= morning[1]) or (afternoon[0] <= t <= afternoon[1])

def is_pre_market():
    """判断是否为盘前时间（9:00-9:30）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time
    return time(9, 0) <= t <= time(9, 30)
