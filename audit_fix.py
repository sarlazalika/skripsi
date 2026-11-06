import sqlite3
import pandas as pd
import json

def safe_int(val):
    if val is None:
        return 0
    if isinstance(val, bytes):
        return int.from_bytes(val, 'little')
    return int(val)

conn = sqlite3.connect('database.db')

# 1. Cek Upload Session (Data Mentah)
cursor = conn.cursor()
cursor.execute('SELECT id, filename, total_rows FROM upload_session WHERE id IN (1, 3, 4)')
sessions = cursor.fetchall()

print('=== DATA MENTAH (RAW) ===')
total_raw = 0
for row in sessions:
    print(f'Session {row[0]}: {row[1]}, Total Rows = {row[2]}')
    total_raw += row[2]
print('Total Raw App (Session 1,3,4):', total_raw)

# 2. Ambil statistik cleaning
cursor.execute('SELECT session_id, total_raw, total_clean, total_batal, total_invalid, cleaning_reasons FROM cleaning_stats WHERE session_id IN (1, 3, 4)')
stats = cursor.fetchall()
print('\n=== STATISTIK CLEANING APLIKASI ===')
app_clean = 0
app_batal = 0
app_invalid = 0
for row in stats:
    print(f'Session {row[0]} | Raw: {row[1]} | Clean: {row[2]} | Batal: {safe_int(row[3])} | Invalid: {safe_int(row[4])}')
    app_clean += safe_int(row[2])
    app_batal += safe_int(row[3])
    app_invalid += safe_int(row[4])
print(f'Total Clean App: {app_clean}')
print(f'Total Batal App: {app_batal}')
print(f'Total Invalid App: {app_invalid}')

# Ambil data cleaned
df = pd.read_sql_query('SELECT * FROM cleaned_transaksi WHERE session_id IN (1, 3, 4)', conn)

print('\n=== ANALISIS DUPLIKASI CLEANED DATA ===')
total_valid = len(df)
print(f'Total valid awal (3 session): {total_valid}')

# Kategorisasi Duplikat
all_dupes = df[df.duplicated(subset=['id_transaksi','produk','jumlah','tanggal'], keep=False)]
identical_dupes = len(all_dupes)

same_id_diff_prod = df[df.duplicated(subset=['id_transaksi'], keep=False) & ~df.duplicated(subset=['id_transaksi','produk'], keep=False)]
same_id_prod_diff_qty = df[df.duplicated(subset=['id_transaksi','produk'], keep=False) & ~df.duplicated(subset=['id_transaksi','produk','jumlah'], keep=False)]

unique_identical_dupes = len(all_dupes.drop_duplicates(subset=['id_transaksi','produk','jumlah','tanggal']))

print(f'Identik persis: {identical_dupes} baris (dari {unique_identical_dupes} transaksi unik)')
print(f'ID sama, Produk Beda (Split Order): {len(same_id_diff_prod)} baris')
print(f'ID+Produk sama, Jumlah beda: {len(same_id_prod_diff_qty)} baris')

# Analisis Lintas Sesi (Overlap)
cross_session = df.groupby('id_transaksi')['session_id'].nunique()
cross_ids = cross_session[cross_session > 1].index.tolist()
cross_rows = df[df['id_transaksi'].isin(cross_ids)]
print(f'\nTotal baris yang muncul di >1 session (Overlap): {len(cross_rows)} baris (dari {len(cross_ids)} ID unik)')

# Produk Non-Item
non_items = df[df['produk'].str.contains('Klip Backdrop|Ongkos Jahit', case=False, na=False)]
print(f'\nTotal baris produk non-item: {len(non_items)} baris')

conn.close()
