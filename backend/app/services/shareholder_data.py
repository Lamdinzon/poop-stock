"""
集保結算所（TDCC）股權分散表：算「大戶持股比例」。

這份資料不是證交所的，是集保結算所每週更新的 CSV，網址不需要金鑰：
https://opendata.tdcc.com.tw/getOD.ashx?id=1-5

欄位：資料日期, 證券代號, 持股分級, 人數, 股數, 占集保庫存數比例%

持股分級是 1~17 的級距代碼，數字越大代表持股量越多，其中：
- 最大的級距編號（通常是17）是「合計」，代表100%，不是真正的分級，要排除
- 次大的級距（依社群慣例通常是15，也就是持股 1,000,001 股以上）
  是一般認知的「大戶」級距，這裡把它當作「大戶持股比例」的代表值

注意：這個級距對照關係沒有在真正連得到集保所網站的環境驗證過，
第一次串接時建議實際印出某支股票的完整分級資料，確認最大級距編號
跟數字是否符合預期（尤其排除掉全部是0的級距）。

這份CSV涵蓋所有股票、所有級距，檔案不小，抓下來後在記憶體整理成
{股票代號: 大戶持股比例} 的對照表，快取久一點（資料本身也才週更）。
"""

import csv
import io
import time
import httpx

TDCC_URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"

_CACHE: dict | None = None
_CACHE_TIME = 0.0
_CACHE_TTL_SECONDS = 60 * 60 * 24  # 資料週更，快取一天沒問題


async def _fetch_csv_text() -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(TDCC_URL)
        resp.raise_for_status()
        return resp.text


async def get_big_holder_ratio_map() -> dict[str, float]:
    """回傳 {股票代號: 大戶持股比例(%)}。抓不到資料時回傳空字典，不讓整條分析掛掉。"""
    global _CACHE, _CACHE_TIME

    now = time.time()
    if _CACHE is not None and (now - _CACHE_TIME) < _CACHE_TTL_SECONDS:
        return _CACHE

    try:
        text = await _fetch_csv_text()
    except httpx.HTTPError:
        return _CACHE or {}

    reader = csv.DictReader(io.StringIO(text))

    # 先把每檔股票的所有級距收集起來，再挑出「合計以外最大的那個級距」
    by_ticker: dict[str, dict[int, float]] = {}
    for row in reader:
        ticker = (row.get("證券代號") or "").strip()
        level_raw = row.get("持股分級")
        ratio_raw = row.get("占集保庫存數比例%")
        if not ticker or level_raw is None or ratio_raw is None:
            continue
        try:
            level = int(level_raw)
            ratio = float(ratio_raw)
        except ValueError:
            continue
        by_ticker.setdefault(ticker, {})[level] = ratio

    result: dict[str, float] = {}
    for ticker, levels in by_ticker.items():
        if not levels:
            continue
        max_level = max(levels)  # 通常是「合計」= 100%，排除掉
        # 級距16依社群開發者實測（finlab等）資料恆為0，是官方保留但沒在用的空級距，
        # 也要排除，不然「大戶持股」永遠會抓到0
        candidate_levels = [lv for lv in levels if lv != max_level and lv != 16]
        if not candidate_levels:
            continue
        big_holder_level = max(candidate_levels)
        result[ticker] = levels[big_holder_level]

    _CACHE = result
    _CACHE_TIME = now
    return result
