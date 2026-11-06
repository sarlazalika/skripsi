import sys
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

print("1. TABEL UPLOAD_SESSION:")
sessions = pd.read_sql_query("SELECT id, filename, total_rows, status, created_at FROM upload_session", conn)
print(sessions.to_string())

print("\n2. TABEL DATASET:")
try:
    ds = pd.read_sql_query("SELECT * FROM dataset", conn)
    print(ds.to_string())
except Exception as e:
    print("Dataset:", e)

print("\n3. TABEL CLEANING_STATS:")
stats = pd.read_sql_query("SELECT * FROM cleaning_stats", conn)
print(stats.to_string())

print("\n4. SKEMA raw_data_temp:")
cols = [c[1] for c in conn.execute("PRAGMA table_info(raw_data_temp)").fetchall()]
print("Kolom raw_data_temp:", cols)

print("\n5. DISTRIBUSI SESSION DI raw_data_temp DAN cleaned_transaksi:")
raw_counts = pd.read_sql_query("SELECT session_id, count(*) as count_raw FROM raw_data_temp GROUP BY session_id", conn)
print("raw_data_temp:")
print(raw_counts.to_string())

clean_counts = pd.read_sql_query("SELECT session_id, count(*) as count_clean FROM cleaned_transaksi GROUP BY session_id", conn)
print("cleaned_transaksi:")
print(clean_counts.to_string())

print("\n6. CEK TANGGAL NOVEMBER & DESEMBER 2026 DI cleaned_transaksi:")
nov_dec_clean = pd.read_sql_query("""
    SELECT session_id, count(*) as count_rows, min(tanggal) as min_tgl, max(tanggal) as max_tgl
    FROM cleaned_transaksi 
    WHERE tanggal >= '2026-11-01'
    GROUP BY session_id
""", conn)
print(nov_dec_clean.to_string())

conn.close()
