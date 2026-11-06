import sys
import json
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

# Ambil seluruh 62 baris
df_nov_dec = pd.read_sql_query("""
    SELECT c.id, c.session_id, u.filename, c.id_transaksi, c.tanggal, c.produk, c.jumlah
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    WHERE c.tanggal >= '2026-11-01'
    ORDER BY c.session_id, c.tanggal, c.id
""", conn)

# Ambil raw_data_temp
raw_rows = conn.execute("SELECT session_id, row_data FROM raw_data_temp WHERE session_id IN (1, 3)").fetchall()
raw_dict = {}
for s_id, r_data in raw_rows:
    d = json.loads(r_data)
    raw_dict[(s_id, str(d.get('No. Pesanan', '')).strip())] = d

audit_rows = []
for idx, row in df_nov_dec.iterrows():
    s_id = row['session_id']
    id_tr = str(row['id_transaksi']).strip()
    raw = raw_dict.get((s_id, id_tr))
    
    tgl_db = row['tanggal']
    if raw:
        raw_tgl = raw.get('Waktu Pengiriman Diatur')
        raw_buat = raw.get('Waktu Pesanan Dibuat')
        # Format asli raw_tgl adalah 'YYYY-MM-DD HH:MM' (misal: '2026-02-11 18:09')
        # Tanggal aslinya adalah 10 karakter pertama: '2026-02-11'
        tgl_asli = raw_tgl[:10] if raw_tgl else 'KOSONG'
        status_verifikasi = "Terbukti Salah Parsing" if tgl_asli != tgl_db else "Sesuai"
        rekomendasi = f"Koreksi ke {tgl_asli}"
    else:
        raw_tgl = "Tidak ditemukan di raw_data_temp"
        tgl_asli = "Tidak tersedia"
        status_verifikasi = "Belum Terverifikasi"
        rekomendasi = "Perlu investigasi file fisik"
        
    audit_rows.append({
        'no': idx + 1,
        'session_id': s_id,
        'filename': row['filename'],
        'id_transaksi': id_tr,
        'tgl_db': tgl_db,
        'raw_tgl_full': raw_tgl,
        'tgl_asli': tgl_asli,
        'produk': row['produk'],
        'jumlah': row['jumlah'],
        'status_verifikasi': status_verifikasi,
        'rekomendasi': rekomendasi
    })

df_result = pd.DataFrame(audit_rows)
print(f"Total baris: {len(df_result)}")
print(f"Terbukti Salah Parsing: {(df_result['status_verifikasi'] == 'Terbukti Salah Parsing').sum()}")
print(f"Belum Terverifikasi: {(df_result['status_verifikasi'] == 'Belum Terverifikasi').sum()}")

print("\nDistribusi Per Sesi:")
print(df_result.groupby(['session_id', 'filename', 'status_verifikasi']).size())

print("\nDistribusi Pemetaan Tanggal Database vs Tanggal Asli:")
print(df_result.groupby(['session_id', 'tgl_db', 'tgl_asli']).size())

# Cek apakah ada data di luar 62 baris yang juga terkena dampak inversi (misal 2026-01-02 yang aslinya 2026-02-01)
print("\n" + "="*60)
print("AUDIT POTENSI INVERSI DI SELURUH DATASET:")
print("="*60)

# Cek semua transaksi di cleaned_transaksi vs raw_data_temp
all_clean = pd.read_sql_query("""
    SELECT c.id, c.session_id, c.id_transaksi, c.tanggal, c.produk
    FROM cleaned_transaksi c
""", conn)

all_raw_rows = conn.execute("SELECT session_id, row_data FROM raw_data_temp").fetchall()
all_raw_dict = {}
for s_id, r_data in all_raw_rows:
    d = json.loads(r_data)
    # cari mapping id
    all_raw_dict[(s_id, str(d.get('No. Pesanan', '')).strip())] = d

mismatch_count = 0
mismatch_summary = {}
for _, r in all_clean.iterrows():
    s_id = r['session_id']
    id_tr = str(r['id_transaksi']).strip()
    raw = all_raw_dict.get((s_id, id_tr))
    if raw:
        raw_tgl = raw.get('Waktu Pengiriman Diatur') or raw.get('Waktu Pesanan Dibuat') or raw.get('Tanggal')
        if raw_tgl and len(str(raw_tgl)) >= 10:
            raw_tgl_date = str(raw_tgl)[:10]
            # jika raw_tgl berformat YYYY-MM-DD
            if raw_tgl_date != r['tanggal']:
                mismatch_count += 1
                key = (s_id, r['tanggal'], raw_tgl_date)
                mismatch_summary[key] = mismatch_summary.get(key, 0) + 1

print(f"Total mismatch tanggal di seluruh cleaned_transaksi: {mismatch_count} baris")
print("Ringkasan Mismatch (Session, Tanggal DB, Tanggal Asli di Raw):")
for k, v in sorted(mismatch_summary.items()):
    print(f"  Session {k[0]}: DB={k[1]} -> Asli RAW={k[2]} : {v} baris")

conn.close()
