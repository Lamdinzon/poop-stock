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

## 部署（全部用 Railway）

前後端都放 Railway 時，是**同一個 Railway 專案裡建兩個服務**，各自指到這個
repo裡不同的資料夾。

### 1. 建立 Railway 專案

1. 到 [railway.app](https://railway.app) 用 GitHub 帳號登入
2. **New Project → Deploy from GitHub repo**，選這個repo
3. 第一次會先建一個服務，等一下手動調整成「後端」用

### 2. 設定後端服務

1. 進去這個服務的 Settings
2. **Root Directory** 設成 `backend`
3. Build/Start 指令不用手動填，`backend/railway.json` 已經寫好了
   （Build 用 Nixpacks 自動偵測 Python，Start 是
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`）
4. 在 Variables 分頁加一筆 `FRONTEND_ORIGINS`，先留空或隨便填，
   等前端網址確定後回來補
5. 部署完成後，Settings → Networking 產生一個公開網址，
   例如 `https://poop-stock-backend-production.up.railway.app`，記下來

### 3. 加第二個服務（前端）

1. 回到專案總覽，**+ New → GitHub Repo**，一樣選同一個repo
2. 進去這個新服務的 Settings，**Root Directory** 設成 `frontend`
3. Build Command：`npm run build`
4. Start Command：`npm run start`
5. **在 Variables 分頁加 `VITE_API_BASE`，值是上一步後端的網址**
   —— 這一步要在第一次部署「之前」設定好，Vite 是 build 當下就把
   環境變數寫進打包好的檔案，build完才設是沒用的
6. 部署，一樣去 Networking 產生公開網址

### 4. 回頭把兩邊接起來

前端網址確定後，回後端服務的 Variables，把 `FRONTEND_ORIGINS` 改成前端的
正式網址（例如 `https://poop-stock-frontend-production.up.railway.app`），
存檔後 Railway 會自動重新部署後端。這一步沒做的話，前端打不到後端，
瀏覽器主控台會看到 CORS 錯誤。

### 費用提醒

Railway 是用量計費，不是固定免費額度，兩個服務24小時常駐大概率會超過
每月 \$1 的免費額度，需要升級 Hobby 方案（\$5/月起）。實際費用建議部署後
自己在 Railway 後台的 Usage 頁面確認一次。

---

<details>
<summary>另一個選擇：Render（後端）+ Vercel（前端），完全免費但後端會閒置休眠</summary>

### 後端 → Render

這個repo根目錄有 `render.yaml`，在 [Render](https://render.com) 選
「New → Blueprint」，指到這個repo即可自動讀取設定建立服務。
部署後記得在 Render 後台把 `FRONTEND_ORIGINS` 環境變數設成正式前端網址
（多個網址用逗號分開），不然前端會被 CORS 擋下來。

免費方案閒置一段時間會自動休眠，下次有人使用時第一個請求會比較慢
（重新開機 + 記憶體快取被清空，要重新抓一次證交所資料）。

### 前端 → Vercel / Netlify

連結這個repo，Build command 用 `npm run build`（在 `frontend/` 目錄下），
Output directory 是 `dist`。記得在平台的環境變數設定加上：

```
VITE_API_BASE=https://你的後端網址.onrender.com
```

</details>

## 資料來源

- 證交所 OpenAPI（`openapi.twse.com.tw`）：收盤價、本益比、月營收、EPS
- 證交所 T86／STOCK_DAY（`www.twse.com.tw`）：法人買賣超、成交量歷史
- 集保結算所開放資料（`opendata.tdcc.com.tw`）：大戶持股分布

都是公開免費資料，不需要API金鑰，程式碼裡有做快取降低請求頻率。

## 隱私

使用者上傳的照片只在記憶體中處理，分析完就丟棄，不會寫入硬碟或資料庫。
