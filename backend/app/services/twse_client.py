"""
證交所 OpenAPI 串接。

免費、不需金鑰。這裡先抓兩個端點：
1. STOCK_DAY_ALL：全部上市股票的每日收盤資訊（收盤價、漲跌、成交量）
2. BWIBBU_ALL：全部上市股票的本益比／殖利率／股價淨值比

注意：正式串接前建議先打 https://openapi.twse.com.tw/ 的 swagger 確認欄位名稱
沒有變動，證交所偶爾會微調回傳格式。

MVP 階段先用簡單的記憶體快取（TTL）避免每次請求都打證交所，
之後如果要正式上線，建議換成 Redis 或排程批次抓取寫入資料庫。
"""

import time
import httpx

TWSE_BASE = "https://openapi.twse.com.tw/v1"
STOCK_DAY_ALL_URL = f"{TWSE_BASE}/exchangeReport/STOCK_DAY_ALL"
BWIBBU_ALL_URL = f"{TWSE_BASE}/exchangeReport/BWIBBU_ALL"
# 集中市場每日成交量前20名證券：跑馬燈用這個，比較貼近「熱門股」的感覺
TOP20_VOLUME_URL = f"{TWSE_BASE}/exchangeReport/MI_INDEX20"

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 小時，反正我們不做即時分析


async def _fetch_json(url: str) -> list[dict]:
    now = time.time()
    cached = _CACHE.get(url)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    _CACHE[url] = (now, data)
    return data


async def get_daily_quotes() -> list[dict]:
    """每日收盤資訊：代號、名稱、收盤價、漲跌、成交量等。"""
    return await _fetch_json(STOCK_DAY_ALL_URL)


async def get_valuation_data() -> list[dict]:
    """本益比、殖利率、股價淨值比。"""
    return await _fetch_json(BWIBBU_ALL_URL)


async def get_top20_by_volume() -> list[dict]:
    """
    每日成交量前20名證券，給跑馬燈用。

    漲跌方向改用「收盤價 vs 開盤價」直接比較來判斷，不依賴 Dir／Change
    這兩個欄位——這兩欄證交所的格式不算穩定（可能是全形符號、也可能是
    未帶正負號的絕對值），之前就因為這樣踩過「全部顯示上漲」的雷。
    開盤價、收盤價是單純數字，比較不會出錯。
    """
    raw = await _fetch_json(TOP20_VOLUME_URL)
    items = []
    for row in raw:
        code = row.get("Code")
        name = row.get("Name", "").strip()
        if not code or not name:
            continue
        try:
            close_price = float(str(row.get("ClosingPrice", "")).replace(",", ""))
        except ValueError:
            close_price = None
        try:
            open_price = float(str(row.get("OpeningPrice", "")).replace(",", ""))
        except ValueError:
            open_price = None

        if close_price is not None and open_price is not None:
            change = round(close_price - open_price, 2)
            if change > 0:
                trend = "up"
            elif change < 0:
                trend = "down"
            else:
                trend = "flat"
        else:
            change = None
            trend = "flat"

        items.append(
            {
                "ticker": code,
                "name": name,
                "close_price": close_price,
                "change": change,
                "trend": trend,
            }
        )
    return items


async def get_merged_stock_pool() -> list[dict]:
    """把收盤資訊跟估值資訊用股票代號合併成一份清單，方便選股邏輯使用。"""
    quotes = await get_daily_quotes()
    valuations = await get_valuation_data()

    valuation_map = {v.get("Code"): v for v in valuations}

    pool = []
    for q in quotes:
        code = q.get("Code")
        if not code:
            continue
        val = valuation_map.get(code, {})
        try:
            close_price = float(q.get("ClosingPrice", "0").replace(",", ""))
        except (ValueError, AttributeError):
            close_price = None
        try:
            pe_ratio = float(val.get("PEratio", "")) if val.get("PEratio") else None
        except ValueError:
            pe_ratio = None

        pool.append(
            {
                "ticker": code,
                "name": q.get("Name", "").strip(),
                "close_price": close_price,
                "pe_ratio": pe_ratio,
                "dividend_yield": val.get("DividendYield"),
            }
        )
    return pool
