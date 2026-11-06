import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# LAKUKAN PENGHAPUSAN
conn.execute('DELETE FROM raw_data_temp WHERE session_id = 2')
conn.execute('DELETE FROM cleaned_transaksi WHERE session_id = 2')
conn.execute('DELETE FROM cleaning_stats WHERE session_id = 2')
# Pada upload_session, primary key adalah 'id'
conn.execute('DELETE FROM upload_session WHERE id = 2')
conn.commit()

# VERIFIKASI
sessions = conn.execute('SELECT id, filename, total_rows FROM upload_session').fetchall()

print('=== DAFTAR SESSION YANG TERSISA ===')
total_raw_all = 0
total_clean_all = 0

for s in sessions:
    s_id = s['id']
    stats = conn.execute('SELECT total_clean FROM cleaning_stats WHERE session_id = ?', (s_id,)).fetchone()
    
    clean_val = 0
    if stats:
        if isinstance(stats['total_clean'], bytes):
            clean_val = int.from_bytes(stats['total_clean'], 'little')
        else:
            clean_val = int(stats['total_clean'] or 0)
    
    total_raw_all += s['total_rows']
    total_clean_all += clean_val
    
    print(f"- Session {s_id} | {s['filename']} | Raw: {s['total_rows']} | Clean: {clean_val}")

print('\n=== TOTAL KESELURUHAN ===')
print(f'Total Raw: {total_raw_all}')
print(f'Total Cleaned: {total_clean_all}')

conn.close()
