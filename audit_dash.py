import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# Ambil dataset_id aktif
dataset = conn.execute("SELECT id FROM dataset WHERE status='aktif' ORDER BY id DESC LIMIT 1").fetchone()
dataset_id = dataset['id']

# Ambil session yang tergabung
sessions = conn.execute("SELECT id, filename, total_rows FROM upload_session WHERE dataset_id=? AND status='cleaned'", (dataset_id,)).fetchall()

print(f'Active Dataset ID: {dataset_id}')
print('Sessions in Dataset:')
for s in sessions:
    s_id = s['id']
    stats = conn.execute("SELECT * FROM cleaning_stats WHERE session_id=?", (s_id,)).fetchone()
    
    if stats:
        batal = 0
        invalid = 0
        if stats['total_clean']:
            valid = int(stats['total_clean'])
        if isinstance(stats['total_batal'], bytes): batal = int.from_bytes(stats['total_batal'], 'little')
        elif stats['total_batal']: batal = int(stats['total_batal'])
        if isinstance(stats['total_invalid'], bytes): invalid = int.from_bytes(stats['total_invalid'], 'little')
        elif stats['total_invalid']: invalid = int(stats['total_invalid'])
        
        print(f"- Session {s_id} | {s['filename']} | Raw: {s['total_rows']} | Valid: {valid} | Batal: {batal} | Invalid: {invalid}")
    else:
        print(f"- Session {s_id} | {s['filename']} | Raw: {s['total_rows']} | No Stats Found")

conn.close()
