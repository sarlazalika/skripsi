import sys
import json
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

# Ambil 62 baris anomali
anomali = pd.read_sql_query("""
    SELECT c.id as clean_id, c.session_id, u.filename, c.id_transaksi, c.tanggal as tgl_db, c.produk, c.jumlah
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    WHERE c.tanggal >= '2026-11-01'
    ORDER BY c.session_id, c.tanggal, c.id
""", conn)

# Ambil raw
raw_records = conn.execute("SELECT session_id, row_data FROM raw_data_temp WHERE session_id IN (1, 3)").fetchall()
raw_dict = {}
for s_id, r_data in raw_records:
    d = json.loads(r_data)
    no_p = str(d.get('No. Pesanan', '')).strip()
    raw_dict[(s_id, no_p)] = d

table_data = []
for idx, r in anomali.iterrows():
    s_id = r['session_id']
    id_tr = str(r['id_transaksi']).strip()
    raw_item = raw_dict.get((s_id, id_tr))
    
    if raw_item:
        raw_val = raw_item.get('Waktu Pengiriman Diatur')
        tgl_asli = raw_val[:10] if raw_val else 'KOSONG'
        status = "Terbukti Salah Parsing" if tgl_asli != r['tgl_db'] else "Sesuai"
        rekomendasi = f"Koreksi ke {tgl_asli}"
    else:
        raw_val = "Tidak ada"
        tgl_asli = "Tidak tersedia"
        status = "Belum Terverifikasi"
        rekomendasi = "Perlu investigasi file fisik"
        
    table_data.append({
        'no': idx + 1,
        'session_id': s_id,
        'filename': r['filename'],
        'id_transaksi': id_tr,
        'tgl_db': r['tgl_db'],
        'raw_val': raw_val,
        'tgl_asli': tgl_asli,
        'status': status,
        'rekomendasi': rekomendasi
    })

df_table = pd.DataFrame(table_data)
print(f"Total rows in table: {len(df_table)}")
print("Status counts:")
print(df_table['status'].value_counts())

# Kelompokkan pola koreksi
print("\nPola Pemetaan Tanggal:")
print(df_table.groupby(['session_id', 'filename', 'tgl_db', 'tgl_asli', 'status', 'rekomendasi']).size())

conn.close()
