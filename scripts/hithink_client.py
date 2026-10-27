"""
同花顺金融数据客户端 — fund-monitor 主数据源（fuyao.aicubes.cn）
- 统一信封校验 code==0；限流(4001)/5xxx/网络错误有界退避，最多 3 次
- 凭据：环境变量优先，回退用户级 credentials.env（%APPDATA%/hithink-finance/）
- 提供：基金消歧、净值、重仓持仓、ETF快照、A股批量快照
- 不可用时返回 None/空结构，由调用方回退旧数据源（腾讯/天天基金）
"""
import json
import os
import time
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = os.environ.get('HITHINK_FINANCE_BASE_URL', 'https://fuyao.aicubes.cn')
_TIMEOUT = 10
_KEY_PREFIX = 'HITHINK_FINANCE_' + 'API_KEY='  # 运行时拼接，避免工具层脱敏误伤
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hithink_cache.json')


def _load_key():
    key = os.environ.get('HITHINK_FINANCE_' + 'API_KEY', '').strip()
    if key:
        return key
    candidates = []
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        candidates.append(os.path.join(appdata, 'hithink-finance', 'credentials.env'))
    candidates.append(os.path.join(os.path.expanduser('~'), '.config', 'hithink-finance', 'credentials.env'))
    for path in candidates:
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(_KEY_PREFIX):
                        value = line[len(_KEY_PREFIX):].strip().strip('"')
                        if value:
                            return value
        except OSError:
            continue
    return ''


API_KEY = _load_key()


def is_available():
    return bool(API_KEY)


def api_get(path, params=None):
    """GET 请求并校验业务信封；成功返回 data(dict)，失败返回 None"""
    if not API_KEY:
        return None
    qs = urlencode({k: v for k, v in (params or {}).items() if v not in (None, '')})
    url = BASE_URL + path + ('?' + qs if qs else '')
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={'X-api-key': API_KEY, 'User-Agent': 'fund-monitor/1.0'})
            with urlopen(req, timeout=_TIMEOUT) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
            envelope = json.loads(body)
            code = envelope.get('code')
            if code == 0:
                return envelope.get('data') or {}
            if code == 4001 or (isinstance(code, int) and code >= 5000):
                time.sleep(0.5 * attempt)  # 限流/服务端错误退避重试
                continue
            return None  # 1xxx/2xxx/3xxx 参数或数据问题，不重试
        except (URLError, OSError, ValueError) as e:
            if attempt >= 3:
                print(f'⚠️ 同花顺接口失败 {path}: {e}')
                return None
            time.sleep(0.5 * attempt)
    return None


# ============ 缓存（简单 JSON 文件） ============
def _cache_get(key, ttl_seconds):
    try:
        with open(_CACHE_FILE, encoding='utf-8') as f:
            entry = json.load(f).get(key)
        if entry and time.time() - entry.get('ts', 0) < ttl_seconds:
            return entry.get('data')
    except (OSError, ValueError):
        pass
    return None


def _cache_put(key, data):
    try:
        cache = {}
        try:
            with open(_CACHE_FILE, encoding='utf-8') as f:
                cache = json.load(f)
        except (OSError, ValueError):
            pass
        cache[key] = {'ts': time.time(), 'data': data}
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass


# ============ 标的消歧 ============
def resolve_fund_thscode(code):
    """基金代码(6位) -> 完整 thscode（如 017641.OF / 588000.SH），带7天缓存"""
    code = str(code).strip()
    if '.' in code:
        return code
    cache_key = 'resolve:' + code
    cached = _cache_get(cache_key, 7 * 86400)
    if cached:
        return cached
    data = api_get('/api/meta/tickers/search', {
        'q': code, 'limit': '10', 'asset_type': 'fund-otc,fund-etf,fund-lof,fund-reits',
    })
    thscode = None
    if data:
        for item in data.get('item') or []:
            if item.get('ticker') == code:
                thscode = item.get('thscode')
                break
        if not thscode and data.get('item'):
            thscode = data['item'][0].get('thscode')
    if thscode:
        _cache_put(cache_key, thscode)
    return thscode


# ============ 净值 ============
def fund_nav_latest(code):
    """最新净值 {'nav': float, 'date': 'MM-DD'}，失败返回 None"""
    thscode = resolve_fund_thscode(code)
    if not thscode:
        return None
    data = api_get('/api/fund/performance/nav', {'thscode': thscode, 'nav_type': 'unit'})
    items = (data or {}).get('item') or []
    if not items:
        return None
    last = items[-1]
    nav_date = last.get('nav_date')
    date_str = ''
    if nav_date:
        date_str = datetime.fromtimestamp(nav_date / 1000).strftime('%m-%d')
    nav = last.get('unit_nav')
    return {'nav': nav, 'date': date_str} if nav is not None else None


