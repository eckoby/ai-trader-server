import os
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Header, HTTPException
from app.data.feed import fetch_candles, get_top_usdt_pairs
from app.database import get_recent_signals, init_db, save_signal
from app.engine.confluence import analyze_setup, calculate_frvp_poc, calculate_indicators

APP_TOKEN = os.getenv("APP_TOKEN", "rahasia123")

def verify_token(authorization: str = Header(None)):
    if authorization != f"Bearer {APP_TOKEN}":
        raise HTTPException(status_code=401, detail="Token tidak valid")

def scan_market():
    print("Memulai pemindaian pasar OKX (Spot & Futures)...")
    try:
        for m_type in ["swap", "spot"]:
            pairs = get_top_usdt_pairs(limit=15, market_type=m_type)
            for tf in ["15m", "1h", "4h"]:
                for sym in pairs:
                    df = fetch_candles(sym, timeframe=tf, limit=250, market_type=m_type)
                    sig = analyze_setup(df, sym, tf, m_type)
                    if sig:
                        save_signal(sig)
                        print(f"Sinyal baru ({m_type.upper()}): {sym} {tf} {sig['side']}")
    except Exception as e:
        print(f"Error saat pemindaian: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scan_market()
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_market, "interval", minutes=15)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="AI Trader Server v2", lifespan=lifespan)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "Server AI Trading Aktif"}

@app.get("/api/signals", dependencies=[Depends(verify_token)])
def read_signals(limit: int = 60):
    return {"status": "ok", "data": get_recent_signals(limit)}

@app.get("/api/chart/{symbol:path}", dependencies=[Depends(verify_token)])
def read_chart(symbol: str, timeframe: str = "1h"):
    m_type = "swap" if ":USDT" in symbol else "spot"
    df = fetch_candles(symbol, timeframe=timeframe, limit=220, market_type=m_type)
    df = calculate_indicators(df)
    poc = calculate_frvp_poc(df, lookback=100)
    last = df.iloc[-1]

    summary = {
        "ema200": round(float(last["ema200"]), 5),
        "trend": "BULLISH (Di atas EMA200)" if last["close"] > last["ema200"] else "BEARISH (Di bawah EMA200)",
        "rsi": round(float(last["rsi"]), 2),
        "macd_status": "Bullish Cross" if last["macd"] > last["macd_signal"] else "Bearish Cross",
        "bb_upper": round(float(last["bb_upper"]), 5),
        "bb_lower": round(float(last["bb_lower"]), 5),
        "poc": round(poc, 5),
    }

    df_out = df.tail(60).copy()
    df_out["timestamp"] = df_out["timestamp"].astype(str)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "summary": summary,
        "candles": df_out[["timestamp", "open", "high", "low", "close", "volume"]].to_dict(orient="records"),
    }
