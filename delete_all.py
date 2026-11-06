import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

tables = ['transaksi', 'cleaned_transaksi', 'upload_session', 'cleaning_stats', 'raw_data_temp']
for t in tables:
    c.execute(f'DELETE FROM {t}')
    c.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")

conn.commit()

for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t}')
    count = c.fetchone()[0]
    print(f"{t}: {count}")

conn.close()
