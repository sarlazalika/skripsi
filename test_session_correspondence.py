import sys
import json
import sqlite3
import pandas as pd
from analysis.preprocessor import clean_data

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

for s_id in [1, 3, 4]:
    # Ambil raw_rows
    raw_rows = conn.execute("SELECT row_index, row_data FROM raw_data_temp WHERE session_id=? ORDER BY row_index ASC", (s_id,)).fetchall()
    records = []
    for r_idx, r_data in raw_rows:
        d = json.loads(r_data)
        d['_orig_row_index'] = r_idx
        records.append(d)
    df_raw = pd.DataFrame(records)
    
    # Ambil mapping
    row_map = conn.execute("SELECT column_mapping FROM upload_session WHERE id=?", (s_id,)).fetchone()
    mapping = json.loads(row_map[0])
    
    # Ambil data cleaned yang tersimpan di DB
    db_clean = pd.read_sql_query("SELECT id, session_id, id_transaksi, tanggal, produk, jumlah FROM cleaned_transaksi WHERE session_id=? ORDER BY id ASC", conn, params=(s_id,))
    
    print(f"\n--- SESSION {s_id} ---")
    print(f"Total raw: {len(df_raw)} baris")
    print(f"Total cleaned di DB: {len(db_clean)} baris")
    
    # Uji verifikasi tanggal asli vs tanggal DB
    # Karena setiap No. Pesanan memiliki tanggal unik:
    raw_dates = {}
    col_id = mapping['id_transaksi']
    col_tgl = mapping['tanggal']
    for _, r in df_raw.iterrows():
        raw_dates[str(r[col_id]).strip()] = str(r[col_tgl]).strip()
        
    mismatches = 0
    matched_all = 0
    for _, crow in db_clean.iterrows():
        id_tr = str(crow['id_transaksi']).strip()
        orig_tgl = raw_dates.get(id_tr)
        if orig_tgl:
            matched_all += 1
            # Tanggal asli yang benar adalah 10 karakter pertama (YYYY-MM-DD)
            tgl_correct = orig_tgl[:10]
            if tgl_correct != crow['tanggal']:
                mismatches += 1
        else:
            print(f"Peringatan: ID {id_tr} tidak ditemukan di raw!")
            
    print(f"Cocok ke raw: {matched_all} dari {len(db_clean)}")
    print(f"Jumlah baris dengan tanggal salah di DB: {mismatches}")

conn.close()
