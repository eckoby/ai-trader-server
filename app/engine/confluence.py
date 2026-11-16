import numpy as np
import pandas as pd

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    
    df["bb_mid"] = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + (2 * bb_std)
    df["bb_lower"] = df["bb_mid"] - (2 * bb_std)
    return df

def calculate_frvp_poc(df: pd.DataFrame, lookback: int = 100, bins: int = 24) -> float:
    sub = df.tail(lookback)
    price_min, price_max = sub["low"].min(), sub["high"].max()
    if price_max == price_min:
        return float(price_max)
    hist, bin_edges = np.histogram(sub["close"], bins=bins, range=(price_min, price_max), weights=sub["volume"])
    max_idx = int(np.argmax(hist))
    return float((bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2.0)

def analyze_setup(df: pd.DataFrame, symbol: str, timeframe: str, market_type: str):
    if len(df) < 205:
        return None
        
    df = calculate_indicators(df)
    c = df.iloc[-2]
    prev = df.iloc[-3]
    
    if pd.isna(c["atr"]) or c["atr"] <= 0:
        return None

    recent = df.iloc[-62:-2]
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())
    poc = calculate_frvp_poc(df.iloc[:-1], lookback=100)
    
    fib_range = swing_high - swing_low
    if fib_range <= 0:
        return None
        
    ote_bull_top = swing_high - (0.50 * fib_range)
    ote_bull_bot = swing_high - (0.786 * fib_range)
    ote_bear_bot = swing_low + (0.50 * fib_range)
    ote_bear_top = swing_low + (0.786 * fib_range)
    
    bull_candle = c["close"] > c["open"] and c["close"] > prev["close"]
    bear_candle = c["close"] < c["open"] and c["close"] < prev["close"]
    bull_fvg = prev["low"] > df.iloc[-5]["high"] or c["low"] > df.iloc[-4]["high"]
    bear_fvg = prev["high"] < df.iloc[-5]["low"] or c["high"] < df.iloc[-4]["low"]
    sweep_low = prev["low"] <= swing_low and c["close"] > swing_low
    sweep_high = prev["high"] >= swing_high and c["close"] < swing_high
    
    tags = []
    # === SKENARIO LONG ===
    if c["close"] > c["ema200"] and bull_candle:
        if ote_bull_bot <= prev["low"] <= ote_bull_top:
            tags.append("Fib Discount")
        if sweep_low:
            tags.append("Liquidity Sweep")
        if bull_fvg:
            tags.append("Bullish FVG")
        if abs(c["close"] - poc) / c["close"] < 0.02:
            tags.append("POC Confluence")
        if c["rsi"] < 50 and c["macd"] > c["macd_signal"]:
            tags.append("Momentum Confirm")
            
        if len(tags) >= 2:
            entry = float(c["close"])
            sl = float(min(c["low"], prev["low"]) - (1.5 * c["atr"]))
            risk = entry - sl
            if risk <= 0:
                return None
            tp = entry + (risk * 2.0)
            return {
                "symbol": symbol,
                "market": market_type.upper(),
                "timeframe": timeframe,
                "side": "LONG",
                "entry": round(entry, 5),
                "sl": round(sl, 5),
                "tp": round(tp, 5),
                "rr": 2.0,
                "poc": round(poc, 5),
                "ote_zone": [round(ote_bull_bot, 5), round(ote_bull_top, 5)],
                "tags": tags,
                "timestamp": str(c["timestamp"]),
            }

    # === SKENARIO SHORT (FUTURES) ===
    if market_type == "swap" and c["close"] < c["ema200"] and bear_candle:
        if ote_bear_bot <= prev["high"] <= ote_bear_top:
            tags.append("Fib Premium")
        if sweep_high:
            tags.append("Liquidity Sweep")
        if bear_fvg:
            tags.append("Bearish FVG")
        if abs(c["close"] - poc) / c["close"] < 0.02:
            tags.append("POC Confluence")
        if c["rsi"] > 50 and c["macd"] < c["macd_signal"]:
            tags.append("Momentum Confirm")
            
        if len(tags) >= 2:
            entry = float(c["close"])
            sl = float(max(c["high"], prev["high"]) + (1.5 * c["atr"]))
            risk = sl - entry
            if risk <= 0:
                return None
            tp = entry - (risk * 2.0)
            return {
                "symbol": symbol,
                "market": "FUTURES",
                "timeframe": timeframe,
                "side": "SHORT",
                "entry": round(entry, 5),
                "sl": round(sl, 5),
                "tp": round(tp, 5),
                "rr": 2.0,
                "poc": round(poc, 5),
                "ote_zone": [round(ote_bear_bot, 5), round(ote_bear_top, 5)],
                "tags": tags,
                "timestamp": str(c["timestamp"]),
            }
            
    return None
