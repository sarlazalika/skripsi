import sqlite3
import pandas as pd
import json
import sys
sys.path.append('.')
from analysis.preprocessor import clean_data

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# Get pending session 6
session_id = 6
upload_row = conn.execute('SELECT * FROM upload_session WHERE id=?', (session_id,)).fetchone()
if not upload_row:
    print("Session 6 not found")
    sys.exit()

# Get raw data
raw_rows = conn.execute('SELECT row_data FROM raw_data_temp WHERE session_id=? ORDER BY row_index ASC', (session_id,)).fetchall()
records = [json.loads(r['row_data']) for r in raw_rows]
df_raw = pd.DataFrame(records)
mapping = json.loads(upload_row['column_mapping'])
df_clean, stats = clean_data(df_raw, mapping)

# Delete old cleaned
old_cleaned = conn.execute('SELECT id_transaksi, tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', (session_id,)).fetchall()
for row in old_cleaned:
    conn.execute('DELETE FROM transaksi WHERE id_transaksi=? AND tanggal=? AND produk=? AND jumlah=?', (row['id_transaksi'], row['tanggal'], row['produk'], row['jumlah']))
conn.execute('DELETE FROM cleaned_transaksi WHERE session_id=?', (session_id,))
conn.execute('DELETE FROM cleaning_stats WHERE session_id=?', (session_id,))

# Insert new cleaned
rows_clean = [(session_id, row['id_transaksi'], row['tanggal'], row['produk'], int(row['jumlah'])) for _, row in df_clean.iterrows()]
conn.executemany('INSERT INTO cleaned_transaksi (session_id, id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?, ?)', rows_clean)

# Insert into transaksi
rows_for_transaksi = [(row['id_transaksi'], row['tanggal'], row['produk'], int(row['jumlah'])) for _, row in df_clean.iterrows()]
conn.executemany('INSERT INTO transaksi (id_transaksi, tanggal, produk, jumlah) VALUES (?, ?, ?, ?)', rows_for_transaksi)

# Stats
conn.execute('''INSERT INTO cleaning_stats (session_id, total_raw, total_clean, total_batal, total_invalid, cleaning_reasons, has_status_col, pct_valid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (session_id, stats['total_raw'], stats['total_clean'], stats['total_batal'], stats['total_invalid'], json.dumps(stats['cleaning_reasons'], ensure_ascii=False), 1 if stats['has_status_col'] else 0, stats['pct_valid']))
conn.execute("UPDATE upload_session SET status='cleaned' WHERE id=?", (session_id,))
conn.commit()

# Check counts
print("cleaned_transaksi total for session 6:", conn.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id=6").fetchone()[0])
print("total active session:", conn.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id IN (SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1)").fetchone()[0])
print("total transaksi:", conn.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0])
conn.close()
