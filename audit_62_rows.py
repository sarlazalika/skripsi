import sys
import json
import sqlite3
import pandas as pd
from analysis.preprocessor import _parse_date

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

# Ambil 62 baris anomali
anomali = pd.read_sql_query("""
    SELECT c.id, c.session_id, u.filename, c.id_transaksi, c.tanggal, c.produk, c.jumlah
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    WHERE c.tanggal >= '2026-11-01'
    ORDER BY c.session_id, c.id
""", conn)

print(f"Total baris anomali di cleaned_transaksi: {len(anomali)}")

# Untuk setiap baris anomali, cari record di raw_data_temp
raw_records = conn.execute("SELECT session_id, row_index, row_data FROM raw_data_temp").fetchall()
raw_by_session_and_id = {}

for s_id, r_idx, r_data in raw_records:
    try:
        d = json.loads(r_data)
        no_pesanan = str(d.get('No. Pesanan', '')).strip()
        raw_by_session_and_id[(s_id, no_pesanan)] = d
    except:
        pass

audit_list = []
for idx, row in anomali.iterrows():
    s_id = row['session_id']
    id_tr = str(row['id_transaksi']).strip()
    raw_d = raw_by_session_and_id.get((s_id, id_tr))
    
    tgl_db = row['tanggal']
    if raw_d:
        waktu_atur = raw_d.get('Waktu Pengiriman Diatur')
        waktu_buat = raw_d.get('Waktu Pesanan Dibuat')
        waktu_bayar = raw_d.get('Waktu Pembayaran Dilakukan')
        waktu_selesai = raw_d.get('Waktu Pesanan Selesai')
        
        # Cek apa hasil parse jika diparsing sekarang
        parsed_atur = _parse_date(waktu_atur)
        
        audit_list.append({
            'session_id': s_id,
            'filename': row['filename'],
            'id_transaksi': id_tr,
            'tgl_db': tgl_db,
            'waktu_atur_raw': waktu_atur,
            'waktu_buat_raw': waktu_buat,
            'waktu_bayar_raw': waktu_bayar,
            'waktu_selesai_raw': waktu_selesai,
            'parsed_atur_now': parsed_atur,
            'produk': row['produk'],
            'jumlah': row['jumlah']
        })
    else:
        audit_list.append({
            'session_id': s_id,
            'filename': row['filename'],
            'id_transaksi': id_tr,
            'tgl_db': tgl_db,
            'waktu_atur_raw': 'TIDAK_DITEMUKAN_DI_RAW',
            'waktu_buat_raw': None,
            'waktu_bayar_raw': None,
            'waktu_selesai_raw': None,
            'parsed_atur_now': None,
            'produk': row['produk'],
            'jumlah': row['jumlah']
        })

df_audit = pd.DataFrame(audit_list)
print("\nRingkasan Sample 10 baris audit:")
print(df_audit[['session_id', 'filename', 'id_transaksi', 'tgl_db', 'waktu_atur_raw', 'waktu_buat_raw', 'parsed_atur_now']].head(10).to_string())

# Cek berapa yang match di raw
ada_di_raw = df_audit[df_audit['waktu_atur_raw'] != 'TIDAK_DITEMUKAN_DI_RAW']
print(f"\nJumlah baris anomali yang ditemukan di raw_data_temp: {len(ada_di_raw)} dari {len(df_audit)}")

# Cek apakah waktu_atur_raw memang menunjukkan tanggal yang berbeda dengan tgl_db
print("\nBandingkan tgl_db vs waktu_atur_raw:")
for _, r in ada_di_raw.drop_duplicates(subset=['tgl_db', 'waktu_atur_raw']).iterrows():
    print(f"Session {r['session_id']} | tgl_db: {r['tgl_db']} | raw_atur: {r['waktu_atur_raw']} | raw_buat: {r['waktu_buat_raw']} | _parse_date(raw_atur): {r['parsed_atur_now']}")

conn.close()
