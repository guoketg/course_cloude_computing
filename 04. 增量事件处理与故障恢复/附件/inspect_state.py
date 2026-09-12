"""只读检查最近一次实验 04 的 SQLite 状态与 Gold 汇总。"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pointer = json.loads((ROOT / "data/state/latest.json").read_text(encoding="utf-8"))
database = Path(pointer["database"])
with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as con:
    count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    offset = con.execute("SELECT offset FROM checkpoint WHERE id=1").fetchone()[0]
    additions = con.execute("SELECT event_id,event_time FROM events WHERE event_id LIKE 'increment-%' ORDER BY event_id").fetchall()
    rows = con.execute("SELECT service,COUNT(*),SUM(input_tokens),SUM(output_tokens) FROM events GROUP BY service ORDER BY service").fetchall()
summary = [dict(zip(["service", "requests", "input_tokens", "output_tokens"], row)) for row in rows]
gold = json.loads((ROOT / "data/gold/realtime_service.json").read_text(encoding="utf-8"))
assert summary == gold
assert count == sum(row["requests"] for row in gold)
print(json.dumps({"database": str(database), "rows": count, "checkpoint": offset,
                  "additions": additions, "aggregate": summary, "matches_gold": True}, ensure_ascii=False, indent=2))