def fund_nav_series(code, range_='week'):
    """区间净值序列 [{'date': 'YYYY-MM-DD', 'nav': float}]"""
    thscode = resolve_fund_thscode(code)
    if not thscode:
        return []
    data = api_get('/api/fund/performance/nav', {'thscode': thscode, 'range': range_, 'nav_type': 'unit'})
    items = (data or {}).get('item') or []
    series = []
    for it in items:
        nav = it.get('unit_nav')
        nav_date = it.get('nav_date')
        if nav is None or not nav_date:
            continue
        series.append({'date': datetime.fromtimestamp(nav_date / 1000).strftime('%Y-%m-%d'), 'nav': nav})
    return series


# ============ 重仓持仓 ============
def fund_holdings(code):
    """重仓持仓 {'main_industry','stock_ratio_pct','stocks': [{'code','name','ratio'}]}，失败返回 None"""
    cache_key = 'hold:' + str(code).strip()
    cached = _cache_get(cache_key, 86400)
    if cached is not None:
        return cached
    thscode = resolve_fund_thscode(code)
    if not thscode:
        return None
    data = api_get('/api/fund/portfolio/holdings', {'thscode': thscode})
    if not data:
        return None
    stocks = []
    for item in data.get('item') or []:
        if item.get('asset_type') != 'stock':
            continue
        ticker = item.get('ticker')
        if not ticker:
            continue
        stocks.append({
            'code': ticker,
            'name': item.get('stock_name'),
            'ratio': item.get('security_market_value_rate_pct') or item.get('hold_ratio'),
            'rank': item.get('investment_rank'),
        })
    stocks.sort(key=lambda s: (s.get('rank') is None, s.get('rank') or 0))
    result = {
        'main_industry': data.get('main_industry'),
        'stock_ratio_pct': data.get('total_stock_ratio_pct'),
        'concentration_ratio': data.get('concentration_ratio'),
        'stocks': stocks,
    }
    _cache_put(cache_key, result)
    return result


# ============ 行情 ============
def etf_snapshot(code):
    """场内 ETF/LOF 快照 {'price','change_pct'}，失败返回 None"""
    thscode = resolve_fund_thscode(code)
    if not thscode:
        return None
    data = api_get('/api/fund/market/snapshot', {'thscode': thscode})
    items = (data or {}).get('item') or []
    if not items:
        return None
    it = items[0]
    price = it.get('last_price')
    change = it.get('price_change_ratio_pct')
    if price is None:
        return None
    return {'price': price, 'change_pct': change, 'thscode': it.get('thscode')}


def resolve_stock_thscode(code):
    """A股 6 位代码 -> thscode，meta 检索精确消歧（7天缓存）；失败回退结构推断"""
    code = str(code).strip()
    if '.' in code:
        return code
    cache_key = 'stock:' + code
    cached = _cache_get(cache_key, 7 * 86400)
    if cached:
        return cached
    thscode = None
    data = api_get('/api/meta/tickers/search', {'q': code, 'limit': '10', 'asset_type': 'a-share'})
    for item in (data or {}).get('item') or []:
        if item.get('ticker') == code:
            thscode = item.get('thscode')
            break
    if not thscode and code.isdigit():
        thscode = code + ('.SH' if code.startswith('6') else '.SZ')
    if thscode:
        _cache_put(cache_key, thscode)
    return thscode


def a_share_quotes(codes):
    """A股批量快照 {code: {'price','change_pct'}}；codes 为 6 位数字代码"""
    codes = [str(c).strip() for c in codes if str(c).strip().isdigit()]
    if not codes:
        return {}
    thscodes = []
    mapping = {}
    for c in codes:
        ths = resolve_stock_thscode(c)
        if ths:
            thscodes.append(ths)
            mapping[ths] = c
    if not thscodes:
        return {}
    data = api_get('/api/a-share/prices/snapshot', {'thscodes': ','.join(thscodes)})
    result = {}
    for item in (data or {}).get('item') or []:
        code = mapping.get(item.get('thscode'))
        price = item.get('last_price')
        if code and price is not None:
            result[code] = {'price': price, 'change_pct': item.get('price_change_ratio_pct')}
    return result
