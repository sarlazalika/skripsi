import sys
import json
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

print("="*60)
print("1. DATA SESI UPLOAD (upload_session):")
print("="*60)
sessions = pd.read_sql_query("SELECT id, filename, upload_time, total_rows, status, dataset_id FROM upload_session", conn)
print(sessions.to_string())

print("\n" + "="*60)
print("2. DATA STATISTIK PEMBERSIHAN (cleaning_stats):")
print("="*60)
c_stats = pd.read_sql_query("SELECT * FROM cleaning_stats", conn)
print(c_stats.to_string())

print("\n" + "="*60)
print("3. ANOMALI TANGGAL >= 2026-11-01 DI cleaned_transaksi:")
print("="*60)
anomali = pd.read_sql_query("""
    SELECT c.session_id, u.filename, count(*) as jml_baris, min(c.tanggal) as tgl_min, max(c.tanggal) as tgl_max
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    WHERE c.tanggal >= '2026-11-01'
    GROUP BY c.session_id, u.filename
""", conn)
print(anomali.to_string())

print("\n" + "="*60)
print("4. TOTAL 62 BARIS ANOMALI DAN PENCOCOKAN DENGAN raw_data_temp:")
print("="*60)
anomali_rows = pd.read_sql_query("""
    SELECT c.id, c.session_id, u.filename, c.id_transaksi, c.tanggal as tgl_cleaned, c.produk, c.jumlah
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    WHERE c.tanggal >= '2026-11-01'
    ORDER BY c.tanggal, c.id
""", conn)
print(f"Total baris anomali ditemukan: {len(anomali_rows)}")

# Cek kolom mapping di session terkait
sess_map = {}
for s_id in anomali_rows['session_id'].unique():
    row = conn.execute("SELECT column_mapping FROM upload_session WHERE id=?", (int(s_id),)).fetchone()
    if row and row[0]:
        sess_map[s_id] = json.loads(row[0])
print("\nColumn mapping per session:")
for s_id, m in sess_map.items():
    print(f"Session {s_id}: {m}")

# Ambil raw_data_temp untuk transaksi-transaksi anomali
# Cari berdasarkan id_transaksi atau session_id
raw_rows = pd.read_sql_query("""
    SELECT session_id, row_index, row_data
    FROM raw_data_temp
    WHERE session_id IN ({})
""".format(','.join(str(s) for s in anomali_rows['session_id'].unique())), conn)

print(f"\nTotal baris raw_data_temp untuk session terkait: {len(raw_rows)}")

# Parse JSON row_data
parsed_raw = []
for idx, r in raw_rows.iterrows():
    try:
        data = json.loads(r['row_data'])
        data['_session_id'] = r['session_id']
        data['_row_index'] = r['row_index']
        parsed_raw.append(data)
    except Exception as e:
        pass

df_raw_parsed = pd.DataFrame(parsed_raw)
print("\nKolom-kolom di raw_data_temp:")
print([col for col in df_raw_parsed.columns if not col.startswith('_')])

# Cari kolom id_transaksi dan kolom tanggal di raw
col_id = sess_map.get(anomali_rows['session_id'].iloc[0], {}).get('id_transaksi')
col_tgl = sess_map.get(anomali_rows['session_id'].iloc[0], {}).get('tanggal')
print(f"\nMapping kolom ID Transaksi: '{col_id}', Kolom Tanggal: '{col_tgl}'")

# Pencocokan antara cleaned_transaksi dan raw_data_temp
match_results = []
for _, crow in anomali_rows.iterrows():
    s_id = crow['session_id']
    id_tr = crow['id_transaksi']
    # Cari di raw
    sub = df_raw_parsed[(df_raw_parsed['_session_id'] == s_id) & (df_raw_parsed[col_id].astype(str) == str(id_tr))]
    if not sub.empty:
        raw_val = sub.iloc[0].get(col_tgl)
        match_results.append({
            'session_id': s_id,
            'filename': crow['filename'],
            'id_transaksi': id_tr,
            'tgl_cleaned': crow['tgl_cleaned'],
            'raw_tgl_val': raw_val,
            'produk': crow['produk'],
            'jumlah': crow['jumlah']
        })
    else:
        match_results.append({
            'session_id': s_id,
            'filename': crow['filename'],
            'id_transaksi': id_tr,
            'tgl_cleaned': crow['tgl_cleaned'],
            'raw_tgl_val': 'NOT_FOUND_IN_RAW',
            'produk': crow['produk'],
            'jumlah': crow['jumlah']
        })

df_match = pd.DataFrame(match_results)
print("\nContoh 20 baris pencocokan:")
print(df_match.head(20).to_string())

print("\nDistribusi nilai raw_tgl_val:")
print(df_match['raw_tgl_val'].value_counts().to_string())

conn.close()
