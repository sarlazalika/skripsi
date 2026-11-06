import sqlite3
import pandas as pd

conn = sqlite3.connect('database.db')
print("raw_data_temp:", pd.read_sql('SELECT COUNT(*) FROM raw_data_temp', conn).iloc[0,0])
print("cleaned_transaksi:", pd.read_sql('SELECT COUNT(*) FROM cleaned_transaksi', conn).iloc[0,0])
print("transaksi:", pd.read_sql('SELECT COUNT(*) FROM transaksi', conn).iloc[0,0])
print("upload_session:")
print(pd.read_sql('SELECT * FROM upload_session ORDER BY id DESC LIMIT 1', conn))
print("cleaning_stats:")
print(pd.read_sql('SELECT * FROM cleaning_stats ORDER BY id DESC LIMIT 1', conn))
conn.close()
