"""
娛樂性影像評分邏輯。

重要：這裡的分析完全是「好玩用」，不是任何形式的醫療診斷。
評分維度只是從照片的色彩、亮度、紋理粗略計算出來的數字，
拿來當作後續選股邏輯的輸入種子，讓使用者有「我的便便決定我的投資」的樂趣。
"""

import io
import random
from PIL import Image, ImageStat
from app.models.schemas import PoopScore

VERDICTS = [
    "今天狀態穩健，適合觀望型操作。",
    "波動有點大，記得先深呼吸再做決定。",
    "非常順暢的一天，市場感覺也對你很友善。",
    "略顯乾澀，今天可能要多喝水、少追高。",
    "色澤飽滿，運勢感覺不錯，但投資還是要理性。",
]


def _color_stats(image: Image.Image) -> tuple[float, float, float]:
    """回傳 (平均亮度, 飽和度估計, 紋理粗糙度估計)。"""
    rgb = image.convert("RGB")
    stat = ImageStat.Stat(rgb)
    r, g, b = stat.mean
    brightness = (r + g + b) / 3

    # 飽和度粗估：用最大最小色版差異
    hsv = rgb.convert("HSV")
    h_stat = ImageStat.Stat(hsv)
    _, saturation, _ = h_stat.mean

    # 紋理粗糙度：用灰階標準差當作代表
    gray = rgb.convert("L")
    gray_stat = ImageStat.Stat(gray)
    texture = gray_stat.stddev[0]

    return brightness, saturation, texture


def score_image(image_bytes: bytes) -> PoopScore:
    image = Image.open(io.BytesIO(image_bytes))
    brightness, saturation, texture = _color_stats(image)

    # 亮度轉換成「黃金指數」：中等亮度給高分（太暗太亮都不理想，純娛樂公式）
    golden_index = int(max(0, 100 - abs(brightness - 140) / 1.4))

    # 飽和度轉換成「密度分」
    density = int(min(100, saturation / 2.55))

    # 紋理標準差轉換成「順暢度」：標準差適中給高分
    smoothness = int(max(0, 100 - abs(texture - 40) * 1.5))

    overall = int((golden_index + density + smoothness) / 3)
    verdict = random.choice(VERDICTS)

    return PoopScore(
        golden_index=max(0, min(100, golden_index)),
        smoothness=max(0, min(100, smoothness)),
        density=max(0, min(100, density)),
        overall=max(0, min(100, overall)),
        verdict=verdict,
    )

