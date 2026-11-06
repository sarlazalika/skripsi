import sys
import json
import sqlite3
import pandas as pd
from analysis.preprocessor import _parse_date

sys.stdout.reconfigure(encoding='utf-8')

backup_file = 'database_backup_before_date_fix.db'
db_file = 'database.db'

# 1. Verifikasi backup sebelum mulai
print("1. Verifikasi ketersediaan backup...")
chk = sqlite3.connect(backup_file)
b_cnt = chk.execute("SELECT COUNT(*) FROM cleaned_transaksi").fetchone()[0]
chk.close()
assert b_cnt == 1779, f"Backup tidak valid: jumlah baris cleaned_transaksi = {b_cnt}"
print("   -> Backup valid dan siap.")

# 2. Hubungkan ke database utama
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Cek kondisi awal
initial_clean_count = cursor.execute("SELECT COUNT(*) FROM cleaned_transaksi").fetchone()[0]
initial_manual_count = cursor.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
print(f"2. Kondisi Awal: cleaned_transaksi = {initial_clean_count}, transaksi manual = {initial_manual_count}")

# 3. Kumpulkan seluruh data raw dan mapping per session
session_mappings = {}
session_raw_dates = {}

for s_id in [1, 3, 4]:
    r_map = cursor.execute("SELECT column_mapping FROM upload_session WHERE id=?", (s_id,)).fetchone()
    mapping = json.loads(r_map[0])
    session_mappings[s_id] = mapping
    
    col_id = mapping['id_transaksi']
    col_tgl = mapping['tanggal']
    
    raw_rows = cursor.execute("SELECT row_index, row_data FROM raw_data_temp WHERE session_id=?", (s_id,)).fetchall()
    
    # Simpan tanggal per (session_id, id_transaksi)
    # Sekaligus verifikasi tidak ada ambiguitas tanggal dalam satu pesanan
    order_dates = {}
    for r_idx, r_json in raw_rows:
        d = json.loads(r_json)
        no_p = str(d.get(col_id, '')).strip()
        raw_val = d.get(col_tgl)
        if not raw_val:
            raw_val = d.get('Waktu Pesanan Dibuat')
            
        if no_p:
            if no_p in order_dates and order_dates[no_p] != raw_val:
                raise ValueError(f"Ambiguitas ditemukan! Sesi {s_id}, No Pesanan {no_p} memiliki lebih dari 1 tanggal: {order_dates[no_p]} vs {raw_val}")
            order_dates[no_p] = raw_val
            
    session_raw_dates[s_id] = order_dates

print("3. Verifikasi keunikan tanggal sumber per pesanan: 100% UNIK (0 ambiguitas).")

# 4. Identifikasi baris yang perlu diperbarui
clean_rows = cursor.execute("SELECT id, session_id, id_transaksi, tanggal, produk, jumlah FROM cleaned_transaksi ORDER BY id ASC").fetchall()

updates_to_make = []
unchanged_count = 0

for c_id, s_id, id_tr, tgl_db, prod, qty in clean_rows:
    id_tr_clean = str(id_tr).strip()
    raw_date_val = session_raw_dates.get(s_id, {}).get(id_tr_clean)
    
    if raw_date_val is None:
        raise ValueError(f"Baris id={c_id} (Sesi {s_id}, Order {id_tr_clean}) tidak ditemukan di raw_data_temp!")
        
    tgl_parsed = _parse_date(raw_date_val)
    if not tgl_parsed:
        raise ValueError(f"Tanggal raw '{raw_date_val}' pada baris id={c_id} gagal diparsing!")
        
    if tgl_parsed != tgl_db:
        updates_to_make.append((tgl_parsed, c_id))
    else:
        unchanged_count += 1

print(f"4. Analisis Rencana Koreksi:")
print(f"   - Total baris yang harus dikoreksi: {len(updates_to_make)}")
print(f"   - Total baris yang tidak berubah: {unchanged_count}")
print(f"   - Total keseluruhan: {len(updates_to_make) + unchanged_count} (harus = {initial_clean_count})")
assert len(updates_to_make) == 917, f"Ekspektasi baris koreksi adalah 917, tetapi didapat {len(updates_to_make)}!"
assert len(updates_to_make) + unchanged_count == initial_clean_count, "Jumlah baris tidak konsisten!"

# 5. Eksekusi Koreksi Dalam Transaksi Database
print("5. Menjalankan transaksi pembaruan dengan ROLLBACK protection...")
try:
    cursor.execute("BEGIN TRANSACTION")
    
    # Jalankan update baris demi baris hanya untuk kolom tanggal
    cursor.executemany("UPDATE cleaned_transaksi SET tanggal = ? WHERE id = ?", updates_to_make)
    
    # Verifikasi integritas pasca-update sebelum commit
    post_clean_count = cursor.execute("SELECT COUNT(*) FROM cleaned_transaksi").fetchone()[0]
    post_manual_count = cursor.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
    
    if post_clean_count != initial_clean_count:
        raise RuntimeError(f"Rollback! Jumlah baris cleaned_transaksi berubah: {post_clean_count} != {initial_clean_count}")
        
    if post_manual_count != initial_manual_count:
        raise RuntimeError(f"Rollback! Tabel transaksi manual berubah: {post_manual_count} != {initial_manual_count}")
        
    # Cek apakah masih ada baris yang bertanggal di atas rentang riil (misal > 2026-05-01)
    future_count = cursor.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE tanggal >= '2026-11-01'").fetchone()[0]
    if future_count > 0:
        raise RuntimeError(f"Rollback! Masih ada {future_count} baris future dates tersisa!")
        
    conn.commit()
    print("   -> COMMIT BERHASIL: 917 baris tanggal berhasil dikoreksi dengan aman.")
except Exception as e:
    conn.rollback()
    print(f"   -> TERJADI KESALAHAN! Transaksi di-ROLLBACK: {e}")
    conn.close()
    sys.exit(1)

conn.close()
print("PROSES KOREKSI DATABASE SELESAI DENGAN SUKSES.")
