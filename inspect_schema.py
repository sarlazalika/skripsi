import sys
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
    print(f"Table: {t}")
    for c in cols:
        print(f"   {c[1]} ({c[2]})")
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"   Total rows: {count}")

conn.close()
