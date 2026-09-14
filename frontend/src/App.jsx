import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// 後端還沒起來、或今天證交所資料抓不到時的備用展示內容
const FALLBACK_TICKER_ITEMS = [
  { ticker: "2330", name: "台積電", close_price: 950.0, trend: "up" },
  { ticker: "0050", name: "元大台灣50", close_price: 182.3, trend: "up" },
  { ticker: "2882", name: "國泰金", close_price: 55.0, trend: "down" },
  { ticker: "1101", name: "台泥", close_price: 33.15, trend: "down" },
];

function TickerTape() {
  const [tickerData, setTickerData] = useState(FALLBACK_TICKER_ITEMS);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/ticker`)
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          setTickerData(data);
        }
      })
      .catch(() => {
        // 抓不到就靜靜用備用資料，不影響主要拍照分析功能
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = [...tickerData, ...tickerData];

  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker__track">
        {items.map((item, i) => (
          <span className="ticker__item" key={i}>
            <span>
              {item.ticker} {item.name}
            </span>
            <span className={item.trend === "down" ? "down" : "up"}>
              {item.trend === "down" ? "▼" : "▲"} {item.close_price ?? "--"}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

function CameraIcon() {
  return (
    <svg
      className="dropzone__icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2l1-2h7l1 2h2A1.5 1.5 0 0 1 20 8.5V18a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18V8.5Z" />
      <circle cx="12" cy="13" r="3.4" />
    </svg>
  );
}

function scoreColor(value) {
  if (value >= 70) return "#2e8b57"; // 高分：綠
  if (value >= 40) return "#c9a227"; // 中等：金
  return "#d6455d"; // 偏低：紅
}

function MeterRow({ label, value }) {
  return (
    <div className="meter-row">
      <span className="meter-row__label">{label}</span>
      <span className="meter-row__track">
        <span
          className="meter-row__fill"
          style={{ width: `${value}%`, backgroundColor: scoreColor(value) }}
        />
      </span>
      <span className="meter-row__value">{value}</span>
    </div>
  );
}

function FundamentalStat({ label, value, unit, signed = true, note }) {
  const hasValue = value !== null && value !== undefined;
  const isPositive = hasValue && value > 0;
  const isNegative = hasValue && value < 0;
  const sign = signed && hasValue && value > 0 ? "+" : "";

  return (
    <div className="fundamental-stat">
      <span className="fundamental-stat__label">{label}</span>
      <span
        className={
          "fundamental-stat__value" +
          (signed && isPositive ? " fundamental-stat__value--pos" : "") +
          (signed && isNegative ? " fundamental-stat__value--neg" : "")
        }
      >
        {hasValue ? `${sign}${value}${unit}` : "資料不足"}
        {hasValue && note ? <span className="fundamental-stat__note">{note}</span> : null}
      </span>
    </div>
  );
}

export default function App() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  function handleFileChange(e) {
    const picked = e.target.files?.[0];
    if (!picked) return;
    setFile(picked);
    setPreviewUrl(URL.createObjectURL(picked));
    setStatus("idle");
    setResult(null);
    setErrorMsg("");
  }

  function resetFile() {
    setFile(null);
    setPreviewUrl(null);
    setStatus("idle");
    setResult(null);
    setErrorMsg("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function submitAnalysis() {
    if (!file) return;
    setStatus("loading");
    setErrorMsg("");
    try {
      const formData = new FormData();
      formData.append("image", file);
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `伺服器回應錯誤（${res.status}）`);
      }
      const data = await res.json();
      setResult(data);
      setStatus("success");
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "分析失敗，請確認後端伺服器是否已啟動。"
      );
      setStatus("error");
    }
  }

  const isBusy = status === "loading";

  return (
    <div className="page">
      <TickerTape />

      <header className="hero">
        <p className="hero__eyebrow">開盤鈴聲響了</p>
        <h1 className="hero__title">
          上班第一件事，<br />
          先看今天<em>開盤</em>。
        </h1>
        <p className="hero__subtitle">
          拍一張照片，換一支今日精選台股，還有一句只有你懂的開盤評語。
          純娛樂，不是醫療診斷，也不是投資建議。
        </p>
      </header>

      <main className="main">
        <section className="stall">
          <div className="stall__plaque">
            <span className="stall__plaque-label">分析櫃檯</span>
            <span
              className={
                "stall__status " +
                (isBusy ? "stall__status--busy" : status === "success" ? "stall__status--ready" : "")
              }
            >
              {isBusy ? "分析中" : status === "success" ? "已完盤" : "待命中"}
            </span>
          </div>

          {!previewUrl ? (
            <div
              className="dropzone"
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            >
              <CameraIcon />
              <span className="dropzone__title">點一下拍照或選擇照片</span>
              <span className="dropzone__hint">支援 JPG / PNG / WEBP</span>
            </div>
          ) : (
            <div className="preview">
              <img className="preview__thumb" src={previewUrl} alt="已選擇的照片預覽" />
              <div>
                <div className="preview__name">{file?.name}</div>
                <button className="preview__reset" onClick={resetFile} type="button">
                  重新選擇照片
                </button>
              </div>
            </div>
          )}

          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            hidden
            onChange={handleFileChange}
          />

          {status === "error" && <div className="error-banner">{errorMsg}</div>}

          <div className="stall__actions">
            <button
              className="btn-primary"
              type="button"
              disabled={!file || isBusy}
              onClick={submitAnalysis}
            >
              {isBusy ? "開盤分析中…" : "送出，開今日盤"}
            </button>
          </div>
        </section>

        {result && (
          <section className="results">
            <article className="card">
              <div className="card__bar card__bar--gold" />
              <div className="card__body">
                <p className="card__label">今日綜合評分</p>
                <div className="score-headline">
                  <span className="score-headline__number">{result.score.overall}</span>
                  <span className="score-headline__suffix">/ 100</span>
                </div>
                <p className="score-verdict">{result.score.verdict}</p>

                <MeterRow label="黃金指數" value={result.score.golden_index} />
                <MeterRow label="順暢度" value={result.score.smoothness} />
                <MeterRow label="密度分" value={result.score.density} />
              </div>
            </article>

            <article className="card">
              <div className="card__bar card__bar--ink" />
              <div className="card__body">
                <p className="card__label">形態衛教參考</p>
                <span className="shape-badge">{result.health.shape_category}</span>
                <h3 className="health-type">{result.health.type_label}</h3>
                <p className="health-desc">{result.health.type_description}</p>
                <p className="health-tip">{result.health.general_tip}</p>
                <p className="health-reminder">{result.health.medical_reminder}</p>
              </div>
            </article>

            <article className="card">
              <div className="card__bar card__bar--rise" />
              <div className="card__body">
                <p className="card__label">今日開盤精選</p>
                <div className="stock-head">
                  <span className="stock-ticker">{result.stock.ticker}</span>
                  <div>
                    <span className="stock-name">{result.stock.name}</span>
                    {result.stock.industry && (
                      <span className="stock-industry">{result.stock.industry}</span>
                    )}
                  </div>
                </div>
                <div className="stock-metrics">
                  {result.stock.close_price != null && (
                    <span>
                      收盤 <strong>{result.stock.close_price}</strong>
                    </span>
                  )}
                  {result.stock.pe_ratio != null && (
                    <span>
                      本益比 <strong>{result.stock.pe_ratio}</strong>
                    </span>
                  )}
                </div>

                <div className="fundamentals-grid">
                  <FundamentalStat label="營收年增 YoY" value={result.stock.revenue_yoy} unit="%" />
                  <FundamentalStat label="營收月增 MoM" value={result.stock.revenue_mom} unit="%" />
                  <FundamentalStat
                    label="每股盈餘 EPS"
                    value={result.stock.eps_latest}
                    unit=" 元"
                    signed={false}
                    note={
                      result.stock.eps_change_pct != null
                        ? `（較上期 ${result.stock.eps_change_pct > 0 ? "+" : ""}${result.stock.eps_change_pct}%）`
                        : null
                    }
                  />
                  <FundamentalStat
                    label="成交量日增率"
                    value={result.stock.volume_change_pct}
                    unit="%"
                  />
                  <FundamentalStat label="大戶持股" value={result.stock.big_holder_ratio} unit="%" signed={false} />
                  <FundamentalStat
                    label="法人近一月買賣超"
                    value={result.stock.institutional_net_month}
                    unit="張"
                    note={
                      result.stock.institutional_net_mom_pct != null
                        ? `（較上月 ${result.stock.institutional_net_mom_pct > 0 ? "+" : ""}${result.stock.institutional_net_mom_pct}%）`
                        : null
                    }
                  />
                </div>

                <p className="stock-reason">{result.stock.fun_reason}</p>
                <p className="stock-intro">{result.stock_intro}</p>
              </div>
            </article>
          </section>
        )}
      </main>

      <footer className="footer">{
        result?.disclaimer ||
        "本App所有內容純屬娛樂，不構成醫療診斷或投資建議。身體健康請諮詢專業醫師，投資決策請自行研究並謹慎評估風險。"
      }</footer>
    </div>
  );
}
