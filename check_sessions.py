import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# 1 & 2. Upload sessions
sessions = conn.execute("SELECT id, filename, upload_time, total_rows, status FROM upload_session ORDER BY id ASC").fetchall()
print(f"=== UPLOAD SESSION: {len(sessions)} record ===")
for s in sessions:
    print(f"  session_id={s['id']} | file={s['filename']} | upload={s['upload_time']} | rows={s['total_rows']} | status={s['status']}")

# 3. Apakah setiap upload punya session_id berbeda? (tampilkan id unik)
ids = [s['id'] for s in sessions]
print(f"\n=== KEUNIKAN SESSION ID ===")
print(f"  Semua session_id: {ids}")
print(f"  Unik: {len(set(ids)) == len(ids)} ({'Ya, semua berbeda' if len(set(ids)) == len(ids) else 'TIDAK, ada duplikasi'})")

# 4. Data per session di cleaned_transaksi
print(f"\n=== CLEANED_TRANSAKSI PER SESSION ===")
cleaned = conn.execute("SELECT session_id, COUNT(*) as cnt FROM cleaned_transaksi GROUP BY session_id ORDER BY session_id ASC").fetchall()
if cleaned:
    for c in cleaned:
        print(f"  session_id={c['session_id']} | cleaned_rows={c['cnt']}")
else:
    print("  (kosong - belum ada data cleaned)")

# 5. Active session
active = conn.execute("SELECT id, filename, total_rows FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1").fetchone()
print(f"\n=== ACTIVE SESSION (Dashboard/MA/Apriori) ===")
if active:
    cleaned_count = conn.execute("SELECT COUNT(*) FROM cleaned_transaksi WHERE session_id=?", (active['id'],)).fetchone()[0]
    print(f"  session_id={active['id']} | file={active['filename']} | cleaned_rows={cleaned_count}")
else:
    print("  Tidak ada session aktif (belum ada yang status='cleaned')")

conn.close()
