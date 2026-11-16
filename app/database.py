import json
import sqlite3
from pathlib import Path

DB_PATH = Path("signals.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                market TEXT,
                timeframe TEXT,
                side TEXT,
                entry REAL,
                sl REAL,
                tp REAL,
                rr REAL,
                poc REAL,
                tags TEXT,
                status TEXT DEFAULT 'OPEN',
                timestamp TEXT,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)

def save_signal(sig: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO signals 
            (symbol, market, timeframe, side, entry, sl, tp, rr, poc, tags, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sig["symbol"], sig["market"], sig["timeframe"], sig["side"],
            sig["entry"], sig["sl"], sig["tp"], sig["rr"], sig["poc"],
            json.dumps(sig["tags"]), sig["timestamp"]
        ))

def get_recent_signals(limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        results = []
        for r in rows:
            item = dict(r)
            item["tags"] = json.loads(item["tags"])
            results.append(item)
        return results
