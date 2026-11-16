import ccxt
import pandas as pd

def get_okx_client(market_type: str = "swap"):
    """Inisialisasi koneksi publik OKX ('spot' atau 'swap' untuk Futures)."""
    return ccxt.okx({
        "enableRateLimit": True,
        "options": {"defaultType": market_type},
    })

def fetch_candles(symbol: str, timeframe: str = "1h", limit: int = 300, market_type: str = "swap") -> pd.DataFrame:
    exchange = get_okx_client(market_type)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def get_top_usdt_pairs(limit: int = 20, market_type: str = "swap") -> list:
    exchange = get_okx_client(market_type)
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers()
    
    valid_pairs = []
    for sym, data in tickers.items():
        if sym in markets and markets[sym].get("quote") == "USDT" and markets[sym].get("active"):
            vol = data.get("quoteVolume") or 0
            valid_pairs.append((sym, vol))
            
    valid_pairs.sort(key=lambda item: item[1], reverse=True)
    return [pair[0] for pair in valid_pairs[:limit]]

if __name__ == "__main__":
    print("Menguji koneksi OKX...")
    df_test = fetch_candles("BTC/USDT:USDT", timeframe="1h", limit=5)
    print(df_test)
    print("Koneksi OKX berhasil.")
