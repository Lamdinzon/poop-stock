"""
單一股票的成交量日增率。

這個不是 openapi.twse.com.tw 那組，是證交所另一個經典端點：
https://www.twse.com.tw/exchangeReport/STOCK_DAY

丟一個股票代號 + 日期，會回傳「那個月」該股票每天的成交資訊
（日期、成交股數、成交金額、開高低收、漲跌、成交筆數）。

因為這是「整個股票池裡2000檔股票都查一次」會很重的那種查詢，
所以設計上只在使用者這次抽到的那一支股票才呼叫一次，
不會對整個股票池做（那樣要打上千次API，不切實際）。

重要：這裡故意「跳過最新一筆交易日」，用「前一天 vs 前兩天」來算日增率，
而不是「今天 vs 昨天」。原因是收盤價／本益比那些欄位來自另一個有6小時快取
的資料源，如果這裡抓的是即時最新一天，兩邊參照的交易日可能對不上
（例如收盤價還停留在上一個快取的日期，但這裡已經抓到最新一天），
故意慢一拍反而比較能跟其他欄位對齊，符合我們「不做即時分析」的原則。

如果剛好是月初、資料筆數不夠，會自動往前一個月補抓一次，確保抓得到
足夠的天數可以比較。
"""

import time
import datetime
import httpx

STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
MIN_ROWS_NEEDED = 3  # 要跳過最新一筆，所以至少要抓到3天資料才夠算比較

_CACHE: dict[str, tuple[float, float | None]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 6


async def _fetch_month(client: httpx.AsyncClient, ticker: str, date: datetime.date) -> dict:
    resp = await client.get(
        STOCK_DAY_URL,
        params={"response": "json", "date": date.strftime("%Y%m01"), "stockNo": ticker},
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("stat") != "OK":
        return {"fields": [], "data": []}
    return {"fields": payload.get("fields", []), "data": payload.get("data", [])}


async def get_volume_change_pct(ticker: str) -> float | None:
    """回傳「前一個交易日 vs 前兩個交易日」成交量的變化百分比（故意不用最新一天）。"""
    now = time.time()
    cached = _CACHE.get(ticker)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    today = datetime.date.today()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            this_month = await _fetch_month(client, ticker, today)
            fields, rows = this_month["fields"], this_month["data"]
            if len(rows) < MIN_ROWS_NEEDED:
                # 這個月交易日還不夠，往前一個月補
                prev_month_date = today.replace(day=1) - datetime.timedelta(days=1)
                prev_month = await _fetch_month(client, ticker, prev_month_date)
                fields = fields or prev_month["fields"]
                rows = prev_month["data"] + rows
    except httpx.HTTPError:
        return None

    if len(rows) < MIN_ROWS_NEEDED or not fields:
        _CACHE[ticker] = (now, None)
        return None

    # 用欄位名稱找「成交股數」在第幾欄，比寫死index更不怕證交所調整欄位順序
    vol_idx = next((i for i, name in enumerate(fields) if "成交股數" in name), None)
    if vol_idx is None:
        _CACHE[ticker] = (now, None)
        return None

    try:
        # 用 [-2]、[-3] 而不是 [-1]、[-2]：故意跳過最新一天，理由見檔案開頭說明
        latest_volume = float(str(rows[-2][vol_idx]).replace(",", ""))
        prev_volume = float(str(rows[-3][vol_idx]).replace(",", ""))
    except (ValueError, IndexError):
        _CACHE[ticker] = (now, None)
        return None

    if not prev_volume:
        _CACHE[ticker] = (now, None)
        return None

    change_pct = round((latest_volume - prev_volume) / prev_volume * 100, 2)
    _CACHE[ticker] = (now, change_pct)
    return change_pct
