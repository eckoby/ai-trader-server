import argparse
from app.data.feed import fetch_candles, get_top_usdt_pairs
from app.engine.confluence import analyze_setup

def simulate_trade(df_future, side: str, entry: float, sl: float, tp: float) -> str:
    for _, row in df_future.iterrows():
        if side == "LONG":
            if row["low"] <= sl:
                return "LOSS"
            if row["high"] >= tp:
                return "WIN"
        else:
            if row["high"] >= sl:
                return "LOSS"
            if row["low"] <= tp:
                return "WIN"
    return "OPEN"

def run_test(tf: str, num_symbols: int, candles: int):
    pairs = get_top_usdt_pairs(limit=num_symbols, market_type="swap")
    wins, losses = 0, 0
    
    for sym in pairs:
        df = fetch_candles(sym, timeframe=tf, limit=min(candles, 1000), market_type="swap")
        for i in range(205, len(df) - 20):
            window = df.iloc[:i+1]
            sig = analyze_setup(window, sym, tf, "swap")
            if sig:
                outcome = simulate_trade(df.iloc[i+1:i+50], sig["side"], sig["entry"], sig["sl"], sig["tp"])
                if outcome == "WIN":
                    wins += 1
                elif outcome == "LOSS":
                    losses += 1
                    
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    print(f"\n=== HASIL WALK-FORWARD OOS ({tf}) ===")
    print(f"Total Sinyal Selesai : {total} (Win: {wins}, Loss: {losses})")
    print(f"Win Rate OOS         : {win_rate:.2f}% (Target RR 1:2.5)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="1h")
    parser.add_argument("--symbols", type=int, default=10)
    parser.add_argument("--candles", type=int, default=1000)
    args = parser.parse_args()
    run_test(args.tf, args.symbols, args.candles)