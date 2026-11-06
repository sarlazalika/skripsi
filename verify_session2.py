import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# 1 & 2: Cek filename Session 1 dan 2
sess1 = conn.execute('SELECT id, filename, total_rows, status FROM upload_session WHERE id = 1').fetchone()
sess2 = conn.execute('SELECT id, filename, total_rows, status FROM upload_session WHERE id = 2').fetchone()

print('=== VERIFIKASI SESSION ===')
if sess1:
    print(f'Session 1: {sess1["filename"]} (Raw: {sess1["total_rows"]})')
if sess2:
    print(f'Session 2: {sess2["filename"]} (Raw: {sess2["total_rows"]})')

print('\n=== DAFTAR TABEL & JUMLAH BARIS DENGAN SESSION_ID = 2 ===')
tables_to_check = ['upload_session', 'cleaning_stats', 'cleaned_transaksi', 'raw_data_temp']
for table in tables_to_check:
    try:
        col = 'id' if table == 'upload_session' else 'session_id'
        count = conn.execute(f'SELECT COUNT(*) FROM {table} WHERE {col} = 2').fetchone()[0]
        print(f'- Tabel `{table}`: {count} baris')
    except Exception as e:
        print(f'- Tabel `{table}`: Error ({e})')

try:
    cols = [info['name'] for info in conn.execute('PRAGMA table_info(transaksi)').fetchall()]
    if 'session_id' in cols:
        count = conn.execute('SELECT COUNT(*) FROM transaksi WHERE session_id = 2').fetchone()[0]
        print(f'- Tabel `transaksi`: {count} baris terkait session_id=2')
    else:
        print('- Tabel `transaksi`: Tidak memiliki kolom session_id (aman)')
except Exception as e:
    pass

print('\n=== RINCIAN DATA SESSION 2 YANG AKAN DIHAPUS ===')
if sess2:
    stats2 = conn.execute('SELECT * FROM cleaning_stats WHERE session_id = 2').fetchone()
    if stats2:
        valid = int(stats2['total_clean'] or 0)
        batal = int.from_bytes(stats2['total_batal'], 'little') if isinstance(stats2['total_batal'], bytes) else int(stats2['total_batal'] or 0)
        invalid = int.from_bytes(stats2['total_invalid'], 'little') if isinstance(stats2['total_invalid'], bytes) else int(stats2['total_invalid'] or 0)
        print(f'1. [upload_session] ID=2, filename={sess2["filename"]}')
        print(f'2. [cleaning_stats] Valid: {valid}, Batal: {batal}, Invalid: {invalid}')
    
    clean_count = conn.execute('SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id = 2').fetchone()[0]
    print(f'3. [cleaned_transaksi] Akan menghapus {clean_count} baris')
    
    raw_count = conn.execute('SELECT COUNT(*) FROM raw_data_temp WHERE session_id = 2').fetchone()[0]
    print(f'4. [raw_data_temp] Akan menghapus {raw_count} baris')

conn.close()
