import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze

app = FastAPI(
    title="Poop Stock API",
    description=(
        "純娛樂用途：拍照分析 + 台股選股推薦。"
        "不構成醫療診斷或投資建議。"
    ),
)

# 允許的前端網域從環境變數讀，用逗號分隔多個網址。
# 本機開發預設放行 Vite 的 5173，部署到正式環境時
# 用 FRONTEND_ORIGINS 環境變數加上正式前端網址，不用改程式碼。
def _clean_origin(raw: str) -> str:
    value = raw.strip().strip('"').strip("'").strip()
    return value.rstrip("/")  # 網址結尾的斜線也順便去掉，避免比對不到


def _clean_origin(raw: str) -> str:
    value = raw.strip().strip('"').strip("'").strip()
    return value.rstrip("/")  # 網址結尾的斜線也順便去掉，避免比對不到


default_origins = "http://localhost:5173,http://127.0.0.1:5173"
origins = [
    _clean_origin(origin)
    for origin in os.environ.get("FRONTEND_ORIGINS", default_origins).split(",")
    if _clean_origin(origin)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
