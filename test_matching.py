import sys
import json
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

# Cek struktur cleaned_transaksi
clean_df = pd.read_sql_query("SELECT id, session_id, id_transaksi, tanggal, produk, jumlah FROM cleaned_transaksi ORDER BY session_id, id", conn)
print(f"Total baris cleaned_transaksi: {len(clean_df)}")

# Cek raw_data_temp
raw_rows = conn.execute("SELECT session_id, row_index, row_data FROM raw_data_temp ORDER BY session_id, row_index").fetchall()
print(f"Total baris raw_data_temp: {len(raw_rows)}")

# Ambil mapping kolom per session
sess_mapping = {}
for s_id in clean_df['session_id'].unique():
    r = conn.execute("SELECT column_mapping FROM upload_session WHERE id=?", (int(s_id),)).fetchone()
    sess_mapping[s_id] = json.loads(r[0]) if r and r[0] else {}

print("Mapping per session:", sess_mapping)

# Buat list baris raw terurai
parsed_raw = []
for s_id, r_idx, r_data in raw_rows:
    d = json.loads(r_data)
    m = sess_mapping.get(s_id, {})
    col_id = m.get('id_transaksi', 'No. Pesanan')
    col_tgl = m.get('tanggal', 'Waktu Pengiriman Diatur')
    col_prod = m.get('produk', 'Nama Produk')
    col_qty = m.get('jumlah', 'Jumlah')
    col_status = m.get('status', 'Status Pesanan')
    
    parsed_raw.append({
        'session_id': s_id,
        'row_index': r_idx,
        'id_transaksi': str(d.get(col_id, '')).strip(),
        'tanggal_raw': str(d.get(col_tgl, '')).strip(),
        'produk': str(d.get(col_prod, '')).strip(),
        'jumlah': d.get(col_qty),
        'status': d.get(col_status)
    })

raw_df = pd.DataFrame(parsed_raw)
print(f"Parsed raw count: {len(raw_df)}")

# Uji keunikan kecocokan:
# Untuk setiap baris di cleaned_transaksi, cari baris pasangannya di raw_df:
# Kriteria pencocokan: session_id, id_transaksi, produk, jumlah (int)
# Perhatikan: jika dalam 1 pesanan ada beberapa produk yang SAMA persis, kita harus pastikan 1-to-1 matching!

clean_matched = 0
clean_unmatched = 0
clean_ambiguous = 0

# Kita lacak baris raw yang sudah dipasangkan agar 1-to-1 strictly terjaga
used_raw_indices = set()

match_records = []
for _, crow in clean_df.iterrows():
    c_id = crow['id']
    s_id = crow['session_id']
    id_tr = str(crow['id_transaksi']).strip()
    prod = str(crow['produk']).strip()
    qty = int(crow['jumlah'])
    
    # Cari kandidat di raw yang belum terpakai
    candidates = raw_df[
        (raw_df['session_id'] == s_id) &
        (raw_df['id_transaksi'] == id_tr) &
        (raw_df['produk'] == prod) &
        (~raw_df['row_index'].isin(used_raw_indices))
    ]
    
    # Jika jumlah match sama persis
    if not candidates.empty:
        # Filter juga berdasarkan jumlah qty jika valid
        qty_matches = candidates[pd.to_numeric(candidates['jumlah'], errors='coerce') == qty]
        if not qty_matches.empty:
            chosen = qty_matches.iloc[0]
        else:
            chosen = candidates.iloc[0]
            
        used_raw_indices.add(chosen['row_index'])
        clean_matched += 1
        match_records.append({
            'clean_id': c_id,
            'session_id': s_id,
            'id_transaksi': id_tr,
            'produk': prod,
            'jumlah': qty,
            'tgl_db': crow['tanggal'],
            'raw_tgl': chosen['tanggal_raw'],
            'raw_row_index': chosen['row_index']
        })
    else:
        clean_unmatched += 1

print(f"Hasil pencocokan 1-to-1:")
print(f"  Matched: {clean_matched} dari {len(clean_df)}")
print(f"  Unmatched: {clean_unmatched}")

# Cek apakah tanggal raw valid dan bisa diparsing
df_matches = pd.DataFrame(match_records)
df_matches['tgl_asli_parsed'] = df_matches['raw_tgl'].str[:10]

mismatches = df_matches[df_matches['tgl_db'] != df_matches['tgl_asli_parsed']]
print(f"\nJumlah baris yang tanggal DB berbeda dengan tanggal asli raw: {len(mismatches)}")
print("\nDistribusi Mismatch per Sesi:")
print(mismatches.groupby(['session_id', 'tgl_db', 'tgl_asli_parsed']).size().to_string())

conn.close()
