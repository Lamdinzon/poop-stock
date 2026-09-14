# 便盤所（Poop Stock）

拍一張照片，換一支今日台股精選，加一句只有你懂的開盤評語。
純娛樂 + 通用衛教用途，**不構成醫療診斷或投資建議**。

## 專案結構

```
poop-stock/
├── backend/    FastAPI + OpenCV，串接證交所/集保結算所開放資料
└── frontend/   React + Vite
```

## 本機開發

### 後端

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1     # macOS/Linux 用 source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端預設打 `http://127.0.0.1:8000` 當後端網址，要改的話在 `frontend/` 建一個
`.env`，寫 `VITE_API_BASE=你的後端網址`。

## 部署

### 後端 → Render

這個repo根目錄已經有 `render.yaml`，在 [Render](https://render.com) 選
「New → Blueprint」，指到這個repo即可自動讀取設定建立服務。
部署後記得在 Render 後台把 `FRONTEND_ORIGINS` 環境變數設成正式前端網址
（多個網址用逗號分開），不然前端會被 CORS 擋下來。

### 前端 → Vercel / Netlify

連結這個repo，Build command 用 `npm run build`（在 `frontend/` 目錄下），
Output directory 是 `dist`。記得在平台的環境變數設定加上：

```
VITE_API_BASE=https://你的後端網址.onrender.com
```

## 資料來源

- 證交所 OpenAPI（`openapi.twse.com.tw`）：收盤價、本益比、月營收、EPS
- 證交所 T86／STOCK_DAY（`www.twse.com.tw`）：法人買賣超、成交量歷史
- 集保結算所開放資料（`opendata.tdcc.com.tw`）：大戶持股分布

都是公開免費資料，不需要API金鑰，程式碼裡有做快取降低請求頻率。

## 隱私

使用者上傳的照片只在記憶體中處理，分析完就丟棄，不會寫入硬碟或資料庫。
