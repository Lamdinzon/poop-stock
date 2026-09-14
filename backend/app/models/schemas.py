from pydantic import BaseModel, Field


class PoopScore(BaseModel):
    """娛樂性評分結果，純粹好玩，不是醫療診斷。"""

    golden_index: int = Field(..., ge=0, le=100, description="黃金指數（色澤）")
    smoothness: int = Field(..., ge=0, le=100, description="順暢度（形狀完整度）")
    density: int = Field(..., ge=0, le=100, description="密度分（紋理／黏稠度）")
    overall: int = Field(..., ge=0, le=100, description="綜合評分")
    verdict: str = Field(..., description="今日結語，一句幽默短評")


class HealthEducation(BaseModel):
    """純形態分類 + 通用衛教，不含任何病理判讀。"""

    type_id: int = Field(..., ge=1, le=7, description="布里斯托分類法型態編號 1~7")
    type_label: str
    type_description: str
    shape_category: str = Field(..., description="形狀大類：顆粒狀／長條狀／一攤泥")
    general_tip: str = Field(..., description="通用衛教建議，非個人化判讀")
    medical_reminder: str = Field(..., description="固定文字：持續異常請就醫")


class StockPick(BaseModel):
    ticker: str
    name: str
    industry: str | None = None
    close_price: float | None = None
    pe_ratio: float | None = None
    ma_trend: str | None = Field(None, description="長期均線趨勢：站上／跌破／盤整")
    volume_change_pct: float | None = Field(
        None, description="成交量日增率(%)，相比上一個交易日"
    )
    revenue_yoy: float | None = Field(None, description="月營收年增率(%)")
    revenue_mom: float | None = Field(None, description="月營收月增率(%)")
    eps_latest: float | None = Field(None, description="最新一期每股盈餘(元)")
    eps_change_pct: float | None = Field(
        None, description="每股盈餘相比上一期財報的變動(%)"
    )
    big_holder_ratio: float | None = Field(
        None, description="集保大戶持股比例(%)，資料源為TDCC股權分散表最高持股級距"
    )
    institutional_net_month: float | None = Field(
        None, description="近一個月三大法人合計買賣超（張），正值為買超"
    )
    institutional_net_mom_pct: float | None = Field(
        None, description="法人買賣超相比上個月同期的變動(%)"
    )
    fun_reason: str = Field(..., description="用便便梗解釋為什麼選到這支股票")


class TickerItem(BaseModel):
    ticker: str
    name: str
    close_price: float | None = None
    change: float | None = None
    trend: str = Field("flat", description="up / down / flat")


class AnalyzeResponse(BaseModel):
    score: PoopScore
    health: HealthEducation
    stock: StockPick
    stock_intro: str = Field(..., description="這支股票在做什麼、有什麼特點的簡介")
    disclaimer: str = (
        "本App所有內容純屬娛樂，不構成醫療診斷或投資建議。"
        "身體健康請諮詢專業醫師，投資決策請自行研究並謹慎評估風險。"
    )
