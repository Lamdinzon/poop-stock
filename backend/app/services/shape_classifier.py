"""
形狀分類模組：用 OpenCV 做輪廓偵測，區分「顆粒狀／長條狀／一攤泥」三大類，
再進一步對應到布里斯托分類法（Bristol Stool Scale）的 1~7 型。

重要：這裡做的是「形狀」偵測（有幾坨、長寬比、邊緣是否平滑），
不做顏色/色調判斷疾病，也不做任何病理推論，維持先前談好的分寸。

演算法邏輯（簡化說明）：
1. 用四個角落的像素粗略猜「背景」大概多亮，藉此決定前景（主體）
   是照片中比較暗的區域還是比較亮的區域，做二值化分割。
2. 找出分割後的輪廓，濾掉太小的雜訊輪廓。
3. 依照「明顯分開的輪廓數量」判斷是不是顆粒狀；
   只有一坨的話，再用長寬比分「長條狀」跟「一攤泥」，
   最後用輪廓的緊實度（solidity，越接近凸包代表邊緣越平滑）微調對應到細分型態。

這一切都是粗略的工程近似，不是醫學影像演算法，文案上要保持「僅供參考」。
"""

import cv2
import numpy as np

MIN_AREA_RATIO = 0.004  # 面積小於畫面 0.4% 的輪廓視為雜訊，忽略
TARGET_WIDTH = 640  # 縮圖到固定寬度，讓後面的門檻參數穩定、也加快運算


def _load_bgr(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("無法解析圖片內容")

    h, w = img.shape[:2]
    if w > TARGET_WIDTH:
        scale = TARGET_WIDTH / w
        img = cv2.resize(img, (TARGET_WIDTH, int(h * scale)))
    return img


def _segment_mask(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape
    corner = max(4, min(h, w) // 12)

    corners = np.concatenate(
        [
            gray[:corner, :corner].flatten(),
            gray[:corner, -corner:].flatten(),
            gray[-corner:, :corner].flatten(),
            gray[-corner:, -corner:].flatten(),
        ]
    )
    background_level = float(np.median(corners))

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    white_pixels = gray[otsu == 255]
    black_pixels = gray[otsu == 0]
    white_mean = float(white_pixels.mean()) if white_pixels.size else background_level
    black_mean = float(black_pixels.mean()) if black_pixels.size else background_level

    # otsu 把畫面切成兩群，哪一群的平均亮度離「背景猜測值」比較遠，就當作前景
    fg_is_white = abs(white_mean - background_level) > abs(black_mean - background_level)
    mask = otsu if fg_is_white else cv2.bitwise_not(otsu)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def classify_shape(image_bytes: bytes) -> dict:
    """回傳 {"type_id": int, "shape_category": str}。"""
    img = _load_bgr(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = _segment_mask(gray)

    total_area = mask.shape[0] * mask.shape[1]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = [c for c in contours if cv2.contourArea(c) > total_area * MIN_AREA_RATIO]

    if not significant:
        # 偵測不到明顯主體（可能整張都是背景、或對比太低），保底回傳中間型態
        return {"type_id": 4, "shape_category": "長條狀"}

    if len(significant) >= 3:
        # 多個分開的獨立小區塊 → 顆粒狀（對應布里斯托 1~2型）
        type_id = 1 if len(significant) >= 5 else 2
        return {"type_id": type_id, "shape_category": "顆粒狀"}

    largest = max(significant, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    rect = cv2.minAreaRect(largest)
    rw, rh = rect[1]
    long_side = max(rw, rh)
    short_side = max(min(rw, rh), 1.0)
    aspect_ratio = long_side / short_side

    hull = cv2.convexHull(largest)
    hull_area = cv2.contourArea(hull) or 1.0
    solidity = area / hull_area

    if aspect_ratio >= 2.0:
        # 明顯拉長的單一區塊 → 長條狀（對應布里斯托 3~4型）
        # 邊緣越接近凸包（solidity高）代表表面越平滑 → 4型；凹凸不平 → 3型
        type_id = 4 if solidity >= 0.9 else 3
        return {"type_id": type_id, "shape_category": "長條狀"}

    # 長寬比不明顯 → 攤開的一坨（對應布里斯托 5~7型）
    if solidity >= 0.9:
        type_id = 5
    elif solidity >= 0.78:
        type_id = 6
    else:
        type_id = 7
    return {"type_id": type_id, "shape_category": "一攤泥"}
