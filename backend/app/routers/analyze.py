import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.scoring import score_image
from app.services.shape_classifier import classify_shape
from app.services.twse_client import get_merged_stock_pool, get_top20_by_volume
from app.services.stock_mapping import pick_stock
from app.services.stock_intro import build_intro
from app.services.health_education import get_stool_type_info, MEDICAL_REMINDER
from app.services.company_fundamentals import get_company_fundamentals_map
from app.services.shareholder_data import get_big_holder_ratio_map
from app.services.institutional_flow import get_institutional_net_month_map
from app.services.volume_history import get_volume_change_pct
from app.models.schemas import AnalyzeResponse, HealthEducation, TickerItem

router = APIRouter(prefix="/api", tags=["analyze"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(image: UploadFile = File(...)):
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "只接受 jpeg / png / webp 格式的照片")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(400, "檔案是空的")

    score = score_image(image_bytes)

    try:
        shape_result = classify_shape(image_bytes)
    except ValueError:
        raise HTTPException(400, "圖片格式無法解析，換一張試試")

    type_info = get_stool_type_info(shape_result["type_id"])
    health = HealthEducation(
        type_id=type_info.type_id,
        type_label=type_info.label,
        type_description=type_info.description,
        shape_category=shape_result["shape_category"],
        general_tip=type_info.general_tip,
        medical_reminder=MEDICAL_REMINDER,
    )

    # 四份證交所/集保資料彼此獨立，平行抓取比較快
    pool, fundamentals, big_holder_ratios, institutional_net = await asyncio.gather(
        get_merged_stock_pool(),
        get_company_fundamentals_map(),
        get_big_holder_ratio_map(),
        get_institutional_net_month_map(),
    )

    stock = pick_stock(score, pool, fundamentals, big_holder_ratios, institutional_net)

    # 成交量日增率是「單股歷史資料」端點，選定股票之後才查這一支，
    # 不會對整個候選池都查一次
    stock.volume_change_pct = await get_volume_change_pct(stock.ticker)

    intro = build_intro(stock)

    return AnalyzeResponse(score=score, health=health, stock=stock, stock_intro=intro)


@router.get("/ticker", response_model=list[TickerItem])
async def ticker():
    """跑馬燈用：今日成交量前20名證券。"""
    items = await get_top20_by_volume()
    return [TickerItem(**item) for item in items]
