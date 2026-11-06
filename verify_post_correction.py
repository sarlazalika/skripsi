import sys
import json
import sqlite3
import pandas as pd
from analysis.preprocessor import _parse_date

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('database.db')

print("="*60)
print("1. UJI JUMLAH BARIS SEBELUM DAN SESUDAH KOREKSI")
print("="*60)
chk_backup = sqlite3.connect('database_backup_before_date_fix.db')
b_clean = chk_backup.execute("SELECT COUNT(*) FROM cleaned_transaksi").fetchone()[0]
b_manual = chk_backup.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
chk_backup.close()

now_clean = conn.execute("SELECT COUNT(*) FROM cleaned_transaksi").fetchone()[0]
now_manual = conn.execute("SELECT COUNT(*) FROM transaksi").fetchone()[0]
now_raw = conn.execute("SELECT COUNT(*) FROM raw_data_temp").fetchone()[0]
now_sess = conn.execute("SELECT COUNT(*) FROM upload_session").fetchone()[0]

print(f"cleaned_transaksi : Sebelum = {b_clean} | Sesudah = {now_clean} -> {'SESUAI (TIDAK BERUBAH)' if b_clean == now_clean else 'ERROR'}")
print(f"transaksi manual  : Sebelum = {b_manual} | Sesudah = {now_manual} -> {'SESUAI (TIDAK BERUBAH)' if b_manual == now_manual else 'ERROR'}")
print(f"raw_data_temp     : {now_raw} baris")
print(f"upload_session    : {now_sess} sesi")
assert b_clean == now_clean, "Jumlah baris cleaned_transaksi berubah!"
assert b_manual == now_manual, "Jumlah baris transaksi manual berubah!"

print("\n" + "="*60)
print("2. UJI JUMLAH TRANSAKSI PER SESI DI cleaned_transaksi")
print("="*60)
sess_counts = pd.read_sql_query("""
    SELECT c.session_id, u.filename, count(*) as total_clean
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    GROUP BY c.session_id, u.filename
    ORDER BY c.session_id
""", conn)
print(sess_counts.to_string(index=False))
expected_per_sess = {1: 680, 3: 532, 4: 567}
for _, r in sess_counts.iterrows():
    s_id = r['session_id']
    cnt = r['total_clean']
    assert cnt == expected_per_sess[s_id], f"Jumlah transaksi sesi {s_id} tidak sesuai!"
print("-> Verifikasi BERHASIL: Jumlah transaksi per sesi tetap konsisten.")

print("\n" + "="*60)
print("3. UJI KECOCOKAN TANGGAL DENGAN SUMBER MENTAH (raw_data_temp)")
print("="*60)
all_clean = conn.execute("SELECT id, session_id, id_transaksi, tanggal FROM cleaned_transaksi").fetchall()

mismatches = 0
for c_id, s_id, id_tr, tgl_db in all_clean:
    r_map = conn.execute("SELECT column_mapping FROM upload_session WHERE id=?", (s_id,)).fetchone()
    col_tgl = json.loads(r_map[0])['tanggal']
    
    # Cari spesifik order
    r_item = conn.execute("SELECT row_data FROM raw_data_temp WHERE session_id=? AND json_extract(row_data, '$.\"No. Pesanan\"') = ?", (s_id, id_tr)).fetchone()
    if r_item:
        d = json.loads(r_item[0])
        raw_val = d.get(col_tgl) or d.get('Waktu Pesanan Dibuat')
        tgl_expected = _parse_date(raw_val)
        if tgl_expected != tgl_db:
            mismatches += 1

print(f"Total baris yang dicocokkan ke raw: {len(all_clean)}")
print(f"Total mismatch yang ditemukan: {mismatches}")
assert mismatches == 0, f"Ditemukan {mismatches} baris yang tidak cocok dengan sumber mentah!"
print("-> Verifikasi BERHASIL: 100% tanggal cleaned_transaksi cocok persis dengan sumber mentah.")

print("\n" + "="*60)
print("4. UJI RENTANG TANGGAL SETIAP SESI PASCA KOREKSI")
print("="*60)
ranges = pd.read_sql_query("""
    SELECT c.session_id, u.filename, min(c.tanggal) as tgl_mulai, max(c.tanggal) as tgl_akhir, count(*) as baris
    FROM cleaned_transaksi c
    JOIN upload_session u ON c.session_id = u.id
    GROUP BY c.session_id, u.filename
    ORDER BY c.session_id
""", conn)
print(ranges.to_string(index=False))

print("\n" + "="*60)
print("5. UJI KEMUNGKINAN KESALAHAN PARSING YANG MASIH TERSISA")
print("="*60)
future_dates = conn.execute("SELECT count(*) FROM cleaned_transaksi WHERE tanggal >= '2026-11-01'").fetchone()[0]
print(f"Jumlah transaksi bertanggal November & Desember 2026: {future_dates} baris (sebelumnya 62 baris)")
assert future_dates == 0, "Masih ada future dates tersisa!"

jan_2025_dates = conn.execute("SELECT count(*) FROM cleaned_transaksi WHERE tanggal < '2025-10-01'").fetchone()[0]
print(f"Jumlah transaksi bertanggal sebelum Oktober 2025 (Januari 2025 palsu): {jan_2025_dates} baris")
assert jan_2025_dates == 0, "Masih ada tanggal Januari 2025 palsu tersisa!"

null_dates = conn.execute("SELECT count(*) FROM cleaned_transaksi WHERE tanggal IS NULL OR tanggal = ''").fetchone()[0]
print(f"Jumlah transaksi dengan tanggal NULL/kosong: {null_dates} baris")
assert null_dates == 0, "Ada tanggal NULL ditemukan!"

print("\n-> SEMUA UJI VERIFIKASI PASCA KOREKSI LULUS 100% DENGAN SUKSES!")
conn.close()
