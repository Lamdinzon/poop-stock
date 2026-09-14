"""
三大法人買賣超（近一個月累加 + 跟上個月比較的變動率）。

重要：這個資料不在 openapi.twse.com.tw 底下，是證交所另一個系列的報表
（www.twse.com.tw/rwd/zh/fund/T86），只給「單日」資料，不接受區間查詢。
要拿到「近一個月」的資料，只能一天一天往回抓、自己加總；
「跟上個月比」則是再往前抓一個20交易日的區間，兩段各自加總後比較。

回傳結構跟 openapi 那組也不一樣，是 {"stat": "OK", "date": ..., "fields": [...], "data": [[...], ...]}
形式，欄位名放在 fields、每一列資料放在 data，要自己把兩者對齊成字典。

欄位名稱依 TWSE 官方頁面通常包含「證券代號」跟「三大法人買賣超股數」，
但這裡沒辦法在有網路的環境實際打一次確認，所以用「找出欄位名稱包含
關鍵字」的防禦性寫法，而不是寫死欄位索引。

單位是「股」，這裡統一換算成「張」（除以1000）比較符合台股習慣的顯示方式。

效能考量：近一個月+上個月合計約40個交易日，要打約40次API，
但每次都是全市場資料一次查完，所以整包快取，快取時間拉長到12小時。
"""

import time
import datetime
import httpx

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
TRADING_DAYS_PER_WINDOW = 20  # 一個月大約20個交易日
LOOKBACK_BUFFER_DAYS = 40  # 往回抓的行事曆天數緩衝，含週末/假日

_CACHE: dict[str, dict] | None = None
_CACHE_TIME = 0.0
_CACHE_TTL_SECONDS = 60 * 60 * 12


def _find_field_index(fields: list[str], keywords: list[str]) -> int | None:
    for i, name in enumerate(fields):
        if all(kw in name for kw in keywords):
            return i
    return None


async def _fetch_one_day(client: httpx.AsyncClient, date_str: str) -> dict | None:
    try:
        resp = await client.get(
            T86_URL, params={"date": date_str, "selectType": "ALL", "response": "json"}
        )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError:
        return None

    if payload.get("stat") != "OK":
        return None  # 非交易日或查無資料
    return payload


async def _fetch_recent_trading_days(client: httpx.AsyncClient, num_days_needed: int) -> list[dict]:
    """回傳最近 num_days_needed 個交易日的原始 payload，由新到舊排序。"""
    results: list[dict] = []
    today = datetime.date.today()
    offset = 0
    max_checks = num_days_needed + LOOKBACK_BUFFER_DAYS
    checked = 0

    while len(results) < num_days_needed and checked < max_checks:
        day = today - datetime.timedelta(days=offset)
        offset += 1
        checked += 1
        if day.weekday() >= 5:  # 週六日直接跳過
            continue
        payload = await _fetch_one_day(client, day.strftime("%Y%m%d"))
        if payload:
            results.append(payload)

    return results


def _sum_payloads(payloads: list[dict]) -> dict[str, float]:
    """把好幾天的 T86 payload 加總成 {股票代號: 合計買賣超(股)}。"""
    totals: dict[str, float] = {}

    for payload in payloads:
        fields = payload.get("fields", [])
        rows = payload.get("data", [])

        code_idx = _find_field_index(fields, ["證券代號"])
        net_idx = _find_field_index(fields, ["三大法人", "買賣超"])
        if code_idx is None:
            continue
        if net_idx is None:
            # 找不到現成的「三大法人合計」欄位，退而求其次，
            # 把外資／投信／自營商各自的買賣超欄位加總
            sub_indices = [
                i for i, name in enumerate(fields) if "買賣超" in name and "自營商" not in name
            ] + [
                i
                for i, name in enumerate(fields)
                if "自營商" in name and "買賣超" in name and "合計" in name
            ]
        else:
            sub_indices = None

        for row in rows:
            if code_idx >= len(row):
                continue
            code = str(row[code_idx]).strip()
            if not code:
                continue
            try:
                if net_idx is not None:
                    net_shares = float(str(row[net_idx]).replace(",", ""))
                else:
                    net_shares = sum(
                        float(str(row[i]).replace(",", ""))
                        for i in (sub_indices or [])
                        if i < len(row) and str(row[i]).strip() not in ("", "-")
                    )
            except ValueError:
                continue

            totals[code] = totals.get(code, 0.0) + net_shares / 1000  # 換算成張

    return totals


async def get_institutional_net_month_map() -> dict[str, dict]:
    """回傳 {股票代號: {net: 近一個月合計買賣超(張), mom_pct: 相比上個月變動(%)}}。"""
    global _CACHE, _CACHE_TIME

    now = time.time()
    if _CACHE is not None and (now - _CACHE_TIME) < _CACHE_TTL_SECONDS:
        return _CACHE

    async with httpx.AsyncClient(timeout=15) as client:
        payloads = await _fetch_recent_trading_days(client, TRADING_DAYS_PER_WINDOW * 2)

    current_payloads = payloads[:TRADING_DAYS_PER_WINDOW]
    previous_payloads = payloads[TRADING_DAYS_PER_WINDOW : TRADING_DAYS_PER_WINDOW * 2]

    current_totals = _sum_payloads(current_payloads)
    previous_totals = _sum_payloads(previous_payloads)

    result: dict[str, dict] = {}
    for code in set(current_totals) | set(previous_totals):
        net = current_totals.get(code)
        prev_net = previous_totals.get(code)
        if net is None:
            continue

        mom_pct = None
        if prev_net:
            mom_pct = round((net - prev_net) / abs(prev_net) * 100, 2)

        result[code] = {"net": round(net, 1), "mom_pct": mom_pct}

    if result:
        _CACHE = result
        _CACHE_TIME = now
        return _CACHE

    return _CACHE or {}
