"""
公司基本面資料：產業別 + 營收成長率 + EPS。

資料來源：
1. t187ap05_L（上市公司每月營收彙總表）：產業別、月增率(MoM)、年增率(YoY)
2. t187ap06_L_ci（上市一般業公司綜合損益表）：抓每股盈餘(EPS)，
   並嘗試跟上一期比較算變動率。

注意：t187ap06_L_ci 這份資料有沒有包含「歷史多期」還是「只有最新一期」，
沒有在真正連得到證交所的環境測過。如果同一家公司在這份資料裡只有一筆，
eps_change_pct 就會一直是 None（只能顯示最新一期EPS，沒辦法算變動率），
這是資料源本身的限制，不是程式邏輯的bug。第一次串接時麻煩實際打一次
這個端點確認一下。
"""

import time
import httpx

TWSE_BASE = "https://openapi.twse.com.tw/v1"
MONTHLY_REVENUE_URL = f"{TWSE_BASE}/opendata/t187ap05_L"
EPS_URL = f"{TWSE_BASE}/opendata/t187ap06_L_ci"

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 12  # 月/季更新的資料，快取久一點沒關係


async def _fetch_json(url: str) -> list[dict]:
    now = time.time()
    cached = _CACHE.get(url)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    _CACHE[url] = (now, data)
    return data


def _to_float(value) -> float | None:
    if value in (None, "", "-", "N/A"):
        return None
    try:
        return round(float(str(value).replace(",", "")), 2)
    except ValueError:
        return None


async def get_monthly_revenue_map() -> dict[str, dict]:
    """回傳 {股票代號: {industry, revenue_yoy, revenue_mom}}。"""
    try:
        raw = await _fetch_json(MONTHLY_REVENUE_URL)
    except httpx.HTTPError:
        return {}

    result: dict[str, dict] = {}
    for row in raw:
        code = row.get("公司代號")
        if not code:
            continue
        result[code] = {
            "industry": (row.get("產業別") or "").strip() or None,
            "revenue_mom": _to_float(row.get("營業收入-上月比較增減(%)")),
            "revenue_yoy": _to_float(row.get("營業收入-去年同月增減(%)")),
        }
    return result


async def get_eps_map() -> dict[str, dict]:
    """
    回傳 {股票代號: {eps_latest, eps_change_pct}}。

    做法：把同一間公司依（年度, 季別）排序，抓最新一期的EPS當作 eps_latest，
    如果剛好有前一期資料，順便算變動率；只有一期的話 eps_change_pct 就是 None。
    """
    try:
        raw = await _fetch_json(EPS_URL)
    except httpx.HTTPError:
        return {}

    by_company: dict[str, list[tuple[str, str, float]]] = {}
    for row in raw:
        code = row.get("公司代號")
        year = row.get("年度")
        quarter = row.get("季別")
        eps = _to_float(row.get("基本每股盈餘（元）") or row.get("每股盈餘"))
        if not code or eps is None or not year or not quarter:
            continue
        by_company.setdefault(code, []).append((year, quarter, eps))

    result: dict[str, dict] = {}
    for code, records in by_company.items():
        records.sort(key=lambda r: (r[0], r[1]))
        latest_eps = records[-1][2]
        change_pct = None
        if len(records) >= 2:
            prev_eps = records[-2][2]
            if prev_eps:
                # EPS可能是負值，分母用絕對值避免正負號讓百分比失去意義
                change_pct = round((latest_eps - prev_eps) / abs(prev_eps) * 100, 2)
        result[code] = {"eps_latest": latest_eps, "eps_change_pct": change_pct}
    return result


async def get_company_fundamentals_map() -> dict[str, dict]:
    """把月營收（產業別/YoY/MoM）跟EPS合併成一份，方便選股邏輯查詢。"""
    monthly = await get_monthly_revenue_map()
    eps = await get_eps_map()

    merged: dict[str, dict] = {}
    codes = set(monthly) | set(eps)
    for code in codes:
        base = monthly.get(code, {})
        eps_data = eps.get(code, {})
        merged[code] = {
            "industry": base.get("industry"),
            "revenue_yoy": base.get("revenue_yoy"),
            "revenue_mom": base.get("revenue_mom"),
            "eps_latest": eps_data.get("eps_latest"),
            "eps_change_pct": eps_data.get("eps_change_pct"),
        }
    return merged
