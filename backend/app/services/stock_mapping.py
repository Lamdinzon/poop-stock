"""
把 PoopScore 對應到一支股票的邏輯。

MVP 先用簡單規則：
- overall >= 70（順暢型）：從本益比偏低的股票裡挑，玩「便宜貨」的梗
- overall 40~69（普通型）：從整個股票池隨機挑，玩「隨緣」的梗
- overall < 40（崎嶇型）：從殖利率較高的股票裡挑，玩「防禦型」的梗

之後要接長期均線、產業熱度、三大法人買賣超時，
可以在這裡加更多分層條件，這個函式是之後擴充的主要入口。
"""

import random
from app.models.schemas import PoopScore, StockPick

FUN_REASONS = {
    "smooth": [
        "今天狀態順暢，配上這支本益比不貴的股票，走的是穩健路線。",
        "順暢指數高，選了一支估值合理的股票，跟你的腸胃一樣不囤積。",
        "今天排得乾脆俐落，這支股票的估值也一樣清爽不拖泥帶水。",
        "難得的順暢時刻，用一支便宜貨股票紀念一下。",
        "今天效率驚人，選股邏輯也跟著講求CP值。",
    ],
    "neutral": [
        "今天不好不壞，股票也是隨緣抽到的，人生嘛。",
        "普通的一天配普通的隨機股，穩定發揮。",
        "沒有特別驚喜也沒有特別意外，這支股票陪你安穩上班。",
        "中庸之道，今天的你跟這支股票都一樣，不上不下剛剛好。",
        "隨緣抽到這支，就像今天的心情一樣平淡但踏實。",
        "普普通通的一天，選股結果也是那種「還好啦」的感覺。",
        "今天沒什麼特別的，這支股票大概也是這樣，佛系持有。",
    ],
    "rough": [
        "今天狀態有點崎嶇，選一支殖利率較高的防禦型股票陪你度過。",
        "波動大的一天，搭配相對穩健、配息不錯的股票求心安。",
        "今天辛苦了，用一支高股息股票犒賞自己的不容易。",
        "崎嶇歸崎嶇，至少這支股票的配息還算大方。",
        "今天有點難熬，選一支防禦型股票，先求穩再求賺。",
    ],
}


def _valid_pool(pool: list[dict]) -> list[dict]:
    return [s for s in pool if s.get("close_price") and s.get("name")]


def pick_stock(
    score: PoopScore,
    pool: list[dict],
    fundamentals: dict[str, dict] | None = None,
    big_holder_ratios: dict[str, float] | None = None,
    institutional_net: dict[str, dict] | None = None,
) -> StockPick:
    fundamentals = fundamentals or {}
    big_holder_ratios = big_holder_ratios or {}
    institutional_net = institutional_net or {}

    candidates = _valid_pool(pool)
    if not candidates:
        # 保底：證交所資料抓不到時的假資料，避免整個 API 掛掉
        return StockPick(
            ticker="0050",
            name="元大台灣50",
            industry="ETF",
            close_price=None,
            pe_ratio=None,
            ma_trend="資料暫時抓不到",
            fun_reason="證交所資料今天有點鬧脾氣，先讓大盤ETF代打一下。",
        )

    if score.overall >= 70:
        pe_candidates = [s for s in candidates if s.get("pe_ratio") and s["pe_ratio"] > 0]
        pe_candidates.sort(key=lambda s: s["pe_ratio"])
        pool_slice = pe_candidates[:20] or candidates
        reason_key = "smooth"
    elif score.overall >= 40:
        pool_slice = candidates
        reason_key = "neutral"
    else:
        yield_candidates = [
            s for s in candidates if s.get("dividend_yield") not in (None, "", "-")
        ]
        try:
            yield_candidates.sort(
                key=lambda s: float(s["dividend_yield"]), reverse=True
            )
        except (ValueError, TypeError):
            pass
        pool_slice = yield_candidates[:20] or candidates
        reason_key = "rough"

    picked = random.choice(pool_slice)
    fun_reason = random.choice(FUN_REASONS[reason_key])

    ticker = picked["ticker"]
    company_data = fundamentals.get(ticker, {})
    inst_data = institutional_net.get(ticker, {})

    return StockPick(
        ticker=ticker,
        name=picked["name"],
        industry=company_data.get("industry"),
        close_price=picked.get("close_price"),
        pe_ratio=picked.get("pe_ratio"),
        ma_trend=None,  # TODO: 之後串接歷史收盤價計算均線
        volume_change_pct=None,  # 選定股票後才由 router 另外查詢、補上
        revenue_yoy=company_data.get("revenue_yoy"),
        revenue_mom=company_data.get("revenue_mom"),
        eps_latest=company_data.get("eps_latest"),
        eps_change_pct=company_data.get("eps_change_pct"),
        big_holder_ratio=big_holder_ratios.get(ticker),
        institutional_net_month=inst_data.get("net"),
        institutional_net_mom_pct=inst_data.get("mom_pct"),
        fun_reason=fun_reason,
    )
