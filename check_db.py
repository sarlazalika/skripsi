import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print('=== 1. STATUS TABEL DATASET ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dataset'")
print('Tabel dataset ada:', cursor.fetchone() is not None)

print('\n=== 2. STATUS KOLOM dataset_id DI upload_session ===')
cursor.execute("PRAGMA table_info(upload_session)")
cols = [col[1] for col in cursor.fetchall()]
print('Kolom dataset_id ada:', 'dataset_id' in cols)

print('\n=== 3. DATASET AKTIF ===')
cursor.execute("SELECT * FROM dataset WHERE status='aktif'")
active_dataset = cursor.fetchone()
if active_dataset:
    print(f"ID: {active_dataset[0]}, Nama: {active_dataset[1]}, Status: {active_dataset[2]}, Created: {active_dataset[3]}")
else:
    print('Tidak ada dataset aktif')

if active_dataset:
    print('\n=== 4. DAFTAR SESSION DALAM DATASET AKTIF ===')
    cursor.execute("SELECT id, filename, status FROM upload_session WHERE dataset_id=?", (active_dataset[0],))
    sessions = cursor.fetchall()
    for s in sessions:
        print(s)
        
    print('\n=== 5. JUMLAH CLEANED TRANSAKSI PER SESSION (DI DATASET AKTIF) ===')
    session_ids_all = [s[0] for s in sessions]
    if session_ids_all:
        placeholders_all = ','.join(['?']*len(session_ids_all))
        cursor.execute(f"SELECT session_id, COUNT(*) FROM cleaned_transaksi WHERE session_id IN ({placeholders_all}) GROUP BY session_id", session_ids_all)
        for row in cursor.fetchall():
            print(f"Session {row[0]}: {row[1]} data")
    else:
        print('Tidak ada session di dataset aktif')
        
    session_ids = [s[0] for s in sessions if s[2] == 'Selesai']
    if session_ids:
        placeholders = ','.join(['?']*len(session_ids))
        print('\n=== 6. TOTAL TRANSAKSI YANG DIGUNAKAN DATASET AKTIF ===')
        cursor.execute(f"SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id IN ({placeholders})", session_ids)
        row = cursor.fetchone()
        print(f"{row[0]} data" if row else "0 data")
    else:
        print('\nBelum ada session yang Selesai di dataset aktif.')
else:
    print('\n=== 7. DAFTAR SEMUA SESSION ===')
    cursor.execute("SELECT id, dataset_id, filename, status FROM upload_session")
    for row in cursor.fetchall():
        print(row)

conn.close()
