import sqlite3
import pandas as pd

conn = sqlite3.connect('database.db')

print("Upload sessions:")
print(pd.read_sql("SELECT id, filename, total_rows, status FROM upload_session", conn))

print("\nCleaning stats:")
print(pd.read_sql("SELECT session_id, total_raw, total_clean, total_batal, total_invalid, cleaning_reasons FROM cleaning_stats", conn))

print("\nCounts per session in raw_data_temp:")
print(pd.read_sql("SELECT session_id, count(*) FROM raw_data_temp GROUP BY session_id", conn))

print("\nCounts per session in cleaned_transaksi:")
print(pd.read_sql("SELECT session_id, count(*) FROM cleaned_transaksi GROUP BY session_id", conn))

conn.close()
