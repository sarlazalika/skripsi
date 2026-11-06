import sqlite3
import pandas as pd
import json
import sys
sys.path.append('.')
from analysis.preprocessor import clean_data

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# Ambil session 6
session_id = 6
upload_row = conn.execute('SELECT * FROM upload_session WHERE id=?', (session_id,)).fetchone()
print(f"Session: {upload_row['filename']}")

raw_rows = conn.execute('SELECT row_data FROM raw_data_temp WHERE session_id=? ORDER BY row_index ASC', (session_id,)).fetchall()
print(f"Raw rows in temp table: {len(raw_rows)}")

records = [json.loads(r['row_data']) for r in raw_rows]
df_raw = pd.DataFrame(records)
print(f"DF Raw rows: {len(df_raw)}")

mapping = json.loads(upload_row['column_mapping'])
df_clean, stats = clean_data(df_raw, mapping)

print(f"DF Clean rows: {len(df_clean)}")
print(f"Stats: {stats}")
